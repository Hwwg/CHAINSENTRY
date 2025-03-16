import base64
import os
from typing import Any, Union

from tools.gpt_con import GPTReply
import json
import logging
import re
import pandas as pd
from prompt.prompt_v1 import alert_prompt
import subprocess
import tempfile
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from KAG.item_splited import Factor_Splitting
import ana_tools.vt_search as vt_tool


class compareprompt:
    def __init__(self, module, manual_control,prompt_path="../prompt/prompt.json", dataset_path="../dataset/datasouce_alert.json"):
        self.gpt = GPTReply(module)
        self.graph_rag = ""
        self.prompt=alert_prompt()
        self.prompt_dic = self.load_json_file(prompt_path)
        self.dataset_path = dataset_path
        self.manual_control = manual_control
        self.prompt_dic = self.load_json_file(prompt_path)
        self.factor_kag = Factor_Splitting()

    @staticmethod
    def load_json_file(path):
        with open(path, "r") as f:
            return json.load(f)


    def calculate_final_result_splited(self, alert_brief, alert_id, alert_ini_data,exec_type):
        """处理警报怀疑项并确定最终结果。"""
        alert_result_tmp = {}
        no_count = 0
        total_count = 0
        final_result_tmp =""
        while True:
            if exec_type == "SOC_l1":
                prompt = "Analyze the following alert"
                infer_result = self.gpt.getreply("",
                                                  prompt+str(alert_brief)+str(alert_ini_data),
                                                  "")
                final_result = self.gpt.getreply("Based on the analysis results, please determine whether the alarm has risks. If so, please output \"Yes\", otherwise, please output \"No\"",
                                                  infer_result,
                                                  "")
            elif exec_type=="cot":
                final_result = self.gpt.getreply(self.prompt_dic["Alert_cot_system"],
                                                 str(alert_brief) + str(
                                                     alert_ini_data),
                                                 "")
            elif exec_type=="prompt":
                final_result = self.gpt.getreply(self.prompt_dic["Alert_prompt_system"],
                                                 str(alert_brief) + str(
                                                     alert_ini_data),
                                                 "")
            if "Hello" in final_result:
                pass
            else:
                break

        if "YES" in final_result.upper():
            final_result_tmp="Yes"
        elif "YES" not in final_result.upper() and "NO" in final_result.upper():
            final_result_tmp="No"
        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result_tmp,
            "Raw Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_result_tmp,
            "traceability_data": alert_ini_data,
            "alert_brief":alert_brief
        }
        print(alert_result)
        return alert_result

    def main_process(self, alert_id, alert_brief, alert_ini_data,exec_type):
        """处理警报数据并生成结果的主方法。"""

        alert_result = {}
        alert_result[alert_id] = self.calculate_final_result_splited(alert_brief,
                                                                     alert_id,
                                                                     alert_ini_data,exec_type)
        return alert_result



file_lock = threading.Lock()

def load_json_file(path):
    """加载 JSON 文件。"""
    with open(path, "r") as f:
        return json.load(f)

def save_result_to_file(result, filename):
    """将结果追加写入文件。"""
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # 使用锁来确保线程安全
    with file_lock:
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
            json.dump(existing_data, f, indent=4,ensure_ascii=False)

def process_alert(i, data, filename,exec_type):
    """处理单个警报任务。"""
    try:
        alert_id = str(i)
        alert_brief = data[alert_id]['alert_brief']
        alert_ini_data = data[alert_id]['ini_data']

        # 检查文件是否已包含该 alert_id
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}
            if alert_id in existing_data:
                print(f"任务 {alert_id} 已存在，跳过执行")
                return

        # 执行任务

        result = alertgpt.main_process(alert_id, alert_brief, alert_ini_data,exec_type)
        print(f"[+]{alert_id}", result)

        # 保存结果到文件
        save_result_to_file(result, filename)
    except Exception as e:
        print(f"[-] Alert ID {alert_id} 失败: {e}")

def test_baseprompt_multithreaded(modle, exec_type, benchmark_type):
    """多线程测试基础提示。"""
    if benchmark_type == "google_Siem":
        # 加载数据
        data = load_json_file(f"../dataset/combined_unique_data_fp.json")

        # 设置文件名
        filename = f"../cache/{modle}/alert_results_{benchmark_type}_combined_unique_data_{exec_type}_fp.json"
    elif benchmark_type == "Ngids":
        data = load_json_file(f"../dataset/NGIDS_DS_1000_modified.json")
        # 设置文件名
        filename = f"../cache/{modle}/alert_results_{benchmark_type}_combined_unique_data_{exec_type}_fp.json"

    # 设置线程数

    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_alert, i, data, filename, exec_type) for i in range(0, 500)]
        for future in concurrent.futures.as_completed(futures):
            # 可选：处理 future 的结果或异常
            pass

# # 初始化 Alertgpt 实例
model_name=["gpt-4o"]
for model_item in model_name:
    alertgpt = compareprompt(model_item,False)
    # # 运行多线程测试
    test_baseprompt_multithreaded(model_item,"cot","Ngids")