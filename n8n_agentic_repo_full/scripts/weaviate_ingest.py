# scripts/weaviate_ingest.py
# Simple script to ingest plain-text documents into Weaviate via REST API.
# Requires: requests, python-dotenv (optional)
#
# This script demonstrates the upsert pattern: read files from a folder,
# compute embeddings using an embedding provider (not included), and upsert into Weaviate.
# You must run an embedding step (OpenAI embeddings or local embedding model) and set vector in payload.

import os
import json
import requests

WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
CLASS_NAME = 'Document'

def create_schema():
    url = WEAVIATE_URL + '/v1/schema'
    schema = {
        "classes": [
            {
                "class": CLASS_NAME,
                "properties": [
                    {"name": "title", "dataType": ["text"]},
                    {"name": "content", "dataType": ["text"]},
                    {"name": "excerpt", "dataType": ["text"]}
                ]
            }
        ]
    }
    r = requests.post(url, json=schema)
    print('schema status', r.status_code, r.text)

def upsert_document(title, content, vector=None):
    url = WEAVIATE_URL + f'/v1/objects'
    payload = {
        "class": CLASS_NAME,
        "properties": {
            "title": title,
            "content": content,
            "excerpt": content[:300]
        }
    }
    if vector:
        payload['vector'] = vector
    r = requests.post(url, json=payload)
    print('upsert', r.status_code, r.text)

if __name__ == '__main__':
    # example ingest of txt files in ./data/docs
    docs_dir = './data/docs'
    for fname in os.listdir(docs_dir):
        if not fname.endswith('.txt'):
            continue
        with open(os.path.join(docs_dir, fname), 'r', encoding='utf-8') as f:
            text = f.read()
        upsert_document(fname, text)
    print('done')
