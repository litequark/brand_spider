import os
import random
import requests
import json
import csv
from time import sleep

INTERVAL = 1  # 网络请求间隔（秒）
API = "https://www.continental-tires.cn/tpservice/Search/searchAgency"
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "地址", "电话", "备注"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/continental.csv")


def sleep_with_random(interval: int, rand_max: int) -> None:
    sleep(interval + random.random() * rand_max)


# 创建父目录（如果不存在）
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# 初始化CSV文件并写入表头
with open(OUTPUT_PATH, "w", encoding="utf-8", newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(RESULT_FIELDS)

# 配置请求参数
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
params = {
    'lng1': '118.62841',
    'lat1': '32.059',
    'lng2': '118.62841',
    'lat2': '32.059',
    'range': '40000000000'
}

# 发送请求
sleep_with_random(INTERVAL, 1)
try:
    response = requests.get(API, params=params, headers=headers)
    response.raise_for_status()
    shops = response.json()
except Exception as e:
    print(f"请求失败: {str(e)}")
    exit()

total = len(shops)
for shop in shops:
    # 构建数据行
    row = [
        "",  # 省
        "",  # Province
        "",  # 市区辅助
        "",  # City
        "",  # 区
        shop.get("name", ""),
        shop.get("address", ""),
        shop.get("phone", ""),
        ""  # 备注
    ]

    # 控制台输出
    print(json.dumps(
        dict(zip(RESULT_FIELDS, row)),
        ensure_ascii=False,
        indent=2
    ))

    # 写入CSV
    with open(OUTPUT_PATH, "a", encoding="utf-8", newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(row)


print(f"总门店数：{total}")