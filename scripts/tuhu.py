import os
import random
import requests
import json
import csv
from time import sleep
import time
from typing import List, Dict
seen = set()
batch_size = 1000  #
shops_buffer = []
request_count = 0
MAX_RETRIES = 3
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
    try:
        response = requests.get(SELECT_BANDS_API,headers=headers,timeout=10)
        response.raise_for_status()
        sleep_with_random(1,1)
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
for brand in brands:
    print(f"<UNK>: {brand}")

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
                sleep_with_random(1, 1)
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

GET_CITY_API="https://cl-gateway.tuhu.cn/cl-base-region-query/region/selectCityList"


def get_all_cities():
    try:
        response = requests.get(GET_CITY_API, headers=headers, timeout=10)
        response.raise_for_status()

        if response.json().get('code') == 10000:
            data = response.json()['data']['regions']
            city_province = set()  # 使用元组去重

            for letter_group in data.values():
                for region in letter_group:
                    # 空值过滤
                    if region.get('city') and region.get('province'):
                        # 标准化处理
                        province = region['province'].replace('自治区', '').replace('省', '')
                        city = region['city'].strip()
                        # 存储元组
                        city_province.add((province, city))

            # 按省份+城市排序
            return sorted(list(city_province), key=lambda x: (x[0], x[1]))

        else:
            print("接口异常:", response.json().get('message'))
            return []

    except Exception as e:
        print(f"处理失败: {str(e)}")
        return []



city_list = get_all_cities()
print(f"共获取 {len(city_list)} 个城市")

print(city_list)


GET_MAIN_SHOP ="https://cl-gateway.tuhu.cn/cl-shop-api/shopList/getMainShopList"

payload_dealers_default = {
"isMatchRegion": "true",
  "pageSize": "",
  "pageIndex": "",
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
        "省": base["province"].replace("自治区", ""),
        "Province":"",
        "市区辅助": f"{base['district']}",
        "City/Area":"",
        "区": base["district"],
        "店名": base["carparName"],
        "类型": Servicetype,
        "地址": base["address"],
        "电话": base["telephone"],
        "备注": ""
    }
shops=[]
for serviceType in service_type:

    for province,city in city_list:
        for model in model_ids:
            page = 1
            retries = 0

            while True:
                try:

                    payload_dealers = payload_dealers_default.copy()
                    payload_dealers.update({
                        "vehicleId": model,
                        "serviceType": serviceType,
                        "city": city,
                        "pageIndex": page,
                        "pageSize": 100,
                        "province": province
                    })


                    resp = requests.post(
                        GET_MAIN_SHOP,
                        headers=headers
                       ,
                        data=json.dumps(payload_dealers, ensure_ascii=False),
                        timeout=20
                    )
                    resp.raise_for_status()


                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        shop_list = data.get("shopList", [])

                        if not shop_list:
                            break


                        for shop in shop_list:
                            row = process_shop(shop)
                            unique_key = f"{row['店名']}_{row['地址']}"

                            if unique_key not in seen:
                                seen.add(unique_key)
                                shops_buffer.append(row)
                                dealer_count+=1


                                if len(shops_buffer) >= batch_size:
                                    with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                                        dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                                        dict_writer.writerows(shops_buffer)
                                    shops_buffer.clear()

                        total_page = data.get("totalPage", 1)
                        if page >= total_page:
                            break
                        page += 1

                        sleep(random.uniform(1.2, 3.5))
                        request_count += 1


                    retries = 0  # 重置重试计数器

                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    print(f"请求异常: {str(e)}")
                    retries += 1
                    if retries >= MAX_RETRIES:
                        print(f"已达到最大重试次数{MAX_RETRIES}，跳过当前请求")
                        break
                    sleep(2 **  retries)



if shops_buffer:
    with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        dict_writer.writerows(shops_buffer)


print("共计" + str(dealer_count) + "个门店")