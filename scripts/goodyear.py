import io
import json
import os
import csv
import random
import time
import requests
import bs4
from typing import Dict, List
import chardet
import gzip
from util.location_translator import get_en_province, get_en_city

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "goodyear.csv")
global totalCount

# API配置
LOCATION_API = "https://www.goodyear.com.cn/wp-content/themes/goodyearforward/js/store/location-filter.json"
STORE_API = "https://www.goodyear.com.cn/wp-admin/admin-ajax.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.goodyear.com.cn/store-locator",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip",
    "X-Requested-With": "XMLHttpRequest",
    'charset': 'utf-8'
}

CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]


def init_output():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def sleep_random(base: int = 2, rand_max: int = 3):
    time.sleep(base + random.uniform(0, rand_max))


def fetch_provinces() -> Dict:
    try:
        response = requests.get(LOCATION_API, headers=HEADERS)
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"获取地区数据失败: {str(e)}")
        return {}


def parse_store(html: str) -> List[Dict]:
    soup = bs4.BeautifulSoup(html, 'html.parser')
    stores = []

    for article in soup.find_all('article', class_='store-card'):
        try:
            # 基础信息解析
            name = article.find('a', class_='inline-link-p1').text.strip()
            address = article.select_one('.address-street').text.strip()
            phone_element = article.select_one('.phone-no-analytics a')
            phone = phone_element['href'].replace('tel:', '') if phone_element else ''

            # 增强版地址解析
            region_text = ''
            # 解析省市信息
            city = ''
            province = ''
            if address_city_state := article.select_one('.address-city-state'):
                region_text = address_city_state.text.strip()
                
                # 处理城市和省份信息
                if ',' in region_text:
                    parts = [p.strip() for p in region_text.split(',')]
                    if len(parts) >= 2:
                        # 取第一部分作为城市名
                        city = parts[0].strip()
                        province = parts[1].strip()
                        # 清理城市名称中的多余字符
                        city = city.replace('\n', '').replace('\r', '').strip()

            city_cn_data = city.split('/')
            city_cn = city_cn_data[1]
            province = province.replace('\n', '').replace('\r', '').strip()
            province_cn_data = province.split('/')
            province_cn = province_cn_data[1]


            # 使用工具函数获取标准化的省份和城市名称

            province_en = get_en_province(province_cn) if province_cn else ''

            # 构建数据记录
            store_data = {
                "品牌": "固特异",
                "省": province_cn,
                "Province": province_en,
                "City/Area": get_en_city(city_cn) if city else '',
                "市区辅助": city_cn,
                "区": "",
                "店名": name,
                "类型": "",
                "地址": address,
                "电话": phone,
                "备注": ""
            }

            stores.append(store_data)
            print(json.dumps(store_data, ensure_ascii=False))

        except Exception as e:
            print(f"解析异常: {str(e)}")
            print("异常节点内容:", article.prettify())

    return stores


def save_data(data: List[Dict]):
    with open(OUTPUT_PATH, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writerows(data)


def fetch_store_page(province: str, page: int) -> int:

    total = 0
    try:
        with requests.Session() as session:
            session.headers.update({
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/x-www-form-urlencoded"
            })

            form_data = {
                'province': province,
                'page_no': str(max(page, 1)),
                'page_size': '15',
                'action': 'filterStores'
            }

            response = session.post(
                STORE_API,
                data=form_data,
                timeout=10,
                allow_redirects=False,
                stream=True
            )

            # 处理压缩响应
            raw_bytes = response.raw.read()
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(raw_bytes)) as f:
                    decompressed = f.read()
            except OSError:
                decompressed = raw_bytes

            # 自动检测编码
            encoding = chardet.detect(decompressed)['encoding'] or 'utf-8'
            content = decompressed.decode(encoding, errors='replace')

            if response.status_code == 200:
                try:
                    data = json.loads(content)
                    total = int(data.get('count', 0))
                    print(f"当前省份 {province} 第 {page} 页，总计 {total} 条数据")

                    if 'resultHTML' in data:
                        stores = parse_store(data['resultHTML'])
                        if stores:
                            save_data(stores)
                            print(f"成功保存 {len(stores)} 条记录")

                except json.JSONDecodeError:
                    print("响应数据不是有效的JSON格式")
                    print("原始响应内容:", content[:500])

            return total

    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {str(e)}")
        return total


def main():
    init_output()
    provinces = fetch_provinces()

    for province_name in provinces.keys():
        print(f"\n{'=' * 40}\n开始处理省份: {province_name}\n{'=' * 40}")
        page = 1
        max_retry = 3

        while True:
            print(f"\n▶ 正在获取第 {page} 页...")
            total = fetch_store_page(province_name, page)

            # 分页终止条件
            if total == 0 or page * 15 >= total:
                break

            page += 1
            sleep_random(1, 2)

        sleep_random(3, 2)



main()
print(f"所有门店数据抓取完成")