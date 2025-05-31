import os
from bs4 import BeautifulSoup

import requests

RESULT_FIELDS = ["省", "Province", "市", "City", "区", "店名", "类型", "地址", "电话", "备注"]
DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # 进入子目录
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output/yokohoma.csv")


def main():
    api = 'https://www.yokohama.com.cn/api/get_comp'

    # 构造请求头和请求体

    payload = ("{\r\n    \"view\": \"Check\",\r\n    \"compId\": \"c_outlets_list_003-1693299992595\","
               "\r\n    \"params\": \"{\\\"size\\\":2000,\\\"query\\\":[{\\\"valueName\\\":\\\"\\\","
               "\\\"dataType\\\":\\\"number\\\",\\\"operator\\\":\\\"eq\\\","
               "\\\"filter\\\":\\\"ignore-empty-check\\\",\\\"esField\\\":\\\"CID\\\",\\\"groupName\\\":\\\"数据展示条件,"
               "默认条件组\\\",\\\"groupEnd\\\":\\\"2,1\\\",\\\"field\\\":\\\"CID\\\",\\\"sourceType\\\":\\\"page\\\","
               "\\\"logic\\\":\\\"and\\\",\\\"groupBegin\\\":\\\"1,2\\\",\\\"fieldType\\\":\\\"number\\\"}],"
               "\\\"header\\\":{\\\"Data-Query-Es-Field\\\":\\\"DETAIL_ES.es_symbol_text_l4B1um48,"
               "DETAIL_ES.es_symbol_address_420l30H3allAddress,DETAIL_ES.es_symbol_text_7eE767rS,"
               "DETAIL_ES.es_multi_address_420l30H3tencentMap,DETAIL_ES.es_multi_image_T328TCK7,"
               "DETAIL_ES.es_float_zdlcm\\\",\\\"Data-Query-Random\\\":0,\\\"Data-Query-Field\\\":\\\"text_l4B1um48,"
               "address_420l30H3allAddress,text_7eE767rS,address_420l30H3tencentMap,image_T328TCK7,zdlcm\\\"},"
               "\\\"from\\\":0,\\\"sort\\\":[]}\"\r\n}")
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'instance': 'NGC202308040001',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Accept': 'text/html, */*; q=0.01',
        'DNT': '1',
        'Content-Type': 'application/json;charset=UTF-8',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'host': 'www.yokohama.com.cn'
    }

    try:
        response = requests.post(api, headers=headers, data=payload)
        response.raise_for_status()
        soup_response = BeautifulSoup(response.text, 'html.parser')
        soup_dealers = soup_response.select('div.e_container-32.s_layout > div')
        print(1)
    except requests.exceptions.RequestException as e:
        print(e)
        exit(1)

if __name__ == "__main__":
    main()
