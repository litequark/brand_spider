import os
import requests
import json
import csv
import time
# from time import sleep # Replaced with bs_sleep
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from util.location_translator import get_en_province, get_en_city
from util.bs_sleep import sleep_with_random # Import sleep_with_random
import random # Import random for UA selection
import re # For parsing endPage

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "hankooktire.csv")

# CSV头定义
CSV_HEADER = ["品牌", "省", "Province", "市", "City", "区", "店名", 
              "类型1", "类型2", "地址", "电话", "纬度", "经度", "邮编", "备注"]

# API配置
API_URL = "https://www.hankooktire.com/wsvc/api/find-store.getStoreList.do"

# User-Agent Pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

# 请求头配置 (User-Agent will be set dynamically)
HEADERS = {
    # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36", # Removed static UA
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.hankooktire.com",
    "Referer": "https://www.hankooktire.com/cn-zh/find-a-store/find-a-store.html" # Adjust if needed
}

# 初始载荷 (根据用户提供的信息)
INITIAL_PAYLOAD = {
    "siteCd": "CN-ZH",
    "query": "",
    "dealType2": "",
    "dealType1": "",
    "distance": "20", # Search radius in km
    "isLocBased": "false",
    "lat": "31.30073",
    "lng": "121.4832",
    "cntlCd": "",
    "page": "1"
}


def create_session():
    """创建带连接池的会话"""
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=3
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_page_data(session, payload):
    """获取单页数据"""
    try:
        # API期望的Content-Type是x-www-form-urlencoded，即使我们发送JSON，它内部似乎做了转换
        # 或者我们可以直接发送form-data格式
        # response = session.post(API_URL, headers=HEADERS, json=payload, timeout=20)
        # 尝试发送 data=payload 形式，因为Content-Type通常是 application/x-www-form-urlencoded for .do
        # 观察到用户提供的curl命令通常将json作为data参数的值，而不是json参数
        # 实际测试发现，直接用json=payload可以工作，但服务器返回的Content-Type是text/html，内容是JSON
        # 确保请求头中的Content-Type是 application/json
        
        current_headers = HEADERS.copy()
        current_headers["User-Agent"] = random.choice(USER_AGENTS) # Select a random User-Agent
        
        response = session.post(API_URL, headers=current_headers, json=payload, timeout=30) # Increased timeout slightly
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        # 有些服务器即使返回JSON，Content-Type也可能是text/html，所以直接尝试json解析
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败 (Payload: {payload}): {e}")
    except json.JSONDecodeError as e:
        print(f"JSON解码失败 (Payload: {payload}): {e}. Response text: {response.text[:200]}")
    return None

def parse_address_components(address_str):
    """尝试从地址字符串中解析省和市"""
    # 示例地址: "上海  上海万荣路1066-1070号 "
    # "上海  上海奉贤运河北路301号 "
    # "江苏省 苏州市 张家港市杨舍镇东方明珠城1幢101室"
    # 这是一个非常基础的解析，可能需要根据实际数据多样性进行调整
    parts = [p.strip() for p in address_str.split(' ') if p.strip()]
    province_zh = ""
    city_zh = ""
    
    if not parts:
        return province_zh, city_zh

    # 尝试匹配模式如 "省份 城市 ..." 或 "直辖市 直辖市 ..."
    if len(parts) >= 2:
        # 检查第一个部分是否是已知的省份或直辖市
        # 对于 "上海 上海..." 的情况
        if parts[0] == parts[1] and (parts[0].endswith('市')):
            province_zh = parts[0]
            city_zh = parts[0]
        elif parts[0].endswith('省'):
            province_zh = parts[0]
            city_zh = parts[1] if not parts[1].endswith('区') and not parts[1].endswith('县') else parts[0] # 粗略判断
        elif parts[0].endswith('市'): #可能是直辖市或地级市
            province_zh = parts[0]
            city_zh = parts[0]
            if len(parts) > 1 and parts[1].endswith('市') and parts[0] != parts[1]: # 如 "苏州市 常熟市..."
                 city_zh = parts[1]
        # 如果第一部分不是明显的省/市，但第二部分是市
        elif len(parts) > 1 and (parts[1].endswith('市') or parts[1].endswith('地区') or parts[1].endswith('自治州')):
            province_zh = parts[0] # 假设第一部分是省
            city_zh = parts[1]
        else:
            # 默认规则：如果地址包含'省'，则'省'之前的是省，之后的是市
            if '省' in address_str:
                prov_idx = address_str.find('省')
                province_zh = address_str[:prov_idx+1].strip()
                remaining_after_prov = address_str[prov_idx+1:].strip()
                if '市' in remaining_after_prov:
                    city_idx = remaining_after_prov.find('市')
                    city_zh = remaining_after_prov[:city_idx+1].strip()
                elif '地区' in remaining_after_prov:
                    city_idx = remaining_after_prov.find('地区')
                    city_zh = remaining_after_prov[:city_idx+2].strip()
                elif '自治州' in remaining_after_prov:
                    city_idx = remaining_after_prov.find('自治州')
                    city_zh = remaining_after_prov[:city_idx+3].strip()
            elif '市' in address_str: # 对于没有'省'但有'市'的，如北京、上海
                city_idx = address_str.find('市')
                # 尝试将第一个'市'作为省和市（适用于直辖市）
                potential_city = address_str[:city_idx+1].strip()
                # 移除空格后判断
                if ' ' not in potential_city:
                    province_zh = potential_city
                    city_zh = potential_city
                else: # 如果有空格，如 "上海 上海市..."，取第一个非空部分
                    province_zh = parts[0]
                    city_zh = parts[0]

    elif len(parts) == 1 and parts[0].endswith('市'): # 单独一个市，如 "北京市"
        province_zh = parts[0]
        city_zh = parts[0]

    # 清理常见的后缀，如 “市辖区” 等，这部分比较复杂，暂时简化
    if city_zh.endswith('市辖区'):
        city_zh = province_zh # 通常市辖区属于该省的省会或主要城市

    return province_zh, city_zh

