import requests

# Try different potential endpoints
endpoints = [
    "https://candidateapi.jobvision.ir/api/v1/JobPost/GetAll",
    "https://candidateapi.jobvision.ir/api/v1/jobs",
    "https://candidateapi.jobvision.ir/api/v1/JobPost/List",
    "https://jobvision.ir/api/jobs",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for endpoint in endpoints:
    try:
        response = requests.get(endpoint, headers=headers, timeout=5)
        print(f"\n{endpoint}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS! Response:")
            print(response.json())
            break
    except Exception as e:
        print(f"Error: {e}")