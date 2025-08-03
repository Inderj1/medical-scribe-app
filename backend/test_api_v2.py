"""Quick API test to verify v2 implementation"""
import requests
import json

# Test endpoints
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_agent_status():
    """Test agent status endpoint"""
    response = requests.get(f"{BASE_URL}/api/v1/agents/status")
    print(f"\nAgent Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_root():
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print(f"\nRoot Endpoint: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing Medical Scribe API v2...")
    print("="*50)
    
    tests = [
        ("Root", test_root),
        ("Health", test_health),
        ("Agent Status", test_agent_status)
    ]
    
    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} test passed")
            else:
                print(f"✗ {name} test failed")
        except Exception as e:
            print(f"✗ {name} test error: {e}")
    
    print(f"\nTotal: {passed}/{len(tests)} tests passed")