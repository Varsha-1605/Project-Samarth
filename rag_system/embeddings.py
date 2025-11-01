import os
import json
import pickle
from typing import List, Dict, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from data_pipeline.config import VECTOR_STORE_DIR
from rag_system.advanced_chunking import AdvancedChunker

class EmbeddingManager:
    """
    Enhanced embedding manager with advanced chunking strategies
    """
    
    def __init__(self, openai_api_key: str):
        os.environ['OPENAI_API_KEY'] = openai_api_key
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_dir = VECTOR_STORE_DIR
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        # Initialize advanced chunker
        self.chunker = AdvancedChunker()
        
        print("Embedding manager initialized with advanced chunking")
    
    def create_document_from_record(self, record: Dict) -> str:
        """Create document text from record (legacy method)"""
        text_parts = []
        dataset_name = record.get('_dataset_name', 'Unknown Dataset')
        category = record.get('_dataset_category', 'Unknown')
        
        text_parts.append(f"Dataset: {dataset_name}")
        text_parts.append(f"Category: {category}")
        
        for key, value in record.items():
            if not key.startswith('_') and value is not None:
                text_parts.append(f"{key}: {value}")
        
        return "\n".join(text_parts)
    
    def prepare_documents_basic(self, data: Dict[str, List[Dict]]) -> List[Document]:
        """
        Basic document preparation (legacy method for compatibility)
        """
        documents = []
        
        for category, records in data.items():
            for idx, record in enumerate(records):
                text_content = self.create_document_from_record(record)
                
                metadata = {
                    'dataset_id': record.get('_dataset_id', 'unknown'),
                    'dataset_name': record.get('_dataset_name', 'Unknown'),
                    'category': category,
                    'record_index': idx,
                    'source': f"{record.get('_dataset_name', 'Unknown')} - Record {idx}"
                }
                
                # Add entity metadata
                for key in ['state_name', 'State', 'region', 'subdivision', 
                           'district_name', 'District', 'crop', 'Commodity']:
                    if key in record and record[key]:
                        metadata[key.lower()] = str(record[key])
                
                doc = Document(page_content=text_content, metadata=metadata)
                documents.append(doc)
        
        return documents
    
    def prepare_documents_advanced(self, data: Dict[str, List[Dict]]) -> List[Document]:
        """
        Advanced document preparation with semantic chunking
        """
        all_documents = []
        
        for category, records in data.items():
            print(f"\nProcessing {category} category with {len(records)} records")
            
            # Use advanced chunking
            category_docs = self.chunker.chunk_documents(records, category)
            
            # Enhance metadata for each document
            for doc in category_docs:
                # Extract dataset info from first record
                if records:
                    first_record = records[0]
                    doc.metadata['dataset_id'] = first_record.get('_dataset_id', 'unknown')
                    doc.metadata['dataset_name'] = first_record.get('_dataset_name', 'Unknown')
                    doc.metadata['source'] = first_record.get('_dataset_name', 'Unknown Dataset')
                
                doc.metadata['category'] = category
            
            all_documents.extend(category_docs)
            print(f"Created {len(category_docs)} chunks for {category}")
        
        return all_documents
    
    def prepare_documents(
        self, 
        data: Dict[str, List[Dict]],
        use_advanced_chunking: bool = True
    ) -> List[Document]:
        """
        Main document preparation method
        """
        if use_advanced_chunking:
            print("Using advanced semantic chunking")
            return self.prepare_documents_advanced(data)
        else:
            print("Using basic chunking")
            return self.prepare_documents_basic(data)
    
    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """Create FAISS vector store from documents"""
        print(f"Creating embeddings for {len(documents)} documents...")
        
        # Create vector store in batches to handle large datasets
        batch_size = 100
        vector_store = None
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
            
            if vector_store is None:
                vector_store = FAISS.from_documents(batch, self.embeddings)
            else:
                batch_store = FAISS.from_documents(batch, self.embeddings)
                vector_store.merge_from(batch_store)
        
        print("Vector store created successfully")
        return vector_store
    
    def save_vector_store(self, vector_store: FAISS, name: str = "main"):
        """Save vector store to disk"""
        save_path = os.path.join(self.vector_store_dir, name)
        vector_store.save_local(save_path)
        print(f"Vector store saved to {save_path}")
    
    def save_documents(self, documents: List[Document], name: str = "main"):
        """Save document list for BM25 indexing"""
        doc_path = os.path.join(self.vector_store_dir, f"{name}_documents.pkl")
        with open(doc_path, 'wb') as f:
            pickle.dump(documents, f)
        print(f"Documents saved to {doc_path}")
    
    def load_vector_store(self, name: str = "main") -> Optional[FAISS]:
        """Load vector store from disk"""
        load_path = os.path.join(self.vector_store_dir, name)
        if os.path.exists(load_path):
            vector_store = FAISS.load_local(
                load_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"Vector store loaded from {load_path}")
            return vector_store
        return None
    
    def load_documents(self, name: str = "main") -> Optional[List[Document]]:
        """Load document list"""
        doc_path = os.path.join(self.vector_store_dir, f"{name}_documents.pkl")
        if os.path.exists(doc_path):
            with open(doc_path, 'rb') as f:
                documents = pickle.load(f)
            print(f"Loaded {len(documents)} documents from {doc_path}")
            return documents
        return None
    
    def build_and_save_vector_store(
        self, 
        data: Dict[str, List[Dict]], 
        name: str = "main",
        use_advanced_chunking: bool = True
    ):
        """Build and save both vector store and documents"""
        
        # Prepare documents
        documents = self.prepare_documents(data, use_advanced_chunking)
        print(f"Prepared {len(documents)} documents")
        
        # Create vector store
        vector_store = self.create_vector_store(documents)
        
        # Save both vector store and documents
        self.save_vector_store(vector_store, name)
        self.save_documents(documents, name)
        
        return vector_store, documents