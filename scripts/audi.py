import os
import random
import csv
from time import sleep
import requests
import json

#加载地区
def get_audi_cities():
    url = "https://www.audi.cn/bin/dealerprocity/location.json"
    cities = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.audi.cn/zh/dealer.html",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        def parse_nodes(nodes):
            for node in nodes:
                # 递归处理所有子节点
                if node.get('locations'):
                    parse_nodes(node['locations'])
                # 仅当无子节点时，添加当前节点名称（终端城市）
                if not node.get('locations'):
                    city = node.get('cnName')
                    if city and city not in cities:
                        cities.append(city)

        if 'data' in data:
            parse_nodes(data['data'])

        return cities

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return []

citys = get_audi_cities()

for city in citys:
    print(city)


INTERVAL = 1  # 网络请求间隔（秒）
API_URL = "https://www.audi.cn/bin/dealerprocity/query.json"
RESULT_FIELDS = ["品牌","省", "Province","市区辅助", "City/Area","区","店名","类型", "地址", "电话"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/audi.csv")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": "https://www.audi.cn/zh/dealer.html"
}


def parse_dealer(dealer):
    services = "、".join([tag for tag in dealer.get("tagTitle", []) if tag not in ["4S", "售后"]])
    models = "、".join(set([car["name"] for car in dealer.get("saleCarBeans", [])]))
    return {
        "品牌":"奥迪",
        "省": dealer.get("province", ""),
        "Province":"",
        "市区辅助": dealer.get("city", ""),
        "City/Area":"",
        "区":"",
        "店名": dealer.get("adDealerName", ""),
        "类型": "4S店" if "4S" in dealer.get("tagTitle", []) else "授权经销商",
        "地址": dealer.get("adAddress", ""),
        "电话": dealer.get("adPhone", ""),
    }


def sleep_with_random(base: int = 1):
    sleep(base + random.uniform(0, 0.5))

def print_dealer_info(dealer_info):

    print(f"【经销商名称】{dealer_info['店名']}")
    for key, value in dealer_info.items():
        if key not in ["店名"] and value:  # 过滤空值
            print(f"{key: <8}：{value}")

def get_city_dealers(city_name: str):

    payload = {"adCity": city_name}
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=DEFAULT_HEADERS,
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", {}).get("common", [])
    except Exception as e:
        print(f"获取{city_name}数据失败: {str(e)}")
        return []


os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
    writer.writeheader()



total_count = 0
for city in citys:
    print(f"正在获取{city}的经销商信息")
    dealers = get_city_dealers(city)
    if not dealers:
        print(f"{city} 未找到经销商信息")
        continue
    with open(OUTPUT_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        for dealer in dealers:
            parsed = parse_dealer(dealer)
            writer.writerow(parsed)
            total_count += 1
            print_dealer_info(parsed)
    print(f" {city} 已找到{len(dealers)}家经销商")
    sleep_with_random()
print(f"数据抓取完成，共获取{total_count}家经销商信息。结果已保存至：{OUTPUT_PATH}")

