import csv
import os
import time
import random
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from urllib.parse import urlparse

# 导入 location_translator
from util.location_translator import get_en_province, get_en_city

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spider.log'),
        logging.StreamHandler()
    ]
)

# 定义CSV文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "jd.csv")

class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20) # 增加等待时间

    def visit(self, url):
        self.driver.get(url)

    def find_element(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def find_elements(self, by, value):
        return self.wait.until(EC.presence_of_all_elements_located((by, value)))

class JdAutoSpider(BasePage):
    def __init__(self, driver):
        super().__init__(driver)
        self.base_url = "https://m-svc.jd.com/?sid=&un_area=1_72_2799_0#/shops/null/null/null/100044619366?appSource=jd&action=1&num=1"
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.csv_file_path = OUTPUT_PATH
        self.fieldnames = [
            '省', 'Province', '市区辅助', 'City/Area', '区', '店名', '地址', '电话'
        ]
        self._initialize_csv()

    def _initialize_csv(self):
        """初始化CSV文件，写入表头"""
        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
        logging.info(f"CSV文件已创建: {self.csv_file_path}")

    def _write_to_csv(self, data):
        """将数据写入CSV文件"""
        with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, quoting=csv.QUOTE_ALL)
            writer.writerow(data)

    def _wait_for_redirect_or_input(self, timeout=300):
        """等待用户输入继续操作的指令，或在重定向到非指定域名时暂停"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_domain = urlparse(self.driver.current_url).netloc
            if "m-svc.jd.com" not in current_domain:
                logging.warning(f"检测到重定向到非指定域名: {self.driver.current_url}。请在 {timeout} 秒内手动处理，或在控制台输入 'Y' 并回车以继续。")
                logging.info("如果不需要处理，请直接输入 'Y'。")
                user_input = input("输入 'Y' 继续...\n").strip().upper()
                if user_input == 'Y':
                    logging.info("收到确认，继续执行。")
                    return True
                else:
                    logging.info("输入无效，请重新输入或等待超时。")
            
            remaining_time = int(timeout - (time.time() - start_time))
            print(f"\r剩余时间: {remaining_time} 秒。", end='', flush=True)
            time.sleep(1)
        
        logging.warning("等待超时，程序退出。")
        return False

    def _scrape_store_details(self, store_url, province_cn, city_cn, district_cn):
        """从门店详情页抓取门店信息"""
        logging.info(f"进入门店详情页: {store_url}")
        self.driver.get(store_url)
        time.sleep(random.uniform(2, 4)) # 等待页面加载

        try:
            # 门店名称
            store_name_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.info .name')))
            store_name = store_name_element.text.strip()

            # 营业时间
            business_hours_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.txt-ul li:nth-child(1) .con .name')))
            business_hours = business_hours_element.text.replace('营业时间：', '').strip()

            # 地址
            address_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.txt-ul li:nth-child(2) .con .name')))
            address = address_element.text.strip()

            # 电话
            phone_number_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.txt-ul li:nth-child(3) .con .name')))
            phone_number = phone_number_element.text.strip()

            # 翻译省份和城市
            province_en = get_en_province(province_cn) if province_cn else ''
            city_en = get_en_city(city_cn) if city_cn else ''

            store_data = {
                '省': province_cn,
                'Province': province_en,
                '市区辅助': city_cn,
                'City/Area': city_en,
                '区': district_cn,
                '店名': store_name,
                '地址': address,
                '电话': phone_number
            }
            logging.info(f"抓取到门店信息: {store_data}")
            print(store_data) # 输出到控制台
            self._write_to_csv(store_data)

        except (NoSuchElementException, TimeoutException) as e:
            logging.error(f"未能抓取门店详情或元素未找到: {e}")
        except Exception as e:
            logging.error(f"抓取门店详情时发生未知错误: {e}")
        finally:
            self.driver.back() # 返回门店列表页
            time.sleep(random.uniform(1, 2))

    def _scrape_stores_in_current_view(self, province_cn, city_cn, district_cn):
        """抓取当前视图下的所有门店信息，并处理滚动加载"""
        logging.info(f"开始抓取 {province_cn}-{city_cn}-{district_cn} 下的门店...")
        store_urls = set() # 使用集合存储已访问的门店URL，避免重复
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            try:
                # 等待门店列表加载完成
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#shop-list-container .shop-item')))
                shop_items = self.find_elements(By.CSS_SELECTOR, '#shop-list-container .shop-item')
                
                current_page_urls = []
                for item in shop_items:
                    try:
                        # 获取门店的点击链接
                        # 京东养车门店列表页的点击事件通常绑定在 shop-item 元素上，没有直接的 href 属性
                        # 需要通过 JavaScript 获取点击后跳转的 URL 或者直接点击元素
                        # 这里我们直接点击元素，然后从当前URL获取门店ID，再构造详情页URL
                        # 假设门店详情页的URL结构为 https://m-svc.jd.com/#/shops/null/null/null/{store_id}
                        # 门店列表页的每个 shop-item 都有一个 report-eventparam 属性，其中包含门店ID
                        shop_item_parent = item.find_element(By.XPATH, './..') # 获取父元素 cp-shop-item
                        store_id_param = shop_item_parent.get_attribute('report-eventparam')
                        if store_id_param:
                            store_id = store_id_param.split('_')[-1] # 提取门店ID
                            detail_url = f"https://m-svc.jd.com/#/shops/null/null/null/{store_id}"
                            if detail_url not in store_urls:
                                current_page_urls.append(detail_url)
                                store_urls.add(detail_url)
                    except StaleElementReferenceException:
                        logging.warning("元素已过时，重新查找。")
                        break # 跳出内层循环，重新获取 shop_items
                    except Exception as e:
                        logging.error(f"获取门店URL时发生错误: {e}")

                for url in current_page_urls:
                    self._scrape_store_details(url, province_cn, city_cn, district_cn)
                    self._wait_for_redirect_or_input() # 每次返回列表页后检查重定向

                # 滚动到底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 4)) # 等待新内容加载

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    logging.info("已滚动到底部，没有更多门店加载。")
                    break
                last_height = new_height

            except TimeoutException:
                logging.info("当前视图下没有门店或加载超时。")
                break
            except Exception as e:
                logging.error(f"滚动或抓取门店列表时发生错误: {e}")
                break

    def run(self):
        """执行爬虫主逻辑"""
        self.visit(self.base_url)
        logging.info(f"已访问京东养车门店列表页面: {self.base_url}")
        self._wait_for_redirect_or_input() # 初始页面加载后检查重定向

        time.sleep(random.uniform(2, 4)) # 随机等待

        try:
            # 点击“区域筛选”按钮
            # 根据jd.html结构，区域筛选按钮的文本是“鼓楼区”或者其他区名，而不是“区域筛选”
            # 找到 class 为 filter-list__item 且 report-eventid 为 MCarSteward_StoreListAddress 的元素
            area_filter_button = self.wait.until(EC.presence_of_element_located((By.XPATH, '//ul[@class="filter-list"]/li[@report-eventid="MCarSteward_StoreListAddress"]')))
            area_filter_button.click()
            logging.info("点击区域筛选按钮。")
            time.sleep(random.uniform(1, 2))

            # 获取所有省份
            # 这里的XPATH需要根据jd.html的实际结构调整
            # location-header 下的 li 元素代表省、市、区
            # 先点击第一个 li (省份)
            province_header_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//ul[@class="location-header"]/li[1]')))
            province_header_element.click()
            time.sleep(random.uniform(1, 2))

            # 获取 addr-list 下的省份列表
            province_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
            province_names = [p.text.strip() for p in province_elements if p.text.strip() and p.text.strip() != '全部']
            logging.info(f"检测到 {len(province_names)} 个省份/直辖市。")

            for i, province_name_cn in enumerate(province_names):
                # 重新获取省份元素，避免StaleElementReferenceException
                province_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
                province_element = province_elements[i+1] # 跳过“全部”选项
                province_element.click()
                logging.info(f"选择省份: {province_name_cn}")
                time.sleep(random.uniform(1, 2))
                self._wait_for_redirect_or_input()

                # 点击城市头部，显示城市列表
                city_header_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//ul[@class="location-header"]/li[2]')))
                city_header_element.click()
                time.sleep(random.uniform(1, 2))

                # 获取所有城市
                city_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
                city_names = [c.text.strip() for c in city_elements if c.text.strip() and c.text.strip() != '全部']
                logging.info(f"在 {province_name_cn} 下检测到 {len(city_names)} 个城市。")

                for j, city_name_cn in enumerate(city_names):
                    # 重新获取城市元素
                    city_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
                    city_element = city_elements[j+1] # 跳过“全部”选项
                    city_element.click()
                    logging.info(f"选择城市: {city_name_cn}")
                    time.sleep(random.uniform(1, 2))
                    self._wait_for_redirect_or_input()

                    # 点击区县头部，显示区县列表
                    district_header_elements = self.find_elements(By.XPATH, '//ul[@class="location-header"]/li')
                    if len(district_header_elements) >= 3: # 检查是否有区县层级
                        district_header_element = district_header_elements[2]
                        district_header_element.click()
                        time.sleep(random.uniform(1, 2))

                        # 获取所有区县
                        district_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
                        district_names = [d.text.strip() for d in district_elements if d.text.strip() and d.text.strip() != '全部']
                        logging.info(f"在 {city_name_cn} 下检测到 {len(district_names)} 个区县。")

                        if not district_names: # 如果没有区县，则直接处理当前城市下的门店
                            logging.info(f"城市 {city_name_cn} 没有细分到区县，直接抓取门店。")
                            self._scrape_stores_in_current_view(province_name_cn, city_name_cn, "")
                        else:
                            for k, district_name_cn in enumerate(district_names):
                                # 重新获取区县元素
                                district_elements = self.find_elements(By.XPATH, '//div[@class="location-content"]/ul[@class="addr-list"]/li')
                                district_element = district_elements[k+1] # 跳过“全部”选项
                                district_element.click()
                                logging.info(f"选择区县: {district_name_cn}")
                                time.sleep(random.uniform(2, 3)) # 等待门店列表加载
                                self._wait_for_redirect_or_input()

                                self._scrape_stores_in_current_view(province_name_cn, city_name_cn, district_name_cn)

                                # 返回到区县列表，以便选择下一个区县
                                if k < len(district_names) - 1:
                                    district_header_element.click() # 重新点击区县头部以刷新列表
                                    time.sleep(random.uniform(1, 2))
                    else:
                        logging.info(f"城市 {city_name_cn} 没有区县层级，直接抓取门店。")
                        self._scrape_stores_in_current_view(province_name_cn, city_name_cn, "")

                    # 返回到城市列表，以便选择下一个城市
                    if j < len(city_names) - 1:
                        city_header_element.click() # 重新点击城市头部以刷新列表
                        time.sleep(random.uniform(1, 2))

                # 返回到省份列表，以便选择下一个省份
                if i < len(province_names) - 1:
                    province_header_element.click() # 重新点击省份头部以刷新列表
                    time.sleep(random.uniform(1, 2))

            logging.info("所有省份、城市、区县门店信息抓取完成。")

        except Exception as e:
            logging.error(f"爬取过程中发生错误: {e}")
        finally:
            self.driver.quit()
            logging.info("浏览器已关闭。")

# 示例用法
if __name__ == '__main__':
    # 配置Chrome WebDriver
    # 请确保您已下载对应Chrome版本的ChromeDriver，并将其路径添加到系统PATH中，或在此处指定其路径
    # 例如: service = Service('path/to/chromedriver')
    service = Service() # 假设chromedriver在PATH中
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 无头模式，不显示浏览器界面
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--start-maximized') # 最大化窗口，避免元素不可见
    options.add_argument('--disable-blink-features=AutomationControlled') # 避免被检测为自动化程序
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=service, options=options)

    spider = JdAutoSpider(driver)
    spider.run()