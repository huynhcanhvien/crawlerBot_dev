#!/usr/bin/env python3
"""
Simple test to check if API is running
"""
import requests
import time

def test_api():
    """Test if API is accessible"""
    ports = [5000, 5001, 5002, 5003]
    
    for port in ports:
        try:
            print(f"Testing port {port}...")
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ API is running on port {port}")
                print(f"Response: {response.json()}")
                
                # Try swagger
                swagger_url = f"http://localhost:{port}/apidocs/"
                print(f"\nTrying Swagger UI at {swagger_url}")
                swagger_response = requests.get(swagger_url, timeout=2)
                if swagger_response.status_code == 200:
                    print(f"✅ Swagger UI is accessible at {swagger_url}")
                else:
                    print(f"❌ Swagger UI not accessible (status: {swagger_response.status_code})")
                
                return True
        except requests.exceptions.ConnectionError:
            print(f"❌ Port {port} - Connection refused")
        except requests.exceptions.Timeout:
            print(f"❌ Port {port} - Timeout")
        except Exception as e:
            print(f"❌ Port {port} - Error: {e}")
    
    print("\n❌ API is not accessible on any tested port")
    return False

if __name__ == "__main__":
    print("🔍 Testing API availability...")
    test_api()