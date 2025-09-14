import requests

# API endpoint URL
url = 'http://localhost:8000/preprocess'

# Path to your CSV file
csv_file_path = 'geo_locations_astana_hackathon'

# Open and send the file
with open(csv_file_path, 'rb') as file:
    files = {'file': ('geo_locations_astana_hackathon.csv', file, 'text/csv')}
    response = requests.post(url, files=files)

# Check the response
if response.status_code == 200:
    result = response.json()
    print("Success! First 5 edges with costs:")
    for edge in result['edges'][:5]:
        print(f"Edge (u={edge['u']}, v={edge['v']}, k={edge['k']}) -> cost: {edge['c']:.2f}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)