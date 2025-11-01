# import os
# import re
# from typing import List, Dict, Optional
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import PromptTemplate
# from langchain_core.documents import Document

# class QAEngine:
#     """
#     Enhanced QA engine with better prompting and answer generation
#     """
    
#     def __init__(self, openai_api_key: str):
#         os.environ['OPENAI_API_KEY'] = openai_api_key
#         self.llm = ChatOpenAI(
#             model="gpt-3.5-turbo",
#             temperature=0.3
#         )
        
#         # Enhanced QA prompt with better instructions
#         self.qa_prompt = PromptTemplate(
#             input_variables=["context", "question", "chat_history"],
#             template="""You are an expert data analyst specializing in agricultural and climate data from India's data.gov.in portal.

# Retrieved Context:
# {context}

# Previous Conversation:
# {chat_history}

# Current Question: {question}

# Instructions:
# 1. **Primary Source**: Base your answer on the retrieved context data whenever possible
# 2. **Data-Driven**: Use specific numbers, statistics, and facts from the context
# 3. **Comprehensive**: If context is limited but you have relevant domain knowledge, provide a complete answer
# 4. **Clear Structure**: 
#    - For comparisons: Use bullet points or numbered lists
#    - For data presentation: Use clear formatting with proper headings
#    - Use markdown formatting: **bold** for emphasis, proper lists, etc.
# 5. **Natural Flow**: Write in a natural, conversational style
# 6. **No Meta-References**: Don't use phrases like "Based on the data" or "According to the documents"
# 7. **Direct Answers**: Start directly with the answer, don't add preambles
# 8. **Professional Tone**: Write in clear, professional language

# Format guidelines:
# - Use **bold** for key metrics and values
# - Use bullet points (•) for listing multiple items
# - Use numbered lists (1., 2., 3.) for sequential information
# - Add line breaks between sections for readability

# Answer:"""
#         )
        
#         self.qa_chain = self.qa_prompt | self.llm
    
#     def format_context(self, documents: List[Document]) -> str:
#         """Format context from retrieved documents"""
#         if not documents:
#             return "No specific data retrieved for this query."
        
#         context_parts = []
#         seen_content = set()
        
#         for i, doc in enumerate(documents, 1):
#             content = doc.page_content
            
#             # Skip duplicates
#             if content in seen_content:
#                 continue
#             seen_content.add(content)
            
#             # Get source information
#             dataset_name = doc.metadata.get('dataset_name', 'Unknown Dataset')
#             category = doc.metadata.get('category', 'unknown')
            
#             # Format document
#             doc_header = f"--- Source {i}: {dataset_name} ({category}) ---"
#             context_parts.append(f"{doc_header}\n{content}\n")
        
#         return "\n".join(context_parts)
    
#     def format_chat_history(self, messages: List[Dict]) -> str:
#         """Format chat history for context"""
#         if not messages:
#             return "No previous conversation."
        
#         history_parts = []
        
#         # Include last 5 messages for context
#         for msg in messages[-5:]:
#             role = msg.get('role', 'user')
#             content = msg.get('content', '')
            
#             if role == 'user':
#                 history_parts.append(f"User: {content}")
#             elif role == 'assistant':
#                 # Truncate long assistant responses
#                 truncated = content[:200] + "..." if len(content) > 200 else content
#                 history_parts.append(f"Assistant: {truncated}")
        
#         return "\n".join(history_parts) if history_parts else "No previous conversation."
    
#     def extract_sources(self, documents: List[Document]) -> List[Dict]:
#         """Extract unique source information"""
#         sources = []
#         seen_datasets = set()
        
#         for doc in documents:
#             dataset_id = doc.metadata.get('dataset_id', 'unknown')
#             dataset_name = doc.metadata.get('dataset_name', 'Unknown Dataset')
#             category = doc.metadata.get('category', 'unknown')
            
#             if dataset_id not in seen_datasets:
#                 seen_datasets.add(dataset_id)
#                 sources.append({
#                     'dataset_id': dataset_id,
#                     'dataset_name': dataset_name,
#                     'category': category
#                 })
        
#         return sources
    
#     def clean_response(self, response_text: str) -> str:
#         """Clean and format the response"""
        
#         # Remove common disclaimer phrases
#         disclaimers = [
#             r"based on the (provided|available) (context|data|information)",
#             r"according to the (documents|data|sources)",
#             r"the (context|data|information) (shows|indicates|suggests)",
#             r"from the (provided|retrieved) (context|data|information)",
#         ]
        
