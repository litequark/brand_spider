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
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'yokohoma.csv')


class CheckPage(BasePage):
    """Check.html页面的类"""

    # Locators
    MANAGE_COOKIES_BUTTON = (By.CSS_SELECTOR, 'button.btn.btn-outline-primary.p_btSet')
    REFUSE_COOKIES_BUTTON = (By.CSS_SELECTOR, 'button.btn.btn-outline-primary.p_btRefuse')
    SELECT_PROVINCE_BUTTON = (By.CSS_SELECTOR, 'div.js-filter-select.p_filter_select.selectPickerWrapper[placeholder="- 省 -"]')
    SELECT_CITY_BUTTON = (By.CSS_SELECTOR, 'div.js-filter-select.p_filter_select.selectPickerWrapper[placeholder="- 市 -"]')
    NEXT_PAGE_BUTTON = (By.CSS_SELECTOR, 'div.e_loop-2.s_list.response-transition > div > div.p_page > div > a.page_a.page_next')


    PROVINCE_LIST = (By.CSS_SELECTOR, 'div.js-filter-select.p_filter_select.selectPickerWrapper[placeholder="- 省 -"] > div.select-picker-options-wrp.p_select_options > div.select-picker-options-list.p_o_list > div.select-picker-options-list-item.p_o_item > span')
    CITY_LIST = (By.CSS_SELECTOR, 'div.js-filter-select.p_filter_select.selectPickerWrapper[placeholder="- 市 -"] > div.select-picker-options-wrp.p_select_options > div.select-picker-options-list.p_o_list > div.select-picker-options-list-item.p_o_item[data-selected="true"] > span')
    DEALER_LIST = (By.CSS_SELECTOR, 'div.e_loop-2.s_list.response-transition > div > div.p_list > div > div.e_container-8.s_layout > div > div.e_container-32.s_layout > div')



    def __init__(self, driver, base_url: str, timeout: int) -> None:
        super().__init__(driver, base_url, timeout)
        self.province_str: str = str()
        self.city_str: str = str()


    def refuse_all_cookies(self):
        self.click(self.MANAGE_COOKIES_BUTTON)
        sleep_with_random(1, 1)
        self.click(self.REFUSE_COOKIES_BUTTON)
        sleep_with_random(1, 1)
        
        
    def get_province_list(self) -> list[WebElement]:
        self.scroll_to_element(self.SELECT_PROVINCE_BUTTON)
        self.click(self.SELECT_PROVINCE_BUTTON)
        return self.find_elements(self.PROVINCE_LIST)
    
    
    def get_city_list(self) -> list[WebElement]:
        self.scroll_to_element(self.SELECT_CITY_BUTTON)
        self.click(self.SELECT_CITY_BUTTON)
        return self.find_elements(self.CITY_LIST)
    
    
    def get_dealer_list(self) -> list[WebElement]:
        return self.find_elements(self.DEALER_LIST)
        
        
    def dealer_to_dict(self, dealer: WebElement) -> dict:
        return {
            "省": self.province_str,
            "Province": get_en_province(self.province_str),
            "市区辅助": self.city_str,
            "City/Area": get_en_city(self.city_str),
            "区": str(),
            "店名": dealer.find_element(By.CSS_SELECTOR, 'p.e_text-4').text.strip(),
            "类型": str(),
            "地址": dealer.find_element(By.CSS_SELECTOR, 'p.e_text-6').text.strip(),
            "电话": dealer.find_element(By.CSS_SELECTOR, 'p.e_text-31').text.strip(),
            "备注": str()
        }
    
    
def save_dict_to_csv(path: str, src: dict) -> None:
    with open(file=path, mode='a', encoding='utf-8', newline='') as fp:
        writer = csv.DictWriter(f=fp, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writerow(src)
    
    
def init_driver():
    DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    chrome_options = Options()
    # 禁用地理位置权限
    chrome_options.add_argument("--disable-geolocation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"user-agent={DEFAULT_UA}")
    # 设置默认拒绝所有网站的定位请求
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 2,  # 2=拒绝, 1=允许, 0=询问
        "profile.default_content_setting_values.notifications": 2,  # 可选：禁用通知
    })
    return webdriver.Chrome(options=chrome_options)


def main():
    total_dealers: int = 0
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(file=OUTPUT_PATH, mode='w', encoding='utf-8', newline='') as fp:
        writer = csv.DictWriter(f=fp, fieldnames=RESULT_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
    
    driver = init_driver()
    
    check_page = CheckPage(driver, base_url='https://www.yokohama.com.cn/Check.html', timeout=5)
    
    check_page.refuse_all_cookies()
    provinces: list[WebElement] = check_page.get_province_list()
    sleep_with_random(1, 1)
    
    for p in provinces:
        check_page.province_str = unquote(p.get_attribute('value') or str())
        check_page.scroll_to_element(p)
        check_page.click(p, 5)
        sleep_with_random(1, 1)
        cities: list[WebElement] = check_page.get_city_list()
        for c in cities:
            check_page.city_str = unquote(c.get_attribute('value') or str())
            check_page.scroll_to_element(c)
            check_page.click(c, 5)
            sleep_with_random(1, 1)
            
            no_more_pages: bool = False
            while not no_more_pages:
                next_button_class: str = check_page.find_element(check_page.NEXT_PAGE_BUTTON).get_attribute('class') or str()
                next_button_class_list: list[str] = next_button_class.split()
                if 'disabled' in next_button_class_list:
                    no_more_pages = True
                
                dealers: list[WebElement] = check_page.get_dealer_list()
                for d in dealers:
                    dealer_dict: dict = check_page.dealer_to_dict(d)
                    print(dealer_dict)
                    save_dict_to_csv(OUTPUT_PATH, dealer_dict)
                    total_dealers += 1
                    
                if not no_more_pages:
                    # 翻页
                    check_page.scroll_to_element(check_page.NEXT_PAGE_BUTTON)
                    check_page.click(check_page.NEXT_PAGE_BUTTON)
                    sleep_with_random(1, 1)
            
            if c != cities[len(cities) - 1]:
                check_page.click(check_page.SELECT_CITY_BUTTON, 5)
                sleep_with_random(1, 1)
        
        if p != provinces[len(provinces) - 1]:
            check_page.click(check_page.SELECT_PROVINCE_BUTTON, 5)
            sleep_with_random(1, 1)

    print(f'共获取到{total_dealers}家门店')

if __name__ == "__main__":
    main()
