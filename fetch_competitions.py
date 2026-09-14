import socket
import requests
import pandas as pd
import urllib3
from urllib3.util.connection import allowed_gai_family

# Force urllib3 to use IPv4 only
def force_ipv4():
    return socket.AF_INET

urllib3.util.connection.allowed_gai_family = force_ipv4

# Sportradar API configuration
API_KEY = "JBmwD9XiZkgFSXM1v234ZuZI1Kc0uY2EAZfTZY10"  # Replace with your actual key
URL = "https://api.sportradar.com/tennis/trial/v3/en/competitions.json"

def main():
    print("Connecting to Sportradar Tennis API via IPv4...")
    params = {"api_key": API_KEY}
    
    # Custom Headers to bypass ISP bot/CLI blocking filters
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Connection": "keep-alive"
    }
    
    try:
        session = requests.Session()
        response = session.get(URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        competitions = data.get("competitions", [])
        print(f"Success! Status Code 200 - Retrieved {len(competitions)} competitions.")
        
        # Convert JSON payload into a pandas DataFrame
        df = pd.json_normalize(competitions)
        
        # Save dataset locally
        csv_filename = "tennis_competitions.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Saved dataset successfully to '{csv_filename}'")
        
        # Preview top rows
        print("\nDataset Preview:")
        preview_cols = [c for c in ['id', 'name', 'type', 'gender'] if c in df.columns]
        print(df[preview_cols].head())

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    main()