#!/usr/bin/env python3
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key starts with: {api_key[:10]}..." if api_key else "No API key found")

try:
    client = OpenAI(api_key=api_key)
    
    # Test with a simple model list
    print("\nTesting model list endpoint...")
    models = client.models.list()
    print(f"Successfully connected! Found {len(list(models))} models")
    
    # Test Whisper
    print("\nTesting Whisper model availability...")
    whisper_models = [m for m in client.models.list() if 'whisper' in m.id.lower()]
    print(f"Whisper models available: {[m.id for m in whisper_models]}")
    
except Exception as e:
    print(f"\nError: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()