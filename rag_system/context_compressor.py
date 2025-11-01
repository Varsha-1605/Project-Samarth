import re
from typing import List, Dict
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from data_pipeline.config import RAG_CONFIG

class ContextCompressor:
    """
    Compress context by extracting most relevant information
    """
    
    def __init__(self, openai_api_key: str):
        self.config = RAG_CONFIG
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            api_key=openai_api_key
        )
        
        # Extraction prompt
        self.extraction_prompt = PromptTemplate(
            input_variables=["query", "context"],
            template="""Extract ONLY the information from this context that is directly relevant to answering the query. Keep specific numbers, dates, locations, and key facts. Remove redundant or irrelevant information.

Query: {query}

Context:
{context}

Relevant extracted information (be concise but preserve key data):"""
        )
    
    def extract_key_sentences(
        self, 
        text: str, 
        query: str,
        max_sentences: int = 5
    ) -> List[str]:
        """
        Extract sentences most relevant to query using simple heuristics
        """
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Score sentences based on query term overlap
        query_terms = set(query.lower().split())
        
        scored_sentences = []
        for sentence in sentences:
            sentence_terms = set(sentence.lower().split())
            
            # Calculate overlap score
            overlap = len(query_terms & sentence_terms)
            
            # Bonus for numerical data
            has_numbers = bool(re.search(r'\d+', sentence))
            number_bonus = 0.3 if has_numbers else 0
            
            # Bonus for specific entities (states, crops)
            entity_bonus = 0
            if any(term in sentence.lower() for term in ['state', 'district', 'region', 'crop']):
                entity_bonus = 0.2
            
            score = overlap + number_bonus + entity_bonus
            
            if score > 0:
                scored_sentences.append((sentence, score))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        return [sent for sent, _ in scored_sentences[:max_sentences]]
    
    def remove_redundancy(self, texts: List[str]) -> List[str]:
        """
        Remove duplicate or highly similar content
        """
        
        unique_texts = []
        seen_content = set()
        
        for text in texts:
            # Create a normalized version for comparison
            normalized = re.sub(r'\s+', ' ', text.lower()).strip()
            
            # Check if we've seen very similar content
            is_duplicate = False
            for seen in seen_content:
                # Simple similarity: check if 80% of words overlap
                text_words = set(normalized.split())
                seen_words = set(seen.split())
                
                if len(text_words) > 0:
                    overlap = len(text_words & seen_words) / len(text_words)
                    if overlap > 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_texts.append(text)
                seen_content.add(normalized)
        
        return unique_texts
    
    def compress_with_llm(
        self, 
        query: str, 
        context: str
    ) -> str:
        """
        Use LLM to extract relevant information
        """
        
        if not self.config["enable_compression"]:
            return context
        
        # Only compress if context is long
        if len(context) < 1000:
            return context
        
        try:
            chain = self.extraction_prompt | self.llm
            response = chain.invoke({
                "query": query,
                "context": context
            })
            
            # Extract content
            compressed = response.content if hasattr(response, 'content') else str(response)
            
            return compressed.strip()
        
        except Exception as e:
            print(f"Error in LLM compression: {e}")
            return context
    
    def compress_documents(
        self,
        query: str,
        documents: List[Document],
        method: str = "hybrid"
    ) -> List[Document]:
        """
        Main compression method
        
        Methods:
        - 'sentences': Extract key sentences
        - 'llm': Use LLM to extract relevant info
        - 'hybrid': Combine both approaches
        """
        
        if not documents:
            return []
        
        print(f"Compressing {len(documents)} documents using '{method}' method")
        
        compressed_docs = []
        
        for doc in documents:
            content = doc.page_content
            
            if method == "sentences":
                # Extract key sentences
                key_sentences = self.extract_key_sentences(content, query)
                compressed_content = "\n".join(key_sentences)
            
            elif method == "llm":
                # Use LLM compression
                compressed_content = self.compress_with_llm(query, content)
            
            elif method == "hybrid":
                # First extract key sentences
                key_sentences = self.extract_key_sentences(content, query, max_sentences=8)
                sentence_content = "\n".join(key_sentences)
                
                # Then apply LLM compression if still long
                if len(sentence_content) > 800:
                    compressed_content = self.compress_with_llm(query, sentence_content)
                else:
                    compressed_content = sentence_content
            
            else:
                compressed_content = content
            
            # Create compressed document
            compressed_doc = Document(
                page_content=compressed_content,
                metadata=doc.metadata.copy()
            )
            compressed_doc.metadata['compressed'] = True
            compressed_doc.metadata['original_length'] = len(content)
            compressed_doc.metadata['compressed_length'] = len(compressed_content)
            
            compressed_docs.append(compressed_doc)
        
        # Remove redundancy across documents
        unique_contents = self.remove_redundancy([d.page_content for d in compressed_docs])
        
        final_docs = []
        for i, content in enumerate(unique_contents):
            if i < len(compressed_docs):
                final_docs.append(Document(
                    page_content=content,
                    metadata=compressed_docs[i].metadata
                ))
        
        # Calculate compression stats
        original_total = sum(d.metadata.get('original_length', 0) for d in compressed_docs)
        compressed_total = sum(len(d.page_content) for d in final_docs)
        
        if original_total > 0:
            compression_ratio = compressed_total / original_total
            print(f"Compression: {original_total} → {compressed_total} chars ({compression_ratio:.1%})")
        
        return final_docs
    
    def create_optimized_context(
        self,
        query: str,
        documents: List[Document],
        max_tokens: int = 3000
    ) -> str:
        """
        Create optimized context string for LLM
        """
        
        # Compress documents
        compressed_docs = self.compress_documents(query, documents, method="hybrid")
        
        # Build context string
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(compressed_docs):
            source = doc.metadata.get('source', f'Source {i+1}')
            dataset_name = doc.metadata.get('dataset_name', 'Unknown Dataset')
            
            doc_text = f"[Source: {dataset_name}]\n{doc.page_content}\n"
            doc_length = len(doc_text.split())  # Rough token count
            
            if current_length + doc_length > max_tokens:
                break
            
            context_parts.append(doc_text)
            current_length += doc_length
        
        return "\n---\n".join(context_parts)