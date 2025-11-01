from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from data_pipeline.config import RAG_CONFIG, DOMAIN_KEYWORDS

class AdvancedRetriever:
    """
    Multi-stage retrieval with BM25, dense retrieval, and Reciprocal Rank Fusion
    """
    
    def __init__(self, vector_store: FAISS, all_documents: List[Document]):
        self.vector_store = vector_store
        self.all_documents = all_documents
        self.config = RAG_CONFIG
        
        # Build BM25 index
        self.bm25_index = self._build_bm25_index()
        print(f"BM25 index built with {len(all_documents)} documents")
    
    def _build_bm25_index(self) -> BM25Okapi:
        """Build BM25 sparse retrieval index"""
        tokenized_corpus = [
            doc.page_content.lower().split() 
            for doc in self.all_documents
        ]
        return BM25Okapi(tokenized_corpus)
    
    def dense_retrieval(self, query: str, k: int = 50) -> List[Tuple[Document, float]]:
        """Dense retrieval using vector similarity"""
        results = self.vector_store.similarity_search_with_score(query, k=k)
        
        # FAISS returns (doc, distance), convert distance to similarity
        # Lower distance = higher similarity
        results_with_similarity = [
            (doc, 1 / (1 + distance)) for doc, distance in results
        ]
        
        return results_with_similarity
    
    def sparse_retrieval(self, query: str, k: int = 50) -> List[Tuple[Document, float]]:
        """Sparse retrieval using BM25"""
        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = [
            (self.all_documents[idx], scores[idx])
            for idx in top_indices
            if scores[idx] > 0  # Only include non-zero scores
        ]
        
        return results
    
    def metadata_filtering(
        self, 
        documents: List[Document], 
        entities: Dict[str, List[str]]
    ) -> List[Document]:
        """Filter documents based on extracted entities"""
        
        if not any(entities.values()):
            return documents
        
        filtered = []
        
        for doc in documents:
            content_lower = doc.page_content.lower()
            metadata_str = str(doc.metadata).lower()
            
            # Check for entity matches
            matches = 0
            
            # Crop matches
            if entities.get('crops'):
                for crop in entities['crops']:
                    if crop in content_lower or crop in metadata_str:
                        matches += 1
                        break
            
            # State matches
            if entities.get('states'):
                for state in entities['states']:
                    if state in content_lower or state in metadata_str:
                        matches += 1
                        break
            
            # Metric matches
            if entities.get('metrics'):
                for metric in entities['metrics']:
                    if metric in content_lower:
                        matches += 1
                        break
            
            # Include document if it has any entity matches or if no specific entities
            if matches > 0 or not (entities['crops'] or entities['states']):
                filtered.append(doc)
        
        return filtered if filtered else documents
    
    def reciprocal_rank_fusion(
        self,
        ranked_lists: List[List[Tuple[Document, float]]],
        k: int = 60
    ) -> List[Tuple[Document, float]]:
        """
        Combine multiple ranked lists using Reciprocal Rank Fusion (RRF)
        RRF score = sum(1 / (k + rank)) for each list
        """
        
        # Create document to score mapping
        doc_scores = defaultdict(float)
        doc_objects = {}
        
        for ranked_list in ranked_lists:
            for rank, (doc, _) in enumerate(ranked_list, start=1):
                # Use page_content as unique identifier
                doc_id = doc.page_content
                doc_scores[doc_id] += 1.0 / (k + rank)
                doc_objects[doc_id] = doc
        
        # Sort by RRF score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return documents with their RRF scores
        results = [
            (doc_objects[doc_id], score)
            for doc_id, score in sorted_docs
        ]
        
        return results
    
    def compute_metadata_relevance(
        self, 
        doc: Document, 
        entities: Dict[str, List[str]]
    ) -> float:
        """Compute relevance score based on metadata matches"""
        
        score = 0.0
        content_lower = doc.page_content.lower()
        metadata_str = str(doc.metadata).lower()
        
        # Crop relevance
        if entities.get('crops'):
            crop_matches = sum(
                1 for crop in entities['crops'] 
                if crop in content_lower or crop in metadata_str
            )
            score += crop_matches * 0.3
        
        # State relevance
        if entities.get('states'):
            state_matches = sum(
                1 for state in entities['states']
                if state in content_lower or state in metadata_str
            )
            score += state_matches * 0.3
        
        # Metric relevance
        if entities.get('metrics'):
            metric_matches = sum(
                1 for metric in entities['metrics']
                if metric in content_lower
            )
            score += metric_matches * 0.2
        
        # Category bonus
        category = doc.metadata.get('category', '')
        if entities.get('climate_terms') and category == 'climate':
            score += 0.2
        elif entities.get('crops') and category == 'agriculture':
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def multi_stage_retrieval(
        self,
        queries: List[str],
        entities: Dict[str, List[str]],
        category: Optional[str] = None
    ) -> List[Document]:
        """
        Main retrieval method with multiple stages:
        1. Broad retrieval (dense + sparse for each query)
        2. Fusion with RRF
        3. Metadata filtering
        4. Return top-k documents
        """
        
        print(f"Stage 1: Broad retrieval for {len(queries)} query variations")
        
        # Stage 1: Retrieve with each query using both dense and sparse
        all_ranked_lists = []
        
        for query in queries[:3]:  # Limit to top 3 queries to avoid over-retrieval
            # Dense retrieval
            dense_results = self.dense_retrieval(
                query, 
                k=self.config["initial_retrieval_k"]
            )
            all_ranked_lists.append(dense_results)
            
            # Sparse retrieval
            sparse_results = self.sparse_retrieval(
                query,
                k=self.config["initial_retrieval_k"]
            )
            all_ranked_lists.append(sparse_results)
        
        print(f"Stage 2: Fusion - combining {len(all_ranked_lists)} ranked lists")
        
        # Stage 2: Fusion with RRF
        fused_results = self.reciprocal_rank_fusion(all_ranked_lists)
        
        # Extract documents
        fused_docs = [doc for doc, _ in fused_results[:self.config["post_fusion_k"]]]
        
        print(f"Stage 3: Metadata filtering from {len(fused_docs)} candidates")
        
        # Stage 3: Metadata filtering
        filtered_docs = self.metadata_filtering(fused_docs, entities)
        
        # Apply category filter if specified
        if category:
            filtered_docs = [
                doc for doc in filtered_docs 
                if doc.metadata.get('category') == category
            ]
        
        print(f"Stage 4: Final ranking - {len(filtered_docs)} documents")
        
        # Stage 4: Re-rank with combined scoring
        scored_docs = []
        for doc in filtered_docs:
            # Get original RRF score
            rrf_score = next(
                (score for d, score in fused_results if d.page_content == doc.page_content),
                0.0
            )
            
            # Compute metadata relevance
            metadata_score = self.compute_metadata_relevance(doc, entities)
            
            # Combined score
            final_score = (
                self.config["dense_weight"] * rrf_score +
                self.config["metadata_weight"] * metadata_score
            )
            
            scored_docs.append((doc, final_score))
        
        # Sort by final score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top documents (before reranking stage)
        top_docs = [doc for doc, _ in scored_docs[:self.config["post_rerank_k"]]]
        
        print(f"Retrieved {len(top_docs)} documents for reranking")
        return top_docs
    
    def retrieve(
        self,
        query: str,
        entities: Dict[str, List[str]] = None,
        category: Optional[str] = None
    ) -> List[Document]:
        """
        Simple retrieval method for single query
        """
        entities = entities or {}
        return self.multi_stage_retrieval([query], entities, category)