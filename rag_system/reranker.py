from typing import List, Tuple
import numpy as np
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from sklearn.metrics.pairwise import cosine_similarity
from data_pipeline.config import RAG_CONFIG

class AdvancedReranker:
    """
    Reranking with Cross-Encoder and MMR for diversity
    """
    
    def __init__(self):
        self.config = RAG_CONFIG
        
        # Load cross-encoder model
        print(f"Loading cross-encoder: {self.config['cross_encoder_model']}")
        self.cross_encoder = CrossEncoder(self.config['cross_encoder_model'])
        print("Cross-encoder loaded successfully")
    
    def cross_encoder_rerank(
        self, 
        query: str, 
        documents: List[Document], 
        top_k: int = None
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents using cross-encoder
        Cross-encoders jointly encode query and document for better relevance
        """
        
        if not documents:
            return []
        
        top_k = top_k or self.config["post_rerank_k"]
        
        # Prepare query-document pairs
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Get relevance scores
        scores = self.cross_encoder.predict(pairs)
        
        # Sort by score
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return doc_score_pairs[:top_k]
    
    def compute_document_embeddings(
        self, 
        documents: List[Document]
    ) -> np.ndarray:
        """
        Compute simple embeddings for MMR
        Using TF-IDF style approach for efficiency
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        texts = [doc.page_content for doc in documents]
        vectorizer = TfidfVectorizer(max_features=100)
        
        try:
            embeddings = vectorizer.fit_transform(texts).toarray()
            return embeddings
        except:
            # Fallback: return random embeddings if TF-IDF fails
            return np.random.rand(len(documents), 100)
    
    def maximal_marginal_relevance(
        self,
        query: str,
        documents: List[Document],
        relevance_scores: List[float],
        lambda_param: float = None,
        top_k: int = None
    ) -> List[Document]:
        """
        MMR: Balance relevance and diversity
        MMR = λ * Relevance(D, Q) - (1-λ) * max Similarity(D, D_selected)
        """
        
        if not documents:
            return []
        
        lambda_param = lambda_param or self.config["mmr_lambda"]
        top_k = top_k or self.config["final_context_k"]
        
        # Compute document embeddings for diversity calculation
        doc_embeddings = self.compute_document_embeddings(documents)
        
        # Normalize relevance scores to [0, 1]
        max_score = max(relevance_scores) if relevance_scores else 1.0
        min_score = min(relevance_scores) if relevance_scores else 0.0
        score_range = max_score - min_score if max_score > min_score else 1.0
        
        normalized_scores = [
            (score - min_score) / score_range 
            for score in relevance_scores
        ]
        
        # Initialize
        selected_indices = []
        remaining_indices = list(range(len(documents)))
        
        # Select first document (highest relevance)
        first_idx = np.argmax(normalized_scores)
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # Iteratively select documents
        while len(selected_indices) < top_k and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance score
                relevance = normalized_scores[idx]
                
                # Max similarity to already selected documents
                similarities = []
                for selected_idx in selected_indices:
                    sim = cosine_similarity(
                        doc_embeddings[idx].reshape(1, -1),
                        doc_embeddings[selected_idx].reshape(1, -1)
                    )[0, 0]
                    similarities.append(sim)
                
                max_similarity = max(similarities) if similarities else 0.0
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                mmr_scores.append((idx, mmr_score))
            
            # Select document with highest MMR score
            best_idx, _ = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Return selected documents in order of selection
        return [documents[idx] for idx in selected_indices]
    
    def rerank_and_diversify(
        self,
        query: str,
        documents: List[Document],
        apply_mmr: bool = True
    ) -> List[Document]:
        """
        Main reranking method:
        1. Cross-encoder reranking for relevance
        2. MMR for diversity (optional)
        """
        
        if not documents:
            return []
        
        print(f"Reranking {len(documents)} documents with cross-encoder")
        
        # Stage 1: Cross-encoder reranking
        reranked_with_scores = self.cross_encoder_rerank(
            query, 
            documents,
            top_k=self.config["post_rerank_k"]
        )
        
        reranked_docs = [doc for doc, _ in reranked_with_scores]
        scores = [score for _, score in reranked_with_scores]
        
        print(f"Cross-encoder scores range: [{min(scores):.3f}, {max(scores):.3f}]")
        
        # Stage 2: Apply MMR for diversity
        if apply_mmr and len(reranked_docs) > self.config["final_context_k"]:
            print(f"Applying MMR for diversity (λ={self.config['mmr_lambda']})")
            
            final_docs = self.maximal_marginal_relevance(
                query,
                reranked_docs,
                scores,
                top_k=self.config["final_context_k"]
            )
        else:
            final_docs = reranked_docs[:self.config["final_context_k"]]
        
        print(f"Final selection: {len(final_docs)} documents")
        
        return final_docs
    
    def simple_rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """
        Simple reranking without MMR
        """
        
        top_k = top_k or self.config["final_context_k"]
        
        reranked = self.cross_encoder_rerank(query, documents, top_k=top_k)
        return [doc for doc, _ in reranked]