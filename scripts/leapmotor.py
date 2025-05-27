import requests
import csv
import os
import json
import time
import random
from typing import List, Dict

BASE_URL = "https://store-center.leapmotor.cn/leap-store/storeDrainage"
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PROJECT_ROOT = os.path.dirname(OUTPUT_DIR)
CSV_PATH = os.path.join(PROJECT_ROOT, "leapmotor.csv")


def get_province_cities() -> List[Dict]:

    try:
        response = requests.get(
            f"{BASE_URL}/getAllProvinceCityStore",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200:
            data = response.json()
            # 合并provinceList和cityList（关键修复点）
            return data.get('data', {}).get('cityList', []) + data.get('data', {}).get('provinceList', [])
    except Exception as e:
        print(f"获取省市数据失败: {str(e)}")
    return []


def fetch_stores(province: Dict) -> List[Dict]:

    if not province.get("areaShopCityCode"):
        return []

    params = {
        "storeType": 0,
        "provinceCode": province["areaShopProvinceCode"],
        "cityCode": province["areaShopCityCode"]
    }

    try:
        response = requests.get(
            f"{BASE_URL}/getLastStoreInfo",
            params=params,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('data', {}).get('recommend', [])
    except Exception as e:
        print(f"请求失败: {province.get('areaShopCity', '未知城市')} - {str(e)}")
    return []


def process_store(store: Dict) -> Dict:

    return {
        "品牌": "零跑汽车",
        "省": store.get("areaShopProvince", ""),
        "Province": "",  # 省份编码
        "市区辅助": store.get("areaShopCity", ""),  # 城市编码
        "City/Area": "",  # 城市名称
        "区": store.get("areaShopDistrict", ""),
        "店名": store.get("storeName", "未知店铺"),
        "类型": "",
        "地址": store.get("site", ""),
        "电话": store.get("salePhone") or store.get("areaShopTell", ""),
        "备注": ""
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    provinces = get_province_cities()
    print(f"获取到{len(provinces)}条省市数据")

    total_count = 0

    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()

        for province in provinces:
            stores = fetch_stores(province)

            for store in stores:
                processed = process_store(store)
                writer.writerow(processed)
                total_count += 1
                print(f"{processed}")

            # 动态延时（1-5秒随机）
            time.sleep(1 + random.uniform(0, 1))

    print(f"\n抓取完成！总计店铺数量: {total_count}")



main()