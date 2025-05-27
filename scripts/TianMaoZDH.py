import json
import os
import time
import csv
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# 常量定义
CSV_HEADER = ["品牌", "省", "Province", "市区辅助", "City/Area", "区",
              "店名", "类型", "地址", "电话", "备注"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output/TianMao.csv")


class TmallStoreCrawlerPro:
    def __init__(self):
        # 创建输出目录
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        # 初始化CSV文件
        if not os.path.exists(OUTPUT_PATH):
            with open(OUTPUT_PATH, "w", newline="", encoding="gb18030") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)

        # 浏览器配置
        chrome_options = Options()
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)
        print("WebDriver 初始化完成。")

    def _write_to_csv(self, city_name, store_data):
        """将单条数据写入CSV文件"""
        row = [
            "天猫养车",  # 品牌
            "",  # 省
            "",  # Province
            "",  # 市区辅助
            city_name,  # City/Area
            "",  # 区
            store_data.get("name", ""),  # 店名
            "门店",  # 类型
            store_data.get("address", ""),  # 地址
            "",  # 电话
            ""  # 备注
        ]

        try:
            with open(OUTPUT_PATH, "a", newline="", encoding="gb18030") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            print(f"已写入记录：{store_data.get('name')}")
        except Exception as e:
            print(f"写入CSV失败：{str(e)}")

    def _activate_search_and_wait_for_city_list(self):
        """点击输入框激活搜索功能，并等待城市列表出现"""
        try:
            input_container = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.style_searchInput__IVFA3"))
            )
            input_container.click()
            self.wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.style_cityListRow__a2_XZ"))
            )
            print("城市列表已激活并显示。")
            return True
        except TimeoutException:
            print("激活搜索或等待城市列表超时。")
            return False

    def _get_all_cities_from_list(self):
        """从显示的城市列表中提取所有城市名称"""
        cities = []
        try:
            city_elements_xpath = "//div[contains(@class, 'style_cityListRow__a2_XZ')]//div[contains(@class, 'style_cityItem__8dWYU')]"
            city_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, city_elements_xpath))
            )

            for city_element in city_elements:
                city_name = city_element.text.strip()
                if city_name:
                    if ' ' in city_name and len(city_name.split(' ', 1)[0]) == 1 and city_name.split(' ', 1)[
                        0].isalpha():
                        cities.append(city_name.split(' ', 1)[1])
                    else:
                        cities.append(city_name)
            print(f"从列表中获取到 {len(cities)} 个城市。")
        except Exception as e:
            print(f"获取城市列表时发生错误: {e}")
        return list(set(cities))

    def _select_city_by_name_from_list(self, city_name_to_select):
        """从已显示的城市列表中通过名称精确点击一个城市"""
        try:
            city_xpath = f"//div[contains(@class, 'style_cityItem__8dWYU')][normalize-space(substring-after(., ' '))='{city_name_to_select}' or normalize-space(.)='{city_name_to_select}']"
            city_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, city_xpath))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", city_element)
            city_element.click()
            print(f"已点击选择城市: {city_name_to_select}")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"选择城市 '{city_name_to_select}' 时发生错误: {e}")
            return False

    def _clear_search_input(self):
        """清除搜索输入框的内容"""
        try:
            input_box = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.style_searchInput__IVFA3 input"))
            )
            current_value = input_box.get_attribute('value')
            if current_value:
                for _ in range(len(current_value)):
                    input_box.send_keys(Keys.BACKSPACE)
                    time.sleep(0.05)
            print("已通过逐字删除清除搜索输入框。")
        except Exception as e:
            print(f"清除搜索框失败: {e}")

    def parse_store(self, element):
        """数据解析"""
        store_data = {}
        try:
            store_data["name"] = element.find_element(By.CSS_SELECTOR, "h3").text.strip()
        except Exception:
            store_data["name"] = "N/A"

        try:
            store_data["address"] = element.find_element(By.CSS_SELECTOR, "h4").text.strip()
        except Exception:
            store_data["address"] = "N/A"

        try:
            distance_elements = element.find_elements(By.XPATH,
                                                      ".//p/span[contains(text(),'km') or contains(text(),'m')]")
            store_data["distance"] = distance_elements[0].text.strip() if distance_elements else "N/A"
        except Exception:
            store_data["distance"] = "N/A"

        try:
            hours_text_element = element.find_element(By.XPATH, ".//div[contains(text(),'营业时间')]")
            hours_full_text = hours_text_element.text.strip()
            store_data["hours"] = hours_full_text.split("：", 1)[1] if "：" in hours_full_text else hours_full_text
        except Exception:
            store_data["hours"] = "N/A"

        return store_data if store_data["name"] != "N/A" or store_data["address"] != "N/A" else None

    def _scroll_and_collect_stores(self, city_name_logging):
        """滚动加载并解析所有门店"""
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.style_stroeList__ib6lc"))
            )
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.style_stroeList__ib6lc div.style_item__4eLwg"))
            )
        except TimeoutException:
            return []

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_no_change = 3

        all_store_elements = []
        processed = set()

        while True:
            current_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                         "div.style_stroeList__ib6lc div.style_item__4eLwg")
            new_found = False

            for el in current_elements:
                try:
                    identifier = el.get_attribute('innerHTML')
                    if identifier not in processed:
                        all_store_elements.append(el)
                        processed.add(identifier)
                        new_found = True
                except Exception:
                    pass

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                if not new_found:
                    scroll_attempts += 1
                    if scroll_attempts >= max_scroll_no_change:
                        break
                else:
                    scroll_attempts = 0
            else:
                scroll_attempts = 0
            last_height = new_height

        parsed_stores = []
        for store_element in all_store_elements:
            try:
                store_info = self.parse_store(store_element)
                if store_info:
                    self._write_to_csv(city_name_logging, store_info)
                    parsed_stores.append(store_info)
                    print("\n当前爬取记录：")
                    print(f"城市: {city_name_logging}")
                    print(f"店名: {store_info.get('name')}")
                    print(f"地址: {store_info.get('address')}")
                    print(f"距离: {store_info.get('distance')}")
                    print(f"营业时间: {store_info.get('hours')}")
                    print("-" * 50)
            except Exception as e:
                print(f"处理门店元素失败：{str(e)}")

        return parsed_stores

    def run(self):
        self.driver.get("https://tmallyc.com/store/")
        final_data_all_cities = []

        if not self._activate_search_and_wait_for_city_list():
            self.driver.quit()
            return json.dumps(final_data_all_cities, ensure_ascii=False, indent=2)

        all_city_names = self._get_all_cities_from_list()
        if not all_city_names:
            self.driver.quit()
            return json.dumps(final_data_all_cities, ensure_ascii=False, indent=2)

        for city_name in all_city_names:
            print(f"\n--- 开始处理城市: {city_name} ---")

            self._clear_search_input()
            if not self._activate_search_and_wait_for_city_list():
                self.driver.get("https://tmallyc.com/store/")
                time.sleep(3)
                if not self._activate_search_and_wait_for_city_list():
                    continue

            if self._select_city_by_name_from_list(city_name):
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.style_stroeList__ib6lc"))
                    )
                    stores = self._scroll_and_collect_stores(city_name)
                    final_data_all_cities.append({
                        "city": city_name,
                        "stores": stores,
                        "count": len(stores)
                    })
                except Exception as e:
                    print(f"处理城市时发生异常：{str(e)}")
                    continue
            else:
                print(f"城市选择失败：{city_name}")

            time.sleep(1)

        self.driver.quit()

        # 保存JSON文件
        json_output = json.dumps(final_data_all_cities, ensure_ascii=False, indent=2)
        with open(os.path.join(SCRIPT_DIR, "output/TianMao.json"), "w", encoding="utf-8") as f:
            f.write(json_output)

        return json_output


if __name__ == "__main__":
    crawler = TmallStoreCrawlerPro()
    results_json = crawler.run()
    print("\n--- 爬取完成 ---")
    print(f"CSV文件已保存至：{OUTPUT_PATH}")
    print(f"JSON文件已保存至：{os.path.join(SCRIPT_DIR, 'output/TianMao.json')}")