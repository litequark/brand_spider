import os
import random
import sys

import requests
import json
import csv
from time import sleep
import time
from typing import List, Dict

seen = set()
batch_size = 1000
shops_buffer = []
request_count = 0
MAX_RETRIES = 5
INTERVAL = 1
GET_CITY_API="https://cl-gateway.tuhu.cn/cl-base-region-query/region/selectCityList"

GET_MAIN_SHOP ="https://cl-gateway.tuhu.cn/cl-shop-api/shopList/getMainShopList"
SELECT_BRANDS_API = "https://cl-gateway.tuhu.cn/cl-vehicle-aggregation/vehicle/selectBrands"

RESULT_FIELDS = ["品牌","省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/tuhu.csv")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "output/tuhu_progress.json") # 新增进度文件路径

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

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
        "Host": "cl-gateway.tuhu.cn",
        "X-Requested-With": "XMLHttpRequest",
        "auth-type":"oauth",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Connection": random.choice(CONNECTION_TYPES)
    }

def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# --- 新增进度管理函数 ---
def save_progress(brand_idx, city_idx, model_idx, service_type_idx):
    progress = {
        "brand_idx": brand_idx,
        "city_idx": city_idx,
        "model_idx": model_idx,
        "service_type_idx": service_type_idx
    }
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f)
        print(f"进度已保存: 品牌索引 {brand_idx}, 城市索引 {city_idx}, 车型索引 {model_idx}, 服务类型索引 {service_type_idx}")
    except IOError as e:
        print(f"保存进度失败: {e}")

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                print(f"从 {PROGRESS_FILE} 加载进度成功.")
                return progress.get("brand_idx", 0), progress.get("city_idx", 0), progress.get("model_idx", 0), progress.get("service_type_idx", 0)
        except (IOError, json.JSONDecodeError) as e:
            print(f"加载进度文件失败或文件格式错误: {e}. 从头开始.")
            return 0, 0, 0, 0 # 文件存在但无法解析，从头开始
    print("未找到进度文件，从头开始.")
    return 0, 0, 0, 0
# --- 进度管理函数结束 ---

# --- 移动 get_brand_names 函数定义到此处 ---
def get_brand_names(select_brands_api):
    try:
        response = requests.get(select_brands_api, headers=get_random_headers(), timeout=10)
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

SELECT_MODELS_BY_BRANDS_URL="https://cl-gateway.tuhu.cn/cl-vehicle-aggregation/vehicle/selectModels"

def fetch_models_by_brands(brand_full_names: List[str], max_retries=5) -> List[Dict]:
    models = []
    brand_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "auth-type":"oauth"
    }
    for brand_full in brand_full_names:
        payload = {"brandName": brand_full}
        attempt = 0
        while attempt < max_retries:
            try:
                response = requests.post(
                    SELECT_MODELS_BY_BRANDS_URL,
                    headers=brand_headers,
                    data=json.dumps(payload,ensure_ascii=False),
                    timeout=15
                )
                response.raise_for_status()
                sleep_with_random(1, 2)
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
def get_all_cities():
    try:
        response = requests.get(GET_CITY_API, headers=get_random_headers(), timeout=10)
        response.raise_for_status()

        if response.json().get('code') == 10000:
            data = response.json()['data']['regions']
            city_province = set()  # 使用集合去重

            for letter_group in data.values():
                for region in letter_group:
                    # 空值过滤
                    if region.get('city') and region.get('province'):
                        # 直接使用原始行政区划名称（保留省/自治区/市）
                        province = region['province'].strip()
                        # 处理自治州、地区等特殊后缀
                        city = region['city'].strip()
                        # 存储元组
                        city_province.add((province, city))

            # 按省份+城市排序（保留完整行政区划名称）
            return sorted(list(city_province), key=lambda x: (x[0], x[1]))

        else:
            print("接口异常:", response.json().get('message'))
            return []

    except Exception as e:
        print(f"处理失败: {str(e)}")
        return []

