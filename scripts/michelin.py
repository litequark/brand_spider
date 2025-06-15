"""
TO-DO:

- 省份及其英文
- 可克达拉市的英文

"""

import os
import random
import requests
import json
import csv
from time import sleep
from util.location_translator import get_en_province, get_en_city

# 配置参数
INTERVAL = 1  # 基础请求间隔（秒）
RANDOM_DELAY = 0.5  # 随机延迟上限
API_TEMPLATE = "https://www.michelin.com.cn/auto/dealer-locator/assets/js/city_az-dealer/{}.json"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15'
]

# 输出配置
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output/michelin.csv")


def random_delay():
    """随机延迟机制"""
    sleep(INTERVAL + random.uniform(0, RANDOM_DELAY))


def get_headers():
    """生成随机请求头"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json',
        'Referer': 'https://www.michelin.com.cn/auto/dealer-locator/'
    }


def process_store(writer, city_name, district_name, store):
    """处理单个门店数据"""
    try:
        # 数据转换逻辑
        store_type = ''
        if store['ty'] == 'TYREPLUS':
            store_type = '驰加'
        elif store['ty'] == 'MCR':
            store_type = '非驰加'
        elif store['ty'] == 'MPC':
            store_type = 'MPC'
        else:
            store_type = store['ty']
            raise Exception('没有找到已知类型')
        city_en = get_en_city(city_name) if callable(get_en_city) else ''

        row = [
            "",  # 省（根据需求置空）
            "",  # Province（英文省名）
            city_name,  # 市区辅助（中文市名）
            city_en,  # City（英文市名）
            district_name,  # 区县
            store['na'],  # 店名
            store_type,  # 门店类型
            store['ad'],  # 地址
            store['ph'],  # 电话
            ""  # 备注
        ]

        # 写入CSV并打印日志
        writer.writerow(row)
        print(row)
        return True
    except Exception as e:
        print(f"数据处理失败: {e}")
        return False


def main():
    # 初始化输出文件
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerow(RESULT_FIELDS)

    total_count = 0

    # 遍历所有字母a-z
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        url = API_TEMPLATE.format(letter)
        print(f"正在处理字母：{letter.upper()}")

        try:
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError:
            print(f"跳过无效字母：{letter.upper()}")
            continue
        except Exception as e:
            print(f"请求失败：{e}")
            continue

        # 处理获取到的数据
        with open(OUTPUT_PATH, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for city, districts in data.items():
                for district, stores in districts.items():
                    total_count += sum(
                        1 for store in stores
                        if process_store(writer, city, district, store)
                    )

        random_delay()

    print(f"爬取完成，共找到 {total_count} 家门店")


if __name__ == "__main__":
    main()