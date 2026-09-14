import socket
import urllib3
import requests
import pandas as pd
import time

# Force urllib3 to use IPv4 sockets
def force_ipv4():
    return socket.AF_INET

urllib3.util.connection.allowed_gai_family = force_ipv4

API_KEY = "JBmwD9XiZkgFSXM1v234ZuZI1Kc0uY2EAZfTZY10"  # Replace with your actual key
BASE_URL = "https://api.sportradar.com/tennis/trial/v3/en"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Connection": "close"  # Disables connection pooling to stop Jio 10054 resets
}

def fetch_json_direct(endpoint, max_retries=4):
    url = f"{BASE_URL}/{endpoint}"
    params = {"api_key": API_KEY}
    
    for attempt in range(1, max_retries + 1):
        try:
            # Enforce 2.5-second pause to strictly respect the 1 req/sec trial rate limit
            time.sleep(2.5) 
            
            # Using direct requests.get instead of persistent Session prevents Jio resets
            response = requests.get(url, params=params, headers=HEADERS, timeout=25)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f" HTTP Error on '{endpoint}': {http_err}")
            break # Do not retry 403 or 404 errors
        except Exception as e:
            print(f" Attempt {attempt}/{max_retries} failed for '{endpoint}': {e}")
            if attempt < max_retries:
                time.sleep(4.0 * attempt)
    return None

def main():
    print("Starting Sportradar API Data Extraction...\n")

    # ---------------------------------------------------------
    # 1. Fetch Competitions & Categories
    # ---------------------------------------------------------
    print("1/3 Fetching Competitions and Categories...")
    comp_data = fetch_json_direct("competitions.json")
    
    if comp_data and "competitions" in comp_data:
        categories_dict = {}
        competitions_rows = []

        for c in comp_data["competitions"]:
            cat = c.get("category", {})
            cat_id = cat.get("id")
            if cat_id and cat_id not in categories_dict:
                categories_dict[cat_id] = cat.get("name", "Unknown")

            competitions_rows.append({
                "competition_id": c.get("id"),
                "competition_name": c.get("name"),
                "parent_id": c.get("parent_id"),
                "type": c.get("type"),
                "gender": c.get("gender"),
                "category_id": cat_id
            })

        df_categories = pd.DataFrame([{"category_id": k, "category_name": v} for k, v in categories_dict.items()])
        df_competitions = pd.DataFrame(competitions_rows)

        df_categories.to_csv("categories.csv", index=False)
        df_competitions.to_csv("competitions.csv", index=False)
        print(f" Saved categories.csv ({len(df_categories)} rows) and competitions.csv ({len(df_competitions)} rows)")

    # ---------------------------------------------------------
    # 2. Fetch Complexes & Venues
    # ---------------------------------------------------------
    print("\n2/3 Fetching Complexes and Venues...")
    complex_data = fetch_json_direct("complexes.json")
    
    if complex_data and "complexes" in complex_data:
        complexes_rows = []
        venues_rows = []

        for comp in complex_data["complexes"]:
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
        print(f" Saved complexes.csv ({len(df_complexes)} rows) and venues.csv ({len(df_venues)} rows)")

    # ---------------------------------------------------------
    # 3. Fetch Doubles Competitor Rankings
    # ---------------------------------------------------------
    print("\n3/3 Fetching Doubles Competitor Rankings...")
    # Exact trial endpoint specified in project specification
    rankings_data = fetch_json_direct("double_competitors_rankings.json")

    if rankings_data and "rankings" in rankings_data:
        competitors_dict = {}
        rankings_rows = []

        for r_group in rankings_data["rankings"]:
            items = r_group.get("competitor_rankings") or r_group.get("competitors") or []
            for item in items:
                comp = item.get("competitor", {})
                comp_id = comp.get("id")

                if comp_id and comp_id not in competitors_dict:
                    competitors_dict[comp_id] = {
                        "competitor_id": comp_id,
                        "name": comp.get("name", "Unknown"),
                        "country": comp.get("country", "Unknown"),
                        "country_code": str(comp.get("country_code", "UNK"))[:3],
                        "abbreviation": comp.get("abbreviation", "N/A")
                    }

                rankings_rows.append({
                    "rank": item.get("rank", 0),
                    "movement": item.get("movement", 0),
                    "points": item.get("points", 0),
                    "competitions_played": item.get("competitions_played", 0),
                    "competitor_id": comp_id
                })

        df_competitors = pd.DataFrame(list(competitors_dict.values()))
        df_rankings = pd.DataFrame(rankings_rows)

        df_competitors.to_csv("competitors.csv", index=False)
        df_rankings.to_csv("rankings.csv", index=False)
        print(f" Saved competitors.csv ({len(df_competitors)} rows) and rankings.csv ({len(df_rankings)} rows)")

    print("\nExtraction complete!")

if __name__ == "__main__":
    main()