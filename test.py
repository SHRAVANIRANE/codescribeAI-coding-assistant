import requests

headers = {
    "Authorization": "Bearer 685ab5ab-4490-4843-9752-7b1ab954e8bc"
}

response = requests.get("http://127.0.0.1:8000/test-auth", headers=headers)
print(response.json())
