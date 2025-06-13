import os
import requests
import json
import csv
from requests.adapters import HTTPAdapter
from util.location_translator import get_en_province, get_en_city
from util.bs_sleep import sleep_with_random
import re


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
    "Referer": "https://www.hankooktire.com/cn-zh/find-a-store/find-a-store.html"  # Adjust if needed
}

# 初始载荷 (根据用户提供的信息)
INITIAL_PAYLOAD = {
    "siteCd": "CN-ZH",
    "query": "",
    "dealType2": "",
    "dealType1": "",
    "distance": "20",  # Search radius in km
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
        current_headers["User-Agent"] = random.choice(USER_AGENTS)  # Select a random User-Agent

        response = session.post(API_URL, headers=current_headers, json=payload,
                                timeout=30)  # Increased timeout slightly
        response.raise_for_status()  # Will raise an HTTPError for bad responses (4XX or 5XX)
        # 有些服务器即使返回JSON，Content-Type也可能是text/html，所以直接尝试json解析
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败 (Payload: {payload}): {e}")
    except json.JSONDecodeError as e:
        print(f"JSON解码失败 (Payload: {payload}): {e}. Response text: {response.text[:200]}")
    return None


def parse_address_components(address_str):
    """尝试从地址字符串中解析省、市、区"""
    address_str = address_str.strip()
    province_zh = ""
    city_zh = ""
    district_zh = ""

    # 常见直辖市列表
    municipalities = ["北京市", "上海市", "天津市", "重庆市"]
    municipalities_short = [m[:-1] for m in municipalities]  # 北京, 上海, 天津, 重庆

    for i, muni_short in enumerate(municipalities_short):
        if address_str.startswith(muni_short):
            province_zh = municipalities[i]
            city_zh = municipalities[i] # 直辖市的市名和省名相同
            remaining_after_muni = address_str[len(muni_short):].strip()
            if remaining_after_muni.startswith("市") and muni_short + "市" == municipalities[i]:
                remaining_after_muni = remaining_after_muni[1:].strip()
            district_match = re.search(r'([^\s]+?(?:区|县|市辖区|自治县))', remaining_after_muni)
            if district_match:
                district_zh = district_match.group(1).strip()
            return province_zh, city_zh, district_zh

    # 模式1: 省/自治区 + 市/盟/州 + 区/县/旗
    # (云南省)(丽江市)(古城区)
    # (内蒙古自治区)(乌兰察布市)(集宁区)
    match = re.match(r'([^省]+省|[^自治区]+自治区)?(?:\s*([^市]+市|[^盟]+盟|[^州]+州|[^地区]+地区))?(?:\s*([^区]+区|[^县]+县|[^市]+市|[^旗]+旗))?(.*)', address_str)
    if match:
        g1, g2, g3, _ = match.groups()

        if g1:
            province_zh = g1.strip()
        if g2:
            city_zh = g2.strip()
            # 去除市名称中可能包含的省份前缀
            if province_zh and city_zh.startswith(province_zh):
                city_zh = city_zh[len(province_zh):].strip()
            if province_zh and city_zh.startswith(province_zh.replace('省','').replace('自治区','')):
                 city_zh = city_zh[len(province_zh.replace('省','').replace('自治区','')):].strip()
            # 确保市名不以“省”结尾，除非它是省名本身（不太可能）
            if city_zh.endswith('省') and city_zh != province_zh:
                city_zh = city_zh[:-1] + '市'

        if g3:
            district_zh = g3.strip()
            # 如果区名是市名，清空区名
            if district_zh == city_zh:
                district_zh = ''
            # 如果区名包含市名，例如 “丽江市古城区”，则区应该是“古城区”
            if city_zh and district_zh.startswith(city_zh) and len(district_zh) > len(city_zh):
                district_zh = district_zh[len(city_zh):].strip()

        # 针对内蒙古的特殊处理
        if province_zh == '内蒙古自治区':
            if city_zh and '省' in city_zh and city_zh != province_zh:
                city_zh = city_zh.replace('省', '')
                if not city_zh.endswith('市') and not city_zh.endswith('盟') and not city_zh.endswith('州'):
                    city_zh += '市'
            if city_zh == '治区': # 来自用户数据的 “内蒙古自治区 治区”
                city_zh = ''
            # 如果区是“乌兰察布省 集宁区”，修正市和区
            if district_zh and '乌兰察布省' in district_zh:
                city_zh = '乌兰察布市'
                district_zh = district_zh.replace('乌兰察布省','').strip()
            if district_zh and '乌海省' in district_zh:
                city_zh = '乌海市'
                district_zh = district_zh.replace('乌海省','').strip()
                if district_zh == city_zh: district_zh = ''

        # 如果市名是省名（例如“云南省”出现在市字段），清空市或尝试修正
        if city_zh and (city_zh == province_zh or city_zh == province_zh.replace('省','').replace('自治区','')):
            # 这种情况通常意味着市信息未正确分离或缺失
            # 例如地址是 “云南省 古城区”，市应该是 “丽江市” (需要推断)
            # 暂时清空，依赖后续从店名或其他地方补充
            city_zh = ''

        # 清理市：确保市名不包含省名，例如 “云南省丽江市” -> “丽江市”
        if province_zh and city_zh and city_zh.startswith(province_zh.replace('省','').replace('自治区','')):
            temp_city = city_zh[len(province_zh.replace('省','').replace('自治区','')):].strip()
            if temp_city.endswith('市') or temp_city.endswith('州') or temp_city.endswith('盟'):
                city_zh = temp_city
        elif province_zh and city_zh and city_zh.startswith(province_zh):
             temp_city = city_zh[len(province_zh):].strip()
             if temp_city.endswith('市') or temp_city.endswith('州') or temp_city.endswith('盟'):
                city_zh = temp_city

        # 如果区是空的，但地址的剩余部分看起来像区
        if not district_zh and _ and _.strip():
            potential_district_match = re.match(r'([^\s]+?(?:区|县|市|旗|镇|乡|街道))', _.strip())
            if potential_district_match:
                district_zh = potential_district_match.group(1).strip()
                if district_zh == city_zh: district_zh = '' # 避免区和市一样

        return province_zh, city_zh, district_zh

    # 兜底：如果上面的复杂正则没有匹配，尝试简单的按顺序提取
    # 省/自治区
    prov_match = re.match(r'([^省]+省|[^自治区]+自治区)', address_str)
    if prov_match:
        province_zh = prov_match.group(1).strip()
        remaining_address = address_str[len(province_zh):].strip()

        # 市/盟/州
        city_match = re.match(r'([^市]+市|[^盟]+盟|[^州]+州|[^地区]+地区)', remaining_address)
        if city_match:
            city_zh = city_match.group(1).strip()
            remaining_address = remaining_address[len(city_zh):].strip()
            # 清理市名中的省份
            if province_zh and city_zh.startswith(province_zh.replace('省','').replace('自治区','')):
                 city_zh = city_zh[len(province_zh.replace('省','').replace('自治区','')):].strip()
            if province_zh and city_zh.startswith(province_zh):
                 city_zh = city_zh[len(province_zh):].strip()
            if province_zh == '内蒙古自治区' and city_zh == '治区': city_zh = ''

        # 区/县/市/旗
        dist_match = re.match(r'([^区]+区|[^县]+县|[^市]+市|[^旗]+旗)', remaining_address)
        if dist_match:
            district_zh = dist_match.group(1).strip()
            if district_zh == city_zh: district_zh = ''

    # 如果省是“内蒙古自”，修正为“内蒙古自治区”
    if province_zh == '内蒙古自':
        province_zh = '内蒙古自治区'
    if province_zh == '云南省' and city_zh == '云南省': # 特殊处理云南省市重复
        city_zh = ''

    # 最后再次确保市名不含省名
    if province_zh and city_zh and city_zh.startswith(province_zh.replace('省','').replace('自治区','')):
        city_zh = city_zh[len(province_zh.replace('省','').replace('自治区','')):].strip()
    if province_zh and city_zh and city_zh.startswith(province_zh):
        city_zh = city_zh[len(province_zh):].strip()

    # 如果市名为空，但区名看起来像一个市（例如“保山市腾冲县”中的“保山市”）
    if not city_zh and district_zh and '市' in district_zh and not district_zh.endswith('市'):
        city_candidate_in_district = re.match(r'([^市]+市)', district_zh)
        if city_candidate_in_district:
            city_zh = city_candidate_in_district.group(1)
            district_zh = district_zh[len(city_zh):].strip()

    return province_zh, city_zh, district_zh

def process_store_item(item):
    """处理单个门店信息"""
    address_full = item.get('ADDR', '').strip()
    store_name = item.get('DEAL_NM', '').strip()

    province_zh, city_zh, district_zh = parse_address_components(address_full)

    # 如果从地址解析不出市，尝试从店名中提取
    if not city_zh and store_name:
        # 尝试从店名中匹配常见的市级行政单位
        # 例如店名 “保山峰旺轮胎经营部” -> city_zh = “保山市”
        # 这个列表可以根据实际情况扩充
        known_cities_prefixes = ['昆明', '曲靖', '玉溪', '保山', '昭通', '丽江', '普洱', '临沧',
                               '楚雄', '红河', '文山', '西双版纳', '大理', '德宏', '怒江', '迪庆'] 
        # 加上后缀 “市”, “州”, “地区”, “盟”
        city_patterns = [prefix + suffix for prefix in known_cities_prefixes 
                         for suffix in ['市', '州', '地区', '盟']]
        
        for city_pattern in city_patterns:
            if city_pattern in store_name:
                # 检查是否与已解析的省份冲突或重复
                if province_zh and city_pattern.startswith(province_zh.replace('省','').replace('自治区','')):
                    # 如果店名中的市是 “云南省昆明市”，而省是“云南省”，则市取“昆明市”
                    potential_city = city_pattern[len(province_zh.replace('省','').replace('自治区','')):].strip()
                    if potential_city:
                        city_zh = potential_city
                        break
                elif not province_zh or not city_pattern.startswith(province_zh): 
                    city_zh = city_pattern
                    break
        # 如果店名直接包含 “XX市”，并且前面没有省份信息冲突
        city_match_in_name = re.search(r'([^省自治区]+市|[^省自治区]+州|[^省自治区]+盟)', store_name)
        if not city_zh and city_match_in_name:
            potential_city_from_name = city_match_in_name.group(1)
            # 避免将省名误认为市名，例如店名包含“云南省代理”
            if not province_zh or not potential_city_from_name.startswith(province_zh.replace('省','').replace('自治区','')):
                 city_zh = potential_city_from_name

    # 如果省份为空，但市不为空，尝试从市推断省 (例如市是“昆明市”，省是“云南省”)
    if not province_zh and city_zh:
        # 这是一个简化的推断，实际需要更完整的映射表
        if city_zh in ['昆明市', '曲靖市', '玉溪市', '保山市', '昭通市', '丽江市', '普洱市', '临沧市']:
            province_zh = '云南省'
        elif city_zh in ['楚雄州', '红河州', '文山州', '西双版纳州', '大理州', '德宏州', '怒江州', '迪庆州']:
            province_zh = '云南省'
        # 可以为其他省份添加类似逻辑

    # 再次确保市名不含省名
    if province_zh and city_zh and city_zh.startswith(province_zh.replace('省','').replace('自治区','')):
        city_zh = city_zh[len(province_zh.replace('省','').replace('自治区','')):].strip()
    if province_zh and city_zh and city_zh.startswith(province_zh):
        city_zh = city_zh[len(province_zh):].strip()

    # 针对用户提供的 “云南省大理市保山市腾冲县山源社区” 这种区信息混乱的情况
    # 如果区信息包含了另一个市名，且该市名与当前市名不符，则优先使用地址中的区信息，并尝试修正市
    if district_zh and city_zh:
        if '保山市' in district_zh and city_zh == '大理市':
            # 这表示原始数据可能将属于保山市的区错误地归类到大理市下
            # 决定是修正市为“保山市”，还是清空区，或标记为特殊情况
            # 暂时以地址中的区信息为准，如果区包含明确的市，且与当前市不同，考虑修正市
            if '腾冲县' in district_zh or '隆阳区' in district_zh: # 假设这些是保山的区县
                city_zh = '保山市' # 将市修正为保山市
                # 从district_zh中移除市名
                district_zh = district_zh.replace('保山市','').strip()
        elif '金色家园小区' == district_zh and city_zh == '丽江市': # “金色家园小区” 不是一个行政区划
            district_zh = '' # 清空不规范的区
        elif '昌宁县宝丰社区' == district_zh and city_zh == '保山市':
            district_zh = '昌宁县' # 取更规范的区县

    return {
        "品牌": "韩泰轮胎",
        "省": province_zh,
        "Province": get_en_province(province_zh) if province_zh else "",
        "市": city_zh,
        "City": get_en_city(city_zh) if city_zh else "",
        "区": district_zh,
        "店名": store_name,
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
    total_pages = 1  # Initialize with 1, will be updated after first fetch
    all_store_data = []

    with create_session() as session:
        while page <= total_pages:
            print(f"正在爬取第 {page} 页 / {total_pages if total_pages > 1 else '?'}...")
            current_payload['page'] = str(page)

            response_data = fetch_page_data(session, current_payload)
            # sleep(random.uniform(1, 3)) # Respectful delay - replaced with sleep_with_random
            sleep_with_random(interval=2, rand_max=3)  # Sleep for 2 to 5 seconds

            if not response_data or response_data.get('resultCode') != '0000':
                print(f"获取第 {page} 页数据失败或API返回错误。")
                # Decide if to break or retry, for now, break
                if response_data:
                    print(f"API Message: {response_data.get('message')}")
                break

            data_section = response_data.get('data', {})
            result_list = data_section.get('ResultList', [])

            if page == 1:  # After first successful fetch, determine total pages
                pg_info = data_section.get('pg', {})
                end_page_str = pg_info.get('endPage', '1')  # 'endPage': '349'
                if isinstance(end_page_str, str) and end_page_str.isdigit():
                    total_pages = int(end_page_str)
                elif isinstance(end_page_str, int):
                    total_pages = end_page_str
                else:  # Fallback if endPage is not easily parsed
                    result_count = data_section.get('ResultCount', 0)
                    # Assuming API returns a consistent number of items per page, e.g., 30 from leRownum or len(result_list)
                    items_per_page = len(result_list) if result_list else 30  # Default if list is empty on first page
                    if items_per_page > 0:
                        total_pages = (result_count + items_per_page - 1) // items_per_page
                    else:
                        total_pages = 1  # Cannot determine, assume 1 page
                print(f"总页数确定为: {total_pages}")
                if not result_list and total_pages > 1 and page == 1:  # No results on first page but more pages indicated
                    print("警告：第一页没有结果，但API指示有多页。可能搜索参数需要调整。")

            if not result_list and page > 1:
                print(f"第 {page} 页没有门店数据，可能已到达末尾或数据中断。")
                # break # Or continue if you suspect sparse data

            for item in result_list:
                processed_item = process_store_item(item)
                print(json.dumps(processed_item, ensure_ascii=False))
                all_store_data.append(processed_item)

            print(f"第 {page} 页处理完成，获取到 {len(result_list)} 条门店数据。累计: {len(all_store_data)}")

            if page >= total_pages:  # Break if we've reached the determined total_pages
                break
            page += 1
            if not result_list and page <= total_pages:  # If current page had no results but not last page
                print(f"第 {page - 1} 页无数据，但未到总页数，继续尝试下一页。")

    if all_store_data:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(all_store_data)
        print(f"\n数据采集完成，共 {len(all_store_data)} 条门店信息已保存到: {OUTPUT_PATH}")
    else:
        print("\n未能采集到任何门店数据。")


if __name__ == "__main__":
    import random  # ensure random is imported if not already at top level for sleep

    main()