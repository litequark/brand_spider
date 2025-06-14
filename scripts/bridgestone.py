import csv
import logging
import os
from time import sleep
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from util.location_translator import get_en_city


def save_store_info_to_csv(fields: list, store_dict: dict, file_path: str) -> None:
    # 创建父目录（如果不存在)
    with open(file_path, "a", encoding="utf-8", newline='') as fp:  # 清除csv文件
        # 写入表头
        d_list_writer = csv.DictWriter(fp, fieldnames=fields, quoting=csv.QUOTE_ALL)
        d_list_writer.writerow(store_dict)


def parse_div_store_info(city: str, district: str, store_element, store_dict: dict) -> None:
    div_store_type = store_element.find_element(By.CSS_SELECTOR, 'div.sl_pop div.square')
    # 门店类型通过.text无法获取，得到的是空字符串。（？？？）
    # 通过 JavaScript 获取 textContent（不受 CSS 影响）
    str_store_type = driver.execute_script("return arguments[0].textContent;", div_store_type).strip()
    store_dict.update({"省": str(),
                       "Province": str(),
                       "市区辅助": city,
                       "City/Area": get_en_city(city),
                       "区": district,
                       "店名": store_element.find_element(By.CSS_SELECTOR, 'div.shop_left div.shop_name').text,
                       "类型": str_store_type,
                       "地址": store_element.find_element(By.CSS_SELECTOR,
                                                          'div.shop_left div.shop_address span').text,
                       "电话": store_element.find_element(By.CSS_SELECTOR,
                                                          'div.shop_phone a:nth-child(2) span').text,
                       "备注": str()})


def process_btn_alphabet_group(p_btn_alphabet_group, p_btn_city_input_box) -> int:
    p_store_count: int = 0
    wait.until(lambda _: p_btn_alphabet_group.is_displayed())
    p_btn_alphabet_group.click()
    # 获取当前城市首字母分组的container
    p_container_alphabet_group = p_btn_city_input_box.find_element(by=By.CSS_SELECTOR,
                                                               value='div.city_list div.city_container.cc')
    wait.until(lambda _: p_container_alphabet_group.is_displayed())

    '''获取分组内所有行（一行城市为一个wrapper，内含城市和对应的区划列表，平级）'''
    p_wrappers_cities: list = p_container_alphabet_group.find_elements(By.CSS_SELECTOR, 'ul.cities-wrapper')
    for p_wrapper_cities in p_wrappers_cities:
        p_store_count += process_wrapper_cities(p_wrapper_cities, p_btn_alphabet_group)
    return p_store_count


def process_wrapper_cities(p_wrapper_cities, p_btn_alphabet_group) -> int:
    p_store_count: int = 0
    wait.until(lambda _: p_wrapper_cities.is_displayed())
    '''获取行内所有的城市按钮'''
    p_btn_cities: list = p_wrapper_cities.find_elements(by=By.CSS_SELECTOR, value='li')

    '''依次处理行内所有的城市'''
    for p_btn_city in p_btn_cities:
        p_store_count += process_btn_city(p_btn_city, p_wrapper_cities, p_btn_alphabet_group)
    return p_store_count


def process_btn_city(p_btn_city, p_wrapper_cities, p_btn_alphabet_group) -> int:
    p_store_count: int = 0
    wait.until(lambda _: p_btn_city.is_displayed())
    p_str_city: str = p_btn_city.get_attribute("title")
    p_btn_city.click()

    # 全部区域 #city_span > div.city_list > div.city_container.cc > ul:nth-child(13) > div.district-content.cr > div:nth-child(1) > span
    '''获取城市下辖的所有区划按钮'''
    p_btn_districts: list = p_wrapper_cities.find_elements(by=By.CSS_SELECTOR,
                                                       value='div.district-content.cr div span')

    '''依次处理城市下辖的所有区划'''
    for p_btn_district in p_btn_districts:
        wait.until(lambda _: p_btn_district.is_displayed())
        if p_btn_district.text == '全部区域':
            continue
        p_store_count += process_btn_district(p_btn_district, p_btn_alphabet_group, p_str_city)
    return p_store_count


