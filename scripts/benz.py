import os
import random
import requests
import json
import csv
from time import sleep

INTERVAL = 1  # 网络请求间隔（秒）

API = "https://api.oneweb.mercedes-benz.com.cn/ow-dealers-location/"

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "类型2", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入父目录（project）
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/benz.csv")

default_payload = {
    "abnormal":"Abnormal",
    "sort":"distance",
    "city":"",
    "longitude":"118.91553187561439",
    "latitude":"32.10242466695606",
    "keywords":"",
    "dealerId":"",
    "needFilterByModel":"false",
    "modelName":"",
    "serviceTypeCode":"",
    "sortRating":"",
    "dealerScope":"MB:EQ:VAN:AMG:SC",
    "dealerType":"ALL",
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

with open(OUTPUT_PATH, "w", encoding="utf-8") as f: # 清除csv文件
    # 写入表头
    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    list_writer.writerow(RESULT_FIELDS)

dealer_count = 0
province_payload = {
    "abnormal":"Abnormal",
    "needFilterByDealer":"true",
    "needFilterByModel":"false",
    "modelName":"",
    "dealerType":"ALL",
}
result_province=requests.get(url=API+"provinces/query",headers=DEFAULT_HEADERS,params=province_payload).json()
sleep_with_random(INTERVAL, 1)
provinces=result_province["result"]
for province in provinces:
    province_id=province["id"]
    city_payload={
        "abnormal":"Abnormal",
        "needFilterByDealer":"true",
        "needFilterByModel":"false",
        "modelName":"",
        "dealerType":"ALL",
        "provinceId":province_id
    }
    response_city=requests.get(url=API+"cities/query",headers=DEFAULT_HEADERS,params=city_payload).json()
    sleep_with_random(INTERVAL, 1)
    cities=response_city["result"]
    for city in cities:
        city_id=city["id"]
        store_payload={
            "abnormal":"Abnormal",
            "sort":"distance",
            "city":city["name"],
            "longitude":"118.91553187561439",
            "latitude":"32.10242466695606",
            "keywords":"",
            "dealerId":"",
            "needFilterByModel":"false",
            "modelName":"",
            "serviceTypeCode":"",
            "sortRating":"",
            "dealerScope":"MB,EQ,VAN,AMG,SC",
            "dealerType":"ALL",
        }
        response_store=requests.get(url=API+"dealers/query",headers=DEFAULT_HEADERS,params=store_payload).json()
        sleep_with_random(INTERVAL, 1)
        for store in response_store["result"]:
            store_towrite = {
                "省": store["province"],
                "市": store["city"],
                "区": "",
                "店名": store["displayName"],
                "类型": "",
                "地址": store["address"],
                "电话": store["phoneNumber"],
                "备注": ""
            }
            if not (store["service_scope"] is None):
                for scope in store["service_scope"]:
                    for typ in scope["types"]:
                        store_towrite["类型"] +=typ["name"]+" "
            print(store_towrite)
        with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
            list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            list_writer.writerow(store_towrite)