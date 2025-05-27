import os
import csv
import time
import json
import requests # 引入 requests 库

# 定义输出字段
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]

# 设置输出路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/landrover.csv")

# 门店查询API地址
API_URL = "https://dealer.landrover.com.cn/index.php"


def fetch_dealer_data():
    """从API获取经销商数据"""
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    params = {
        "s": "/LRDealer/api/getDealerList",
        "is_extend": "21",
        "is_lack": "1"
    }
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()  # 如果请求失败则引发HTTPError
        data = response.json()
        if data.get("is_success") and "data" in data:
            return data["data"]
        else:
            print(f"API返回错误: {data.get('errmsg', '未知错误')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"请求API失败: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"解析JSON失败: {e}")
        return []

def main():
    print("开始爬取路虎门店信息...")

    # 创建输出目录和CSV文件
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    dealer_list = fetch_dealer_data()

    if not dealer_list:
        print("未能获取经销商数据，程序退出。")
        return

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()

        total_stores = 0
        for dealer in dealer_list:
            # 根据API返回的数据结构调整字段映射
            # 假设API返回的字段名与截图中的一致，如 province_name, city_name, dealer_name, address, telephone
            # 如果API返回的字段名不同，需要在此处进行相应调整
            store_info = {
                "省": dealer.get("province_name", ""),
                "Province": dealer.get("province_name", ""), # 通常与“省”相同
                "市区辅助": dealer.get("city_name", ""),
                "City": dealer.get("city_name", ""), # 通常与“市区辅助”相同
                "区": "", # API数据中似乎没有区的概念，留空或根据实际情况处理
                "店名": dealer.get("dealer_name", ""),
                "类型": "", # API数据中似乎没有类型信息，留空或根据实际情况处理
                "地址": dealer.get("address", ""), # 需要确认API返回的地址字段名
                "电话": dealer.get("telephone", ""), # 需要确认API返回的电话字段名
                "备注": ""
            }
            # 确保从API获取的字段名是正确的，例如：
            # 'province_name', 'city_name', 'dealer_name', 'address', 'tel' (或 'phone')
            # 根据截图中的JSON响应，字段名可能是：
            # province_name, city_name, dealer_name, dealer_addr (地址), dealer_tel (电话)
            # 请根据实际API返回的JSON结构调整下面的字段获取
            # store_info = {
            #     "省": dealer.get("province_name", ""),
            #     "Province": dealer.get("province_name", ""),
            #     "市区辅助": dealer.get("city_name", ""),
            #     "City": dealer.get("city_name", ""),
            #     "区": "", 
            #     "店名": dealer.get("dealer_name", ""),
            #     "类型": "", 
            #     "地址": dealer.get("dealer_addr", ""), # 假设地址字段是 dealer_addr
            #     "电话": dealer.get("dealer_tel", ""), # 假设电话字段是 dealer_tel
            #     "备注": ""
            # }
            writer.writerow(store_info)
            total_stores += 1

        print(f"\n爬取完成，共获取 {total_stores} 个门店信息")
        print(f"数据已保存到: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
