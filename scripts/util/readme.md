# `Util`：实用工具

## `location_translator`：行政单位名称中英转换

`location_translator`模块提供了两个函数：`get_en_city`和`get_en_province`，用于将中文的城市和省份名称转换为英文名称。

### 导入方法

```python
from util.location_translator import get_en_city, get_en_province
```

### 示例用法

```python
# 获取城市英文名
english_city = get_en_city("上海市")  # 返回 "Shanghai"

# 获取省份英文名
english_province = get_en_province("湖南省")  # 返回 "Hunan"
```

只要字符串参数为某个行政单位中文全称的子串，模块就返回其英文名。

```python
# 获取城市英文名
english_city = get_en_city("上海")  # 返回 "Shanghai"

# 获取省份英文名
english_province = get_en_province("湖南")  # 返回 "Hunan"
```

如果模块未找到该行政单位的英文名，会返回原始中文字符串。例如：

```python
english_city = get_en_city("城市")  # 返回 "城市"
english_province = get_en_province("湖蓝")  # 返回 "湖蓝"
```
