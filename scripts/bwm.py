import os
import random
import requests
import json
import csv
from time import sleep
from urllib.parse import urljoin

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/bmw.csv")

# CSV头定义
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]

# API基础配置
BASE_URL = "https://service-center-customer-api.lingyue-digital.com"
PROVINCE_API = "/customer-dealer/dealer/area-province-city?level=0&parentId=1"
CITY_API_TEMPLATE = "/customer-dealer/dealer/area-province-city?level=1&parentId={province_id}"
OUTLET_API_TEMPLATE = "/customer-dealer/dealer/outlets?brand=1&cityCode={city_code}&coordinateType=baidu"

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Business-Type": "NC-TEST_DRIVE",  # 必须包含的认证头[4,7](@ref)
    "Referer": "https://www.bmw.com.cn/",
    "Accept-Encoding": "gzip, deflate, br"
}

# 代理配置（可选）
PROXY = None  # 如需代理可参考网页1设置

def create_session():
    """创建带重试机制的会话"""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_data(session, url):
    """通用数据获取函数"""
    try:
        sleep(random.uniform(1, 3))  # 随机延时防封禁[2,6](@ref)
        response = session.get(url, headers=HEADERS, proxies=PROXY, timeout=15)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        print(f"请求失败: {url}，错误: {str(e)}")
        return None

def get_provinces(session):
    """获取省份数据"""
    url = urljoin(BASE_URL, PROVINCE_API)
    return fetch_data(session, url)

def get_cities(session, province_id):
    """获取城市数据"""
    url = urljoin(BASE_URL, CITY_API_TEMPLATE.format(province_id=province_id))
    return fetch_data(session, url)

def get_outlets(session, city_code):
    """获取经销商数据"""
    url = urljoin(BASE_URL, OUTLET_API_TEMPLATE.format(city_code=city_code))
    return fetch_data(session, url)

def process_outlet(province_info, city_info, outlet):
    """处理单条经销商数据"""
    return {
        "品牌": "宝马",
        "省": province_info['name'],
        "Province": "",
        "市区辅助": city_info['shortName'],
        "City/Area": "",
        "区": outlet.get('countyNameZh', ''),
        "店名": outlet['outletNameCn'],
        "类型": outlet['outletTypeNameCn'],
        "地址": outlet['businessAddressCn'],
        "电话": outlet['phone'],
        "备注": ""
    }

def main():
    # 初始化CSV文件
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()

        with create_session() as session:
            # 第一阶段：获取省份
            provinces = get_provinces(session)
            print(f"获取到 {len(provinces)} 个省份")

            for province in provinces:
                # 第二阶段：获取城市
                cities = get_cities(session, province['id'])
                if not cities:
                    continue

                for city in cities:
                    # 第三阶段：获取经销商
                    outlets = get_outlets(session, city['code'])
                    if not outlets:
                        continue

                    # 写入数据
                    for outlet in outlets:
                        row = process_outlet(province, city, outlet)
                        writer.writerow(row)
                        print(f"已抓取: {row['店名']}")
                        print(json.dumps(row, ensure_ascii=False))

    print(f"数据采集完成，总计 {sum(1 for _ in open(OUTPUT_PATH)) - 1} 条记录")


main()