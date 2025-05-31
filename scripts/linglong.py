import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException  # Import exceptions here

# Constants provided by the user
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output", "linglong.csv")
URL = "https://www.linglong.cn/product/network.html"


def ensure_output_dir_exists():
    output_dir = os.path.dirname(OUTPUT_PATH)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def scrape_linglong_stores():
    ensure_output_dir_exists()

    # Setup WebDriver (ensure chromedriver is in PATH or specify its location)
    # You might need to configure options, e.g., headless mode
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Optional: run in headless mode
    # options.add_argument('--disable-gpu') # Optional: if running headless on Windows
    driver = webdriver.Chrome(options=options)

    stores_data = []

    try:
        driver.get(URL)
        # Wait for the store list container to be present
        # The user provided HTML snippet suggests the id is 'ajaxList'
        # The page might take time to load all stores, or require interaction (e.g., scrolling)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ajaxList"))
        )
        time.sleep(5)  # Additional wait for dynamic content if necessary

        # The user's HTML snippet shows store items are <li> elements within <ul id="ajaxList">
        store_list_ul = driver.find_element(By.ID, "ajaxList")
        store_items = store_list_ul.find_elements(By.TAG_NAME, "li")

        print(f"Found {len(store_items)} store items.")

        for item_index, item in enumerate(store_items):
            store_name = "[Store name not retrieved]"  # Initialize store_name
            address = "[Address not retrieved]"
            phone = "[Phone not retrieved]"
            try:
                store_name = item.get_attribute("data-title") or store_name  # Keep default if attribute is empty
                address = item.get_attribute("data-address") or address
                phone = item.get_attribute("data-tel") or phone

                store_type = ""  # Default to empty string
                try:
                    wait_for_item_element = WebDriverWait(item, 10)

                    b_tag_brand = wait_for_item_element.until(
                        EC.presence_of_element_located((By.XPATH, ".//b[normalize-space(.)='经营品牌：']"))
                    )

                    parent_p_element = b_tag_brand.find_element(By.XPATH, "./parent::p")
                    parent_p_text = parent_p_element.text

                    if "经营品牌：" in parent_p_text:
                        parts = parent_p_text.split("经营品牌：", 1)
                        if len(parts) > 1:
                            store_type = parts[1].split('\n')[0].strip()
                except TimeoutException:
                    print(
                        f"Timeout waiting for '经营品牌' in item {item_index + 1} (Store: {store_name}). HTML: {item.get_attribute('outerHTML')}")
                except NoSuchElementException:
                    print(
                        f"Could not find '经营品牌' for item {item_index + 1} (Store: {store_name}). HTML: {item.get_attribute('outerHTML')}")
                except Exception as e_type:
                    print(
                        f"Error extracting type for item {item_index + 1} (Store: {store_name}): {e_type}. HTML: {item.get_attribute('outerHTML')}")

                # For Province, City, District - these need to be parsed from the address or found elsewhere
                # For now, we'll leave them blank or try a very basic split if possible.
                # This part will likely need a more sophisticated address parsing utility.
                province = ""
                city = ""
                district = ""
                # Example: Attempt to parse from address (very basic, needs improvement)
                # This is a placeholder and likely won't be accurate for all addresses.
                # You might need to use a geocoding library or a more complex regex.
                if address:
                    # A more robust solution would involve a proper address parser or geocoding service.
                    # For now, let's assume the first few characters might give a hint for province/city.
                    # This is highly dependent on address format and not reliable.
                    pass  # Placeholder for address parsing logic

                stores_data.append({
                    "省": province,
                    "Province": province,  # Assuming Chinese province name can be used for English too initially
                    "市区辅助": city,
                    "City": city,  # Assuming Chinese city name can be used for English too initially
                    "区": district,
                    "店名": store_name,
                    "类型": store_type,
                    "地址": address,
                    "电话": phone,
                    "备注": ""
                })
            except Exception as e:
                # Ensure store_name is defined for this outer exception message as well
                current_store_name = store_name if store_name != "[Store name not retrieved]" else "N/A (error before name retrieval)"
                print(
                    f"Error processing one store item {item_index + 1} (Store: {current_store_name}): {e}. HTML: {item.get_attribute('outerHTML')}")
                continue

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        driver.quit()

    # Write to CSV
    if stores_data:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=RESULT_FIELDS)
            writer.writeheader()
            writer.writerows(stores_data)
        print(f"Data successfully written to {OUTPUT_PATH}")
    else:
        print("No data was scraped.")


if __name__ == "__main__":
    scrape_linglong_stores()