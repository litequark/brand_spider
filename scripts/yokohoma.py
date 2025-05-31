import logging
import os
from os import write

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

from scripts.util.bs_sleep import sleep_with_random
from util.location_translator import get_en_city
import requests

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/yokohoma.csv")


class Browser:
    def __init__(self, home_page: str, user_agent: str):
        self.home_page: str = home_page

        # logger = logging.getLogger('selenium')
        #
        # log_path = 'bridge_log.log'
        # handler = logging.FileHandler(log_path)
        # logger.addHandler(handler)
        # logger.setLevel(logging.DEBUG)
        # logging.basicConfig(encoding='utf-8')

        chrome_options = Options()
        # 禁用地理位置权限
        chrome_options.add_argument("--disable-geolocation")
        chrome_options.add_argument("--disable-infobars")  # 可选：禁用信息栏提示
        chrome_options.add_argument("--no-sandbox")  # 禁用沙盒（Linux必加）
        chrome_options.add_argument("--disable-dev-shm-usage")  # 避免内存不足
        chrome_options.add_argument("--window-size=1920,1080")  # 设置窗口大小（避免响应式布局问题）
        # chrome_options.add_argument("--headless=new")  # 启用新版无头模式
        chrome_options.add_argument("--disable-gpu")  # 可选：禁用GPU加速（旧版需启用）
        chrome_options.add_argument(f"user-agent={user_agent}")

        # 设置默认拒绝所有网站的定位请求
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.geolocation": 2,  # 2=拒绝, 1=允许, 0=询问
            "profile.default_content_setting_values.notifications": 2,  # 可选：禁用通知
        })

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, timeout=3)

        self.province = None
        self.city = None

        self.btn_province = None
        self.btn_city = None

        self.btn_city_list: list = list()
        self.btn_provinces_list: list = list()


    def run(self):
        driver = self.driver
        home_page = self.home_page
        wait = self.wait

        try:
            driver.get(home_page)
            '''拒绝所有Cookie'''
            btn_manage_cookies = driver.find_element(By.CSS_SELECTOR, value='button.btn.btn-outline-primary.p_btSet')
            wait.until(lambda _: btn_manage_cookies.is_displayed())
            btn_manage_cookies.click()
            sleep_with_random(1, 1)
            btn_refuse_cookies = driver.find_element(By.CSS_SELECTOR, value='button.btn.btn-outline-primary.p_btRefuse')
            wait.until(lambda _: btn_refuse_cookies.is_displayed())
            btn_refuse_cookies.click()

            '''选择省份'''
            self.btn_province = driver.find_element(By.CSS_SELECTOR, value='div.js-filter-select.p_filter_select.selectPickerWrapper')
            driver.execute_script("arguments[0].scrollIntoView();", self.btn_province)

            if self.btn_province is None:
                exit(1)

            wait.until(lambda _: self.btn_province.is_displayed())
            self.btn_province.click()

            '''获取省份列表'''
            self.btn_provinces_list = driver.find_elements(By.CSS_SELECTOR, value='div.js-filter-select.p_filter_select.selectPickerWrapper[placeholder="- 省 -"] > div.select-picker-options-wrp.p_select_options > div.select-picker-options-list.p_o_list > div.select-picker-options-list-item.p_o_item > span')
            wait.until(lambda _:self.btn_provinces_list[0].is_displayed())
        except TypeError as e:
            print(e)
            exit(1)
        


        print(1)




def main():
    home_page = 'https://www.yokohama.com.cn/Check.html'

    browser = Browser(home_page, DEFAULT_UA)
    browser.run()


if __name__ == "__main__":
    main()
