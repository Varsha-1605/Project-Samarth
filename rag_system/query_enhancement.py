import re
from typing import List, Dict, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from data_pipeline.config import SYNONYM_MAP, DOMAIN_KEYWORDS, RAG_CONFIG

class QueryEnhancer:
    """
    Advanced query enhancement with expansion, decomposition, and HyDE
    """
    
    def __init__(self, openai_api_key: str):
        self.config = RAG_CONFIG
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,
            api_key=openai_api_key
        )
        
        # Query expansion prompt
        self.expansion_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Given this query about agricultural or climate data, generate {num_variations} alternative phrasings that maintain the same meaning but use different words and perspectives.

Original Query: {query}

Generate variations that:
1. Use synonyms and related terms
2. Rephrase in different structures
3. Add implicit context when relevant

Variations (one per line):"""
        )
        
        # Query decomposition prompt
        self.decomposition_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Break down this complex query into simpler sub-questions that need to be answered.

Query: {query}

Sub-questions (one per line, numbered):"""
        )
        
        # HyDE prompt
        self.hyde_prompt = PromptTemplate(
            input_variables=["query"],
            template="""You are a data analyst. Write a hypothetical passage from a dataset that would perfectly answer this query about agricultural or climate data.

Query: {query}

Write a detailed, data-rich passage (2-3 sentences) that contains specific numbers, locations, and facts that would answer this query:"""
        )
    
    def expand_query_with_synonyms(self, query: str) -> List[str]:
        """Expand query using synonym mapping"""
        expanded_queries = [query]
        query_lower = query.lower()
        
        for term, synonyms in SYNONYM_MAP.items():
            if term in query_lower:
                for synonym in synonyms[:2]:  # Limit to 2 synonyms per term
                    expanded = query_lower.replace(term, synonym)
                    if expanded != query_lower:
                        expanded_queries.append(expanded)
        
        return list(set(expanded_queries))[:self.config["max_query_variations"]]
    
    def extract_domain_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract domain-specific entities from query"""
        entities = {
            'crops': [],
            'states': [],
            'metrics': [],
            'climate_terms': []
        }
        
        query_lower = query.lower()
        
        for crop in DOMAIN_KEYWORDS['crops']:
            if crop in query_lower:
                entities['crops'].append(crop)
        
        for state in DOMAIN_KEYWORDS['states']:
            if state in query_lower:
                entities['states'].append(state)
        
        for metric in DOMAIN_KEYWORDS['metrics']:
            if metric in query_lower:
                entities['metrics'].append(metric)
        
        for term in DOMAIN_KEYWORDS['climate_terms']:
            if term in query_lower:
                entities['climate_terms'].append(term)
        
        return entities
    
    def expand_with_llm(self, query: str) -> List[str]:
        """Use LLM to generate query variations"""
        if not self.config["enable_query_expansion"]:
            return [query]
        
        try:
            num_variations = self.config["max_query_variations"] - 1
            
            chain = self.expansion_prompt | self.llm
            response = chain.invoke({
                "query": query,
                "num_variations": num_variations
            })
            
            # Extract content from AIMessage
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse variations
            variations = [query]  # Always include original
            for line in response_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith(('Original', 'Query:', 'Variations')):
                    # Remove numbering if present
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                    if cleaned:
                        variations.append(cleaned)
            
            return variations[:self.config["max_query_variations"]]
        
        except Exception as e:
            print(f"Error in LLM expansion: {e}")
            return [query]
    
    def decompose_query(self, query: str) -> List[str]:
        """Decompose complex query into sub-questions"""
        
        # Simple heuristic: if query has multiple clauses, it might be complex
        if ' and ' not in query.lower() and ' compare ' not in query.lower():
            return [query]
        
        try:
            chain = self.decomposition_prompt | self.llm
            response = chain.invoke({"query": query})
            
            # Extract content
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse sub-questions
            sub_questions = []
            for line in response_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith(('Query:', 'Sub-questions')):
                    # Remove numbering
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                    if cleaned:
                        sub_questions.append(cleaned)
            
            return sub_questions if sub_questions else [query]
        
        except Exception as e:
            print(f"Error in query decomposition: {e}")
            return [query]
    
    def generate_hyde_document(self, query: str) -> str:
        """Generate hypothetical document using HyDE technique"""
        if not self.config["enable_hyde"]:
            return query
        
        try:
            chain = self.hyde_prompt | self.llm
            response = chain.invoke({"query": query})
            
            # Extract content
            hyde_doc = response.content if hasattr(response, 'content') else str(response)
            
            return hyde_doc.strip()
        
        except Exception as e:
            print(f"Error in HyDE generation: {e}")
            return query
    
    def enhance_query(self, query: str) -> Dict[str, any]:
        """
        Main method: Enhance query with all techniques
        Returns dictionary with original query, variations, sub-questions, entities, and HyDE doc
        """
        
        # Extract entities
        entities = self.extract_domain_entities(query)
        
        # Expand with synonyms
        synonym_expansions = self.expand_query_with_synonyms(query)
        
        # Expand with LLM
        llm_variations = self.expand_with_llm(query)
        
        # Combine expansions (remove duplicates)
        all_variations = list(set(synonym_expansions + llm_variations))
        
        # Decompose if complex
        sub_questions = self.decompose_query(query)
        
        # Generate HyDE document
        hyde_doc = self.generate_hyde_document(query)
        
        return {
            'original_query': query,
            'query_variations': all_variations,
            'sub_questions': sub_questions if len(sub_questions) > 1 else [],
            'entities': entities,
            'hyde_document': hyde_doc,
            'is_complex': len(sub_questions) > 1
        }
    
    def get_search_queries(self, enhanced_query: Dict) -> List[str]:
        """
        Get all queries to use for retrieval
        """
        queries = [enhanced_query['original_query']]
        
        # Add variations
        queries.extend(enhanced_query['query_variations'])
        
        # Add sub-questions if complex
        if enhanced_query['is_complex']:
            queries.extend(enhanced_query['sub_questions'])
        
        # Add HyDE document
        if enhanced_query['hyde_document'] != enhanced_query['original_query']:
            queries.append(enhanced_query['hyde_document'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)
        
        return unique_queries