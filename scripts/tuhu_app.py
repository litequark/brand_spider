import os
import random
import sys
import requests
import json
import csv
from time import sleep
import time
from typing import List, Dict, Tuple
from util.location_translator import get_en_province, get_en_city


def sleep_with_random(interval: int, rand_max: int) -> None:
    rand = random.uniform(0.0, 1.0) * rand_max
    sleep(interval + rand)


# 全局变量
batch_size = 1000
shops_buffer = []
request_count = 0
MAX_RETRIES = 5
INTERVAL = 1

# API 接口
GET_CITY_API = "https://gateway.tuhu.cn/cl/cl-base-region-query/region/selectCityList"
GET_SHOP_API = "https://gateway.tuhu.cn/cl/cl-shop-api/shopList/getMainShopList"

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/tuhu_app.csv")

RESULT_FIELDS = ["品牌", "省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]
USER_AGENTS = [
    "Dalvik/2.1.0 (Linux; U; Android 10; M2004J7BC Build/QP1A.190711.020) tuhuAndroid 7.25.0",
]


# 组装请求头的函数
def get_request_headers():
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Encoding": "gzip",
        "Content-Type": "application/json",
        "mid": "3F4Dn25zdKrMa",
        "authorization": "Bearer null",
        "api_level": "2",
        "distinct_id": "d04b63da4632df98",
        "channel": "Android",
        "deviceid": "8a2d67db-43f0-34aa-a6b9-1dfd7d8300ff",
        "version": "7.25.0",
        "authtype": "oauth",
        "blackbox": "rGPHt1749617672YkpK9SAbpE6",
        "fingerprint": "rGPVN1749617672YKEtOGRoYM3",
        "content-type": "application/json; charset=utf-8"
    }
    return headers


ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "zh-CN,zh;q=0.9",
    "ja-JP,ja;q=0.9",
    "fr-FR,fr;q=0.9"
]

CONNECTION_TYPES = [
    "keep-alive",
    "close"
]


# 获取随机headers的函数
def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Referer": "https://www.tuhu.cn/",
        "Host": "gateway.tuhu.cn",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Connection": random.choice(CONNECTION_TYPES)
    }


# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# --- 数据获取函数 ---
def get_all_cities():
    """获取所有城市数据"""
    try:
        response = requests.get(GET_CITY_API, headers=get_request_headers(), timeout=10)
        response.raise_for_status()

        if response.json().get('code') == 10000:
            data = response.json()['data']['regions']
            city_list = []

            for letter_group in data.values():
                for region in letter_group:
                    if region.get('city') and region.get('province'):
                        city_info = {
                            'province': region['province'].strip(),
                            'city': region['city'].strip(),
                            'district': region.get('district', '').strip(),
                            'provinceId': region.get('provinceId'),
                            'cityId': region.get('cityId'),
                            'districtId': region.get('districtId')
                        }
                        city_list.append(city_info)

            # 按省份+城市排序
            city_list.sort(key=lambda x: (x['province'], x['city']))

            return city_list
        else:
            print("接口异常:", response.json().get('message'))
            return []
    except Exception as e:
        print(f"获取城市数据失败: {str(e)}")
        return []


def get_shops_by_city(city_info: Dict, service_type: str, page_index: int = 1, page_size: int = 20):
    """根据城市和服务类型获取店铺数据"""
    payload = {
        "serviceType": service_type,
        "city": city_info['city'],
        "latitude": "",
        "pageSize": page_size,
        "sort": "default",
        "locationCityName": "",
        "province": city_info['province'],
        "pageIndex": page_index,
        "rankId": "",
        "locationMatchCity": False,
        "isMatchRegion": False,
        "longitude": ""
    }

    try:
        response = requests.post(
            GET_SHOP_API,
            headers=get_request_headers(),
            data=json.dumps(payload, ensure_ascii=False),
            timeout=20
        )
        response.raise_for_status()

        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('code') == 10000:
                return response_json.get('data', {})
            else:
                print(f"API业务错误: code={response_json.get('code')}, message={response_json.get('message')}")
                print(json.dumps(response_json, ensure_ascii=False))
                return None
        else:
            print(f"HTTP错误: {response.status_code}")
            return None

    except Exception as e:
        print(f"请求店铺数据失败: {str(e)}")
        return None


