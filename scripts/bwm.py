import os
import random
import requests
import json
import csv
import time
from time import sleep
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from util.location_translator import get_en_province, get_en_city

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/bmw.csv")

# CSV头定义
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]

# API配置
BASE_URL = "https://service-center-customer-api.lingyue-digital.com"
PROVINCE_API = "/customer-dealer/dealer/area-province-city?level=0&parentId=1"
CITY_API = "/customer-dealer/dealer/area-province-city?level=1&parentId=1"
OUTLET_API_TEMPLATE = "/customer-dealer/dealer/outlets?brand=1&cityCode={city_code}&coordinateType=baidu&page={page}&pageSize=100"

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Business-Type": "NC-TEST_DRIVE",
    "Referer": "https://www.bmw.com.cn/",
    "Accept-Encoding": "gzip, deflate, br"
}


class DataValidator:
    @staticmethod
    def validate_province(province):
        """验证省份数据结构"""
        required_keys = ['id', 'name', 'code', 'parentId']
        if not all(k in province for k in required_keys):
            raise ValueError(f"无效的省份数据结构: {province}")

    @staticmethod
    def validate_city(city):
        """验证城市数据结构"""
        required_keys = ['id', 'name', 'code', 'parentId']
        if not all(k in city for k in required_keys):
            raise ValueError(f"无效的城市数据结构: {city}")


def create_session():
    """创建带连接池的会话"""
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=50,
        pool_maxsize=100,
        max_retries=3
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def fetch_data(session, url, max_retries=3):
    """增强的请求函数"""
    for attempt in range(max_retries):
        try:
            sleep(random.uniform(0.5, 1.5))
            response = session.get(url, headers=HEADERS, timeout=(3, 15))
            response.raise_for_status()
            return response.json().get('data', [])
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"请求失败（尝试 {attempt + 1}/{max_retries}）: {url} - {str(e)}")
            if attempt == max_retries - 1:
                return None
            sleep(2 ** attempt)


def get_provinces_and_cities(session):
    """获取所有省份和城市数据"""
    # 获取所有省份
    province_url = urljoin(BASE_URL, PROVINCE_API)
    provinces = fetch_data(session, province_url)
    if not provinces:
        raise ValueError("无法获取省份数据")
    
    # 创建省份ID到省份数据的映射
    province_map = {p['id']: p for p in provinces}
    
    # 获取所有城市
    city_url = urljoin(BASE_URL, CITY_API)
    cities = fetch_data(session, city_url)
    if not cities:
        raise ValueError("无法获取城市数据")
    
    return province_map, cities


def get_outlets(session, city):
    """获取指定城市的所有门店"""
    DataValidator.validate_city(city)
    
    outlets = []
    page = 1
    while True:
        url = urljoin(BASE_URL, OUTLET_API_TEMPLATE.format(
            city_code=city['code'],
            page=page
        ))
        data = fetch_data(session, url)
        if not data:
            break

        # 检查返回的数据结构
        if isinstance(data, list):
            # 如果是列表，直接添加到outlets
            outlets.extend(data)
            print(f"城市 {city['name']} 第 {page} 页，获取 {len(data)} 条")
            break  # 假设列表形式的返回只有一页
        elif isinstance(data, dict):
            # 如果是字典，按原来的逻辑处理
            current_page = data.get('current', 1)
            total_pages = data.get('pages', 1)
            records = data.get('records', [])
            outlets.extend(records)

            print(f"城市 {city['name']} 第 {current_page}/{total_pages} 页，获取 {len(records)} 条")

            if page >= total_pages:
                break
        else:
            print(f"城市 {city['name']} 返回了未知的数据结构: {type(data)}")
            break
            
        page += 1
    
    return outlets


def process_row(province, city, outlet):
    """处理单条数据"""
    return {
        "品牌": "宝马",
        "省": province['name'],
        "Province": get_en_province(province['name']),
        "市区辅助": city.get('shortName', ''),
        "City/Area": get_en_city(city.get('shortName', '')),
        "区": outlet.get('countyNameZh', ''),
        "店名": outlet.get('outletNameCn', ''),
        "类型": outlet.get('outletTypeNameCn', ''),
        "地址": outlet.get('businessAddressCn', ''),
        "电话": outlet.get('phone', ''),
        "备注": ""
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()

        with create_session() as session:
            try:
                # 获取所有省份和城市数据
                province_map, cities = get_provinces_and_cities(session)
                print(f"成功获取 {len(province_map)} 个省份和 {len(cities)} 个城市")

                # 遍历城市
                for city in cities:
                    # 根据城市的parentId找到对应的省份
                    province_id = city.get('parentId')
                    if province_id not in province_map:
                        print(f"警告：城市 {city['name']}(ID:{city['id']}) 的省份ID {province_id} 不存在")
                        continue
                    
                    province = province_map[province_id]
                    print(f"\n处理城市: {city['name']}(ID:{city['id']})，所属省份: {province['name']}(ID:{province['id']})")
                    
                    # 获取该城市的所有门店
                    outlets = get_outlets(session, city)
                    if not outlets:
                        print(f"城市 {city['name']} 无门店数据")
                        continue

                    print(f"发现 {len(outlets)} 个门店")
                    
                    # 处理每个门店数据
                    for outlet in outlets:
                        writer.writerow(process_row(province, city, outlet))
                        print(json.dumps(process_row(province, city, outlet), ensure_ascii=False))

            except Exception as e:
                print(f"致命错误: {str(e)}")
                raise

    print(f"\n数据采集完成，存储路径: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()