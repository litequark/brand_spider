import requests
import csv
import os
import time
import random
import json
from urllib.parse import quote
from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)

# 配置参数
BASE_URL = "https://www.tmallyc.com"
API_URL = BASE_URL + "/superapi/canary/appStoreFacade/nearQueryList"
RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output/TianMao.csv")


def setup_driver():

    options = webdriver.ChromeOptions()
    options.add_argument()
    return webdriver.Chrome(options=options)


def parse_city_list(session_data):
    print(json.dumps(session_data['cityList'], indent=4))
    return [
        {
            'province': '',
            'city': item['areaName'],
            'areaId': item['areaId']
        } for item in json.loads(session_data['cityList'])
    ]

def fetch_store_data(params):

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        sleep_with_random(1,1)
        response.raise_for_status()
        return response.json()['info']
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return []


def save_to_csv(data):

    file_exists = os.path.isfile(OUTPUT_PATH)
    with open(OUTPUT_PATH, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if not file_exists:
            writer.writeheader()
        for item in data:
            writer.writerow({
                '省': '',
                '市': item.get('cityName', ''),
                '区': item.get('areaId', ''),
                '店名': item['storeName'],
                '地址': item['address'],
                '电话': item.get('phone', '')
            })
            print(f"已保存: " + json.dumps(item, indent=4))

import json
from urllib.parse import quote


def construct_request_params(area_id, page_no=1):

    timestamp = str(int(time.time() * 1000))
    return {
        'appkey': '7004516',
        'timestamp': timestamp,
        'session-id': 'S_9298b6c1-1b82-4ee9-aff6-ca8d6b394f4b',
        'user-agent': 'DEPRECATING',
        'version': '2.0',
        'sign': '206F8B93BCB97EAA3020371D9E23ADA6',
        'data': quote(json.dumps({
            "longitude": 120.12,
            "latitude": 30.16,
            "areaId": area_id,
            "pageSize": 50,  # 每页最大数据量
            "pageNo": page_no,
            "entryType": 4
        }))
    }


def fetch_paginated_data(area_id):
    page_no = 1
    all_stores = []

    while True:
        try:
            params = construct_request_params(area_id, page_no)
            response = requests.get(API_URL, params=params, timeout=15)
            response.raise_for_status()

            current_data = response.json().get('info', [])
            current_count = len(current_data)

            if current_count == 0:
                break
            if current_count < 50 and page_no > 1:
                all_stores.extend(current_data)
                break

            all_stores.extend(current_data)
            page_no += 1

            # 增加随机延迟防封禁[1](@ref)
            sleep(random.uniform(1.5, 3.5))

        except requests.exceptions.RequestException as e:
            print(f"分页请求异常: {str(e)}")
            break

    return all_stores


def main():
    driver = setup_driver()
    total_stores = 0

    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))

        session_data = driver.execute_script("return window.sessionStorage;")
        cities = parse_city_list(session_data)
        for city in cities:
            print(json.dumps(city, indent=4))

        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
            writer.writeheader()

            for city in cities:
                print(f"正在爬取 {city['city']}...")
                stores = fetch_paginated_data(city['areaId'])

                if stores:
                    for store in stores:
                        writer.writerow({
                            '省': '',
                            '市': store.get('cityName', ''),
                            '区': store.get('areaId', ''),
                            '店名': store['storeName'],
                            '地址': store['address'],
                            '电话': store.get('phone', '')
                        })
                    total_stores += len(stores)
                    print(f"{city['city']} 获取到 {len(stores)} 家店铺")

    finally:
        driver.quit()
        print(f"\n最终统计: 共爬取 {total_stores} 家店铺")
        print(f"数据路径: {os.path.abspath(OUTPUT_PATH)}")

main()