import os
import random
import requests
import csv
import json
from time import sleep
import cpca  # 中文地址解析库
from util.location_translator import get_en_province, get_en_city
from typing import List, Dict, Set

INTERVAL = 1  # 网络请求间隔（秒）
API = "https://www.continental-tires.cn/tpservice/Search/searchAgencyByName"
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "地址", "电话", "备注"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]
SEARCH_KEYS = ['养', '厂', '区', '市', '省', '县', '镇', '州', '盟', '店', '司', '车', '中', '美']   # 覆盖各类行政单位的关键词

# 文件路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/continental.csv")


def sleep_with_random(interval: int, rand_max: int = 1) -> None:
    """带随机时间的休眠函数"""
    sleep(interval + random.random() * rand_max)


def parse_address(address: str) -> Dict[str, str]:
    """使用cpca解析中文地址"""
    df = cpca.transform([address])
    return {
        "省": df.iloc[0]['省'],
        "市": df.iloc[0]['市'],
        "区": df.iloc[0]['区']
    }


def fetch_stores(search_key: str) -> List[Dict]:
    """获取单个搜索关键词的门店数据"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.continental-tires.cn/find-a-dealer"
    }
    params = {
        "name": search_key,
        "lng": "118.82155",
        "lat": "32.32222",
        "range": "25000000000"
    }

    try:
        response = requests.get(API, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return []


def process_store(store: Dict, existing_ids: Set[int]) -> Dict:
    """处理单个门店数据"""
    if store['id'] in existing_ids:
        return None

    # 解析地址信息
    address_info = parse_address(store['address'])

    # 获取英文行政区划
    en_province = get_en_province(address_info["省"]) if address_info["省"] else ""
    en_city = get_en_city(address_info["市"]) if address_info["市"] else ""

    return {
        "省": address_info["省"],
        "Province": en_province,
        "市区辅助": address_info["市"],
        "City": en_city,
        "区": address_info["区"],
        "店名": store['name'],
        "地址": store['address'],
        "电话": store['phone'],
        "备注": f"ID:{store['id']}"
    }


def main():
    # 初始化数据存储
    existing_ids = set()
    total_count = 0

    # 创建输出目录
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()

        # 遍历所有搜索关键词
        for key in SEARCH_KEYS:
            print(f"正在搜索关键词: {key}")
            stores = fetch_stores(key)

            for store in stores:
                processed = process_store(store, existing_ids)
                if not processed:
                    continue

                # 记录数据
                existing_ids.add(store['id'])
                total_count += 1

                # 控制台输出
                print(json.dumps(processed, ensure_ascii=False, indent=2))

                # 写入CSV
                writer.writerow(processed)

            # 遵守访问间隔
            sleep_with_random(INTERVAL)

    print(f"爬取完成，共获取 {total_count} 家门店")


if __name__ == "__main__":
    main()