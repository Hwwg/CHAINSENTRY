import base64
import os
from typing import Any, Union

from tools.gpt_con import GPTReply
import json
import logging
import re
import pandas as pd
from prompt.prompt_v1 import ana_info
import subprocess
import tempfile
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from KAG.item_splited import Factor_Splitting
import ana_tools.vt_search as vt_tool
from ana_tools.budocument_retrieval import Doretrieval


# from alertgpt_v1 import Alertgpt

class Alerinfotgpt:
    def __init__(self, newgpt, manual_control, prompt_path="../prompt/prompt.json",
                 dataset_path="../dataset/datasouce_alert.json"):
        self.gpt = newgpt
        self.graph_rag = ""
        self.prompt = ana_info()
        self.dataset_path = dataset_path
        self.manual_control = manual_control
        self.prompt_dic = self.load_json_file(prompt_path)
        self.factor_kag = Factor_Splitting()
        # self.alertgpt_test = Alertgpt(module,False)
        self.filelock = threading.Lock()
        self.doret = Doretrieval("gpt-4o-mini", "../dataset/document.txt")
        self.lock = threading.Lock()

    @staticmethod
    def load_json_file(path):
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def extract_json_from_text(data):
        """Extracts JSON content from text if wrapped in ```json code blocks."""
        if "NULL" in str(data).upper():
            return "NULL"
        code_regexp_pattern = re.compile(r"```json(.*?)```", re.DOTALL)
        matches = re.findall(code_regexp_pattern, data)
        return matches[0] if matches else data

    def find_key_in_json(self, data, target_key):
        result = []
        if isinstance(data, dict):
            for key, value in data.items():
                if key == target_key:
                    result.append(value)
                elif isinstance(value, (dict, list)):
                    result.extend(self.find_key_in_json(value, target_key))
        elif isinstance(data, list):
            for item in data:
                result.extend(self.find_key_in_json(item, target_key))
        return result

    def extract_method(self, data_type, task_description, alert_ini_data):
        ex_method = self.gpt.getreply(self.prompt.extract_method_system,
                                      self.prompt.extract_method_user.format(task_description, data_type,
                                                                             alert_ini_data),
                                      self.prompt.extract_method_user2)
        return ex_method

    def extract_tools(self, extract_method):
        result = {}

        try:
            if extract_method['method'] == "vt":
                if extract_method['data_type'] == "file":
                    for i in extract_method['value']:
                        result[f'file_reputation'] = vt_tool.file_info(i)
                elif extract_method['data_type'] == "url":
                    for i in extract_method['value']:
                        result[f'url_reputation'] = vt_tool.url_info(i)
                elif extract_method['data_type'] == "ip":
                    for i in extract_method['value']:
                        result[f'url_reputation'] = vt_tool.url_info(i)
            elif extract_method['data_type'] == "search":
                for i in extract_method['value']:
                    result[f'document_value'] = self.doret.info_retrieval_process(i)
                    # result[f'document_value'] = "NULL"
                    # print("result",result)
                    if result[f'document_value'] == "":
                        result = "NULL"
            return result
        except Exception as e:
            print(e)
            raise RuntimeError

    def new_traceability_data_extract(self, data_type, task_description, alert_ini_data):
        while True:
            try:
                extract_method = self.extract_method(data_type, task_description, alert_ini_data)
                # print("new_traceability_data_extract0",extract_method)
                formated_extract_method = self.extract_json_from_text(extract_method)
                flag = 0
                # print("new_traceability_data_extract",formated_extract_method)
                # for extract_method_item in formated_extract_method:
                flag += 1
                if "NULL" == formated_extract_method:
                    return "NULL"
                else:
                    extract_method = json.loads(formated_extract_method)
                extract_result = self.extract_tools(extract_method)
                # print("new_traceability_data_extract_specific")
                # print("new_traceability_data_extrac3")
                return extract_result
            except Exception as e:
                print(e)

    def external_info_process(self, eff_data, null_data, data, key):
        """
        data应该是完整的溯源数据,需要做的事：
        判断缺少的信息，然后选择获取的方式，VT or 微步在线，接下来补充以后，在进行一次判断
        :param data:
        :return:
        """
        # 1.提取出为null的data，然后尝试从外部获取信息填充，并进行再次判断
        # null_data = {}
        # for key,value in data["Details"].items():
        # null_data = data["Details"][key]["null_data"]

        task_description = data["Details"][key]["description"]
        for data_type in null_data.keys():
            # print("ew_traceability_data_extract1")
            new_traceability_data = self.new_traceability_data_extract(data_type, task_description,
                                                                       data["traceability_data"])
            null_data[data_type] = new_traceability_data
        for data_type in eff_data.keys():
            # print("ew_traceability_data_extract2")
            new_traceability_data = self.new_traceability_data_extract(data_type, task_description,
                                                                       data["traceability_data"])
            eff_data[data_type] += "\r\n" + str(new_traceability_data)
        return null_data, eff_data

    def external_info_process_t(self, eff_data, null_data, task_description, traceability_data):

        for data_type in null_data.keys():
            # print("new_traceability_data_extract")
            new_traceability_data = self.new_traceability_data_extract(data_type, task_description,
                                                                       traceability_data)
            null_data[data_type] = new_traceability_data

        for data_type in eff_data.keys():
            new_traceability_data = self.new_traceability_data_extract(data_type, task_description,
                                                                       traceability_data)
            eff_data[data_type] += "\r\n" + str(new_traceability_data)

        return null_data, eff_data

    # def update_alert_status(self,data):
    #     new_calculate_result = {}
    #     for key,value in data["Details"].items():
    #         null_data = data["Details"][key]["null_data"]
    #         eff_data = data["Details"][key]["alert_packet"]
    #
    #         new_calculate_result[key] = data["Details"][key]
    #         update_null_data,update_eff_data = self.external_info_process(eff_data,null_data, data, key)
    #         # 还是去除仍未null的数据，避免影响判断
    #         null_data, update_eff_data_from_null = self.alertgpt_test.nu_data_splited(update_null_data)
    #         update_eff_data.update(update_eff_data_from_null)
    #         new_calculate_result[key] = self.alertgpt_test.calculate_final_result(data["alert_brief"],{key:value['description']},update_eff_data,"")
    #     update_result = self.alertgpt_test.update_calculate_result(new_calculate_result,data["traceability_data"])
    #     # print(update_result)
    #
    #     return update_result

    def update_new_results_to_file(self, filename, result):
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # 使用锁来确保线程安全
        with self.filelock:
            # 如果文件存在，先读取内容
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = {}
            else:
                existing_data = {}

            # 更新现有数据
            existing_data.update(result)

            # 写入更新后的数据
            with open(filename, "w") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)

    def ana_process(self, data, filename, key):
        """处理警报数据并生成结果的主方法。"""
        alert_result = {}
        alert_result[key] = self.update_alert_status(data)
        print(alert_result)
        self.update_new_results_to_file(filename, alert_result)


