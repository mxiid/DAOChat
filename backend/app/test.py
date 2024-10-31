import requests
import os

api_key = os.getenv("UNSTRUCTURED_API_KEY")
api_url = "https://api.unstructuredapp.io/general/v0/general"

# Create a small test file
with open("test.txt", "w") as f:
    f.write("This is a test document.")

# Send test request
with open("test.txt", "rb") as f:
    response = requests.post(
        api_url, headers={"unstructured-api-key": api_key}, files={"files": f}
    )

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
