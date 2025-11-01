import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import threading

from database.schema import init_db, get_db_session, ChatSession, ChatMessage
from data_pipeline.extractor import DataExtractor
from rag_system.embeddings import EmbeddingManager
from rag_system.rag_pipeline import AdvancedRAGPipeline, SimpleRAGPipeline

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Get port from environment variable - Hugging Face uses 7860
PORT = int(os.getenv('PORT', 7860))

# Global variables
openai_api_key = os.getenv('OPENAI_API_KEY')
embedding_manager = None
rag_pipeline = None
use_advanced_rag = True
system_initialized = False
initialization_lock = threading.Lock()
initialization_error = None


def initialize_system():
    """Initialize the complete RAG system (called lazily on first request)"""
    global embedding_manager, rag_pipeline, system_initialized, initialization_error
    
    with initialization_lock:
        # Check if already initialized
        if system_initialized:
            return True
        
        if not openai_api_key:
            print("ERROR: OPENAI_API_KEY not set. Cannot initialize RAG system.")
            initialization_error = "OPENAI_API_KEY not configured"
            return False
        
        try:
            print("\n" + "="*60)
            print("STARTING SYSTEM INITIALIZATION")
            print("="*60 + "\n")
            
            # Initialize database
            init_db()
            print("✓ Database initialized")
            
            # Initialize data extractor
            extractor = DataExtractor()
            data_summary = extractor.get_dataset_summary()
            print(f"✓ {len(data_summary)} datasets available")
            
            # Initialize embedding manager
            embedding_manager = EmbeddingManager(openai_api_key)
            
            # Try to load existing vector store
            vector_store = embedding_manager.load_vector_store("main")
            all_documents = embedding_manager.load_documents("main")
            
            if not vector_store or not all_documents:
                print("\n⚠ Vector store not found. Building from cached data...")
                print("This may take several minutes...\n")
                
                # Extract data
                all_data = extractor.extract_all_datasets(force_refresh=False)
                
                # Build with advanced chunking
                vector_store, all_documents = embedding_manager.build_and_save_vector_store(
                    all_data,
                    name="main",
                    use_advanced_chunking=True
                )
                
                print("✓ Vector store created and saved")
            else:
                print("✓ Vector store loaded from cache")
                print(f"✓ {len(all_documents)} documents loaded")
            
            # Initialize RAG pipeline
            if use_advanced_rag:
                print("\nInitializing Advanced RAG Pipeline...")
                rag_pipeline = AdvancedRAGPipeline(
                    vector_store,
                    all_documents,
                    openai_api_key
                )
                print("✓ Advanced RAG Pipeline ready!")
            else:
                print("\nInitializing Simple RAG Pipeline...")
                rag_pipeline = SimpleRAGPipeline(vector_store, openai_api_key)
                print("✓ Simple RAG Pipeline ready!")
            
            system_initialized = True
            
            print("\n" + "="*60)
            print("SYSTEM INITIALIZATION COMPLETE")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR during initialization: {str(e)}")
            import traceback
            traceback.print_exc()
            initialization_error = str(e)
            return False


