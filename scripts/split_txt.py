from collections import defaultdict
import json
import re
def count_keys_by_level(data, level=0, key_count=defaultdict(int)):
    """递归统计 JSON 数据每层的键名数量"""
    # 如果是字典，遍历并统计键名数量
    if isinstance(data, dict):
        key_count[level] += len(data)  # 当前层级的键名数量
        for value in data.values():
            count_keys_by_level(value, level + 1, key_count)  # 递归调用处理字典的值
    # 如果是列表，遍历列表中的每个字典项
    elif isinstance(data, list):
        for item in data:
            count_keys_by_level(item, level, key_count)  # 保持在当前层级处理列表中的项
    return key_count


def build_json_tree(data, level=0):
    """递归构建 JSON 数据的键名树，返回树形结构字符串"""
    tree_str = ""  # 用来存储最终的树形结构字符串

    # 如果是字典，遍历并处理键名
    if isinstance(data, dict):
        for key, value in data.items():
            tree_str += "  " * level + f"Level {level}: {key}\n"
            # 递归调用并将树形结构拼接到字符串中
            tree_str += build_json_tree(value, level + 1)

    # 如果是列表，遍历并处理每个字典项
    elif isinstance(data, list):
        for index, item in enumerate(data):
            tree_str += "  " * level + f"Level {level}: [Item {index}]\n"
            # 递归调用并将树形结构拼接到字符串中
            tree_str += build_json_tree(item, level + 1)

    return tree_str


def analyze_tree_structure(tree_str):
    """分析树形结构的字符串，统计每层级的键名数量，并记录每层级的唯一键名"""
    level_counts = {}

    # 正则表达式匹配每个Level {number}结构
    pattern = re.compile(r'Level (\d+):')

    # 分割输入字符串按行
    data = tree_str.split("\n")

    # 用于跟踪当前的层级
    current_level = -1
    stack = []

    for line in data:
        # 去除前后的空格
        line = line.strip()
        if not line:
            continue  # 如果是空行，跳过

        # 查找符合层级格式的部分
        match = pattern.search(line)

        if match:
            level = int(match.group(1))  # 获取匹配到的层级数字
            key_name = line.split(":")[1].strip()  # 获取键名部分

            # 更新每个层级的信息，使用 set 保证键名唯一
            if level not in level_counts:
                level_counts[level] = {"count": 0, "keys": set()}  # 使用 set 保证唯一

            level_counts[level]["keys"].add(key_name)  # 自动去重
            level_counts[level]["count"] = len(level_counts[level]["keys"])  # 更新计数

            # 更新当前层级
            current_level = level
            stack.append(level)

    return level_counts


def group_data_by_level(data, level):
    """
    根据给定的层级进行分组分析
    :param data: 输入的JSON数据
    :param level: 目标分组的层级
    :return: 按层级分组后的数据
    """
    grouped_data = defaultdict(list)

    # 根据当前层级递归遍历数据
    def recursive_group(data, current_level, current_key):
        if current_level == level:
            # 按当前层级的键分组数据
            grouped_data[current_key].append(data)
            return
        if isinstance(data, dict):
            for key, value in data.items():
                recursive_group(value, current_level + 1, key)
        elif isinstance(data, list):
            for item in data:
                recursive_group(item, current_level + 1, current_key)

    recursive_group(data, 0, None)
    return grouped_data


def group_json_data(sample_json, level=1):
    """
    按指定层级分组分析输入的JSON数据
    :param sample_json: 输入的 JSON 数据
    :param level: 要分组的层级，默认为1
    :return: 分组后的 JSON 数据
    """
    # 将输入的 JSON 字符串解析成 Python 数据结构
    data = sample_json

    # 按层级分组数据
    grouped_data = group_data_by_level(data, level)

    # 将分组后的数据转换为 JSON 字符串并返回
    return json.dumps(grouped_data, indent=4)

def load_json_file(path):
    with open(path, "r") as f:
        return json.load(f)
sample_json= load_json_file("../dataset/datasouce_alert.json")[0]['ini_data']
# 统计 JSON 键名树各层的键名数量
json_tree_str = build_json_tree(sample_json)
print(json_tree_str)
# 输出 JSON 键名树
level_counts = analyze_tree_structure(json_tree_str)

# 输出各层级的键名数量
print("Level counts:")
for level in sorted(level_counts.keys()):
    print(f"Level {level}: {level_counts[level]} keys")

# grouped_result = group_json_data(sample_json, level=3)
# print(grouped_result)