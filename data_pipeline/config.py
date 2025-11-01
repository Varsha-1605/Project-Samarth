DATA_GOV_API_KEY = "579b464db66ec23bdd000001879abcda89f64ed3614f510926894f9e"

DATASET_IDS = {
    "agriculture": [
        {
            "id": "35be999b-0208-4354-b557-f6ca9a5355de",
            "name": "Crop Production Data",
            "category": "agriculture",
            "description": "State and district-wise crop production data including area and production"
        },
        {
            "id": "0bc5ead8-b329-4577-8bf2-4c0c40c4b877",
            "name": "Horticulture Production",
            "category": "agriculture",
            "description": "Fruits, vegetables, flowers, nuts, spices production data"
        },
        {
            "id": "12e7661e-1b97-4f8c-a901-33844fa5412d",
            "name": "Major Crops Production",
            "category": "agriculture",
            "description": "Production data for major crops by year"
        },
        {
            "id": "50bc5a96-d6d5-483e-92b1-2d8fe09f0a0d",
            "name": "Irrigation Methods Comparison",
            "category": "agriculture",
            "description": "Water usage and yield comparison between traditional and drip irrigation"
        },
        {
            "id": "4186e93e-64fd-4e31-89d3-1dde0ec869c9",
            "name": "Fertilizer Import Data",
            "category": "agriculture",
            "description": "Monthly fertilizer import data by port and product"
        },
        {
            "id": "35985678-0d79-46b4-9ed6-6f13308a1d24",
            "name": "Agricultural Market Prices",
            "category": "agriculture",
            "description": "Commodity prices across different markets and states"
        }
    ],
    "climate": [
        {
            "id": "440dbca7-86ce-4bf6-b1af-83af2855757e",
            "name": "Subdivision Rainfall Data",
            "category": "climate",
            "description": "Monthly and annual rainfall data by subdivision"
        },
        {
            "id": "722e2530-dcb1-4104-bd8f-5a0b22e68999",
            "name": "Regional Rainfall Data",
            "category": "climate",
            "description": "Monthly and annual rainfall data by region"
        },
        {
            "id": "40e1b431-eae6-4ab2-8587-b8ddbdd6bf1c",
            "name": "Monsoon Rainfall",
            "category": "climate",
            "description": "Monsoon season rainfall data"
        },
        {
            "id": "4aea13fa-48a8-41c5-8471-73980a936f68",
            "name": "Temperature Data",
            "category": "climate",
            "description": "Monthly and annual temperature data"
        },
        {
            "id": "d35d7fcb-5b89-4c08-b96f-dd4916453421",
            "name": "Temperature Range Data",
            "category": "climate",
            "description": "Min and max temperature ranges by season"
        }
    ]
}

# Advanced RAG Configuration
RAG_CONFIG = {
    # Chunking settings
    "semantic_chunk_size": 800,
    "semantic_chunk_overlap": 150,
    "min_chunk_size": 300,
    "max_chunk_size": 1200,
    
    # Retrieval settings
    "initial_retrieval_k": 50,
    "post_fusion_k": 30,
    "post_rerank_k": 15,
    "final_context_k": 8,
    
    # Scoring weights
    "dense_weight": 0.5,
    "sparse_weight": 0.3,
    "metadata_weight": 0.2,
    
    # Query enhancement
    "enable_query_expansion": True,
    "enable_hyde": True,
    "max_query_variations": 3,
    
    # Reranking
    "cross_encoder_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "mmr_lambda": 0.7,  # Balance between relevance and diversity
    
    # Context compression
    "enable_compression": True,
    "compression_ratio": 0.6,  # Keep 60% of content
}

# Domain-specific keywords for agricultural data
DOMAIN_KEYWORDS = {
    "crops": [
        "wheat", "rice", "cotton", "sugarcane", "soyabean", "maize", "bajra",
        "jowar", "barley", "gram", "tur", "groundnut", "sunflower", "rapeseed",
        "mustard", "coconut", "arecanut", "cashew", "tea", "coffee", "rubber"
    ],
    "states": [
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
        "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
        "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
        "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
        "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal"
    ],
    "metrics": [
        "production", "yield", "area", "rainfall", "temperature", "irrigation",
        "fertilizer", "price", "export", "import", "consumption", "harvest"
    ],
    "climate_terms": [
        "monsoon", "precipitation", "humidity", "drought", "flood", "cyclone",
        "rainfall pattern", "climate change", "seasonal variation", "weather"
    ]
}

# Synonym mapping for query expansion
SYNONYM_MAP = {
    "production": ["yield", "output", "harvest", "cultivation"],
    "rainfall": ["precipitation", "monsoon", "rain"],
    "temperature": ["temp", "heat", "thermal"],
    "crop": ["produce", "agricultural product", "farming output"],
    "area": ["acreage", "land", "cultivation area"],
    "farmer": ["cultivator", "agriculturist", "grower"],
    "price": ["cost", "rate", "value", "market price"],
}

DATASET_CACHE_DIR = "data_cache"
VECTOR_STORE_DIR = "vector_store"