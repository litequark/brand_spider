import os
import random
import requests
import json
import csv
from time import sleep
from util.location_translator import get_en_city, get_en_province

INTERVAL = 1  # 网络请求间隔（秒）

API = "https://api.onthemap.io/server/v1/api/location"

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入父目录（project）
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/maserati.csv")

default_payload = {
    "query": "[countryIsoCode2]=[CN OR cn OR HK OR hk OR MO OR mo OR TW OR tw]",
    "language": "zh",
    "sort": "dealername",
    "key": "6e0b94fb-7f95-11ec-9c36-eb25f50f4870",
    "channel": "www.maserati.com"
}

DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}


def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)


def get_business_hours(properties):
    """获取营业时间信息"""
    hours = []
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day in days:
        morning = f"{day}-M-From"
        evening = f"{day}-E-From"
        if morning in properties and evening in properties:
            hours.append(f"{day}: {properties[morning]}-{properties[evening]}")
    return " | ".join(hours)


#创建父目录（如果不存在)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8",newline="") as f: # 清除csv文件
    # 写入表头
    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    list_writer.writerow(RESULT_FIELDS)

dealer_count = 0
result_store = requests.get(url=API, headers=DEFAULT_HEADERS, params=default_payload).json()
sleep_with_random(INTERVAL, 1)

for feature in result_store.get("data", {}).get("results", {}).get("features", []):
    try:
        properties = feature.get("properties", {})
        
        # 提取基本信息
        name = properties.get("dealername", "")
        dealer_type = "经销商" if properties.get("sales") == "true" else "服务中心"
        
        # 处理地址信息
        province = properties.get("province", "")
        city = properties.get("city", "")
        district = properties.get("hamlet", "")
        address = properties.get("address", "")
        
        # 获取联系方式
        phone = properties.get("formatted_phone", "")
        
        # 获取英文省份和城市名称
        en_province = get_en_province(province)
        en_city = get_en_city(city)
        
        store_towrite = [
            province,
            en_province,
            city,
            en_city,
            district,
            name,
            dealer_type,
            address,
            phone,
            ''  # 备注字段留空
        ]
        
        with open(OUTPUT_PATH, "a", encoding="utf-8",newline="") as f:
            list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            list_writer.writerow(store_towrite)
        
        dealer_count += 1
        print(f"已处理第 {dealer_count} 家经销商: {name}")
        
    except Exception as e:
        print(f"处理经销商数据时出错: {str(e)}")
        continue

print(f"\n爬取完成！共处理 {dealer_count} 家经销商信息")