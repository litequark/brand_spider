import os
import random
import requests
import json
import csv
from time import sleep
from util.location_translator import get_en_city, get_en_province

INTERVAL = 1  # 网络请求间隔（秒）

API = "https://resources-nav.porsche.services/dealers/region/CN?env=production"

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入父目录（project）
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/porsche.csv")

default_payload = {
    "env": "production",
}

DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}


def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)


#创建父目录（如果不存在)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f: # 清除csv文件
    # 写入表头
    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    list_writer.writerow(RESULT_FIELDS)

dealer_count = 0
result_store = requests.get(url=API, headers=DEFAULT_HEADERS, params=default_payload).json()
sleep_with_random(INTERVAL, 1)

for region in result_store["regions"]:
    region_name = region.get("regionNameLocalized", "")
    for city_data in region.get("cities", []):
        city_name = city_data.get("cityNameLocalized", "")
        dealers = city_data.get("dealers", {})
        
        for dealer_id, dealer_info in dealers.items():
            try:
                dealer = dealer_info.get("ppnDealer", {})
                
                # 提取基本信息
                name = dealer.get("nameLocalized", "")
                dealer_type = dealer.get("facilityType", "")
                
                # 处理地址信息
                address = dealer.get("address", {})
                address_localized = dealer.get("addressLocalized", {})
                
                province = address_localized.get("state", "")
                city = address_localized.get("city", "")
                street = address_localized.get("street", "")
                
                # 从地址中提取区信息（如果存在）
                district = ""
                if "区" in street:
                    district = street.split("区")[0] + "区"
                
                # 获取联系方式
                contact = dealer.get("contactDetails", {})
                phone = contact.get("phoneNumber", "")
                
                # 获取英文省份和城市名称
                en_province = get_en_province(province)
                en_city = get_en_city(city)
                
                # 组合完整地址
                full_address = street
                
                store_towrite = [
                    province,
                    en_province,
                    city,
                    en_city,
                    district,
                    name,
                    dealer_type,
                    full_address,
                    phone,
                    ''  # 备注字段留空
                ]
                
                with open(OUTPUT_PATH, "a", encoding="utf-8", newline="") as f:
                    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                    list_writer.writerow(store_towrite)
                
                dealer_count += 1
                print(f"已处理第 {dealer_count} 家经销商: {name}")
                
            except Exception as e:
                print(f"处理经销商数据时出错: {str(e)}")
                continue

print(f"\n爬取完成！共处理 {dealer_count} 家经销商信息")