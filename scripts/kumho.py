import os
import random
import time
import csv
import json
import urllib.request
from bs4 import BeautifulSoup
import requests

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 假设 BaseScraper 定义在其他地方或是一个您已有的基类
# from .base_scraper import BaseScraper # 或者其他正确的导入路径
class BaseScraper:  # 占位符定义，请替换为您实际的 BaseScraper
    def __init__(self, brand_name):
        self.brand_name = brand_name
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.stores_data = []

    def setup_driver(self):
        pass  # 如果不需要 Selenium，可以为空

    def quit_driver(self):
        pass  # 如果不需要 Selenium，可以为空


# 配置常量
RESULT_FIELDS = ["品牌", "店名", "省", "市区辅助", "区", "地址", "电话",
                 "类型", "备注"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output", "kumho_stores.csv")  # 修正了CSV文件名


class KumhoScraper(BaseScraper):
    def __init__(self, brand_name="锦湖轮胎"):
        super().__init__(brand_name)
        self.base_url = "http://www.kumhotire.com.cn"
        self.api_url = "http://www.kumhotire.com.cn/cn/global/tire/agnc/list.do"
        self.session = requests.Session()
        self.csrf_token = None
        self.csrf_header_name = None
        # self.output_file = os.path.join(self.output_dir, f"{self.brand_name}_stores.json") # 改为CSV输出
        self.driver = None  # 初始化 driver 属性

    def get_csrf_token_from_page(self):
        try:
            # 初始页面获取，也用于获取省份列表
            list_do_url = self.base_url + "/cn/global/tire/agnc/list.do"
            print(f"正在从 {list_do_url} 获取 CSRF token 和省份列表...")
            # 添加 verify=False 来禁用 SSL 验证
            response = self.session.get(list_do_url, timeout=20, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            token_tag = soup.find('meta', {'name': '_csrf'})
            header_name_tag = soup.find('meta', {'name': '_csrf_header'})

            if token_tag and 'content' in token_tag.attrs and \
                    header_name_tag and 'content' in header_name_tag.attrs:
                self.csrf_token = token_tag['content']
                self.csrf_header_name = header_name_tag['content']
                print(f"成功获取 CSRF Token: {self.csrf_token}, Header: {self.csrf_header_name}")
                return soup  # 返回 soup 对象以便 get_provinces 使用
            else:
                print("错误：未能从页面中找到 CSRF token 或 header name 的 meta 标签。")
                if not token_tag:
                    print("未找到 meta name='_csrf'")
                if not header_name_tag:
                    print("未找到 meta name='_csrf_header'")
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取 CSRF token 页面时发生错误: {e}")
            return None

    def parse_store_info(self, store_data, province_name):
        # 确保 self, store_data, province_name 在这里是可访问的
        print(f"原始API门店数据 (store_data): {store_data}")

        store_name = store_data.get('AGNC_NM', '').strip()
        address = store_data.get('ADDR', '').strip()  # 修正: ADDR (如果API直接提供完整地址)
        # 如果地址分为 addr1 和 addr2, 且API确实返回这些字段，则使用之前的逻辑：
        # addr1 = store_data.get('ADDR1', '') # 假设API用大写
        # addr2 = store_data.get('ADDR2', '') # 假设API用大写
        # if addr1 or addr2:
        #     address = f"{addr1} {addr2}".strip()

        # city_from_api = store_data.get('CITY', province_name) # API返回 CITY，如果CITY为空则用province_name
        # 如果 RESULT_FIELDS 中的 city_name 期望的是API返回的市名，则用 city_from_api
        # 如果 RESULT_FIELDS 中的 city_name 期望的是省名（如当前CSV截图），则保持 province_name
        # 假设我们用API返回的市名，如果它存在的话
        city_name_for_csv = store_data.get('CITY', province_name)
        # 如果API也可能返回 cityNm，可以这样: city_name_for_csv = store_data.get('CITY', store_data.get('cityNm', province_name))

        # 对于 district_name, phone_number, store_type, 需要确认API是否返回以及确切的键名
        # 假设API可能返回 SIGUNGU_NM (或其他大写形式) 作为区县
        district = store_data.get('SIGUNGU_NM', store_data.get('boroughNm', ''))  # 尝试大写，再尝试小写
        phone_number = store_data.get('TEL_NO', '')  # 假设API用大写 TEL_NO
        store_type = store_data.get('AGNC_GB_NM', '')  # 假设API用大写 AGNC_GB_NM

        longitude = store_data.get('LNG', '')  # 修正: LNG
        latitude = store_data.get('LAT', '')  # 修正: LAT

        parsed_info = {
            '品牌': self.brand_name,
            '店名': store_name,
            '省': province_name,
            '市区辅助': '',  # 使用从API获取或回退的市名
            '区': district,
            '地址': address,
            '电话': phone_number,
            '类型': store_type,
            '备注': ''
        }
        print(f"解析后的门店信息 (parsed_info): {parsed_info}")
        return parsed_info

    def parse_store_data(self, json_data, province_name):
        new_stores_found_in_this_parse = []
        try:
            store_list_from_api = json_data.get("agncList", [])
            print(f"API为 {province_name} 返回 {len(store_list_from_api)} 个门店记录准备解析...")

            for store_item_json in store_list_from_api:
                print(f"原始门店数据: {store_item_json}")  # <--- 在这里添加打印语句
                store_info = self.parse_store_info(store_item_json, province_name)
                if store_info:
                    new_stores_found_in_this_parse.append(store_info)

            print(f"本次从 {province_name} 的API响应中解析到 {len(new_stores_found_in_this_parse)} 个门店。")
        except Exception as e:
            print(f"解析 {province_name} 的API门店数据时出错: {type(e).__name__} - {e}")
        return new_stores_found_in_this_parse

    def search_stores_by_province(self, province_code, province_name):
        if not self.csrf_token or not self.csrf_header_name:
            print("错误：CSRF token 未获取。")
            return []

        all_stores_for_province = []  # 当前省份的所有门店
        # 移除 existing_store_names_for_province = set()
        current_page_num = 0
        page_size = 5

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            self.csrf_header_name: self.csrf_token,
            'Referer': self.base_url
        }

        while True:
            payload = {
                'currentPage': 0,
                'pageNum': current_page_num,
                'langCd': 'LN000020',
                'isoCd': 'cn',
                'ajaxType': 'Y',
                'searchGubun': 'Y' if current_page_num == 0 else 'N',
                'lat': '',
                'lon': '',
                'states': province_code,
            }
            print(
                f"正在请求省份 {province_name} 的门店数据，pageNum: {current_page_num}, searchGubun: {payload['searchGubun']}")
            try:
                # 添加 verify=False 来禁用 SSL 验证
                response = self.session.post(self.api_url, headers=headers, data=payload, timeout=50, verify=False)
                response.raise_for_status()
                data = response.json()

                stores_on_page = data.get('agncList', [])
                if not stores_on_page:
                    print(f"省份 {province_name} 在 pageNum {current_page_num} 没有更多门店数据了。")
                    break

                # 不再传递 existing_store_names_for_province
                parsed_stores = self.parse_store_data(data, province_name)
                all_stores_for_province.extend(parsed_stores)
                print(f"已获取 {len(parsed_stores)} 家门店，当前省份总计 {len(all_stores_for_province)} 家。")

                total_count = data.get('totalCount', 0)
                # total_count 是该省份的总数，所以用 all_stores_for_province 的长度比较
                if len(all_stores_for_province) >= total_count:
                    print(f"已获取省份 {province_name} 的所有 {total_count} 家门店。")
                    break

                current_page_num += page_size
                time.sleep(random.uniform(1, 3))

            except requests.exceptions.RequestException as e:
                print(f"请求省份 {province_name} (pageNum: {current_page_num}) 门店数据时发生错误: {e}")
                break
            except json.JSONDecodeError:
                print(
                    f"解析省份 {province_name} (pageNum: {current_page_num}) 门店数据时发生JSON解码错误。响应内容: {response.text}")
                break
        return all_stores_for_province

    def get_provinces(self, soup):
        """从已获取的页面 BeautifulSoup 对象中解析省份列表"""
        provinces = []
        if not soup:
            print("错误：未提供页面内容 (soup) 以解析省份列表。")
            return provinces
        try:
            province_select_tag = soup.find('select', {'name': 'states'})
            if province_select_tag:
                for option in province_select_tag.find_all('option'):
                    value = option.get('value')
                    text = option.text.strip()
                    if value and value != "":  # 确保 value 有效
                        provinces.append({'value': value, 'text': text})
                print(f"成功解析到 {len(provinces)} 个省份。")
            else:
                print("错误：未能在页面中找到省份选择框 (select name='states')。")
        except Exception as e:
            print(f"解析省份列表时发生错误: {e}")
        return provinces

    def scrape(self):
        self.stores_data = []  # 每次抓取都重新初始化

        # 首先获取 CSRF token 和初始页面内容 (soup)
        page_soup = self.get_csrf_token_from_page()
        if not self.csrf_token or not self.csrf_header_name or not page_soup:
            print("未能获取CSRF token 或初始页面内容，无法继续，爬虫终止。")
            return

        provinces = self.get_provinces(page_soup)
        if not provinces:
            print("未能获取省份列表，爬虫终止。")
            return

        print(f"获取到的 CSRF Token: {self.csrf_token}, Header Name: {self.csrf_header_name}")

        for province in provinces:
            province_value = province['value']
            province_name = province['text']
            print(f"\n正在处理省份: {province_name} ({province_value})")

            province_stores = self.search_stores_by_province(province_value, province_name)

            if province_stores:
                self.stores_data.extend(province_stores)
            time.sleep(random.uniform(1, 2))  # API请求之间可以加个小延时

        self.save_to_csv(self.stores_data)  # 传递 self.stores_data
        print(f"\n所有省份处理完毕，共抓取 {len(self.stores_data)} 条门店数据。")

    def save_to_csv(self, data_to_save):
        """将数据保存到CSV文件"""
        if not data_to_save:
            print("没有数据可以保存。")
            return

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        try:
            with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=RESULT_FIELDS)
                writer.writeheader()
                writer.writerows(data_to_save)
            print(f"数据已成功保存到 {OUTPUT_PATH}")
        except IOError as e:
            print(f"保存CSV文件失败: {e}")
        except Exception as e:
            print(f"保存CSV时发生未知错误: {e}")