def validate_model(model: Dict) -> bool:

    return bool(model.get("code")) and bool(model.get("name"))


def filter_models(raw_models: List[Dict]) -> List[Dict]:

    required_fields = {'modelId', 'modelName', 'series'}
    return [
        model for model in raw_models
        if all(field in model for field in required_fields)
    ]

# --- 移动 brands 变量的初始化到此处 ---
brands = get_brand_names(SELECT_BRANDS_API)
print("提取的品牌列表：")
for brand_name_item in brands:
    print(f"品牌: {brand_name_item}")

city_list = get_all_cities()
print(f"共获取 {len(city_list)} 个城市")
# print(city_list) # 可以取消注释以查看城市列表

models_data = fetch_models_by_brands(brands)
print(f"共获取 {len(models_data)} 款车型数据")
model_ids = [item['modelId'] for item in models_data]
# print(model_ids) # 可以取消注释以查看车型ID列表

# --- 移动 payload_dealers_default 变量的定义到此处 ---
payload_dealers_default = {
"isMatchRegion": False,
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
shops = []

# 加载进度
start_brand_idx, start_city_idx, start_model_idx, start_service_type_idx = load_progress()

# 初始化CSV（仅在首次运行时）
if not os.path.exists(PROGRESS_FILE):
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline='') as f:
        list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        list_writer.writerow(RESULT_FIELDS)
    print(f"已初始化CSV文件: {OUTPUT_PATH}")

dealer_count = 0
seen = set() # 用于去重
shops_buffer = [] # 用于批量写入CSV
batch_size = 100 # 每100条写入一次

