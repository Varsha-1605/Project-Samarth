from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from rag_system.query_enhancement import QueryEnhancer
from rag_system.advanced_retriever import AdvancedRetriever
from rag_system.reranker import AdvancedReranker
from rag_system.context_compressor import ContextCompressor
from rag_system.qa_engine import QAEngine

class AdvancedRAGPipeline:
    """
    Complete advanced RAG pipeline orchestrating all components
    """
    
    def __init__(
        self,
        vector_store: FAISS,
        all_documents: List[Document],
        openai_api_key: str
    ):
        print("Initializing Advanced RAG Pipeline...")
        
        # Initialize all components
        self.query_enhancer = QueryEnhancer(openai_api_key)
        print("✓ Query enhancer initialized")
        
        self.retriever = AdvancedRetriever(vector_store, all_documents)
        print("✓ Advanced retriever initialized")
        
        self.reranker = AdvancedReranker()
        print("✓ Reranker initialized")
        
        self.compressor = ContextCompressor(openai_api_key)
        print("✓ Context compressor initialized")
        
        self.qa_engine = QAEngine(openai_api_key)
        print("✓ QA engine initialized")
        
        print("Advanced RAG Pipeline ready!\n")
    
    def process_query(
        self,
        query: str,
        chat_history: List[Dict] = None,
        category: Optional[str] = None,
        enable_all_features: bool = True
    ) -> Dict:
        """
        Complete RAG pipeline processing
        
        Pipeline stages:
        1. Query enhancement (expansion, decomposition, HyDE)
        2. Multi-stage retrieval (dense + sparse + fusion)
        3. Reranking (cross-encoder + MMR)
        4. Context compression
        5. Answer generation
        """
        
        print(f"\n{'='*60}")
        print(f"Processing Query: {query}")
        print(f"{'='*60}\n")
        
        # Stage 1: Query Enhancement
        print("STAGE 1: Query Enhancement")
        print("-" * 40)
        
        if enable_all_features:
            enhanced_query = self.query_enhancer.enhance_query(query)
            
            print(f"Original query: {enhanced_query['original_query']}")
            print(f"Query variations: {len(enhanced_query['query_variations'])}")
            if enhanced_query['sub_questions']:
                print(f"Sub-questions: {len(enhanced_query['sub_questions'])}")
            print(f"Entities found: {sum(len(v) for v in enhanced_query['entities'].values())}")
            
            # Get all search queries
            search_queries = self.query_enhancer.get_search_queries(enhanced_query)
            entities = enhanced_query['entities']
        else:
            search_queries = [query]
            entities = {}
        
        print(f"Total search queries: {len(search_queries)}\n")
        
        # Stage 2: Multi-Stage Retrieval
        print("STAGE 2: Multi-Stage Retrieval")
        print("-" * 40)
        
        retrieved_docs = self.retriever.multi_stage_retrieval(
            search_queries,
            entities,
            category
        )
        
        print(f"Retrieved {len(retrieved_docs)} documents\n")
        
        # Stage 3: Reranking
        print("STAGE 3: Reranking & Diversification")
        print("-" * 40)
        
        if enable_all_features and len(retrieved_docs) > 8:
            reranked_docs = self.reranker.rerank_and_diversify(
                query,
                retrieved_docs,
                apply_mmr=True
            )
        else:
            reranked_docs = retrieved_docs[:8]
            print(f"Using top {len(reranked_docs)} documents (reranking skipped)")
        
        print(f"Final selection: {len(reranked_docs)} documents\n")
        
        # Stage 4: Context Compression
        print("STAGE 4: Context Compression")
        print("-" * 40)
        
        if enable_all_features:
            compressed_docs = self.compressor.compress_documents(
                query,
                reranked_docs,
                method="hybrid"
            )
        else:
            compressed_docs = reranked_docs
        
        print(f"Compressed to {len(compressed_docs)} documents\n")
        
        # Stage 5: Answer Generation
        print("STAGE 5: Answer Generation")
        print("-" * 40)
        
        result = self.qa_engine.answer_with_confidence(
            query,
            compressed_docs,
            chat_history
        )
        
        print(f"Answer generated (confidence: {result['confidence']:.2f})")
        print(f"Quality score: {result['quality_metrics']['quality_score']}/100")
        print(f"\n{'='*60}\n")
        
        # Add pipeline metadata
        result['pipeline_info'] = {
            'query_variations': len(search_queries),
            'retrieved_count': len(retrieved_docs),
            'reranked_count': len(reranked_docs),
            'final_context_count': len(compressed_docs),
            'entities_found': entities if enable_all_features else {},
            'features_enabled': enable_all_features
        }
        
        return result
    
    def quick_query(
        self,
        query: str,
        chat_history: List[Dict] = None
    ) -> str:
        """
        Quick query method that returns just the answer text
        """
        result = self.process_query(query, chat_history, enable_all_features=True)
        return result['answer']
    
    def batch_query(
        self,
        queries: List[str],
        chat_history: List[Dict] = None
    ) -> List[Dict]:
        """
        Process multiple queries in batch
        """
        results = []
        
        for i, query in enumerate(queries):
            print(f"\nProcessing query {i+1}/{len(queries)}")
            result = self.process_query(query, chat_history)
            results.append(result)
        
        return results


class SimpleRAGPipeline:
    """
    Simplified RAG pipeline for fallback or testing
    """
    
    def __init__(
        self,
        vector_store: FAISS,
        openai_api_key: str
    ):
        self.vector_store = vector_store
        self.qa_engine = QAEngine(openai_api_key)
    
    def process_query(
        self,
        query: str,
        chat_history: List[Dict] = None,
        k: int = 10
    ) -> Dict:
        """
        Simple retrieval and generation
        """
        
        # Simple similarity search
        retrieved_docs = self.vector_store.similarity_search(query, k=k)
        
        # Generate answer
        result = self.qa_engine.answer_question(
            query,
            retrieved_docs,
            chat_history
        )
        
        return result