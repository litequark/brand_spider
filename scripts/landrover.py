import os
import csv
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

# 定义输出字段
RESULT_FIELDS = ["省", "Province", "市区辅助", "City", "区", "店名", "类型", "地址", "电话", "备注"]

# 设置输出路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/landrover.csv")


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # 初始时设置无头模式为注释状态，方便调试
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def wait_for_page_load(driver, timeout=10):
    """等待页面完全加载"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # 额外等待确保动态内容加载
    except TimeoutException:
        print("页面加载超时")


def get_available_provinces(driver):
    """获取所有可用省份"""
    try:
        wait_for_page_load(driver)

        # 等待省份下拉框加载
        province_select = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='province']"))
        )

        # 使用JavaScript获取选项，避免Select类的问题
        provinces = driver.execute_script("""
            var select = document.querySelector("select[name='province']");
            var options = select.options;
            var provinces = [];
            for(var i = 1; i < options.length; i++) {
                if(options[i].text.trim() && options[i].value.trim()) {
                    provinces.push({
                        text: options[i].text.trim(),
                        value: options[i].value.trim()
                    });
                }
            }
            return provinces;
        """)

        print(f"找到 {len(provinces)} 个省份")
        return provinces
    except Exception as e:
        print(f"获取省份列表失败: {str(e)}")
        return []


def select_province(driver, province_info):
    """选择省份"""
    try:
        province_name = province_info['text']
        province_value = province_info['value']

        # 使用JavaScript直接设置选择
        success = driver.execute_script("""
            var select = document.querySelector("select[name='province']");
            if(select) {
                select.value = arguments[0];
                var event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
                return true;
            }
            return false;
        """, province_value)

        if success:
            print(f"成功选择省份: {province_name}")
            time.sleep(3)  # 等待城市列表加载
            return True
        else:
            print(f"选择省份失败: {province_name}")
            return False

    except Exception as e:
        print(f"选择省份 {province_info['text']} 失败: {str(e)}")
        return False


def get_cities_by_province(driver):
    """获取当前省份下的所有城市"""
    try:
        # 等待城市下拉框更新
        time.sleep(2)

        # 使用JavaScript获取城市选项
        cities = driver.execute_script("""
            var citySelect = document.querySelector("select[name='city']");
            if(!citySelect) return [];

            var options = citySelect.options;
            var cities = [];
            for(var i = 1; i < options.length; i++) {
                if(options[i].text.trim() && options[i].value.trim()) {
                    cities.push({
                        text: options[i].text.trim(),
                        value: options[i].value.trim()
                    });
                }
            }
            return cities;
        """)

        print(f"找到 {len(cities)} 个城市")
        return cities

    except Exception as e:
        print(f"获取城市列表失败: {str(e)}")
        return []


def select_city(driver, city_info):
    """选择城市"""
    try:
        city_name = city_info['text']
        city_value = city_info['value']

        # 使用JavaScript直接设置选择
        success = driver.execute_script("""
            var select = document.querySelector("select[name='city']");
            if(select) {
                select.value = arguments[0];
                var event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
                return true;
            }
            return false;
        """, city_value)

        if success:
            print(f"成功选择城市: {city_name}")
            time.sleep(3)  # 等待门店列表加载
            return True
        else:
            print(f"选择城市失败: {city_name}")
            return False

    except Exception as e:
        print(f"选择城市 {city_info['text']} 失败: {str(e)}")
        return False


def get_store_list(driver):
    """获取门店列表"""
    try:
        # 等待门店列表加载
        time.sleep(5)  # 增加等待时间
        
        # 打印当前页面URL和标题
        print(f"当前页面URL: {driver.current_url}")
        print(f"页面标题: {driver.title}")
        
        # 检查页面是否包含门店相关内容
        page_source = driver.page_source
        if "dealer" in page_source.lower() or "经销商" in page_source:
            print("页面包含门店相关内容")
        else:
            print("页面不包含门店相关内容")
        
        # 尝试多种可能的门店容器选择器
        store_selectors = [
            ".dealer-item",
            ".dealer-list .item", 
            ".store-item",
            "[class*='dealer']",
            ".dealer-info",
            ".dealer-card",
            ".shop-item",
            "[class*='shop']",
            "div[class*='store']",
            "li[class*='dealer']"
        ]
        
        store_elements = []
        for selector in store_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"选择器 {selector}: 找到 {len(elements)} 个元素")
                if elements:
                    store_elements = elements
                    break
            except Exception as e:
                print(f"选择器 {selector} 出错: {e}")
                continue
        
        # 如果仍然没有找到，尝试查找所有可能的容器
        if not store_elements:
            print("尝试查找所有div元素...")
            all_divs = driver.find_elements(By.TAG_NAME, "div")
            print(f"页面总共有 {len(all_divs)} 个div元素")
            
            # 查找包含地址或电话信息的div
            potential_stores = []
            for div in all_divs:
                text = div.text.strip()
                if any(keyword in text for keyword in ["地址", "电话", "tel", "phone", "address"]):
                    potential_stores.append(div)
            
            print(f"找到 {len(potential_stores)} 个可能包含门店信息的元素")
            store_elements = potential_stores[:10]  # 限制数量避免过多
        
        return store_elements
        
    except Exception as e:
        print(f"获取门店列表失败: {str(e)}")
        return []


def parse_store_element(driver, store_element, province, city):
    """解析单个门店信息"""
    try:
        # 尝试多种可能的选择器来提取信息
        store_name = ""
        phone = ""
        address = ""
        store_type = ""

        # 提取店名的多种尝试
        name_selectors = [
            "h2[data-msg]",
            "h2",
            "h3",
            ".dealer-name",
            ".store-name",
            "[class*='name']"
        ]

        for selector in name_selectors:
            try:
                element = store_element.find_element(By.CSS_SELECTOR, selector)
                store_name = element.text.strip()
                if store_name:
                    break
            except:
                continue

        # 提取电话的多种尝试
        phone_selectors = [
            "div.phone",
            ".phone",
            ".tel",
            "[class*='phone']",
            "[class*='tel']"
        ]

        for selector in phone_selectors:
            try:
                element = store_element.find_element(By.CSS_SELECTOR, selector)
                phone = element.text.strip()
                if phone:
                    break
            except:
                continue

        # 提取地址的多种尝试
        address_selectors = [
            "div.address",
            ".address",
            ".addr",
            "[class*='address']",
            "[class*='addr']"
        ]

        for selector in address_selectors:
            try:
                element = store_element.find_element(By.CSS_SELECTOR, selector)
                address = element.text.strip()
                if address:
                    break
            except:
                continue

        # 如果基本信息都没有获取到，尝试获取整个元素的文本
        if not store_name and not phone and not address:
            full_text = store_element.text.strip()
            print(f"门店元素完整文本: {full_text}")
            # 可以在这里添加文本解析逻辑
            return None

        return {
            "省": province,
            "Province": province,
            "市区辅助": city,
            "City": city,
            "区": "",
            "店名": store_name,
            "类型": store_type,
            "地址": address,
            "电话": phone,
            "备注": ""
        }

    except Exception as e:
        print(f"解析门店信息失败: {str(e)}")
        return None


def wait_for_stores_to_load(driver, timeout=15):
    """等待门店信息加载完成"""
    try:
        # 等待任何包含门店信息的元素出现
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.XPATH, "//*[contains(text(), '地址') or contains(text(), '电话') or contains(text(), 'tel') or contains(text(), 'phone')]")) > 0
        )
        print("检测到门店信息已加载")
        return True
    except TimeoutException:
        print("等待门店信息加载超时")
        return False


def main():
    driver = setup_driver()
    try:
        print("开始访问路虎门店查询页面...")
        driver.get("https://dealer.landrover.com.cn/")
        wait_for_page_load(driver)

        # 创建输出目录和CSV文件
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
            writer.writeheader()

            # 获取所有省份
            print("正在获取省份列表...")
            provinces = get_available_provinces(driver)

            if not provinces:
                print("未能获取省份列表，程序退出")
                return

            total_stores = 0

            for i, province_info in enumerate(provinces):
                province_name = province_info['text']
                print(f"\n处理省份 ({i + 1}/{len(provinces)}): {province_name}")

                if select_province(driver, province_info):
                    # 获取当前省份下的所有城市
                    cities = get_cities_by_province(driver)

                    for j, city_info in enumerate(cities):
                        city_name = city_info['text']
                        print(f"  处理城市 ({j + 1}/{len(cities)}): {city_name}")

                        if select_city(driver, city_info):
                            # 保存调试截图
                            save_debug_screenshot(driver, f"debug_{province_name}_{city_name}")

                            # 等待门店加载
                            if wait_for_stores_to_load(driver):
                                # 获取门店列表
                                store_elements = get_store_list(driver)

                            if store_elements:
                                print(f"    找到 {len(store_elements)} 个门店")

                                # 解析每个门店信息
                                for k, store_element in enumerate(store_elements):
                                    store_info = parse_store_element(driver, store_element, province_name, city_name)
                                    if store_info:
                                        writer.writerow(store_info)
                                        total_stores += 1

            print(f"\n爬取完成，共获取 {total_stores} 个门店信息")

    except Exception as e:
        print(f"程序执行出错: {str(e)}")
    finally:
        driver.quit()


def save_debug_screenshot(driver, filename):
    """保存调试截图"""
    try:
        screenshot_path = os.path.join(PROJECT_ROOT, "output", f"{filename}.png")
        driver.save_screenshot(screenshot_path)
        print(f"调试截图已保存: {screenshot_path}")
    except Exception as e:
        print(f"保存截图失败: {e}")


if __name__ == "__main__":
    main()
