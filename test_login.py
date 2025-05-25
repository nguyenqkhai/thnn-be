import requests
import json

def test_login():
    url = "http://localhost:8000/api/v1/auth/login"
    
    # Test data
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        print("Testing login API...")
        print(f"URL: {url}")
        print(f"Data: {data}")
        
        response = requests.post(url, data=data, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {result.get('access_token', 'N/A')}")
            print(f"Token Type: {result.get('token_type', 'N/A')}")
        else:
            print("❌ Login failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_login()
