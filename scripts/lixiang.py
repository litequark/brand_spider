import requests
import csv
import os
import json

from scripts.util.location_translator import get_en_province, get_en_city

API_URL = "https://api-web.lixiang.com/saos-store-web/tur_store/v1-0/service-centers?types=RETAIL%2CDELIVER%2CAFTERSALE%2CSPRAY%2CTEMPORARY_EXHIBITION%2CTEMPORARY_AFTERSALE_SUPPORT&sortType=CITY&storeEffectiveStatus="
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区","店名", "类型", "地址", "电话", "备注"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/lixiang.csv")

def fetch_data():

    try:
        response = requests.get(API_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        return response.json()['data']
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"数据解析失败: {str(e)}")
        return None


def save_to_csv(data):

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)

        for item in data:
            row = [
                "理想",  # 品牌
                item.get('provinceName', ''),  # 省（置空）
                get_en_province(item.get('provinceName', '')),  # Province
                item.get('cityName', ''),  # 市区辅助（置空）
                get_en_city(item.get('cityName', '')),  # City/Area
                item.get('countyName', ''),  # 区
                item.get('name', ''),  # 店名
                item.get('type', ''),  # 类型
                item.get('address', ''),  # 地址
                item.get('telephone', ''),  # 电话
                ""  # 备注（置空）
            ]
            writer.writerow(row)
            print(json.dumps(row, ensure_ascii=False))

service_data = fetch_data()
if service_data:
        save_to_csv(service_data)
        print(f"共爬取 {len(service_data)} 条数据")
else:
        print("数据获取失败，请检查网络或API状态")