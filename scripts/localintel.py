import json
import os
import pandas as pd
from datasets import Dataset
# from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import AnswerSimilarity
import re
import concurrent.futures
import time
import json

ground_truth_file_path = '/cache/LocalIntel_GPT_4o_mini_chainsentry_Dataset.xlsx'
df = pd.read_excel(ground_truth_file_path)
gpt_4o_completions = list(df['gpt_4o_mini'])
# for i in range(0,len(gpt_4o_completions)):
    # print()
all_data = []
for i in range(0,len(gpt_4o_completions)):
    try:
        # 使用 eval 将字符串转化为字典
        # data = json.loads(completion.replace("'", "\""))
        data = eval(gpt_4o_completions[i].strip())
        # print(data)
        # if isinstance(data, dict):
        all_data.extend(data.items())  # 将字典的键值对添加到列表中
        # else:
        #     print(f"Skipping non-dictionary data: {data}")
    except Exception as e:
        # 如果转换失败，打印错误信息
        print(f"Error: {e}")

# 按照键名排序
sorted_data = dict(sorted(all_data, key=lambda item: int(item[0])))

# 提取键值并存储到新的列表中
values_list = list(sorted_data.values())
ground_truth_list = list(df['Ground_truth'])
gpt_4o_mini_completions = values_list
prediction_list = gpt_4o_mini_completions
with open("/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/baseline/geval/prompts/summeval/con_detailed.txt", "r") as f:
    prompt_template = f.read()
# 存储 G-Eval 评估结果
new_json = []
ct, ignore = 0, 0
from openai import OpenAI
client = OpenAI(api_key="sk-zJGvkmuoGr2ai5gX7d4bEb6627304cC7851801F9483c8709", base_url="https://open.xiaojingai.com/v1")

def process_instance(i):
    source = ground_truth_list[i]  # Ground Truth 作为 Source Document
    system_output = prediction_list[i]  # 预测摘要

    cur_prompt = prompt_template.replace('{{Document}}', source).replace('{{Summary}}', system_output)

    instance = {"index": i, "prompt": cur_prompt}
    all_responses = []

    max_retries = 5  # 最大重试次数
    for runtime in range(20):  # 生成 20 个评分
        retries = 0
        while retries < max_retries:
            try:
                _response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": cur_prompt}],
                    temperature=0,
                    stop=None,
                )
                result = _response.choices[0].message.content
                all_responses.append(result)
                break  # 成功后跳出 while 循环
            except Exception as e:
                print(f"Error for index {i}, attempt {retries+1}: {e}")
                if "limit" in str(e).lower():
                    time.sleep(2 ** retries)  # 指数退避等待
                    retries += 1
                else:
                    break  # 其他错误直接跳过

    instance['all_responses'] = all_responses
    return instance

# 运行多线程任务
new_json = []
max_threads = 10  # 可调整线程数
with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
    futures = {executor.submit(process_instance, i): i for i in range(len(prediction_list))}
    for future in concurrent.futures.as_completed(futures):
        try:
            result = future.result()
            new_json.append(result)
        except Exception as e:
            print(f"Thread error: {e}")

# 保存为 JSON
with open("../cache/chainsentry_gpt_4o_mini_results.json", "w") as f:
    json.dump(new_json, f, indent=4)


# import re

# import re
print(new_json)
def extract_numeric_scores(response_list):
    """
    从 `response_list` 中提取数字部分，过滤掉乱码和无关字符。
    """
    valid_scores = []
    for response in response_list:
        # 使用正则表达式提取所有数字部分（包括整数和小数）
        numbers = re.findall(r"-?\d+\.?\d*", str(response))
        if numbers:
            # 将提取的数字转换为浮点数
            for num in numbers:
                try:
                    valid_scores.append(float(num))
                except ValueError:
                    continue  # 如果转换失败，跳过
    return valid_scores

# 处理 `all_responses`，确保只包含数值
for item in new_json:
    item["filtered_responses"] = extract_numeric_scores(item["all_responses"])

g_eval_scores = [sum(map(float, item["all_responses"])) / len(item["all_responses"]) if item["all_responses"] else 0 for item in new_json]
print(g_eval_scores)