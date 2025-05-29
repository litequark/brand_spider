import os
import json
import csv
import requests
import time

# Constants
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "nio.csv")

# Path to the JSON file containing all store information
# Make sure this path is correct and the file exists
ALL_STORES_JSON_PATH = r"d:\brand_spider\scripts\.json"  # Using raw string for Windows path

# Updated URL from cURL command
DETAIL_API_URL = "https://chargermap-fe-gateway.nio.com/pe/bff/gateway/powermap/h5/charge-map/v2/outlets/detail?app_ver=5.2.0&client=pc&container=brower&lang=zh&region=CN&app_id=100119&channel=officialMap&brand=nio&timestamp=1748513178"

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def get_store_details(store_id, point_type, point_sub_type):
    """Fetches additional details for a store, including the phone number and address."""
    payload = {
        "outlets_id": store_id,
        "type": point_type ,
        "subType": point_sub_type
    }
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'Content-Type': 'application/json',
        'DNT': '1',
        'sec-ch-ua-mobile': '?0',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'host': 'chargermap-fe-gateway.nio.com'
    }
    try:
        response = requests.post(DETAIL_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        detail_data = response.json()

        phone_number = None
        address = None
        if detail_data.get('data') and isinstance(detail_data['data'], dict):
            phone_number = detail_data['data'].get('phone')
            address = detail_data['data'].get('address') # Extract address

        return phone_number, address # Return both phone and address
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for store {store_id}: {e}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for store {store_id}: {response.text}")
    return None, None # Return None for both if error


def main():
    """Main function to scrape NIO store information."""
    all_store_data = []

    try:
        with open(ALL_STORES_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {ALL_STORES_JSON_PATH} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {ALL_STORES_JSON_PATH}.")
        return

    if 'data' not in data or 'resources' not in data['data']:
        print("Error: JSON structure is not as expected. Missing 'data' or 'data.resources'.")
        return

    stores = data['data']['resources']
    print(f"Found {len(stores)} total entries in the JSON file.")

    processed_stores = 0
    for store in stores:
        # We are interested in 'nio_store' types as per your screenshot
        if store.get('point_type') == 'nio_store':
            store_id = store.get('id')
            name = store.get('name')
            point_type = store.get('point_type')  # e.g., 'nio_store'
            point_sub_type = store.get('point_sub_type')  # e.g., 'nio_space', 'nio_house'
            location_str = store.get('location')  # e.g., "109.055,34.222"

            # Placeholder for address components - to be implemented with geocoding
            province_name = ""
            city_name = ""
            district_name = "" # District extraction can be complex, keeping it simple for now
            full_address_from_detail = ""

            print(f"Processing store: {name} (ID: {store_id}) - Type: {point_type}, SubType: {point_sub_type}")

            phone_number, address_from_detail = get_store_details(store_id, point_type, point_sub_type)
            
            if not phone_number:
                phone_number = "N/A"
            
            if address_from_detail:
                full_address_from_detail = address_from_detail
                # Basic parsing for province and city from address_from_detail
                # This is a simplified approach and might need refinement
                if '省' in address_from_detail:
                    province_name = address_from_detail.split('省')[0] + '省'
                    remaining_address = address_from_detail.split('省')[1]
                    if '市' in remaining_address:
                        city_name = remaining_address.split('市')[0] + '市'
                elif '市' in address_from_detail: # For municipalities or addresses without '省'
                    # Check for common municipalities first to avoid splitting them incorrectly
                    municipalities = ["北京市", "上海市", "天津市", "重庆市"]
                    found_municipality = False
                    for m in municipalities:
                        if address_from_detail.startswith(m):
                            city_name = m
                            province_name = m # For municipalities, province and city are often the same
                            found_municipality = True
                            break
                    if not found_municipality:
                        # General case if '市' is present but not a known municipality start
                        # This might incorrectly pick up city if province is missing but city is present
                        # e.g. "江苏省苏州市" vs "苏州市工业园区"
                        # A more robust solution would use a proper address parsing library or regex
                        parts = address_from_detail.split('市')
                        if len(parts) > 1:
                             # Attempt to capture characters before the first '市' as city
                             # This is a heuristic and might not always be province if province is missing
                            potential_city_or_province = parts[0] + '市'
                            # Heuristic: if it ends with '市' and is short, likely a city.
                            # If it's a known province name (e.g. from provinces.json), it's a province.
                            # For simplicity, we'll assign to city_name. Province might remain empty or be set if it's a municipality.
                            city_name = potential_city_or_province
                            # If province_name is still empty, and city_name looks like a province (e.g. ends with 市 but is a province name)
                            # This part needs a list of provinces to check against, or a more sophisticated parser.
                            # For now, we'll leave province_name as is if not a municipality.

            # Use address from detail if available, otherwise fallback to lat/lon
            current_address_to_display = full_address_from_detail
            if not current_address_to_display and location_str:
                try:
                    lon, lat = location_str.split(',')
                    current_address_to_display = f"Lat: {lat}, Lon: {lon}"
                except ValueError:
                    print(f"Warning: Could not parse location_str for store {name}: {location_str}")

            store_type_display = point_sub_type

            row = {
                "省": province_name,
                "Province": province_name, # Placeholder, ideally use location_translator
                "市区辅助": city_name, 
                "City": city_name, # Placeholder, ideally use location_translator
                "区": district_name,
                "店名": name,
                "类型": store_type_display,
                "地址": current_address_to_display,
                "电话": phone_number,
                "备注": ""
            }
            all_store_data.append(row)
            processed_stores += 1

            time.sleep(0.5)  # Adjust as needed

    print(f"Processed {processed_stores} stores of type 'nio_store'.")

    # Write to CSV
    if all_store_data:
        try:
            with open(OUTPUT_PATH, 'w', newline='',
                      encoding='utf-8-sig') as csvfile:  # utf-8-sig for Excel compatibility
                writer = csv.DictWriter(csvfile, fieldnames=RESULT_FIELDS)
                writer.writeheader()
                writer.writerows(all_store_data)
            print(f"Successfully wrote {len(all_store_data)} store entries to {OUTPUT_PATH}")
        except IOError:
            print(f"Error: Could not write to CSV file {OUTPUT_PATH}.")
    else:
        print("No store data to write to CSV.")


if __name__ == "__main__":
    main()