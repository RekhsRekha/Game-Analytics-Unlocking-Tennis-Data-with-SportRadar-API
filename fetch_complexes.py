import socket
import urllib3
import requests
import pandas as pd
import time

def force_ipv4():
    return socket.AF_INET

urllib3.util.connection.allowed_gai_family = force_ipv4

API_KEY = "JBmwD9XiZkgFSXM1v234ZuZI1Kc0uY2EAZfTZY10"  # Replace with your actual key
URL = "https://api.sportradar.com/tennis/trial/v3/en/complexes.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Connection": "close"
}

def main():
    print("Fetching Complexes and Venues...")
    
    for attempt in range(1, 6):
        try:
            time.sleep(3.0)
            response = requests.get(URL, params={"api_key": API_KEY}, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "complexes" in data:
                complexes_rows = []
                venues_rows = []

                for comp in data["complexes"]:
                    complex_id = comp.get("id")
                    complexes_rows.append({
                        "complex_id": complex_id,
                        "complex_name": comp.get("name")
                    })

                    for v in comp.get("venues", []):
                        venues_rows.append({
                            "venue_id": v.get("id"),
                            "venue_name": v.get("name"),
                            "city_name": v.get("city_name", "N/A"),
                            "country_name": v.get("country_name", "N/A"),
                            "country_code": str(v.get("country_code", "N/A"))[:3],
                            "timezone": v.get("timezone", "UTC"),
                            "complex_id": complex_id
                        })

                df_complexes = pd.DataFrame(complexes_rows)
                df_venues = pd.DataFrame(venues_rows)

                df_complexes.to_csv("complexes.csv", index=False)
                df_venues.to_csv("venues.csv", index=False)
                print(f"Success! Saved complexes.csv ({len(df_complexes)} rows) and venues.csv ({len(df_venues)} rows)")
                return

        except Exception as e:
            print(f"Attempt {attempt}/5 failed: {e}")
            time.sleep(4.0)

if __name__ == "__main__":
    main()