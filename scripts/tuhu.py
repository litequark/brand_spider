import os
import random
import requests
import json
import csv
from time import sleep
import time
from typing import List, Dict, Optional

INTERVAL = 1

SELECT_BANDS_API ="https://cl-gateway.tuhu.cn/cl-vehicle-aggregation/vehicle/selectBrands"

RESULT_FIELDS = ["品牌","省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/tuhu.csv")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}

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


os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f: # 清除csv文件

    list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    list_writer.writerow(RESULT_FIELDS)

dealer_count = 0


def get_brand_names(SELECT_BANDS_API):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.audi.cn/zh/dealer.html",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:

        response = requests.get(SELECT_BANDS_API,headers=headers,timeout=10)
        response.raise_for_status()


        json_data = response.json()


        if json_data.get('code') == 10000:
            return [brand['fullName'] for brand in json_data.get('data', {}).get('brands', [])]

        return []

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return []
    except KeyError as e:
        print(f"JSON结构异常，缺少关键字段: {str(e)}")
        return []
    except Exception as e:
        print(f"未知错误: {str(e)}")
        return []




brands = get_brand_names(SELECT_BANDS_API)

print("提取的品牌列表：")
print(brands)

SELECT_MODELS_BY_BRANDS_URL="https://cl-gateway.tuhu.cn/cl-vehicle-aggregation/vehicle/selectModels"






def fetch_models_by_brands(brand_full_names: List[str], max_retries=5) -> List[Dict]:

    models = []


    for brand_full in brand_full_names:

        payload = {"brandName": brand_full}
        attempt = 0

        while attempt < max_retries:
            try:
                response = requests.post(
                    SELECT_MODELS_BY_BRANDS_URL,
                    headers=headers,
                    data=json.dumps(payload,ensure_ascii=False),
                    timeout=15
                )
                response.raise_for_status()

                if response.status_code == 200:
                    resp_data = response.json()
                    if resp_data.get('code') == 10000:
                        raw_models = resp_data.get('data', {}).get('models', [])
                        models.extend(normalize_models(raw_models))
                        print(normalize_models(raw_models))
                        break
                    else:
                        print(f"接口业务异常: {resp_data.get('message')}")
                else:
                    print(f"HTTP异常状态码: {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"请求失败: {str(e)}，第 {attempt + 1} 次重试...")
                attempt += 1
                time.sleep(2  **  attempt)
                continue
            except Exception as e:
                print(f"处理异常: {str(e)}")
                break

    return models


def normalize_models(raw_models: List[Dict]) -> List[Dict]:

    return [{
        "modelId": model.get("code"),
        "modelName": model.get("name"),
        "brand": model.get("brandFullName"),
        "manufacturer": model.get("factory"),
        "price": model.get("avgPrice"),
        "tireSpecs": list(set(model.get("specialTires", []) + model.get("standardTires", [])))
    } for model in raw_models if validate_model(model)]


def validate_model(model: Dict) -> bool:

    return bool(model.get("code")) and bool(model.get("name"))


def filter_models(raw_models: List[Dict]) -> List[Dict]:

    required_fields = {'modelId', 'modelName', 'series'}
    return [
        model for model in raw_models
        if all(field in model for field in required_fields)
    ]

models_data = fetch_models_by_brands(brands)

print(f"共获取 {len(models_data)} 款车型数据")


model_ids = [item['modelId'] for item in models_data]



pageIndex =1
pageNum = 9999


GET_CITY_API="https://cl-gateway.tuhu.cn/cl-base-region-query/region/selectCityList"


def get_all_cities():

    url = "https://cl-gateway.tuhu.cn/cl-base-region-query/region/selectCityList"

    try:
        response = requests.get(url,headers=headers, timeout=10)
        response.raise_for_status()

        if response.json().get('code') == 10000:
            data = response.json()['data']['regions']
            cities = set()


            for letter_group in data.values():
                for region in letter_group:

                    if 'city' in region and region['city']:
                        cities.add(region['city'].strip())

            return sorted(list(cities))
        else:
            print("接口返回异常:", response.json().get('message'))
            return []

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return []
    except Exception as e:
        print(f"处理异常: {str(e)}")
        return []



city_list = get_all_cities()
print(f"共获取 {len(city_list)} 个城市")

print(city_list)


GET_MAIN_SHOP ="https://cl-gateway.tuhu.cn/cl-shop-api/shopList/getMainShopList"

payload_dealers_default = {
"isMatchRegion": "true",
  "pageSize": pageNum,
  "pageIndex": pageIndex,
  "city": "",
  "district": "",
  "latitude": "32.10242466695606",
  "longitude": "118.91553187561439",
  "province": "",
  "rankId": "",
  "serviceType": "",
  "sort": "default",
  "vehicleInfo": {
    "displacement": "",
    "productionYear": "",
    "tid": "",
    "vehicleId": ""
  }
        }

service_type =["MR","TR","BY","GZ"]


def process_shop(shop):

    base = shop["shopBaseInfo"]
    stats = shop["statistics"]
    Servicetype=""
    if(stats["type"]=="GZ"):
        Servicetype="改装门店"
    elif (stats["type"] == "MR"):
        Servicetype = "美容门店"
    elif (stats["type"] == "BY"):
        Servicetype = "保养门店"
    else:
        Servicetype = "轮胎门店"

    return {
        "品牌": "途虎养车",  # 品牌强制统一
        "省": base["province"].replace("自治区", ""),  # 简化省级名称
        "Province":"",
        "市区辅助": f"{base['district']}",  # 合并行政区域
        "City/Area":"",
        "区": base["district"],
        "店名": base["carparName"],
        "类型": Servicetype,
        "地址": base["address"],
        "电话": base["telephone"],
        "备注": ""  # 预留字段
    }




for serviceType in service_type:
     for city in city_list:
           for model in model_ids:
               payload_dealers = payload_dealers_default.copy()
               payload_dealers.update({"vehicleId": model, "serviceType": serviceType, "city": city})
               resp = requests.post(
                   "https://cl-gateway.tuhu.cn/cl-shop-api/shopList/getMainShopList",
                   headers=headers,
                   data=json.dumps(payload_dealers, ensure_ascii=False),
                   timeout=10
               )
               if(resp.status_code == 200):
                   print("调取数据成功")
                   data = resp.json()["data"]


                   for shop in data["shopList"]:

                    row = process_shop(shop)
                    print(row)
                    with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                     dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
                     dict_writer.writerow(row)






print("共计" + str(dealer_count) + "个门店")