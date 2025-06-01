import requests
import csv
import os
import json
from time import sleep
import random

from scripts.util.location_translator import get_en_province, get_en_city

BRAND_MAPPING = {
    "JK": "华为问界",
    "CH": "华为智界",
    "BQ": "华为享界"
}
def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]
API_URL = "https://cbg.huawei.com/isrp/lms/store-info/car-store-list/query"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/huawei.csv")


def fetch_stores(brand_code):
    payload = {"brandCodes": [brand_code]}
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return data["result"]
        return []
    except Exception as e:
        print(f"品牌 {brand_code} 抓取失败: {str(e)}")
        return []


def process_store(store, brand_name):
    """处理单条门店数据并打印"""
    processed = {
        "品牌": brand_name,
        "省": store.get("province", ""),
        "Province": get_en_province(store.get("province", "")),  # 实际项目中可能需要中英文转换
        "City/Area": get_en_city(store.get("cityName")),
        "区": store.get("county", ""),
        "店名": store["storeName"],
        "类型": store.get("vehicleStoreTypeCn", "体验中心"),
        "地址": store["storeAddress"],
        "电话": store.get("fixedLinePhoneNumber", ""),
        "市区辅助": store.get("cityName"),  # 根据实际需求补充地理编码数据
        "备注": ""
    }

    # 打印完整信息（包含经纬度等详细信息）
    print(f"【{brand_name}】新增门店：{json.dumps(processed, ensure_ascii=False, indent=2)}")
    return processed


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()

        total_count = 0
        for code, brand in BRAND_MAPPING.items():
            stores = fetch_stores(code)
            print(f"\n开始处理品牌 {brand}({code})，共发现 {len(stores)} 家门店")

            for store in stores:
                row = process_store(store, brand)
                writer.writerow(row)
                total_count += 1
                sleep_with_random(1,1)  # 避免请求过快

    print(f"\n 数据抓取完成！共获取 {total_count} 家门店数据，已保存至：{OUTPUT_PATH}")



main()