def load_json_file(path):
    """加载 JSON 文件。"""
    with open(path, "r") as f:
        return json.load(f)


filelock = threading.Lock()


def worker(alertinfogpt_obj, data, out_file, key):
    # key="20"
    """工作线程的主要逻辑。"""
    with filelock:
        try:
            # 检查目标文件中是否已有该 key
            with open(out_file, "r") as f:
                existing_data = json.load(f)
            if key in existing_data:
                # print(f"Key '{key}' 已存在，跳过处理。")
                return
        except Exception as e:
            print(e)
            # 如果文件不存在，则直接进行处理
            return f"error in {key}"

        # 如果 key 不存在，进行处理
        try:
            alertinfogpt_obj.ana_process(data, out_file, key)
        except Exception as e:
            print(e, key)

        return key

# if __name__ == "__main__":
#     # 加载数据
#     test_data = load_json_file("../cache/alert_results_combined_unique_data_fp.json")
#     alertinfogpt = Alerinfotgpt("deepseek-coder", False)
#
#     # 创建线程池，设置最大线程数为 10
#     out_file = "../cache/gpt-4o-mini/alert_results_combined_unique_data_fp_new.json"
#     # worker(alertinfogpt, test_data['168'], out_file, '168')
#     if not os.path.exists(out_file):
#         print(f"文件 '{out_file}' 不存在，创建新文件。")
#         with open(out_file, "w") as f:
#             json.dump({}, f)  # 初始化为空 JSON 对象
#
#     with ThreadPoolExecutor(max_workers=20) as executor:
#         futures = []
#         for key in test_data.keys():
#             futures.append(executor.submit(worker, alertinfogpt, test_data[key], out_file, key))
#
#         # 等待所有任务完成
#         for future in as_completed(futures):
#             try:
#                 result = future.result()  # 获取任务返回值
#                 # print(f"Task completed with result: {result}")
#             except Exception as e:
#                 print(f"Task failed with exception: {e}")
#
#     print("所有任务已提交，线程池已关闭。")