def process_btn_district(p_btn_district, p_btn_alphabet_group, p_str_city: str) -> int:
    """此层级中会出现页面重载（因为点击了查询按钮）"""
    p_store_count: int = 0
    wait.until(lambda _: p_btn_district.is_displayed())
    p_str_district: str = p_btn_district.get_attribute("title")
    p_btn_district.click()
    '''获取“查询”按钮'''
    p_btn_search = btn_city_input_box.find_element(by=By.ID, value="search_btn_mylo2")
    wait.until(lambda _: p_btn_search.is_displayed())
    p_btn_search.click()

    '''等待查询完毕'''
    p_edit_field = driver.find_element(By.ID, value='edit-actions--2')
    wait.until(lambda _: p_edit_field.is_enabled())

    '''获取门店总数'''
    p_div_district_total_stores = driver.find_element(by=By.CSS_SELECTOR, value="#agency_length2")
    wait.until(lambda _: p_div_district_total_stores.is_displayed())
    p_str_district_total_stores: str = p_div_district_total_stores.text
    # 从字符串中提取数字
    p_match_store_count = re.search(r"(\d+)",
                                  p_str_district_total_stores) if p_str_district_total_stores else None
    p_int_district_total_stores: int = int(p_match_store_count.group()) if p_match_store_count else 0

    '''获取门店列表'''
    p_div_district_stores: list = driver.find_elements(By.CSS_SELECTOR, '#agencys-region2 div.store_list')
    # 加入实际爬取门店的计数
    p_store_count += len(p_div_district_stores)

    '''依次对列表里的店铺提取属性'''
    for p_div_district_store in p_div_district_stores:
        process_div_district_store(p_div_district_store, p_str_city, p_str_district)

    driver.find_element(by=By.ID, value='city_span').click()
    p_btn_alphabet_group.click()
    sleep(0.5)

    return p_store_count


def process_div_district_store(p_div_district_store, p_str_city: str, p_str_district: str) -> None:
    p_store_info: dict = STORE.copy()
    if p_div_district_store.is_displayed():
        parse_div_store_info(p_str_city, p_str_district, p_div_district_store, p_store_info)
    else:
        '''表示该元素处于下一页，需要翻页'''
        p_paginator_next = driver.find_element(By.CSS_SELECTOR,
                                               '#agency_list2 div.page_bottom2 span.next2')
        wait.until(lambda _: p_paginator_next.is_displayed())
        p_paginator_next.click()
        wait.until(lambda _: p_div_district_store.is_displayed())
        parse_div_store_info(p_str_city, p_str_district, p_div_district_store, p_store_info)

    print(p_store_info)
    '''写入CSV'''
    save_store_info_to_csv(RESULT_FIELDS, p_store_info, OUTPUT_PATH)


def get_store_type(type_map: dict, str_type: str) -> str:
    return type_map[str] if (str in type_map) else str_type


HOME_PAGE = "https://www.bridgestone.com.cn/interactioncenter/search_shop.html"

RESULT_FIELDS = ["省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]

STORE: dict = {
    "省": str(),
    "Province": str(),
    "市区辅助": str(),
    "City/Area": str(),
    "区": str(),
    "店名": str(),
    "类型": str(),
    "地址": str(),
    "电话": str(),
    "备注": str()
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/bridgestone.csv")

TYPE_MAP: dict = dict()

logger = logging.getLogger('selenium')

log_path = 'bridge_log.log'
handler = logging.FileHandler(log_path)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

chrome_options = Options()
# 禁用地理位置权限
chrome_options.add_argument("--disable-geolocation")
chrome_options.add_argument("--disable-infobars")  # 可选：禁用信息栏提示
chrome_options.add_argument("--no-sandbox")  # 禁用沙盒（Linux必加）
chrome_options.add_argument("--disable-dev-shm-usage")  # 避免内存不足
chrome_options.add_argument("--window-size=1920,1080")  # 设置窗口大小（避免响应式布局问题）
chrome_options.add_argument("--headless=new")  # 启用新版无头模式
chrome_options.add_argument("--disable-gpu")  # 可选：禁用GPU加速（旧版需启用）

# 设置默认拒绝所有网站的定位请求
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_setting_values.geolocation": 2,  # 2=拒绝, 1=允许, 0=询问
    "profile.default_content_setting_values.notifications": 2,  # 可选：禁用通知
})

driver = webdriver.Chrome(options=chrome_options)
driver.get(HOME_PAGE)

claimed_store_count: int = 0
scraped_store_count: int = 0

try:
    '''写入表头'''
    # 创建父目录（如果不存在)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline='') as f:  # 清除csv文件
        # 写入表头
        list_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        list_writer.writerow(RESULT_FIELDS)

    '''初始化等待器'''
    wait = WebDriverWait(driver, timeout=3)

    '''按城市查找'''
    # 搜索按钮对象
    btn_search_by_city = driver.find_element(by=By.ID, value='search_type2')
    # 等待按钮出现
    wait.until(lambda _: btn_search_by_city.is_displayed())
    # 点击按钮
    btn_search_by_city.click()

    '''展开城市列表'''
    btn_city_input_box = driver.find_element(by=By.ID, value='city_span')
    wait.until(lambda _: btn_city_input_box.is_displayed())
    btn_city_input_box.click()

    '''获取城市首字母分组'''
    btn_alphabet_groups: list = btn_city_input_box.find_elements(by=By.CSS_SELECTOR, value='div.city_list ul.letter li')

    store_total: int = 0
    '''依次处理所有的城市首字母分组'''
    for btn_alphabet_group in btn_alphabet_groups:
        wait.until(lambda _: btn_alphabet_group.is_displayed())
        # 跳过“热门”分组，只处理具体的首字母分组
        if btn_alphabet_group.text == '热门':
            continue
        store_total += process_btn_alphabet_group(btn_alphabet_group, btn_city_input_box)

    print(f"共计{store_total}家门店")

except Exception as e:
    print(e)
