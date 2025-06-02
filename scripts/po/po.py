from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement # 方便类型注解
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException # 异常识别

import logging


class BasePage:
    """Page Object 模型的基类，封装了常见的方法"""

    def __init__(self, driver, base_url: str, timeout: int) -> None:
        self.driver = driver
        self.base_url: str = base_url
        self.timeout: int = timeout
        self.logger = logging.getLogger(__name__)
        
        if base_url:
            self.driver.get(base_url)


    def find_element(self, locator, timeout=None):
        """查找单个元素（带显式等待）"""
        timeout = timeout or self.timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            self.logger.error(f"查找元素超时: {locator}")
            raise


    def find_elements(self, locator, timeout=None, visible: bool = False):
        """查找所有元素构成的列表"""
        timeout = timeout or self.timeout
        try:
            if visible:
                return WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_all_elements_located(locator)
                )
            else:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located(locator)
                )
        except TimeoutException:
            self.logger.warning(f"查找元素集合超时: {locator}")
            return []  # 返回空列表而非抛出异常
    

    def click(self, locator, timeout=None):
        """点击元素（带等待元素可点击）"""
        timeout = timeout or self.timeout
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()
        except StaleElementReferenceException:
            # 元素可能已过时，尝试重新查找
            self.logger.warning("元素已过时，重新尝试点击")
            return self.click(locator, timeout)  # 递归重试
        except TimeoutException:
            self.logger.error(f"点击元素失败（不可点击或不存在）: {locator}")
            raise


    def get_text(self, locator, timeout=None):
        """获取元素文本内容"""
        element = self.find_element(locator, timeout)
        return element.text.strip()
    
    
    def get_value(self, locator, timeout=None):
        """获取元素的value值"""
        element = self.find_element(locator, timeout)
        return element.value_of_css_property('value').strip()
    

    def is_visible(self, locator, timeout=None):
        """检查元素是否可见"""
        timeout = timeout or self.timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False
        

    def is_clickable(self, locator, timeout=None):
        """检查元素是否可以点击"""
        timeout = timeout or self.timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            return True
        except TimeoutException:
            return False
        

    # ####################
    # JavaScript相关方法
    # ####################
    
    def execute_script(self, script, *args):
        """执行JavaScript脚本"""
        return self.driver.execute_script(script, *args)
    

    def scroll_to_element(self, locator: tuple[str, str] | WebElement):
        """滚动到指定元素位置"""
        if isinstance(locator, tuple):
            element = self.find_element(locator)
        elif isinstance(locator, WebElement):
            element = locator
        
        self.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    
    
    def scroll_to_contained_element(self, target: tuple[str, str] | WebElement, container: tuple[str, str] | WebElement):
        """将指定容器滚动，使指定元素位于其视口中央"""
        if isinstance(target, tuple):
            elem_target = self.find_element(target)
        elif isinstance(target, WebElement):
            elem_target = target
            
        if isinstance(container, tuple):
            elem_container = self.find_element(container)
        elif isinstance(container, WebElement):
            elem_container = container
            
        self.execute_script("arguments[0].scrollTop = arguments[1].offsetTop;", elem_container, elem_target)


    # ####################
    # 等待相关方法
    # ####################
    
    def wait_for_ajax_complete(self, timeout=30):
        """等待所有AJAX请求完成"""
        script = "return jQuery.active === 0"  # 仅适用于使用jQuery的网站
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script(script) is True
            )
        except TimeoutException:
            self.logger.warning("AJAX请求超时，可能仍有请求未完成")
    
    
    # ####################
    # Cookies处理
    # ####################
    
    def get_cookies(self):
        """获取所有Cookies"""
        return self.driver.get_cookies()
    
    
    def add_cookie(self, cookie_dict):
        """添加Cookie"""
        self.driver.add_cookie(cookie_dict)