def process_shop(shop_data: Dict, city_info: Dict) -> Dict:
    base = shop_data.get("shopBaseInfo", {})
    stats = shop_data.get("statistics", {})

    # 服务类型映射
    service_type_map = {
        "GZ": "改装门店",
        "MR": "美容门店",
        "BY": "保养门店",
        "TR": "轮胎门店"
    }

    # 使用更安全的get方法避免KeyError
    service_type_code = stats.get("type", "TR")
    service_type = service_type_map.get(service_type_code, "轮胎门店")

    # 对店名进行标准化处理：去除前后空格
    shop_name = base.get("carparName", "").strip()

    return {
        "品牌": "途虎养车",
        "省": base.get("province", "").replace("自治区", ""),
        "Province": get_en_province(base.get("province", "")),
        "市区辅助": base.get("city", ""),
        "City/Area": get_en_city(base.get("city", "")),
        "区": base.get("district", ""),
        "店名": shop_name,  # 使用标准化后的店名
        "类型": service_type,
        "地址": base.get("address", ""),
        "电话": base.get("telephone", ""),
        "备注": ""
    }


# --- 主程序 ---
def main():
    # 获取城市数据
    print("正在获取城市数据...")
    city_list = get_all_cities()
    if not city_list:
        print("无法获取城市数据，程序退出")
        return

    print(f"共获取 {len(city_list)} 个城市")

    service_types = ["BY", "TR", "MR", "GZ"]

    # 新增：用于跟踪已处理的店名（全局唯一）
    seen_shop_names = set()  # 存储已处理的店名

    dealer_count = 0
    shops_buffer = []
    batch_size = 100

    # 创建CSV文件并写入表头
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        dict_writer.writeheader()

    for service_type in service_types:
        for city_info in city_list:
            page = 1
            retries = 0

            print(f"\n正在处理: 服务类型={service_type}, 城市={city_info['province']}-{city_info['city']}")

            while True:
                try:
                    shop_data = get_shops_by_city(city_info, service_type, page, 20)

                    if shop_data is None:
                        print(f"获取店铺数据失败，跳过当前页面")
                        break

                    shop_list = shop_data.get("shopList", [])

                    if not shop_list:
                        print(f"没有相关店铺信息: 服务类型={service_type}, 城市={city_info['city']}, 页码={page}")
                        break

                    for shop_item in shop_list:
                        row = process_shop(shop_item, city_info)
                        shop_name = row["店名"]

                        # 新增：检查店名是否已存在（去重逻辑）
                        if shop_name in seen_shop_names:
                            print(f"跳过重复店铺: {shop_name}")
                            continue

                        # 新增：记录已处理的店名
                        seen_shop_names.add(shop_name)
                        shops_buffer.append(row)
                        dealer_count += 1

                        print(json.dumps(row, ensure_ascii=False))  # 打印店铺信息

                        # 批量写入到CSV
                        if len(shops_buffer) >= batch_size:
                            with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                                dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                                dict_writer.writerows(shops_buffer)
                            print(f"已批量写入 {len(shops_buffer)} 条店铺数据到CSV")
                            shops_buffer.clear()

                    total_page = shop_data.get("totalPage", 1)
                    if page >= total_page or page >= 100:
                        break

                    page += 1
                    sleep_with_random(1, 1)
                    retries = 0

                except Exception as e:
                    print(f"请求异常: {str(e)}")
                    retries += 1

                    if retries >= MAX_RETRIES:
                        print(f"已达到最大重试次数 {MAX_RETRIES}，退出")
                        if shops_buffer:
                            with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                                dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                                dict_writer.writerows(shops_buffer)
                            print(f"已保存 {len(shops_buffer)} 条数据到CSV")
                            shops_buffer.clear()
                        sys.exit(1)

                    print(f"等待 {2   **   retries} 秒后重试...")
                    sleep(2   **  retries)

            # 写入剩余数据（新增：确保最后一批数据也被写入）
            if shops_buffer:
                with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                    dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                    dict_writer.writerows(shops_buffer)
                print(f"已写入剩余 {len(shops_buffer)} 条店铺数据到CSV")
                shops_buffer.clear()

            print(f"爬取完成，共计 {dealer_count} 个门店数据已保存到 {OUTPUT_PATH}")

if __name__ == "__main__":
            main()