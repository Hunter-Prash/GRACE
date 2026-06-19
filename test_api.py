import requests
import json

response = requests.post("http://[::1]:3000/api/chat", json={"text": "search the web for the latest nvidia ceo news", "sessionId": "default"}, timeout=30).json()

print(f"Has searchData: {'searchData' in response}")
if 'searchData' in response:
    print(f"searchData keys: {list(response['searchData'].keys())}")
else:
    print(f"Keys in response: {list(response.keys())}")
