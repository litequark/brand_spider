RESULT_FIELDS = ["品牌","省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]
import requests
import csv
import time
import random
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入父目录（project）
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/xiaopeng.csv")
url = "https://www.xiaopeng.com/api/store/queryAll"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "X-CSRF-Token": "0fosdprS-MDfYAwz9zaGCdKIxps5yyEtc-Bk",  # 需动态获取
    # 上述token有可能过期，需要动态获取
    "Cookie": "acw_tc=0a472f8d17477387207782546e0083f74bf866295422b64cd27d05c4bd7e35; csrfToken=H4B37xD-t6pzhBK0WNJ6X-em;...",  # 需完整Cookie
    # ？？？这也能跑？？？？？？？？？
    "Referer": "https://www.xiaopeng.com/pengmetta.html?forcePlat=h5"
}
count =0
response = requests.post(url, headers=headers)
data_list = []
time.sleep(random.uniform(1, 2))
for store in response.json().get("data", []):
    row = {
        "品牌": "小鹏汽车",  # 固定值
        "省": store.get("provinceName", ""),
        "Province": "",
        "市区辅助": f"{store.get('cityName', '')} {store.get('districtName', '')}",
        "City/Area": "",
        "区": store.get("districtName", "") or "",
        "店名": store.get("storeName", ""),
        "类型": store.get("storeTypeName", ""),
        "地址": store.get("address", ""),
        "电话": store.get("mobile", "").replace(" ", ""),
        "备注": ""
    }
    data_list.append([row[field] for field in RESULT_FIELDS])
    count += 1
    print([row[field] for field in RESULT_FIELDS])
with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
 writer = csv.writer(f)
 writer.writerow(RESULT_FIELDS)  # 写入表头
 writer.writerows(data_list)

print(f"数据已成功保存至：{OUTPUT_PATH}")
print(f"一共爬取{count}家店铺")