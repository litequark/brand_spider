# 使用`location_translator`模块进行中英转换

```python
from util.location_translator import get_en_city, get_en_province

# 获取城市英文名
english_city = get_en_city("上海市")  # 返回 "Shanghai"

# 获取省份英文名
english_province = get_en_province("湖南省")  # 返回 "Hunan"
```

如果模块未找到该行政单位的英文名，会返回原始中文字符串。

注意：传入的字符串必须是行政单位的全称（包括“省”“市”等）。