import os
import requests
import pandas as pd
import json
import re
from datetime import datetime

# Constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/geely.csv")

# API URLs
SERVICE_PROVIDER_URL = "https://www.geely.com/api/geely/official/common/GetServiceProviderList"
BATTERY_RECYCLE_URL = "https://www.geely.com/api/geely/official/common/GetBatteryRecycle"

# Result fields as specified
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]

# Load provinces and cities data
PROVINCES_FILE = os.path.join(SCRIPT_DIR, "util", "provinces.json")
CITIES_FILE = os.path.join(SCRIPT_DIR, "util", "cities.json")

provinces_data = {}
cities_data = {}

try:
    with open(PROVINCES_FILE, 'r', encoding='utf-8') as f:
        provinces_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Warning: Could not load provinces data: {e}")

try:
    with open(CITIES_FILE, 'r', encoding='utf-8') as f:
        cities_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Warning: Could not load cities data: {e}")


def extract_location_info(address):
    """从地址中提取省市区信息"""
    province = ""
    city = ""
    district = ""

    if not address:
        return province, city, district

    # 省份匹配
    province_patterns = [
        r'(\w+省)', r'(\w+自治区)', r'(北京市|上海市|天津市|重庆市)',
        r'(内蒙古|广西|西藏|宁夏|新疆)\w*自治区', r'(香港|澳门)\w*特别行政区'
    ]

    for pattern in province_patterns:
        match = re.search(pattern, address)
        if match:
            province = match.group(1)
            break

    # 城市匹配
    city_patterns = [r'(\w+市)', r'(\w+州)', r'(\w+盟)', r'(\w+地区)']
    for pattern in city_patterns:
        matches = re.findall(pattern, address)
        if matches:
            # 取第一个非省级城市
            for match in matches:
                if match != province:
                    city = match
                    break

    # 区县匹配
    district_patterns = [r'(\w+区)', r'(\w+县)', r'(\w+旗)']
    for pattern in district_patterns:
        match = re.search(pattern, address)
        if match:
            district = match.group(1)
            break

    return province, city, district


def make_api_request(url, params=None):
    """Makes a GET request to the specified URL with optional parameters."""
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("isSuccess") and data.get("status") == 200:
            return data.get("data", [])
        else:
            print(f"API request failed: {data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []


def process_service_providers():
    """处理服务商数据"""
    print("开始爬取吉利服务商信息...")
    all_data = []

    # 尝试不同的参数组合来获取数据
    # 根据API响应，看起来可以直接调用而不需要特定参数
    providers = make_api_request(SERVICE_PROVIDER_URL)

    if not providers:
        # 如果直接调用失败，尝试一些常见的参数
        print("尝试使用参数获取数据...")
        for province_id in range(10, 350, 10):
            for city_id in range(1, 50):
                params = {
                    "provinceId": str(province_id),
                    "cityId": f"2{province_id:03d}{city_id:02d}"
                }
                providers = make_api_request(SERVICE_PROVIDER_URL, params)
                if providers:
                    break
            if providers:
                break

    if providers:
        for provider in providers:
            address = provider.get("Address", "")
            province, city, district = extract_location_info(address)

            # 获取英文省市名称
            province_en = provinces_data.get(province, "")
            city_en = cities_data.get(city, "")

            data_row = {
                "省": province,
                "Province": province_en,
                "市区辅助": city,
                "City": city_en,
                "区": district,
                "店名": provider.get("DealerName", ""),
                "类型": "服务商",
                "地址": address,
                "电话": provider.get("HotLine", ""),
                "备注": f"DealerId:{provider.get('DealerId', '')}, Code:{provider.get('DealerCode', '')}, 坐标:{provider.get('Coordinates', '')}"
            }
            all_data.append(data_row)

    print(f"服务商数据获取完成，共{len(all_data)}条记录")
    return all_data


def process_battery_recycle():
    """处理电池回收点数据"""
    print("开始爬取吉利电池回收点信息...")
    all_data = []

    locations = make_api_request(BATTERY_RECYCLE_URL)

    if locations:
        for location in locations:
            address = location.get("Address", "")
            province, city, district = extract_location_info(address)

            # 获取英文省市名称
            province_en = provinces_data.get(province, "")
            city_en = cities_data.get(city, "")

            data_row = {
                "省": province,
                "Province": province_en,
                "市区辅助": city,
                "City": city_en,
                "区": district,
                "店名": location.get("UnitName", ""),
                "类型": "电池回收点",
                "地址": address,
                "电话": location.get("PhoneNo", ""),
                "备注": f"UnitId:{location.get('UnitId', '')}, UnitNo:{location.get('UnitNo', '')}, 坐标:{location.get('Coordinates', '')}"
            }
            all_data.append(data_row)

    print(f"电池回收点数据获取完成，共{len(all_data)}条记录")
    return all_data


def main():
    """主函数"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print("开始爬取吉利门店信息...")

    # 获取所有数据
    all_data = []

    # 处理服务商数据
    service_data = process_service_providers()
    all_data.extend(service_data)

    # 处理电池回收点数据
    battery_data = process_battery_recycle()
    all_data.extend(battery_data)

    # 保存数据
    if all_data:
        df = pd.DataFrame(all_data, columns=RESULT_FIELDS)
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
        print(f"\n爬取完成！")
        print(f"总共获取 {len(all_data)} 条记录")
        print(f"数据已保存到: {OUTPUT_PATH}")

        # 显示统计信息
        type_counts = df['类型'].value_counts()
        print("\n数据统计:")
        for type_name, count in type_counts.items():
            print(f"  {type_name}: {count} 条")
    else:
        print("未获取到任何数据")


if __name__ == "__main__":
    main()