# 主循环
for i_st, current_serviceType in enumerate(service_type[start_service_type_idx:], start=start_service_type_idx):
    # 如果是从中断处恢复，且不是第一个service_type，则city_idx从0开始
    current_start_city_idx = start_city_idx if i_st == start_service_type_idx else 0
    for i_city, (province, city) in enumerate(city_list[current_start_city_idx:], start=current_start_city_idx):
        # 如果是从中断处恢复，且不是第一个city，则model_idx从0开始
        current_start_model_idx = start_model_idx if i_st == start_service_type_idx and i_city == start_city_idx else 0
        for i_model, model in enumerate(model_ids[current_start_model_idx:], start=current_start_model_idx):
            page = 1
            retries = 0
            print(f"\n正在处理: 服务类型={current_serviceType} ({i_st+1}/{len(service_type)}), "
                  f"省份城市={province}-{city} ({i_city+1}/{len(city_list)}), "
                  f"车型ID={model} ({i_model+1}/{len(model_ids)})"
            )
            save_progress(0, i_city, i_model, i_st) # 注意：这里的brand_idx暂时设为0，因为brands列表在models_data中已处理

            while True:
                try:
                    payload_dealers = payload_dealers_default.copy()
                    payload_dealers.update({
                        "serviceType": current_serviceType,
                        "city": city,
                        "pageIndex": page,
                        "pageSize": 20,
                        "province": province,
                    })
                    payload_dealers["vehicleInfo"]["vehicleId"] = model
                    # print(payload_dealers) # 可以取消注释以查看请求体

                    # 修改主循环中的异常处理
                    try:
                        resp = requests.post(
                            GET_MAIN_SHOP,
                            headers=get_random_headers(),  # 使用随机headers
                            data=json.dumps(payload_dealers, ensure_ascii=False),
                            timeout=20
                        )
                        resp.raise_for_status()

                        if resp.status_code == 200:
                            # print("成功访问API") # 可以取消注释
                            response_json = resp.json()
                            if response_json.get('code') == 10000:
                                # print("操作成功") # 可以取消注释
                                data = response_json.get("data")
                                # print(f"返回的data: {json.dumps(data, ensure_ascii=False)}") # 可以取消注释

                                retry_data_count = 0
                                while data is None and retry_data_count < MAX_RETRIES:
                                    print(
                                        f"data为None，重试第{retry_data_count + 1}次，serviceType={current_serviceType}, province={province}, city={city}, model={model}")
                                    resp = requests.post(
                                        GET_MAIN_SHOP,
                                        headers=get_random_headers(),
                                        data=json.dumps(payload_dealers, ensure_ascii=False),
                                        timeout=20
                                    )
                                    resp.raise_for_status()
                                    data = resp.json().get("data")
                                    retry_data_count += 1

                                if not isinstance(data, dict):
                                    print(f"警告: API返回的data非字典类型或为None，跳过当前车型分页。Data: {data}")
                                    break # 跳出分页循环，处理下一个车型

                                shop_list = data.get("shopList")

                                if shop_list is None:
                                    print(f"shopList为null: serviceType={current_serviceType}, province={province}, city={city}, model={model}, page={page}")
                                    break # 当前分页没有店铺列表，尝试下一页或下一个组合

                                if not shop_list:
                                    print(
                                        f"没有相关店铺信息: serviceType={current_serviceType}, province={province}, city={city}, model={model}, page={page}")
                                    break # 当前分页店铺列表为空，处理完毕

                                for shop_item in shop_list:
                                    row = process_shop(shop_item)
                                    unique_key = f"{row['店名']}_{row['地址']}"

                                    if unique_key not in seen:
                                        seen.add(unique_key)
                                        shops_buffer.append(row)
                                        # print(json.dumps(row, ensure_ascii=False)) # 可以取消注释
                                        dealer_count += 1

                                        if len(shops_buffer) >= batch_size:
                                            with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                                                dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                                                dict_writer.writerows(shops_buffer)
                                            print(f"已批量写入 {len(shops_buffer)} 条店铺数据到CSV")
                                            shops_buffer.clear()

                                total_page = data.get("totalPage", 1)
                                if page >= total_page or page >= 100: # 限制最大页数，防止无限循环
                                    break
                                page += 1
                                # sleep(random.uniform(1.2, 1)) # 可以根据需要调整延时
                            else:
                                print(f"API业务错误: code={response_json.get('code')}, message={response_json.get('message')}")
                                break # API返回业务错误，跳过当前组合
                        else:
                            print(f"HTTP错误: {resp.status_code}")
                            # 根据需要，这里也可以加入重试逻辑或直接break
                            break

                        retries = 0  # 成功请求后重置重试计数器

                    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                        print(f"请求或解析异常: {str(e)}")
                        print("保存当前进度并等待重试...")
                        save_progress(0, i_city, i_model, i_st)
                        retries += 1
                        if retries >= MAX_RETRIES:
                            print(f"已达到最大重试次数 {MAX_RETRIES}，保存进度并退出")
                            # 保存当前批次数据
                            if shops_buffer:
                                with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
                                    dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                                    dict_writer.writerows(shops_buffer)
                                print(f"已保存 {len(shops_buffer)} 条数据到CSV")
                                shops_buffer.clear()
                            sys.exit(1)  # 异常退出，保留进度文件
                        print(f"等待 {2 ** retries} 秒后重试...")
                        sleep(2 ** retries)
                except Exception as e_global:
                    print(f"发生未预料的全局错误: {str(e_global)}。正在保存当前进度并尝试跳过当前组合。")
                    save_progress(0, i_city, i_model, i_st) # 发生未知错误时也保存进度
                    break # 跳出分页循环，尝试下一个组合

        # 重置内层循环的起始索引，确保下一个外层循环从头开始
        start_model_idx = 0
    start_city_idx = 0

# 确保所有缓冲数据都被写入
if shops_buffer:
    with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        dict_writer.writerows(shops_buffer)
    print(f"已写入剩余 {len(shops_buffer)} 条店铺数据到CSV")
    shops_buffer.clear()

# 清理进度文件（可选，如果希望每次都从头开始，则不应清理）
# if os.path.exists(PROGRESS_FILE):
#     os.remove(PROGRESS_FILE)
#     print(f"爬取完成，已删除进度文件: {PROGRESS_FILE}")

print(f"爬取完成，共计 {dealer_count} 个门店数据已保存到 {OUTPUT_PATH}")