def process_store_item(item):
    """处理单个门店信息"""
    address_full = item.get('ADDR', '').strip()
    province_zh, city_zh = parse_address_components(address_full)

    return {
        "品牌": "韩泰轮胎",
        "省": province_zh,
        "Province": get_en_province(province_zh) if province_zh else "",
        "市": city_zh,
        "City": get_en_city(city_zh) if city_zh else "",
        "区": "", # API不直接提供区信息，可从地址中进一步解析，此处留空
        "店名": item.get('DEAL_NM', ''),
        "类型1": item.get('DEAL_TYPE1', ''),
        "类型2": item.get('DEAL_TYPE2', ''),
        "地址": address_full,
        "电话": item.get('TEL_OTHER_NO') or item.get('TEL_1_NO') or item.get('TEL_2_NO') or item.get('TEL_3_NO') or "",
        "备注": ""
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    current_payload = INITIAL_PAYLOAD.copy()
    page = 1
    total_pages = 1 # Initialize with 1, will be updated after first fetch
    all_store_data = []

    with create_session() as session:
        while page <= total_pages:
            print(f"正在爬取第 {page} 页 / {total_pages if total_pages > 1 else '?'}...")
            current_payload['page'] = str(page)
            
            response_data = fetch_page_data(session, current_payload)
            # sleep(random.uniform(1, 3)) # Respectful delay - replaced with sleep_with_random
            sleep_with_random(interval=2, rand_max=3) # Sleep for 2 to 5 seconds

            if not response_data or response_data.get('resultCode') != '0000':
                print(f"获取第 {page} 页数据失败或API返回错误。")
                # Decide if to break or retry, for now, break
                if response_data:
                    print(f"API Message: {response_data.get('message')}")
                break

            data_section = response_data.get('data', {})
            result_list = data_section.get('ResultList', [])
            
            if page == 1: # After first successful fetch, determine total pages
                pg_info = data_section.get('pg', {})
                end_page_str = pg_info.get('endPage', '1') # 'endPage': '349'
                if isinstance(end_page_str, str) and end_page_str.isdigit():
                    total_pages = int(end_page_str)
                elif isinstance(end_page_str, int):
                    total_pages = end_page_str
                else: # Fallback if endPage is not easily parsed
                    result_count = data_section.get('ResultCount', 0)
                    # Assuming API returns a consistent number of items per page, e.g., 30 from leRownum or len(result_list)
                    items_per_page = len(result_list) if result_list else 30 # Default if list is empty on first page
                    if items_per_page > 0:
                        total_pages = (result_count + items_per_page - 1) // items_per_page
                    else:
                        total_pages = 1 # Cannot determine, assume 1 page
                print(f"总页数确定为: {total_pages}")
                if not result_list and total_pages > 1 and page ==1 : # No results on first page but more pages indicated
                    print("警告：第一页没有结果，但API指示有多页。可能搜索参数需要调整。")
            
            if not result_list and page > 1:
                 print(f"第 {page} 页没有门店数据，可能已到达末尾或数据中断。")
                 # break # Or continue if you suspect sparse data

            for item in result_list:
                processed_item = process_store_item(item)
                print(json.dumps(processed_item, ensure_ascii=False))
                all_store_data.append(processed_item)
            
            print(f"第 {page} 页处理完成，获取到 {len(result_list)} 条门店数据。累计: {len(all_store_data)}")

            if page >= total_pages: # Break if we've reached the determined total_pages
                break
            page += 1
            if not result_list and page <= total_pages: # If current page had no results but not last page
                print(f"第 {page-1} 页无数据，但未到总页数，继续尝试下一页。")

    if all_store_data:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(all_store_data)
        print(f"\n数据采集完成，共 {len(all_store_data)} 条门店信息已保存到: {OUTPUT_PATH}")
    else:
        print("\n未能采集到任何门店数据。")

if __name__ == "__main__":
    import random # ensure random is imported if not already at top level for sleep
    main()