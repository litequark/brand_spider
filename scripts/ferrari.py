import os
import csv
import requests
import json
from pypinyin import lazy_pinyin, Style

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)#进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/ferrari.csv")

API_URL = "https://api.onthemap.io/server/v1/api/location"
params = {
    "dataset": "dealer",
    "disable_focus": "true",
    "radius": "100000000",
    "language": "CHI",
    "query": "[Nation]=[CN]",
    "key": "8a5c90b0-d81f-11eb-92d3-a51e1f563c94",
    "channel": "static.apps.ferrarinetwork.ferrari.com"
}

CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]


def chinese_to_pinyin(chinese_str):

    if not chinese_str:
        return ""
    return ''.join(lazy_pinyin(chinese_str, style=Style.NORMAL)).title()


def fetch_api_data():
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        return json.loads(response.text)
    except Exception as e:
        print(f"API请求失败: {str(e)}")
        return None


def process_features(raw_data):
    if not raw_data or "data" not in raw_data:
        return []

    features = raw_data["data"]["results"]["features"]
    processed = []
    print(f"\n开始处理数据，共发现{len(features)}个经销商信息：")

    for index, feature in enumerate(features, 1):
        prop = feature["properties"]
        geo = feature["geometry"]


        province_cn = prop.get("main_CountyCountrySub-Division", "")
        province_py = chinese_to_pinyin(province_cn)


        city_cn = prop.get("main_CityName", "")
        city_py = chinese_to_pinyin(city_cn)

        record = [
            "法拉利",  # 品牌
            province_cn,  # 省（中文）
            "",
            city_cn,  # 市区辅助（市中文）
            "",
            prop.get("main_CitySub-DivisionName", ""),
            prop.get("Name", ""),
            "展厅" if "showroom" in prop.get("DealerType", "") else "服务中心",  # 类型
            f'{prop.get("Address", "")}',  # 地址
            prop.get("Telephone", "").replace("0086", "+86"),  # 电话
            ""
        ]

        processed.append(record)
        print(f"{record[0]}, {record[1]}, {record[2]}, {record[3]}, {record[4]}, {record[5]}, {record[6]}, {record[7]},")


    return processed


def save_to_csv(data):
    try:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(data)
        print(f"\n数据已保存至：{os.path.abspath(OUTPUT_PATH)}")
    except Exception as e:
        print(f"文件保存失败: {str(e)}")


raw_data = fetch_api_data()
if raw_data:
    processed_data = process_features(raw_data)
    if processed_data:
            save_to_csv(processed_data)
            print(f"\n 处理完成！共成功转换{len(processed_data)}条数据")
    else:
            print(" 无有效数据处理")
else:
        print(" 未获取到API数据")