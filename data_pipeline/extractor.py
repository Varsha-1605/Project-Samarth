import requests
import json
import os
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from data_pipeline.config import DATA_GOV_API_KEY, DATASET_IDS, DATASET_CACHE_DIR

class DataExtractor:
    def __init__(self):
        self.api_key = DATA_GOV_API_KEY
        self.base_url = "https://api.data.gov.in/resource"
        self.cache_dir = DATASET_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_dataset(self, dataset_id: str, limit: int = 1000) -> Optional[Dict]:
        url = f"{self.base_url}/{dataset_id}"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"Failed to fetch {dataset_id}: Status {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching {dataset_id}: {str(e)}")
            return None
    
    def clean_record(self, record: Dict) -> Dict:
        cleaned = {}
        for key, value in record.items():
            if value in ['NA', 'N.A.', 'na', '']:
                cleaned[key] = None
            elif isinstance(value, str):
                try:
                    cleaned[key] = float(value.replace(',', ''))
                except:
                    cleaned[key] = value
            else:
                cleaned[key] = value
        return cleaned
    
    def standardize_dataset(self, data: Dict, dataset_info: Dict) -> List[Dict]:
        if not data or 'records' not in data:
            return []
        
        records = data['records']
        cleaned_records = []
        
        for record in records:
            cleaned = self.clean_record(record)
            cleaned['_dataset_id'] = dataset_info['id']
            cleaned['_dataset_name'] = dataset_info['name']
            cleaned['_dataset_category'] = dataset_info['category']
            cleaned_records.append(cleaned)
        
        return cleaned_records
    
    def save_to_cache(self, dataset_id: str, data: List[Dict]):
        cache_file = os.path.join(self.cache_dir, f"{dataset_id}.json")
        with open(cache_file, 'w') as f:
            json.dump({
                'dataset_id': dataset_id,
                'fetched_at': datetime.utcnow().isoformat(),
                'record_count': len(data),
                'records': data
            }, f, indent=2)
    
    def load_from_cache(self, dataset_id: str) -> Optional[List[Dict]]:
        cache_file = os.path.join(self.cache_dir, f"{dataset_id}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data.get('records', [])
        return None
    
    def extract_all_datasets(self, force_refresh: bool = False):
        all_data = {
            'agriculture': [],
            'climate': []
        }
        
        for category in ['agriculture', 'climate']:
            for dataset_info in DATASET_IDS[category]:
                dataset_id = dataset_info['id']
                
                if not force_refresh:
                    cached_data = self.load_from_cache(dataset_id)
                    if cached_data:
                        print(f"Loaded {dataset_id} from cache: {len(cached_data)} records")
                        all_data[category].extend(cached_data)
                        continue
                
                print(f"Fetching {dataset_info['name']} ({dataset_id})...")
                raw_data = self.fetch_dataset(dataset_id)
                
                if raw_data:
                    cleaned_data = self.standardize_dataset(raw_data, dataset_info)
                    self.save_to_cache(dataset_id, cleaned_data)
                    all_data[category].extend(cleaned_data)
                    print(f"  Fetched and cleaned {len(cleaned_data)} records")
                else:
                    print(f"  No data fetched for {dataset_id}")
                
                time.sleep(1)
        
        return all_data
    
    def get_dataset_summary(self) -> Dict:
        summary = {}
        for category in ['agriculture', 'climate']:
            for dataset_info in DATASET_IDS[category]:
                dataset_id = dataset_info['id']
                cached_data = self.load_from_cache(dataset_id)
                summary[dataset_id] = {
                    'name': dataset_info['name'],
                    'category': category,
                    'cached': cached_data is not None,
                    'record_count': len(cached_data) if cached_data else 0
                }
        return summary