#         cleaned = response_text
#         for pattern in disclaimers:
#             cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
#         # Fix awkward markdown-style structures like "1. Maharashtra Rainfall Patterns: -"
#         # Replace pattern: "Number. Text: -" with "## Text"
#         cleaned = re.sub(r'(\d+)\.\s*([A-Z][^:]+):\s*-', r'## \2', cleaned)
        
#         # Replace pattern: "Text: -" with "**Text:**"
#         cleaned = re.sub(r'([A-Za-z\s]+):\s*-\s*', r'**\1:**\n', cleaned)
        
#         # Fix multiple colons
#         cleaned = re.sub(r'::+', ':', cleaned)
        
#         # Clean up extra whitespace
#         cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
#         cleaned = re.sub(r' +', ' ', cleaned)  # Single spaces
        
#         return cleaned.strip()
    
#     def assess_answer_quality(self, answer: str, documents: List[Document]) -> Dict:
#         """Assess the quality of the generated answer"""
        
#         quality_metrics = {
#             'has_numbers': bool(re.search(r'\d+', answer)),
#             'length': len(answer.split()),
#             'uses_context': len(documents) > 0,
#             'has_structure': bool(re.search(r'(\n\n|1\.|2\.|•|##)', answer)),
#         }
        
#         # Simple quality score
#         score = 0
#         if quality_metrics['has_numbers']:
#             score += 25
#         if quality_metrics['length'] > 50:
#             score += 25
#         if quality_metrics['uses_context']:
#             score += 30
#         if quality_metrics['has_structure']:
#             score += 20
        
#         quality_metrics['quality_score'] = score
        
#         return quality_metrics
    
#     def answer_question(
#         self, 
#         question: str, 
#         retrieved_docs: List[Document],
#         chat_history: List[Dict] = None
#     ) -> Dict:
#         """
#         Generate answer to question using retrieved documents
#         """
        
#         # Format inputs
#         context = self.format_context(retrieved_docs)
#         history = self.format_chat_history(chat_history or [])
        
#         # Generate answer
#         response = self.qa_chain.invoke({
#             "context": context,
#             "question": question,
#             "chat_history": history
#         })
        
#         # Extract content
#         response_text = response.content if hasattr(response, 'content') else str(response)
        
#         # Clean response
#         cleaned_response = self.clean_response(response_text)
        
#         # Extract sources
#         sources = self.extract_sources(retrieved_docs)
        
#         # Assess quality
#         quality = self.assess_answer_quality(cleaned_response, retrieved_docs)
        
#         return {
#             'answer': cleaned_response,
#             'sources': sources,
#             'num_sources': len(sources),
#             'num_documents': len(retrieved_docs),
#             'quality_metrics': quality
#         }
    
#     def answer_with_confidence(
#         self,
#         question: str,
#         retrieved_docs: List[Document],
#         chat_history: List[Dict] = None,
#         min_confidence_threshold: float = 0.3
#     ) -> Dict:
#         """
#         Answer with confidence scoring
#         """
        
#         result = self.answer_question(question, retrieved_docs, chat_history)
        
#         # Calculate confidence based on retrieval quality
#         confidence = 0.5  # Base confidence
        
#         if result['num_documents'] > 5:
#             confidence += 0.2
#         if result['quality_metrics']['has_numbers']:
#             confidence += 0.15
#         if result['quality_metrics']['quality_score'] > 70:
#             confidence += 0.15
        
#         confidence = min(confidence, 1.0)
        
#         result['confidence'] = confidence
#         result['is_confident'] = confidence >= min_confidence_threshold
        
#         return result


















































import os
import re
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

class QAEngine:
    """
    Enhanced QA engine with better prompting and answer generation
    """
    
    def __init__(self, openai_api_key: str):
        os.environ['OPENAI_API_KEY'] = openai_api_key
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.5  # Slightly higher for better general knowledge responses
        )
        
        # Enhanced QA prompt with better instructions
        self.qa_prompt = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""You are an expert data analyst specializing in agricultural and climate data from India.

Retrieved Context:
{context}

Previous Conversation:
{chat_history}

Current Question: {question}

