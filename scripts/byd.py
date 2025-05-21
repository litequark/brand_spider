import os
import random
import requests
import json
import csv
from time import sleep

INTERVAL = 1  # 网络请求间隔（秒）

API = "https://site-api.byd.com/domestic-official-api/store/"

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "类型2", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)#进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/byd.csv")

default_payload = {
    "dealerKey": "",
    "provinceId": "",
    "cityId": "",
    "provinceName": "",
    "cityName": "",
    "longtitude": 114.174328,  # 原文如此
    "latitude": 22.316554,
    "pageNum": 0,
    "numPerPage": 100,
    "dealerType": "0"
}

DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "content-type": "application/json",
}


def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)


#创建父目录（如果不存在)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f: # 清除csv文件
    # 写入表头
    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    list_writer.writerow(RESULT_FIELDS)

dealer_count = 0
for sale_network in {"2", "3"}:
    sale_network_literal = ""
    if sale_network == "2":
        sale_network_literal = "王朝"
    elif sale_network == "3":
        sale_network_literal = "海洋"
    print(f"开始处理 {sale_network_literal}")

    city_ids = []

    # 获取省份列表
    payload_provinces = {"dealerType": "0"}
    api_province = API + "province"
    response_provinces = requests.post(url=api_province,
                                       data=json.dumps(payload_provinces, ensure_ascii=False),
                                       headers=DEFAULT_HEADERS).json()

    province_total = len(response_provinces["data"])
    print(f"{sale_network_literal} 获取到 {province_total} 个省份信息")

    province_ids = []
    for m in response_provinces["data"]:
        province_ids.append(m["n_province_id"])

    # 分省处理
    city_total = 0
    api_city = API + "city"
    for province_id in province_ids:
        # 获取城市列表
        payload_cities = {"dealerType": "0", "provinceId": province_id}
        response_cities = requests.post(url=api_city,
                                        data=json.dumps(payload_cities, ensure_ascii=False),
                                        headers=DEFAULT_HEADERS).json()
        city_total += len(response_cities["data"])
        for m in response_cities["data"]:
            city_ids.append(m["n_city_id"])

    print(f"{sale_network_literal} 获取到 {city_total} 个城市信息")
    processed_city = 0

    # 分市处理
    api_dealer = API + "list"
    for city_id in city_ids:
        payload_dealers_default = {
            "dealerKey": "",
            "provinceId": "",
            "cityId": city_id,
            "provinceName": "",
            "cityName": "",
            "longtitude": 114.174328,
            "latitude": 22.316554,
            "pageNum": 0,
            "numPerPage": 1000,
            "dealerType": ""  # 0: 售前经销, 1: 售后服务
        }

        for dealer_type in {"0", "1"}:
            header_dealers = DEFAULT_HEADERS.copy()
            header_dealers.update({"salenetwork": sale_network})
            payload_dealers = payload_dealers_default.copy()
            payload_dealers.update({"dealerType": dealer_type})

            response_dealers = requests.post(url=api_dealer,
                                             data=json.dumps(payload_dealers, ensure_ascii=False),
                                             headers=header_dealers).json()
            while response_dealers["success"] is False:
                print("HTTP请求成功但JSON返回失败，可能被限流，10秒后重试……\n")
                sleep_with_random(10, 1)
                response_dealers = requests.post(url=api_dealer,
                                                 data=json.dumps(payload_dealers, ensure_ascii=False),
                                                 headers=header_dealers).json()
            sleep_with_random(1, 1)

            for m in response_dealers["data"]:
                dealer_count += 1
                # 删除\n
                for k in m: # keys
                    if isinstance(m[k], str):
                        m[k] = m[k].replace('\\n', ' ').replace('\n', ' ')

                dealer_type_literal = ""
                if dealer_type == "0":
                    dealer_type_literal = "售前经销"
                elif dealer_type == "1":
                    dealer_type_literal = "售后服务"

                dealer_type2_literal = ""
                has_attr = False
                for attr in {"卫星", "城展", "服务", "4S"}:
                    if attr in m["dealerName"] and '店' in m["dealerName"]:
                        dealer_type2_literal += attr
                        has_attr = True
                if has_attr:
                    dealer_type2_literal += '店'

                for attr in {"商超店", "城市展厅", "钣喷中心"}:
                    if attr in m["dealerName"]:
                        dealer_type2_literal += attr

                dealer = {
                    "省": m["provinceName"],
                    "Province": "",
                    "市": m["cityName"],
                    "City": "",
                    "区": "",
                    "店名": m["dealerName"],
                    "类型": dealer_type_literal,
                    "类型2": dealer_type2_literal,
                    "地址": m["dealerAddress"],
                    "电话": m["dealerTel"],
                    "备注": ""
                }
                print(dealer)
                with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                    dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
                    dict_writer.writerow(dealer)
        processed_city += 1
        print(f"{sale_network_literal}: 已处理" + str('%.2f' % ((processed_city / city_total) * 100)) + "%")

print("共计" + str(dealer_count) + "个门店")
