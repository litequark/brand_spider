import requests
import csv
import os
import time
import random
from time import sleep

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "类型2", "地址", "电话", "备注"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/volvo.csv")
def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.random() * rand_max
    sleep(interval + rand)

def main():
    url = "https://campaigns.volvocars.com.cn/campaign/statistic/api/web/index.php/v1/apiservice/dealers/volvo-rdm-new.php"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            print(f"API返回错误: {data.get('message')}")
            return

        dealers_data = data["data"]["city"]

        # 确保输出目录存在
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        total_count = 0

        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(RESULT_FIELDS)

            for city in dealers_data.values():
                for dealer in city:
                    # 解析数据
                    province = dealer.get("Province", "")
                    city_name = dealer.get("City", "")
                    dealer_name = dealer.get("DealerName", "")
                    address = dealer.get("Address", "")
                    phone = dealer.get("SaleTel", "")
                    categories = dealer.get("Category", [])

                    # 构造CSV行
                    row = [
                        province,  # 省
                        "",  # Province
                        city_name,  # 市
                        "" # City
                        "",  # 区（留空）
                        dealer_name,  # 店名
                        categories[0] if len(categories) > 0 else "",  # 类型
                        categories[1] if len(categories) > 1 else "",  # 类型2
                        address,  # 地址
                        phone,  # 电话
                        ""  # 备注（留空）
                    ]

                    # 打印记录
                    print(f"| {' | '.join([str(field) for field in row])} |")
                    sleep_with_random(1,1)

                    # 写入CSV
                    writer.writerow(row)
                    total_count += 1

        print(f"\n总共找到 {total_count} 家店铺")

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {str(e)}")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")



main()