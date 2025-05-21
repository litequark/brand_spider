import json
import os

class LocationTranslator:
    def __init__(self):
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 加载城市数据
        cities_path = os.path.join(current_dir, 'cities.json')
        with open(cities_path, 'r', encoding='utf-8') as f:
            self.cities_dict = json.load(f)
            
        # 加载省份数据
        provinces_path = os.path.join(current_dir, 'provinces.json')
        with open(provinces_path, 'r', encoding='utf-8') as f:
            self.provinces_dict = json.load(f)
    
    def get_en_city(self, city_zh: str) -> str:
        """
        将中文城市名转换为英文
        
        参数:
            city_zh: 城市的中文名字符串
            
        返回值:
            城市的英文名字符串，如果未找到则返回原中文名
        """
        return self.cities_dict.get(city_zh, city_zh)
    
    def get_en_province(self, province_zh: str) -> str:
        """
        将中文省份名转换为英文
        
        参数:
            province_zh: 省级行政区的中文名字符串
            
        返回值:
            省份的英文名字符串，如果未找到则返回原中文名
        """
        return self.provinces_dict.get(province_zh, province_zh)

# 为了方便直接调用，创建一个全局实例
_translator = LocationTranslator()

# 提供直接调用的函数
def get_en_city(city_zh: str) -> str:
    """
    将中文城市名转换为英文
    
    参数:
        city_zh: 城市的中文名字符串
        
    返回值:
        城市的英文名字符串，如果未找到则返回原中文名
    """
    return _translator.get_en_city(city_zh)

def get_en_province(province_zh: str) -> str:
    """
    将中文省份名转换为英文
    
    参数:
        province_zh: 省级行政区的中文名字符串
        
    返回值:
        省份的英文名字符串，如果未找到则返回原中文名
    """
    return _translator.get_en_province(province_zh)
# 为了方便直接调用，创建一个全局实例
_translator = LocationTranslator()

# 提供直接调用的函数
def get_en_city(city_zh: str) -> str:
    """
    将中文城市名转换为英文
    
    参数:
        city_zh: 城市的中文名字符串
        
    返回值:
        城市的英文名字符串，如果未找到则返回原中文名
    """
    return _translator.get_en_city(city_zh)

def get_en_province(province_zh: str) -> str:
    """
    将中文省份名转换为英文
    
    参数:
        province_zh: 省级行政区的中文名字符串
        
    返回值:
        省份的英文名字符串，如果未找到则返回原中文名
    """
    return _translator.get_en_province(province_zh)