Instructions:
1. **Primary Source**: Use the retrieved context data as your primary source when available
2. **Intelligent Fallback**: When specific data is not available in the context:
   - Use your general knowledge about Indian agriculture and climate
   - Provide typical ranges, historical patterns, or general trends
   - Give helpful context and insights
   - NEVER say "data not available", "assumed data", or mention data limitations
   - Present all information with equal confidence
3. **Data-Driven**: Use specific numbers, statistics, and facts whenever possible
4. **Clear Structure**: 
   - For comparisons: Use bullet points or numbered lists
   - For data presentation: Use clear formatting with proper headings
   - Use markdown formatting: **bold** for emphasis, proper lists, etc.
5. **Natural Flow**: Write in a natural, conversational style
6. **No Meta-References**: 
   - Don't say "Based on the data" or "According to the documents"
   - Don't mention "data not available" or "not in the dataset"
   - Don't add disclaimers about data limitations
   - NEVER cite source numbers like "(Source: Source 1)" or "(Source: Source 3)"
   - Don't say "assumed data" or "based on historical patterns"
   - Don't indicate which data came from context vs general knowledge
7. **Direct Answers**: Start directly with the answer, don't add preambles
8. **Professional Tone**: Write in clear, professional language
9. **Seamless Integration**: Mix retrieved data with general knowledge naturally without indicating the source

Format guidelines:
- Use **bold** for key metrics and values
- Use bullet points (•) for listing multiple items
- Use numbered lists (1., 2., 3.) for sequential information
- Add line breaks between sections for readability
- Never add parenthetical source citations

**IMPORTANT - Always End With Summary:**
At the end of every response, add a brief "**Key Takeaway:**" or "**In Simple Terms:**" section that:
- Summarizes the main findings in 2-3 simple sentences
- Uses plain language that anyone can understand (no technical jargon)
- Highlights the most important insight or comparison
- Makes it actionable or relatable

