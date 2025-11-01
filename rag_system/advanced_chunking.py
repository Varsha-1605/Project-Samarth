import re
from typing import List, Dict, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from data_pipeline.config import RAG_CONFIG

class AdvancedChunker:
    """
    Advanced chunking with semantic boundaries and contextual enrichment
    """
    
    def __init__(self):
        self.config = RAG_CONFIG
        self.base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["semantic_chunk_size"],
            chunk_overlap=self.config["semantic_chunk_overlap"],
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
    
    def extract_structured_info(self, record: Dict) -> Dict:
        """Extract key structured information from record"""
        structured = {}
        
        # Temporal information
        for key in ['year', 'Year', 'season', 'Season', 'month', 'Month']:
            if key in record:
                structured['temporal'] = str(record[key])
                break
        
        # Geographic information
        for key in ['state_name', 'State', 'region', 'Region', 'subdivision']:
            if key in record:
                structured['geographic'] = str(record[key])
                break
        
        # Crop/commodity information
        for key in ['crop', 'Crop', 'commodity', 'Commodity']:
            if key in record:
                structured['crop'] = str(record[key])
                break
        
        # Metric type
        for key in ['production', 'Production', 'area', 'Area', 'rainfall', 'Rainfall']:
            if key in record and record[key] is not None:
                structured['metric_type'] = key.lower()
                structured['metric_value'] = str(record[key])
                break
        
        return structured
    
    def create_contextual_header(self, record: Dict) -> str:
        """Create rich contextual header for chunk"""
        dataset_name = record.get('_dataset_name', 'Unknown Dataset')
        category = record.get('_dataset_category', 'Unknown')
        
        header_parts = [
            f"# Dataset: {dataset_name}",
            f"Category: {category}"
        ]
        
        structured = self.extract_structured_info(record)
        
        if structured.get('temporal'):
            header_parts.append(f"Time Period: {structured['temporal']}")
        if structured.get('geographic'):
            header_parts.append(f"Location: {structured['geographic']}")
        if structured.get('crop'):
            header_parts.append(f"Crop/Commodity: {structured['crop']}")
        
        return "\n".join(header_parts) + "\n\n"
    
    def format_record_content(self, record: Dict) -> str:
        """Format record into readable content"""
        content_parts = []
        
        for key, value in record.items():
            if key.startswith('_') or value is None:
                continue
            
            # Format numbers with proper units
            if isinstance(value, (int, float)):
                if 'area' in key.lower():
                    content_parts.append(f"{key}: {value} hectares")
                elif 'production' in key.lower():
                    content_parts.append(f"{key}: {value} tonnes")
                elif 'rainfall' in key.lower():
                    content_parts.append(f"{key}: {value} mm")
                elif 'temperature' in key.lower():
                    content_parts.append(f"{key}: {value}°C")
                elif 'price' in key.lower():
                    content_parts.append(f"{key}: ₹{value}")
                else:
                    content_parts.append(f"{key}: {value}")
            else:
                content_parts.append(f"{key}: {value}")
        
        return "\n".join(content_parts)
    
    def chunk_by_data_type(self, records: List[Dict], category: str) -> List[str]:
        """Apply category-specific chunking strategies"""
        
        if category == "agriculture":
            return self._chunk_agriculture_data(records)
        elif category == "climate":
            return self._chunk_climate_data(records)
        else:
            return self._chunk_generic_data(records)
    
    def _chunk_agriculture_data(self, records: List[Dict]) -> List[str]:
        """Group agriculture records by crop and region"""
        chunks = []
        
        # Group by crop-state combination
        grouped = {}
        for record in records:
            crop = record.get('crop', record.get('Crop', 'Unknown'))
            state = record.get('state_name', record.get('State', 'Unknown'))
            key = f"{crop}_{state}"
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(record)
        
        # Create chunks from groups
        for group_key, group_records in grouped.items():
            if len(group_records) > 0:
                chunk_content = self.create_contextual_header(group_records[0])
                chunk_content += "\n".join([
                    self.format_record_content(r) for r in group_records[:5]
                ])
                chunks.append(chunk_content)
        
        return chunks
    
    def _chunk_climate_data(self, records: List[Dict]) -> List[str]:
        """Group climate records by region and time period"""
        chunks = []
        
        # Group by region-year combination
        grouped = {}
        for record in records:
            region = record.get('subdivision', record.get('region', 'Unknown'))
            year = record.get('year', record.get('Year', 'Unknown'))
            key = f"{region}_{year}"
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(record)
        
        # Create chunks from groups
        for group_key, group_records in grouped.items():
            if len(group_records) > 0:
                chunk_content = self.create_contextual_header(group_records[0])
                chunk_content += "\n".join([
                    self.format_record_content(r) for r in group_records[:5]
                ])
                chunks.append(chunk_content)
        
        return chunks
    
    def _chunk_generic_data(self, records: List[Dict]) -> List[str]:
        """Generic chunking for unspecified data types"""
        chunks = []
        
        for record in records:
            chunk_content = self.create_contextual_header(record)
            chunk_content += self.format_record_content(record)
            chunks.append(chunk_content)
        
        return chunks
    
    def create_semantic_chunks(self, text: str, metadata: Dict) -> List[str]:
        """Create semantically meaningful chunks"""
        
        # Use base splitter for initial split
        initial_chunks = self.base_splitter.split_text(text)
        
        # Post-process chunks to respect semantic boundaries
        semantic_chunks = []
        current_chunk = ""
        
        for chunk in initial_chunks:
            # Check if chunk ends with complete sentence
            if chunk.rstrip().endswith(('.', '!', '?', '\n')):
                semantic_chunks.append(current_chunk + chunk if current_chunk else chunk)
                current_chunk = ""
            else:
                current_chunk += chunk + " "
        
        # Add remaining chunk if any
        if current_chunk.strip():
            semantic_chunks.append(current_chunk.strip())
        
        return semantic_chunks
    
    def enrich_chunk_with_context(self, chunk: str, parent_metadata: Dict) -> str:
        """Add parent document context to chunk"""
        
        context_prefix = []
        
        if parent_metadata.get('dataset_name'):
            context_prefix.append(f"[Context: {parent_metadata['dataset_name']}]")
        
        if parent_metadata.get('category'):
            context_prefix.append(f"[Domain: {parent_metadata['category']}]")
        
        if parent_metadata.get('temporal'):
            context_prefix.append(f"[Period: {parent_metadata['temporal']}]")
        
        if context_prefix:
            return "\n".join(context_prefix) + "\n\n" + chunk
        
        return chunk
    
    def chunk_documents(self, records: List[Dict], category: str) -> List[Document]:
        """Main method to create advanced chunks"""
        documents = []
        
        # First, group records intelligently
        grouped_texts = self.chunk_by_data_type(records, category)
        
        # Then create semantic chunks with enrichment
        for idx, text in enumerate(grouped_texts):
            # Extract metadata from first record in group
            base_metadata = {
                'category': category,
                'chunk_index': idx,
                'chunk_strategy': 'semantic_grouped'
            }
            
            # Create semantic sub-chunks if text is too long
            if len(text) > self.config["max_chunk_size"]:
                sub_chunks = self.create_semantic_chunks(text, base_metadata)
                
                for sub_idx, sub_chunk in enumerate(sub_chunks):
                    enriched_chunk = self.enrich_chunk_with_context(
                        sub_chunk, 
                        base_metadata
                    )
                    
                    doc_metadata = base_metadata.copy()
                    doc_metadata['sub_chunk_index'] = sub_idx
                    
                    documents.append(
                        Document(page_content=enriched_chunk, metadata=doc_metadata)
                    )
            else:
                enriched_text = self.enrich_chunk_with_context(text, base_metadata)
                documents.append(
                    Document(page_content=enriched_text, metadata=base_metadata)
                )
        
        return documents