def main():
    scraper = KumhoScraper()
    scraper.scrape()


if __name__ == "__main__":
    main()

# class KumhoSpider:  # <--- 这行开始是问题代码的起点，应注释掉
#     def parse_store_info(self, store_details, province_name, city_name_from_api):
#         address_parts = [
#             store_details.get('addr1', ''),
#             store_details.get('addr2', '')
#         ]
#         address = ' '.join(filter(None, address_parts)).strip()
#
#         # 确保这里的键与 RESULT_FIELDS 中的值完全对应
#         return {
#             "省": province_name,  # 假设 province_name 是正确的省份名
#             "Province": province_name, # 或者对应的英文省份名
#             "市区辅助": city_name_from_api, # 假设 city_name_from_api 是正确的市名
#             "City": city_name_from_api, # 或者对应的英文市名
#             "区": store_details.get('sigunguNm', ''), # API返回的区县名
#             "店名": store_details.get('agncNm', ''),  # 这是关键，确保键是 "店名"
#             "类型": "Kumho Tire",  # 或者从API获取的类型
#             "地址": address,
#             "电话": store_details.get('telNo', ''),
#             "备注": "", # 根据需要填写
#             # 'brand_name': self.brand_name, # 注意：这个键不在 RESULT_FIELDS 中#         }