Answer:"""
        )
        
        self.qa_chain = self.qa_prompt | self.llm
    
    def format_context(self, documents: List[Document]) -> str:
        """Format context from retrieved documents"""
        if not documents:
            return "No specific data retrieved for this query."
        
        context_parts = []
        seen_content = set()
        
        for i, doc in enumerate(documents, 1):
            content = doc.page_content
            
            # Skip duplicates
            if content in seen_content:
                continue
            seen_content.add(content)
            
            # Get source information
            dataset_name = doc.metadata.get('dataset_name', 'Unknown Dataset')
            category = doc.metadata.get('category', 'unknown')
            
            # Format document
            doc_header = f"--- Source {i}: {dataset_name} ({category}) ---"
            context_parts.append(f"{doc_header}\n{content}\n")
        
        return "\n".join(context_parts)
    
    def format_chat_history(self, messages: List[Dict]) -> str:
        """Format chat history for context"""
        if not messages:
            return "No previous conversation."
        
        history_parts = []
        
        # Include last 5 messages for context
        for msg in messages[-5:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                history_parts.append(f"User: {content}")
            elif role == 'assistant':
                # Truncate long assistant responses
                truncated = content[:200] + "..." if len(content) > 200 else content
                history_parts.append(f"Assistant: {truncated}")
        
        return "\n".join(history_parts) if history_parts else "No previous conversation."
    
    def extract_sources(self, documents: List[Document]) -> List[Dict]:
        """Extract unique source information"""
        sources = []
        seen_datasets = set()
        
        for doc in documents:
            dataset_id = doc.metadata.get('dataset_id', 'unknown')
            dataset_name = doc.metadata.get('dataset_name', 'Unknown Dataset')
            category = doc.metadata.get('category', 'unknown')
            
            if dataset_id not in seen_datasets:
                seen_datasets.add(dataset_id)
                sources.append({
                    'dataset_id': dataset_id,
                    'dataset_name': dataset_name,
                    'category': category
                })
        
        return sources
    
    def clean_response(self, response_text: str) -> str:
        """Clean and format the response"""
        
        # Remove source citations like "(Source: Source 1)", "(Source: Source 3)", etc.
        cleaned = re.sub(r'\(Source:\s*Source\s*\d+\)', '', response_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(Source:\s*[^\)]+\)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove "assumed data" mentions
        cleaned = re.sub(r'\(Assumed data based on historical patterns\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(assumed.*?\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'assumed data based on historical patterns', '', cleaned, flags=re.IGNORECASE)
        
        # Remove common disclaimer phrases
        disclaimers = [
            r"based on the (provided|available) (context|data|information)",
            r"according to the (documents|data|sources)",
            r"the (context|data|information) (shows|indicates|suggests)",
            r"from the (provided|retrieved) (context|data|information)",
            r"data (is )?not available( in the (dataset|context))?",
            r"information (is )?not (present|available|provided)",
            r"(the )?(dataset|data|context) does not (contain|include|provide)",
            r"no specific data (found|available|present)",
            r"limited (data|information) in the context",
        ]
        
        for pattern in disclaimers:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # Fix awkward markdown-style structures like "1. Maharashtra Rainfall Patterns: -"
        # Replace pattern: "Number. Text: -" with "## Text"
        cleaned = re.sub(r'(\d+)\.\s*([A-Z][^:]+):\s*-', r'## \2', cleaned)
        
        # Replace pattern: "Text: -" with "**Text:**"
        cleaned = re.sub(r'([A-Za-z\s]+):\s*-\s*', r'**\1:**\n', cleaned)
        
        # Fix multiple colons
        cleaned = re.sub(r'::+', ':', cleaned)
        
        # Remove lines that only say "Data not available" or similar
        lines = cleaned.split('\n')
        filtered_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines that are just variations of "data not available"
            if not any(phrase in line_lower for phrase in [
                'data not available',
                'not available',
                'no data',
                'information not available',
                'not provided',
                'data is missing',
                'assumed data'
            ]):
                filtered_lines.append(line)
        
        cleaned = '\n'.join(filtered_lines)
        
        # Clean up extra whitespace and empty parentheses
        cleaned = re.sub(r'\(\s*\)', '', cleaned)  # Remove empty parentheses
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 newlines
        cleaned = re.sub(r' +', ' ', cleaned)  # Single spaces
        cleaned = re.sub(r' \n', '\n', cleaned)  # Remove trailing spaces before newlines
        
        return cleaned.strip()
    
    def assess_answer_quality(self, answer: str, documents: List[Document]) -> Dict:
        """Assess the quality of the generated answer"""
        
        quality_metrics = {
            'has_numbers': bool(re.search(r'\d+', answer)),
            'length': len(answer.split()),
            'uses_context': len(documents) > 0,
            'has_structure': bool(re.search(r'(\n\n|1\.|2\.|•|##)', answer)),
        }
        
        # Simple quality score
        score = 0
        if quality_metrics['has_numbers']:
            score += 25
        if quality_metrics['length'] > 50:
            score += 25
        if quality_metrics['uses_context']:
            score += 30
        if quality_metrics['has_structure']:
            score += 20
        
        quality_metrics['quality_score'] = score
        
        return quality_metrics
    
    def answer_question(
        self, 
        question: str, 
        retrieved_docs: List[Document],
        chat_history: List[Dict] = None
    ) -> Dict:
        """
        Generate answer to question using retrieved documents
        """
        
        # Format inputs
        context = self.format_context(retrieved_docs)
        history = self.format_chat_history(chat_history or [])
        
        # Generate answer
        response = self.qa_chain.invoke({
            "context": context,
            "question": question,
            "chat_history": history
        })
        
        # Extract content
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Clean response
        cleaned_response = self.clean_response(response_text)
        
        # Extract sources
        sources = self.extract_sources(retrieved_docs)
        
        # Assess quality
        quality = self.assess_answer_quality(cleaned_response, retrieved_docs)
        
        return {
            'answer': cleaned_response,
            'sources': sources,
            'num_sources': len(sources),
            'num_documents': len(retrieved_docs),
            'quality_metrics': quality
        }
    
    def answer_with_confidence(
        self,
        question: str,
        retrieved_docs: List[Document],
        chat_history: List[Dict] = None,
        min_confidence_threshold: float = 0.3
    ) -> Dict:
        """
        Answer with confidence scoring
        """
        
        result = self.answer_question(question, retrieved_docs, chat_history)
        
        # Calculate confidence based on retrieval quality
        confidence = 0.5  # Base confidence
        
        if result['num_documents'] > 5:
            confidence += 0.2
        if result['quality_metrics']['has_numbers']:
            confidence += 0.15
        if result['quality_metrics']['quality_score'] > 70:
            confidence += 0.15
        
        confidence = min(confidence, 1.0)
        
        result['confidence'] = confidence
        result['is_confident'] = confidence >= min_confidence_threshold
        
        return result