def ensure_system_initialized():
    """Ensure system is initialized before processing requests"""
    global system_initialized, initialization_error
    
    if not system_initialized and initialization_error is None:
        # Try to initialize
        success = initialize_system()
        if not success:
            return False, initialization_error or "System initialization failed"
    
    if not system_initialized:
        return False, initialization_error or "System not ready"
    
    return True, None


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - always responds quickly"""
    return jsonify({
        'status': 'ok',
        'system_ready': system_initialized,
        'rag_mode': 'advanced' if use_advanced_rag else 'simple',
        'openai_configured': openai_api_key is not None,
        'initialization_error': initialization_error
    })


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new chat session"""
    try:
        session_id = str(uuid.uuid4())
        db = get_db_session()
        
        session = ChatSession(session_id=session_id)
        db.add(session)
        db.commit()
        db.close()
        
        return jsonify({
            'session_id': session_id,
            'created_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint with advanced RAG"""
    try:
        # Ensure system is initialized
        is_ready, error = ensure_system_initialized()
        if not is_ready:
            return jsonify({
                'error': f'System not initialized: {error}. Please wait a moment and try again.'
            }), 503
        
        # Parse request
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', '')
        category = data.get('category')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Get database session
        db = get_db_session()
        
        # Retrieve chat history
        chat_history = []
        if session_id:
            messages = db.query(ChatMessage)\
                .filter_by(session_id=session_id)\
                .order_by(ChatMessage.timestamp)\
                .all()
            
            chat_history = [
                {'role': msg.role, 'content': msg.content} 
                for msg in messages
            ]
        
        # Process query with RAG pipeline
        print(f"\n{'='*60}")
        print(f"New Query: {question}")
        print(f"Session: {session_id[:8]}...")
        print(f"{'='*60}")
        
        result = rag_pipeline.process_query(
            question,
            chat_history=chat_history,
            category=category,
            enable_all_features=use_advanced_rag
        )
        
        # Save to database
        if session_id:
            # Save user message
            user_msg = ChatMessage(
                session_id=session_id,
                role='user',
                content=question,
                sources=None
            )
            db.add(user_msg)
            
            # Save assistant message
            assistant_msg = ChatMessage(
                session_id=session_id,
                role='assistant',
                content=result['answer'],
                sources=result['sources']
            )
            db.add(assistant_msg)
            
            # Update session activity
            session = db.query(ChatSession)\
                .filter_by(session_id=session_id)\
                .first()
            
            if session:
                session.last_active = datetime.utcnow()
            
            db.commit()
        
        db.close()
        
        # Prepare response
        response = {
            'answer': result['answer'],
            'sources': result['sources'],
            'num_sources': result['num_sources'],
            'num_documents': result.get('num_documents', 0),
        }
        
        # Add advanced features info if available
        if 'confidence' in result:
            response['confidence'] = result['confidence']
        
        if 'pipeline_info' in result:
            response['pipeline_info'] = result['pipeline_info']
        
        return jsonify(response)
    
    except Exception as e:
        print(f"\n❌ ERROR in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Retrieve chat history for a session"""
    try:
        db = get_db_session()
        messages = db.query(ChatMessage)\
            .filter_by(session_id=session_id)\
            .order_by(ChatMessage.timestamp)\
            .all()
        
        history = []
        for msg in messages:
            history.append({
                'role': msg.role,
                'content': msg.content,
                'sources': msg.sources,
                'timestamp': msg.timestamp.isoformat()
            })
        
        db.close()
        return jsonify({'history': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    """Get information about available datasets"""
    try:
        extractor = DataExtractor()
        summary = extractor.get_dataset_summary()
        return jsonify({'datasets': summary})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/initialize', methods=['POST'])
def trigger_initialization():
    """Manually trigger system initialization"""
    try:
        if system_initialized:
            return jsonify({
                'status': 'already_initialized',
                'message': 'System is already initialized'
            })
        
        success = initialize_system()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'System initialized successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': initialization_error or 'Initialization failed'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rebuild-index', methods=['POST'])
def rebuild_index():
    """Rebuild vector store (admin endpoint)"""
    try:
        if not openai_api_key:
            return jsonify({'error': 'OPENAI_API_KEY not configured'}), 500
        
        print("\n" + "="*60)
        print("REBUILDING VECTOR STORE")
        print("="*60 + "\n")
        
        # Extract fresh data
        extractor = DataExtractor()
        all_data = extractor.extract_all_datasets(force_refresh=True)
        
        # Rebuild with advanced chunking
        global embedding_manager, rag_pipeline
        
        if not embedding_manager:
            embedding_manager = EmbeddingManager(openai_api_key)
        
        vector_store, all_documents = embedding_manager.build_and_save_vector_store(
            all_data,
            name="main",
            use_advanced_chunking=True
        )
        
        # Reinitialize pipeline
        if use_advanced_rag:
            rag_pipeline = AdvancedRAGPipeline(
                vector_store,
                all_documents,
                openai_api_key
            )
        else:
            rag_pipeline = SimpleRAGPipeline(vector_store, openai_api_key)
        
        return jsonify({
            'status': 'success',
            'message': 'Vector store rebuilt successfully',
            'document_count': len(all_documents)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Serve static files
@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)


# Initialize database on startup (quick operation)
try:
    init_db()
    print("✓ Database initialized")
except Exception as e:
    print(f"⚠ Database initialization warning: {e}")


print("\n" + "="*60)
print("PROJECT SAMARTH - ADVANCED RAG SYSTEM")
print("Intelligent Q&A for Agricultural & Climate Data")
print("="*60)
print(f"Port: {PORT}")
print("System will initialize on first request")
print("="*60 + "\n")


if __name__ == '__main__':
    print(f"Starting Flask server on 0.0.0.0:{PORT}...")
    print(f"Access the application at: http://localhost:{PORT}\n")
    app.run(host='0.0.0.0', port=PORT, debug=False)  # debug=False for production