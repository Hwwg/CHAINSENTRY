import json

def load_json_file(path):
    with open(path, "r") as f:
        return json.load(f)
data = load_json_file("../dataset/datasouce_alert.json")

def ini_data_formated():
    data = load_json_file("../dataset/datasouce_alert.json")
    result = {}
    fialed_result = []
    for i in range(0,200):
        try:
            result[i] = {}
            # alert_brief = data[i]['alert_ini_content']['mute_content_real']
            # alert_ini_data = data[i]['ini_data']
            result[i]['alert_brief'] = data[i]['alert_ini_content']['event_data']['description']
            result[i]['ini_data'] = data[i]['alert_ini_content']['event_data']['message'].split("<br>----------------------------")[2]
        except:
            try:
                result[i]['alert_brief'] =  data[i]['alert_ini_content']['mute_content_real']
                result[i]['ini_data'] =data[i]['alert_ini_content']['event_data']['message'].split("<br>----------------------------")[2]
            except:
                fialed_result.append(i)
            pass
    print(fialed_result)

    with open("../dataset/datasouce_alert_formated_.json","w+") as f:
        f.write(json.dumps(result,indent=4,ensure_ascii=False))


def traceability_data_formated():
    data = load_json_file("../dataset/datasouce_alert_formated.json")

    print(data['0']['ini_data'].keys())


def get_json_keys_tree(data, parent_key=""):
    tree = {}

    # 如果当前是字典类型
    if isinstance(data, dict):
        for key, value in data.items():
            # 拼接父键名，构建树
            new_key = f"{parent_key}.{key}" if parent_key else key
            tree[new_key] = get_json_keys_tree(value, new_key)

    # 如果当前是列表类型
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{parent_key}[{i}]"
            tree[new_key] = get_json_keys_tree(item, new_key)

    # 其他类型的数据可以直接返回空树或一个基本结构
    else:
        tree[parent_key] = None

    return tree
# data = load_json_file("../dataset/datasouce_alert_formated.json")['0']

def remove_empty_keys(d):
    """
    递归地移除字典中所有值为空的键。
    参数:
    - d: 需要处理的字典
    返回:
    - 清除空值后的字典
    """
    if isinstance(d, dict):  # 如果是字典
        # 递归移除空值
        d = {k: remove_empty_keys(v) for k, v in d.items() if v not in [None, '', [], {}, 0] and (not isinstance(v, dict) or v)}
        return {k: v for k, v in d.items() if v not in [None, '', [], {}, 0]}  # 移除最终的空字典
    elif isinstance(d, list):  # 如果是列表
        return [remove_empty_keys(v) for v in d if v not in [None, '', [], {}, 0]]
    else:
        return d


import openai
import json
from tools import gpt_con

def extract_paths_and_values(data, prefix="", results=None):
    """
    递归提取 JSON 数据中的所有端到端路径及其对应的值。
    :param data: JSON 数据
    :param prefix: 当前路径前缀
    :param results: 存储路径和值的列表
    :return: 包含所有路径和值的列表
    """
    if results is None:
        results = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            extract_paths_and_values(value, new_prefix, results)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            new_prefix = f"{prefix}[{index}]"
            extract_paths_and_values(item, new_prefix, results)
    else:
        # 格式化路径和值为自然语言描述
        results.append(f"{prefix} => 值: {data}")
    # print(results[-1])
    return results

def query_large_model(query, paths_with_values):
    """
    使用大模型根据用户的查询对 JSON 路径和值进行语义匹配。
    :param query: 用户的查询字符串
    :param paths_with_values: 提取的路径和值列表
    :return: 大模型返回的最相关路径和值
    """

    prompt = (
            f"请根据以下用户的查询，找出最相关的 JSON 数据路径及其对应的值。\n\n"
            f"用户查询: \"{query}\"\n\n"
            f"JSON 数据路径及对应值列表:\n"
            + "\n".join(paths_with_values)
            + "\n\n"
              "请返回最相关的路径及其对应的值，按照以下格式输出：\n"
              "1. 路径: xxx => 值: xxx\n"
              "2. 路径: xxx => 值: xxx\n"
              "..."
    )

    # 调用 OpenAI GPT API
    result = gptreply.getreply("你是一个专业的数据分析助手。", prompt, "")

    # 提取并返回大模型的回答
    return result

def main():
    # 加载 JSON 数据
    def load_json_file(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    data = load_json_file("../dataset/datasouce_alert.json")
    json_data = remove_empty_keys(data[2]['ini_data'])['data']['data']

    traceability_data_item=json_data[len(json_data)-1]
    # 提取所有路径和值
    print(traceability_data_item)
    paths_with_values = extract_paths_and_values(traceability_data_item['process'])
    # print(paths_with_values)
    # 用户查询关键词
    query = "进程调用链"
    print(f"用户查询: {query}\n")

    # 使用大模型进行语义匹配
    results = query_large_model(query, paths_with_values)

    # 输出结果
    print("最相关的路径及对应值:")
    print(results)

if __name__ == "__main__":
    gptreply = gpt_con.GPTReply("gpt-4o")
    ini_data_formated()