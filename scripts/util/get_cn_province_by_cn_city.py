import json
import os

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_city_province_mapping():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载省份和城市数据
    provinces = load_json_file(os.path.join(current_dir, 'stand_province.json'))
    cities = load_json_file(os.path.join(current_dir, 'stand_city.json'))
    
    # 创建省份代码到省份名称的映射
    province_code_to_name = {p['code']: p['name'] for p in provinces}
    
    # 创建城市到省份的映射
    city_to_province = {}
    
    # 特殊处理直辖市
    direct_municipalities = {
        '11': '北京市',
        '12': '天津市',
        '31': '上海市',
        '50': '重庆市'
    }
    
    for city in cities:
        province_code = city['p_code']
        city_name = city['name']
        
        # 处理直辖市
        if province_code in direct_municipalities:
            city_to_province[city_name] = direct_municipalities[province_code]
            # 直辖市的名称本身也映射到直辖市
            city_to_province[direct_municipalities[province_code]] = direct_municipalities[province_code]
        else:
            # 普通省份
            province_name = province_code_to_name.get(province_code)
            if province_name:
                city_to_province[city_name] = province_name
    
    return city_to_province

# 全局变量存储映射关系
_CITY_PROVINCE_MAP = None

def get_province_by_city(city_name):

    global _CITY_PROVINCE_MAP
    
    if _CITY_PROVINCE_MAP is None:
        _CITY_PROVINCE_MAP = build_city_province_mapping()
    
    # 处理输入的城市名称
    city_name = city_name.strip()
    if not city_name.endswith('市'):
        city_name = f"{city_name}市"
    
    return _CITY_PROVINCE_MAP.get(city_name)



