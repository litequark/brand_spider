# https://www.triangle.com.cn/cn/index/listview/catid/6.html
import logging
import csv
import os
from time import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement # 方便类型注解
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException # 异常识别
from util.bs_sleep import sleep_with_random
from util.location_translator import get_en_city, get_en_province
import requests
from urllib.parse import unquote

from po.po import BasePage

RESULT_FIELDS = ["省", "Province", "市区辅助", "City/Area", "区", "店名", "类型", "地址", "电话", "备注"]
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入子目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'triangle.csv')
LOGGING_DIR = os.path.join(PROJECT_ROOT, "log")
LOGGING_PATH = os.path.join(LOGGING_DIR, 'triangle.log')


class QueryDealerPage(BasePage):
    '''元素选择器'''
    # 导航栏与标题
    NAV_BAR = (By.CSS_SELECTOR, 'body > div > div.he_theme > div > section > div.l_breadnav')
    TITLE = (By.CSS_SELECTOR, 'body > div > div.he_theme > div > section > div.l_cbox1 > div.l_cbx1tit.l_sybx2tit > h2')
    
    # 按钮
    SELECT_PROVINCE_BUTTON = (By.CSS_SELECTOR, '#show_province')
    SELECT_CITY_BUTTON = (By.CSS_SELECTOR, '#show_city')
    SELECT_TYPE_BUTTON = (By.CSS_SELECTOR, '#show_type')
    SELECT_BRAND_BUTTON = (By.CSS_SELECTOR, '#show_tyre')
    SEARCH_BUTTON = (By.CSS_SELECTOR, '#store_sub')
    NEXT_PAGE_BUTTON = (By.CSS_SELECTOR, 'body > div > div.he_theme > div > section > div.l_cbox1 > div.d_list > div > div > div > ul > a.next')
    
    # 可滚动的容器
    PROVINCE_CONTAINER = (By.CSS_SELECTOR, '#mCSB_1')
    CITY_CONTAINER = (By.CSS_SELECTOR, 'div.city_lists > div.mCustomScrollBox')
    
    PROVINCE = (By.CSS_SELECTOR, '#mCSB_1_container > p.select_province:not([data-val=""])')
    CITY = (By.CSS_SELECTOR, 'div.city_lists > div > div.mCSB_container > p')
    TYPE = (By.CSS_SELECTOR, '#store_form > div.he_xzfyu.fl.clearfix > div.he_xzfrm.fl.clearfix > div.l_c3_csxl.l_c3_ltlb.fl.normalxl.l_c3_csxl_act > div.l_c3_cslist.l_c3_lblist > p.select_type:not([data-val=""])')
    BRAND = (By.CSS_SELECTOR, '#store_form > div.he_xzfyu.fl.clearfix > div.he_xzfrm.fl.clearfix > div.l_c3_csxl.l_c3_ltlb.fl.normalxl.l_c3_csxl_act > div.l_c3_cslist.l_c3_lblist > p.select_tyre:not([data-val=""])')
    DEALER = (By.CSS_SELECTOR, 'body > div > div.he_theme > div > section > div.l_cbox1 > div.d_list > div > ul > li > div.dlul_box')
    
    
    def __init__(self, driver, base_url: str, timeout: int=5) -> None:
        super().__init__(driver, base_url, timeout)
        self.province: str = str()
        self.city: str = str()
        self.type: str = str()
        self.brand: str = str()
        
        
    def write_dealers_to_csv(self, dealers: list[dict], path: str) -> None:
        with open(path, mode='a', encoding='utf-8', newline='') as fp:
            writer = csv.DictWriter(fp, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
            writer.writerows(dealers)
        
     
    def dealer_webelem_to_dict(self, dealer: WebElement) -> dict:
        return {
            "省": self.province,
            "Province": get_en_province(self.province),
            "市区辅助": self.city,
            "City/Area": get_en_city(self.city),
            "区": str(),
            "店名": dealer.find_element(By.CSS_SELECTOR, 'div.dlul_tit').text.strip().replace('\\n', ' ').replace('\n', ' '),
            "类型": self.type,
            "地址": dealer.find_element(By.XPATH, '//ul[@class="dlul_ul"]/li[@class="dlul_ul_li"]/div[@class="dlul_ul_li_box" and .//div[@class="dlul_ul_li_le" and .//div[@class="dull_text" and text()="地  址："]]]/div[@class="dlul_ul_li_ri"]/p').text.strip().replace('获取路线','').replace('\\n', ' ').replace('\n', ' '),
            "电话": dealer.find_element(By.XPATH, '//ul[@class="dlul_ul"]/li[@class="dlul_ul_li"]/a[@class="dlul_ul_li_box" and .//div[@class="dlul_ul_li_le" and .//div[@class="dull_text" and text()="电  话："]]]/div[@class="dlul_ul_li_ri"]/p').text.strip().replace('\\n', ' ').replace('\n', ' '),
            "备注": str()
        }
        
        
    def get_province_list(self) -> list[WebElement]:
        self.click(self.SELECT_PROVINCE_BUTTON)
        sleep_with_random(1, 1)
        provinces: list[WebElement] = self.find_elements(self.PROVINCE)
        return provinces
    
    
    def get_city_list(self) -> list[WebElement]:
        self.click(self.SELECT_CITY_BUTTON)
        sleep_with_random(1, 1)
        cities: list[WebElement] = self.find_elements(self.CITY)
        return cities
    
    
    def get_types_list(self) -> list[WebElement]:
        self.click(self.SELECT_TYPE_BUTTON)
        sleep_with_random(1, 1)
        types: list[WebElement] = self.find_elements(self.TYPE)
        return [t for t in types if t.text != '']
    
    
    def get_brands_list(self) -> list[WebElement]:
        self.click(self.SELECT_BRAND_BUTTON)
        sleep_with_random(1, 1)
        brands: list[WebElement] = self.find_elements(self.BRAND)
        return brands
    
    
    def get_dealer_list(self) -> list[dict]:
        self.click(self.SEARCH_BUTTON)
        sleep_with_random(1, 1)
        self.scroll_to_element(self.NAV_BAR)
        dealers: list[WebElement] = self.find_elements(self.DEALER, visible=True)
        return [self.dealer_webelem_to_dict(dealer) for dealer in dealers]
    
    
    def goto_next_page(self) -> bool:
        try:
            next_btn: WebElement = self.find_element(self.NEXT_PAGE_BUTTON)
            if next_btn.get_attribute('href') == 'javascript:void(0);': # 无下一页
                return False
            else:
                try:
                    self.click(self.NEXT_PAGE_BUTTON)
                    sleep_with_random(1, 1)
                except Exception:
                    return False
                return True
        except TimeoutException:
            return False


def init_driver():
    DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    chrome_options = Options()
    # 禁用地理位置权限
    chrome_options.add_argument("--disable-geolocation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"user-agent={DEFAULT_UA}")
    # 设置默认拒绝所有网站的定位请求
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 2,  # 2=拒绝, 1=允许, 0=询问
        "profile.default_content_setting_values.notifications": 2,  # 可选：禁用通知
    })
    return webdriver.Chrome(options=chrome_options)
        
        
