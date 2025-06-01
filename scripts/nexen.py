import requests
import time
import csv
import os
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from util.location_translator import get_en_city, get_en_province

# 基础参数
INTERVAL = 1  # 网络请求间隔（秒）
RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]

# 文件路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/nexen.csv")

# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# 基础URL
BASE_URL = "https://www.nexentire.com/cn/utils/"

def fetch_data(payload, api_name):
    """发送POST请求获取数据"""
    url = BASE_URL + api_name
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

def parse_shop_list(html, addr1, addr2, addr3):
    """解析门店列表HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    shops = []
    
    # 查找门店行
    rows = soup.select('table.branch-table tbody tr')
    
    for row in rows:
        # 店名可能在第一个td或隐藏的strong标签中
        if name_td := row.select_one('td:first-child'):
            shop_name = name_td.text.strip()
        else:
            shop_name = row.select_one('strong.txt2').text.strip() if row.select_one('strong.txt2') else ""
        
        # 地址
        address = row.select_one('span.address').text.strip() if row.select_one('span.address') else ""
        
        # 电话 - 优先从隐藏的电话单元格获取
        if phone_td := row.select_one('td.hidden-xs.hidden-sm:nth-child(3)'):
            phone = phone_td.text.strip()
        elif tel_link := row.select_one('a[href^="tel:"]'):
            phone = tel_link['href'].replace("tel:", "")
        else:
            phone = ""
        
        shop_data = {
            "省": addr1, "Province": get_en_province(addr1),
            "市": addr2, "City": get_en_city(addr2),
            "区": addr3, 
            "店名": shop_name.replace('\\n', ' ').replace('\n', ' '),
            "类型": "", 
            "地址": address.replace('\\n', ' ').replace('\n', ' '), 
            "电话": phone.replace('\\n', ' ').replace('\n', ' '),
            "备注": ""
        }
        shops.append(shop_data)
        print(shop_data)  # 控制台输出门店信息
    
    return shops

def save_to_csv(shops):
    """保存数据到CSV文件"""
    
    with open(OUTPUT_PATH, 'a', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=RESULT_FIELDS, 
                              quoting=csv.QUOTE_ALL)
        for shop in shops:
            writer.writerow(shop)

def main():
    # 清空csv文件
    with open(file=OUTPUT_PATH, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f=f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
    # 1. 获取省份列表(addr1)
    payload1 = 'target=addr1'
    response = fetch_data(payload1, "get_shop_attr.php")
    if not response:
        print("获取省份列表失败")
        return
    
    addr1_list = response.json()
    print(f"获取到 {len(addr1_list)} 个省份")
    
    total_shops = 0
    
    # 2. 遍历每个省份
    for addr1 in addr1_list:
        time.sleep(INTERVAL)
        print(f"\n处理省份: {addr1}")
        
        # 3. 获取该省份的城市列表(addr2)
        payload2 = urlencode({'addr1': addr1, 'target': 'addr2'})
        response = fetch_data(payload2, "get_shop_attr.php")
        if not response:
            print(f"获取城市列表失败 (省份: {addr1})")
            continue
            
        addr2_list = response.json()
        
        # 4. 遍历每个城市
        for addr2 in addr2_list:
            time.sleep(INTERVAL)
            print(f"处理城市: {addr1}/{addr2}")
            
            # 5. 获取该城市的区域列表(addr3)
            payload3 = urlencode({'addr1': addr1, 'addr2': addr2, 'target': 'addr3'})
            response = fetch_data(payload3, "get_shop_attr.php")
            if not response:
                print(f"获取区域列表失败 (城市: {addr2})")
                continue
                
            addr3_list = response.json()
            
            # 6. 遍历每个区域
            for addr3 in addr3_list:
                time.sleep(INTERVAL)
                print(f"处理区域: {addr1}/{addr2}/{addr3}")
                
                # 7. 获取该区域的门店列表
                payload4 = urlencode({
                    'addr1': addr1,
                    'addr2': addr2,
                    'addr3': addr3,
                    'offset': 0
                })
                response = fetch_data(payload4, "get_shop_list.php")
                if not response or not response.text:
                    print(f"获取门店列表失败 (区域: {addr3})")
                    continue
                
                # 8. 解析门店数据
                shops = parse_shop_list(response.text, addr1, addr2, addr3)
                total_shops += len(shops)
                
                # 9. 保存到CSV
                save_to_csv(shops)
    
    # 10. 输出结果
    print(f"\n爬取完成! 共找到 {total_shops} 家门店")
    print(f"数据已保存至: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()