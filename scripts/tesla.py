from time import sleep
import os
import json
import csv
import bs4
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions # 新增导入
# from selenium.webdriver.common.devtools.v134.css import CSSRule # 注释掉或删除此行
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException  # 重命名以区分
from selenium.common.exceptions import NoSuchElementException  # 新增导入
from urllib3.exceptions import ReadTimeoutError

HOME_PAGE = "https://www.tesla.cn/findus/list"

RESULT_FIELDS = ["省份", "门店名称", "门店类型", "地址", "电话", "备注"]  # 更新字段

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入子目录

OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/tesla_stores.csv")  # 已更新

# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# 初始化CSV文件 (保持不变)
with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
    writer.writeheader()

processed_stores_identifiers = set()  # 新增：用于存储已处理店面的唯一标识符
chrome_options = ChromeOptions()
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(60)  # 设置页面加载超时为60秒
driver.implicitly_wait(10)


def save_store_info(store_info):
    """保存店铺信息到CSV文件并打印到控制台，增加去重逻辑"""
    # 创建一个唯一标识符，例如：省份 + 店名 + 地址
    identifier = (store_info["省份"], store_info["门店名称"], store_info["地址"])

    if identifier in processed_stores_identifiers:
        print(f"信息重复，跳过：{store_info['省份']} - {store_info['门店名称']}")
        return False  # 返回 False 表示未保存

    processed_stores_identifiers.add(identifier)

    with open(OUTPUT_PATH, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writerow(store_info)
    print(json.dumps(store_info, ensure_ascii=False))
    return True  # 返回 True 表示已保存


def get_store_info(store_element, province_name):
    """从店铺元素中提取信息 (根据截图更新)"""
    name = "未知店名"
    full_address = "未知地址"
    phone_str = "未知电话"
    store_type_str = "综合服务"  # 默认门店类型

    try:
        name_element = store_element.find_element(By.CSS_SELECTOR, 'div.anchor-container a')
        name = name_element.text.strip() if name_element else "未知店名"

        street_address_element = store_element.find_element(By.CSS_SELECTOR, 'span.street-address-states')
        street_address = street_address_element.text.strip() if street_address_element else ""

        locality_city_postal_element = store_element.find_element(By.CSS_SELECTOR, 'span.locality-city-postal')
        locality_city_postal = locality_city_postal_element.text.strip() if locality_city_postal_element else ""

        full_address = f"{street_address} {locality_city_postal}".strip()
        if not full_address:
            full_address = "未知地址"

        # 尝试提取电话信息
        try:
            tel_elements_container = store_element.find_element(By.CSS_SELECTOR, 'span.tel')
            phone_type_elements = tel_elements_container.find_elements(By.CSS_SELECTOR, 'span.type')
            phone_value_elements = tel_elements_container.find_elements(By.CSS_SELECTOR, 'span.value')

            phones_str_parts = []
            store_types_parts = []

            for i in range(len(phone_type_elements)):
                p_type = phone_type_elements[i].text.strip()
                p_value = ""
                try:
                    if i < len(phone_value_elements):
                        p_value_el = phone_value_elements[i]
                        try:
                            a_in_value = p_value_el.find_element(By.TAG_NAME, 'a')
                            p_value = a_in_value.text.strip()
                        except:
                            p_value = p_value_el.text.strip()
                except Exception:
                    pass

                if p_type and p_value:
                    phones_str_parts.append(f"{p_type}: {p_value}")
                if p_type:
                    store_types_parts.append(p_type.replace("电话", "").strip())

            if phones_str_parts:
                phone_str = "; ".join(phones_str_parts)
            if store_types_parts:
                # 去重并组合门店类型
                unique_store_types = sorted(list(set(filter(None, store_types_parts))))
                store_type_str = ", ".join(unique_store_types) if unique_store_types else "综合服务"

        except NoSuchElementException:
            print(f"在 {province_name} 的门店 '{name}' 未找到电话信息 (span.tel)。将使用默认值。")
            # phone_str 和 store_type_str 保持默认值
        except Exception as e_tel:
            print(f"提取 {province_name} 的门店 '{name}' 电话信息时发生内部错误: {e_tel}。将使用默认值。")
            # phone_str 和 store_type_str 保持默认值

    except Exception as e_outer:
        print(f"提取门店信息时发生主要错误: {e_outer} - 发生在省份: {province_name} 店名: {name}")
        # print(f"出错的元素HTML: {store_element.get_attribute('outerHTML')}") # 取消注释以调试
        # 如果在最外层捕获到错误，确保返回None或一个包含错误标记的字典，以避免后续处理问题
        # 但由于我们已经为各个字段设置了默认值，这里可以直接返回这些默认值
        pass  # 允许返回已收集或默认的信息

    return {
        "省份": province_name,
        "门店名称": name,
        "门店类型": store_type_str,
        "地址": full_address,
        "电话": phone_str,
        "备注": ""
    }


# 移除了旧的 process_stores, check_next_page, get_store_count 函数

# --- 旧的普利司通爬取逻辑已被移除 ---
# try:
#     driver.find_element(by=By.ID, value='search_type2').click()
#     ...
# finally:
#     driver.quit() # 这个quit会导致后续代码出错
# --- 旧的普利司通爬取逻辑结束 ---

total_stores_collected = 0

try:
    print(f"正在访问首页: {HOME_PAGE} 以获取省份列表...")
    driver.get(HOME_PAGE)
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.list-container ul li a'))
    )

    province_link_elements = driver.find_elements(By.CSS_SELECTOR, 'div.list-container ul li a')

    province_data = []
    for link_el in province_link_elements:
        href = link_el.get_attribute('href')
        # 提取省份名称，例如从 " Tesla 体验店 - 四川省" 中提取 "四川省"
        # 或者直接使用 link_el.text，然后清理
        text_content = link_el.text.strip()
        province_name = text_content.split(' - ')[-1] if ' - ' in text_content else text_content
        if href:
            province_data.append({"name": province_name, "url": href})

    if not province_data:
        print("未能从首页获取到任何省份链接，请检查CSS选择器 'div.list-container ul li a' 或页面结构。")
    else:
        print(f"从首页获取到 {len(province_data)} 个省份/区域的链接。")

    for province_info in province_data:
        province_name = province_info["name"]
        province_url = province_info["url"]

        if not province_url.startswith('http'):
            base_url_parts = HOME_PAGE.split('/')
            base_url = f"{base_url_parts[0]}//{base_url_parts[2]}"
            # 使用 urljoin 来更安全地合并 URL
            from urllib.parse import urljoin

            province_url = urljoin(base_url, province_url.lstrip('/'))
            # 移除之前手动的 https:/ http:/ 替换逻辑，urljoin 通常能处理好

        print(f"正在访问省份页面: {province_name} ({province_url})")
        try:
            driver.get(province_url)
        except SeleniumTimeoutException:
            print(f"页面加载超时 (Selenium): {province_name} ({province_url})。跳过此省份。")
            continue
        except ReadTimeoutError:
            print(f"读取超时 (urllib3): {province_name} ({province_url})。跳过此省份。")
            continue
        except Exception as e_page_load:
            print(f"加载省份页面时发生其他错误: {province_name} ({province_url}) - {e_page_load}。跳过此省份。")
            continue

        store_card_selector = 'address.vcard'
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, store_card_selector))
            )
            store_elements_in_province = driver.find_elements(By.CSS_SELECTOR, store_card_selector)
        except SeleniumTimeoutException:  # 修改此处
            print(f"在 {province_name} ({province_url}) 等待 '{store_card_selector}' 超时或未找到元素。跳过此省份。")
            continue  # 跳到下一个省份
        except Exception as e_wait:
            print(
                f"在 {province_name} ({province_url}) 等待 '{store_card_selector}' 时发生其他错误: {e_wait}。跳过此省份。")
            continue

        if not store_elements_in_province:
            print(f"在 {province_name} ({province_url}) 未找到门店信息 (选择器: '{store_card_selector}')。")
            continue

        print(f"在 {province_name} 找到 {len(store_elements_in_province)} 个门店条目 (使用 '{store_card_selector}')。")

        actual_stores_count_in_province = 0
        # 之前这里有一个嵌套循环查找 individual_store_cards，现在 store_elements_in_province 直接就是门店列表了
        for store_element in store_elements_in_province:
            store_info = get_store_info(store_element, province_name)
            if store_info:
                if save_store_info(store_info):  # 修改此处，根据返回值判断是否计数
                    total_stores_collected += 1
                    actual_stores_count_in_province += 1
        print(f"在 {province_name} 实际处理了 {actual_stores_count_in_province} 个门店。")

    print(f"总共收集到 {total_stores_collected} 个店铺信息。")

except Exception as e:
    print(f"主程序发生错误: {e}")
    import traceback

    traceback.print_exc()  # 打印完整的错误堆栈
finally:
    if driver:
        driver.quit()

