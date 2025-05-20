import os
import csv
import requests
import json


count =0
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)  # 自动创建目录[6,8](@ref)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ferrari_dealers.csv")

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
def fetch_api_data():
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        return json.loads(response.text)
    except Exception as e:
        print(f"API请求失败: {str(e)}")
        return None


def process_features(raw_data):
    """处理数据特征"""
    if not raw_data or "data" not in raw_data:
        return []

    features = raw_data["data"]["results"]["features"]
    processed = []

    for feature in features:
        prop = feature["properties"]
        geo = feature["geometry"]


        record = [
            "法拉利",  # 品牌
            prop.get("main_CountyCountrySub-Division", ""),  # 省
            prop.get("ProvinceStateExt", ""),  # Province
            prop.get("main_CityName", ""),  # 市区辅助
            prop.get("Locality", ""),  # City/Area
            prop.get("main_CitySub-DivisionName", ""),  # 区
            prop.get("Name", ""),  # 店名
            "展厅" if "showroom" in prop.get("DealerType", "") else "服务中心",  # 类型
            f'{prop.get("Address", "")}（坐标：{geo["coordinates"][0]},{geo["coordinates"][1]}）',  # 地址
            prop.get("Telephone", "").replace("0086", "+86"),  # 电话
            generate_remark(prop)  # 备注
        ]
        processed.append(record)

    return processed


def generate_remark(prop):

    return "\n".join([
        f"工作日：{prop.get('Mon-M-From', '')}-{prop.get('Mon-M-To', '')}",
        f"周末：{prop.get('Sat-M-From', '')}-{prop.get('Sat-M-To', '')}",
        f"最后更新：{prop.get('otm_visible_date', '2025-05')}"
    ])


def save_to_csv(data):

    try:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(data)
        print(f"数据已保存至：{os.path.abspath(OUTPUT_PATH)}")
    except Exception as e:
        print(f"文件保存失败: {str(e)}")



raw_data = fetch_api_data()
count=len(raw_data)
print(f"一共{count}条数据")
if raw_data:
        processed_data = process_features(raw_data)
        if processed_data:
            save_to_csv(processed_data)
            print(processed_data)
        else:
            print("无有效数据处理")
else:
        print("未获取到API数据")