def main() -> int:
    home_page: str = 'https://www.triangle.com.cn/cn/index/listview/catid/6.html'
    
    total_dealers: int = 0
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(LOGGING_PATH), exist_ok=True)
    
    logging.basicConfig(
        filename=LOGGING_PATH,       # 日志文件名
        level=logging.INFO,       # 日志级别
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8')
    
    with open(file=OUTPUT_PATH, mode='w', encoding='utf-8', newline='') as fp:
        writer = csv.DictWriter(f=fp, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
    
    driver = init_driver()
    query_page = QueryDealerPage(driver, base_url=home_page, timeout=2)
    
    query_page.scroll_to_element(query_page.NAV_BAR)
    
    elem_provinces: list[WebElement] = query_page.get_province_list()
    if len(elem_provinces) == 0:
        print("省份列表为空")
        return 1
    sleep_with_random(1, 1)
    
    for i in range(0, len(elem_provinces)):
        p: WebElement = elem_provinces[i]
        
        query_page.scroll_to_contained_element(p, query_page.PROVINCE_CONTAINER)
        
        query_page.province = p.text
        
        p.click()
        sleep_with_random(0, 1)
        
        elem_cities: list[WebElement] = query_page.get_city_list()
        if len(elem_cities) == 0:
            print("城市列表为空")
            query_page.scroll_to_element(query_page.SELECT_CITY_BUTTON)
            query_page.click(query_page.SELECT_CITY_BUTTON)
        
        
        for j in range(0, len(elem_cities)):
            c: WebElement = elem_cities[j]
            
            query_page.scroll_to_contained_element(c, query_page.CITY_CONTAINER)
            
            query_page.city = c.text
            
            c.click()
            
            elem_types: list[WebElement] = query_page.get_types_list()
            
            
            for k in range(0, len(elem_types)):
                t: WebElement = elem_types[k]
                query_page.type = t.text
                
                t.click()
                
                dealers: list[dict] = query_page.get_dealer_list()
                query_page.write_dealers_to_csv(dealers, OUTPUT_PATH)
                [print(_) for _ in dealers]
                total_dealers += len(dealers)
                
                while query_page.goto_next_page():
                    sleep_with_random(1, 1)
                    dealers: list[dict] = query_page.get_dealer_list()
                    query_page.write_dealers_to_csv(dealers, OUTPUT_PATH)
                    [print(_) for _ in dealers]
                    total_dealers += len(dealers)
                    
                if t != elem_types[len(elem_types) - 1]:
                    elem_types = query_page.get_types_list()
                    sleep_with_random(0, 1)
            
            if c != elem_cities[len(elem_cities) - 1]:
                elem_cities = query_page.get_city_list()
                sleep_with_random(0, 1)
        
        if p != elem_provinces[len(elem_provinces) - 1]:
            elem_provinces = query_page.get_province_list()
            sleep_with_random(0, 1)
    
    print(f'共获取到{total_dealers}家门店')
    return 0

    
if __name__ == "__main__":
    main()