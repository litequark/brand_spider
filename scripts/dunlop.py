import csv
import ast
import os
import re
import requests
from bs4 import BeautifulSoup

from util.bs_sleep import sleep_with_random
from util.location_translator import get_en_province, get_en_city

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]
DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)#进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/dunlop.csv")


def save_dealers_to_csv(dealer: dict | list[dict], path: str) -> None:
    if isinstance(dealer, list):
        for d in dealer:
            save_dealers_to_csv(d, path)
    else:
        try:
            with open(path, "a", encoding='utf-8', newline='') as f:
                dict_writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
                dict_writer.writerow(dealer)
        except Exception as e:
            print(e)


def parse_baidu_map_string(s) -> dict:
    """
    解析类似 inItBaiduMap(...) 格式的字符串，返回包含地址、电话、类型和名称的字典
    示例输入：inItBaiduMap(5196, '石牌镇梅溪路2号金象温泉城37幢2单元102室', '15759065582', 'D驾族', '大田县鑫铭轮胎店', 117.8459027000, 25.6551277600);
    """
    # 使用正则表达式提取括号内的参数部分
    pattern = r'(?<=inItBaiduMap\()(.*)(?=\);?)'
    match = re.search(pattern, s)

    if not match:
        raise ValueError("输入字符串不符合 inItBaiduMap(...) 格式")

    # 获取所有参数组成的字符串
    args_str = match.group(1)

    try:
        # 创建完整的元组字符串并安全评估（eval）为Python对象
        tuple_str = f'({args_str})'
        args = ast.literal_eval(tuple_str)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"参数解析错误: {e}") from e

    # 检查参数数量是否足够
    if len(args) < 5:
        raise ValueError(f"参数数量不足，至少需要5个，实际得到{len(args)}个")

    # 提取所需信息并构建结果字典
    result = {
        "地址": args[1],  # 第二个参数是地址
        "电话": args[2],  # 第三个参数是电话
        "类型": args[3],  # 第四个参数是类型
        "店名": args[4]  # 第五个参数是名称
    }

    return result


def get_dealers(soup) -> list[dict]:
    dealers: list[dict] = list()
    dealers_elem = soup.select('div.location_list > ul > li')
    for e in dealers_elem:
        p_id = e.get('onclick')
        dealers.append(parse_baidu_map_string(p_id))
    return dealers


def get_provinces(soup) -> dict:
    province_ids: dict = dict()
    provinces_elem = soup.select('#province > li')
    for e in provinces_elem:
        p_id: str = e.get('data-val')
        p_name: str = e.text
        province_ids.update({p_id: p_name})
    return province_ids


def get_cities(soup) -> dict:
    city_ids: dict = dict()
    cities_elem = soup.select('li')
    for e in cities_elem:
        c_id: str = e.get('data-val')
        c_name: str = e.text
        city_ids.update({c_id: c_name})
    return city_ids


def fetch_html(url):
    try:
        # 发送 GET 请求
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)

        # 检查响应状态
        if response.status_code == 200:
            # 处理可能的编码问题
            response.encoding = response.apparent_encoding
            return response.text
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求发生异常: {e}")
        return None


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:  # 清除csv文件
        # 写入表头
        list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        list_writer.writerow(RESULT_FIELDS)

    api = "https://www.dunlop.com.cn/index_salearea.html"

    dealer_count: int = 0

    html_content = fetch_html(api)

    # 使用BeautifulSoup解析HTML
    provinces_soup = BeautifulSoup(html_content, 'html.parser')

    provinces: dict = get_provinces(provinces_soup)
    print(f'已获取{len(provinces)}个省份')

    for province_id, province_name in provinces.items():
        city_params: dict = {
            "paction": "getlist",
            "prov_id": province_id
        }
        response = requests.get(api, params=city_params, headers=DEFAULT_HEADERS)
        response.raise_for_status()  # 如果状态码非200，抛出异常
        cities_html = response.text
        cities_soup = BeautifulSoup(cities_html, 'html.parser')
        cities: dict = get_cities(cities_soup)
        print(f'当前省份已获取{len(cities)}个城市')
        for city_id, city_name in cities.items():
            dealer_params: dict = {
                "prov": province_id,
                "city": city_id
            }
            response = requests.get(api, params=dealer_params, headers=DEFAULT_HEADERS)
            response.raise_for_status()  # 如果状态码非200，抛出异常
            dealers_html = response.text
            dealers_soup = BeautifulSoup(dealers_html, 'html.parser')
            dealers: list[dict] = get_dealers(dealers_soup)
            for d in dealers:
                attr_province: str = province_name
                attr_city: str = str()
                attr_district: str = str()
                if any(city in province_name for city in ['北京', '上海', '天津', '重庆']):
                    attr_city = province_name
                    attr_district = city_name
                    d.update({
                        "区": attr_district
                    })
                else:
                    attr_city = city_name

                d.update({
                    "省": attr_province,
                    "Province": get_en_province(attr_province),
                    "市": attr_city,
                    "City": get_en_city(attr_city)
                })
            save_dealers_to_csv(dealers, OUTPUT_PATH)
            print(dealers)
            dealer_count += len(dealers)

            sleep_with_random(1, 1)

    print(f'共获取到{dealer_count}家门店')


if __name__ == "__main__":
    main()
