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
    pass

if __name__ == "__main__":
    main()
