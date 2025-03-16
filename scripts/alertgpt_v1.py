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
from alertbagpt_v1 import Alerinfotgpt
import time

class Alertgpt:
    def __init__(self, module, manual_control, prompt_path="../prompt/prompt.json",
                 dataset_path="../dataset/datasouce_alert.json"):
        self.gpt = GPTReply(model)
        self.graph_rag = ""
        self.prompt = alert_prompt()
        self.dataset_path = dataset_path
        self.manual_control = manual_control
        self.prompt_dic = self.load_json_file(prompt_path)
        self.factor_kag = Factor_Splitting()
        self.alerinfotgpt = Alerinfotgpt(self.gpt, False)
        self.lock = threading.Lock()

    @staticmethod
    def load_json_file(path):
        with open(path, "r") as f:
            return json.load(f)

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

    def info_continued_extractor(self, extract_object, traceability_data):
        traceability_data_result_tmp = self.gpt.getreply(
            self.prompt.extracotr_data_object_format_system,
            self.prompt.extracotr_data_object_format_user.format(extract_object),
            self.prompt.extracotr_data_object_format_user_2.format(traceability_data)
        )
        return traceability_data_result_tmp

    def alert_traceability_extraction_with_document(self, alert_traceability_data_type, traceability_data, manual_flag):
        """Handles alert traceability data extraction with centralized manual input handling (single-threaded version)."""

        def process_key(key):
            """Process a single key."""
            max_retry = 3  # 设置最大重试次数
            retry_count = 0
            traceability_data_result_tmp = None

            while retry_count < max_retry:
                try:
                    # 调用 GPT 获取结果
                    traceability_data_result_tmp = self.gpt.getreply(
                        self.prompt_dic['Alert_dataExtract_system'],
                        self.prompt_dic['Alert_dataExtract_user'].format(
                            str(key) + str(alert_traceability_data_type[key]),
                            str(traceability_data)
                        ),
                        ""
                    )
                    if "Hello," in traceability_data_result_tmp:
                        traceability_data_result_tmp = "NULL"
                    return key, traceability_data_result_tmp
                except Exception as e:
                    print(f"Error processing key {key} (retry {retry_count + 1}): {e}")
                    retry_count += 1

            # 如果重试次数用完，记录错误并返回 None
            print(f"Failed to process key {key} after {max_retry} retries.")
            return key, None

        traceability_data_result = {}

        # 单线程逐个处理 key
        for key in alert_traceability_data_type:
            try:
                key, result = process_key(key)
                if result is not None:
                    traceability_data_result[key] = result
                else:
                    # 如果结果为 None，表示处理失败，记录错误
                    print(f"Key {key} failed to process.")
            except Exception as e:
                print(f"Error processing key {key}: {e}")

        return traceability_data_result

    def get_alert_data(self, alert_id):
        """Fetches alert data from the dataset file based on the alert ID."""
        data = self.load_json_file(self.dataset_path)
        if alert_id:
            # 使用列表推导式过滤
            result = [item for item in data if str(item.get("alert_id")) == alert_id]

            # 如果找到匹配项，取出第一个
            if result:
                alert_data = result[0]  # 提取第一个匹配的元素
                alert_brief = alert_data.get('alert_ini_content', {}).get('mute_content_real', None)
                alert_ini_data = str(alert_data.get('ini_data', None))
                return alert_brief, alert_ini_data
        return None, None

    @staticmethod
    def extract_json_from_text(data):
        """Extracts JSON content from text if wrapped in ```json code blocks."""
        code_regexp_pattern = re.compile(r"```json\n(.*?)```", re.DOTALL)
        matches = re.findall(code_regexp_pattern, data)
        return matches[0] if matches else data

    @staticmethod
    def extract_code_from_text(data):
        """Extracts JSON content from text if wrapped in ```json code blocks."""
        code_regexp_pattern = re.compile(r"```python\n(.*?)```", re.DOTALL)
        matches = re.findall(code_regexp_pattern, data)
        return matches[0] if matches else data

    def alert_data_preprocessing(self, data):

        """
        making llm deciding the split method and generate the code
        :param data:
        :return:
        """
        TPL_RUN2 = """import base64
%s
print(split_text(\"\"\"%s\"\"\"))
        """

        def code_execution(code):
            with tempfile.NamedTemporaryFile(suffix=".py", delete=True, mode='w') as temp_file:
                temp_file.write(code)
                temp_file.flush()
                temp_file_path = temp_file.name
                # 使用subprocess来执行该代码文件
                try:
                    result = subprocess.run(
                        ["python", temp_file_path],
                        capture_output=True, text=True
                    )
                    test_result = result.stdout if result.returncode == 0 else result.stderr
                    return test_result
                except Exception as e:
                    raise f"Error executing file: {str(e)}"

        def data_splitter(document):
            while True:
                try:
                    split_function = self.extract_code_from_text(
                        self.gpt.getreply(self.prompt.traceability_split_methodgen_system,
                                          self.prompt.traceability_split_methodgen_user.format(len(document),
                                                                                               document[:300]),
                                          ""))
                    if "def split_text(" not in split_function:
                        continue
                    else:
                        split_result = eval(code_execution(TPL_RUN2 % (split_function, document)))
                        return split_result
                        # break
                except Exception as e:
                    print(e)
                    pass

        split_data = data_splitter(data)
        return split_data

    def calculate_final_result_one(self, alert_id, alert_brief, alert_ini_data):
        alert_result_tmp = {}
        no_count = 0
        total_count = 0
        try:
            # Process the suspicion item and get the result for all roles
            alert_result_tmp['1'] = self.process_alert_suspicion_item(
                alert_brief, alert_id, alert_ini_data
            )
            # print(f"[+]{suspicion_item['type']}\r\n", alert_result_tmp[suspicion_item['type']])

            # Count the "Yes" results from all roles
            for role_result in alert_result_tmp['1']['voting_result'].values():
                total_count += 1
                if role_result['Result'].upper() == 'No':
                    no_count += 1
        except Exception as e:
            print(e)
            pass

        # Determine the final result based on the count of "Yes"
        final_result = "No" if no_count > total_count / 2 else "Yes"

        # Add summary to the result
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_result_tmp,
            "traceability_data": alert_ini_data
        }

        return alert_result

    def nu_data_splited(self, data):
        null_data = {}
        eff_data = {}
        for key, value in data.items():
            if "NULL" in str(value).upper():
                null_data[key] = value
            else:
                eff_data[key] = value
        return null_data, eff_data

    def process_alert_suspicion_item(self, alert_brief, suspicion_item, alert_id, alert_ini_data):

        # def nu_data_splited(data):
        #     null_data = {}
        #     eff_data = {}
        #     for key,value in data.items():
        #         if "NULL" in value.upper():
        #             null_data[key] = value
        #         else:
        #             eff_data[key] = value
        #     return  null_data,eff_data

        """Processes each suspicion item to derive results and auxiliary data types.
        :param
        traceability_data_type: traceability data type which is needed for analysis
        """
        try:
            # 提取辅助数据类型
            traceability_data_type = self.extract_traceability_data_types(suspicion_item)
            # print("Auxiliary data types: %s", traceability_data_type)

            # splited_data = self.alert_data_preprocessing(alert_ini_data)
            traceability_data = alert_ini_data

            # 获取溯源数据内容
            null_data, alert_inidata = self.nu_data_splited(
                self.extract_traceability_data(traceability_data_type, alert_id, traceability_data))
            # with self.lock:
            null_data, eff_data = self.alerinfotgpt.external_info_process_t(alert_inidata, null_data,
                                                                            suspicion_item["description"],
                                                                            traceability_data)
            null_data, update_nulldata = self.nu_data_splited(null_data)
            eff_data.update(update_nulldata)
            if len(eff_data) == 0:
                eff_data = alert_ini_data

            # print("Initial data content: %s", alert_inidata)

            # 获取数据权重（可微调提升效果）
            # alert_score = self.calculate_data_weight(suspicion_item, traceability_data_type)
            # print("Data weight: %s", alert_score)
            #
            # # 打包数据
            # alert_packet = self.pack_data("","", alert_inidata)
            # print("Packed result: %s", alert_packet)

            # 计算最终结果
            calculate_result = self.calculate_final_result(alert_brief, suspicion_item, str(eff_data), null_data)
            # print(calculate_result)
            return calculate_result
        except Exception as e:
            print(e)

    def extract_alert_suspicion_item_localintel(self, alert_brief, suspicion_item, alert_id, alert_ini_data):
        """Processes each suspicion item to derive results and auxiliary data types.
        :param
        traceability_data_type: traceability data type which is needed for analysis
        """
        try:
            # 提取辅助数据类型
            traceability_data_type = self.extract_traceability_data_types(suspicion_item)
            # print("Auxiliary data types: %s", traceability_data_type)

            # splited_data = self.alert_data_preprocessing(alert_ini_data)
            traceability_data = alert_ini_data

            # 获取溯源数据内容
            null_data, alert_inidata = self.nu_data_splited(
                self.extract_traceability_data(traceability_data_type, alert_id, traceability_data))
            if alert_inidata=="":
                alert_inidata =  self.extract_traceability_data({"0":suspicion_item}, alert_id, traceability_data)

            restate_prompt = f"""
            Please help me summarize the following content so that it can be a logically coherent answer to this question:{suspicion_item}
            Note: Please do not leave out too many details
            """
            final_result = self.gpt.getreply(restate_prompt,str(alert_inidata),"")
            # with self.lock:
            # null_data, eff_data = self.alerinfotgpt.external_info_process_t(alert_inidata, null_data,
            #                                                                 suspicion_item["description"],
            #                                                                 traceability_data)
            # null_data, update_nulldata = self.nu_data_splited(null_data)
            # eff_data.update(update_nulldata)
            # if len(eff_data) == 0:
            #     eff_data = alert_ini_data

            # print(calculate_result)
            return final_result
        except Exception as e:
            print(e)

    def process_alert_suspicion_item_localintel(self, alert_brief, suspicion_item, alert_id, alert_ini_data):

        # def nu_data_splited(data):
        #     null_data = {}
        #     eff_data = {}
        #     for key,value in data.items():
        #         if "NULL" in value.upper():
        #             null_data[key] = value
        #         else:
        #             eff_data[key] = value
        #     return  null_data,eff_data

        """Processes each suspicion item to derive results and auxiliary data types.
        :param
        traceability_data_type: traceability data type which is needed for analysis
        """
        try:
            # 提取辅助数据类型
            # traceability_data_type = self.extract_traceability_data_types(suspicion_item)
            # print("Auxiliary data types: %s", traceability_data_type)
            #
            # # splited_data = self.alert_data_preprocessing(alert_ini_data)
            # traceability_data = alert_ini_data
            #
            # # 获取溯源数据内容
            # null_data, alert_inidata = self.nu_data_splited(
            #     self.extract_traceability_data(traceability_data_type, alert_id, traceability_data))
            # # with self.lock:
            # null_data, eff_data = self.alerinfotgpt.external_info_process_t(alert_inidata, null_data,
            #                                                                 suspicion_item["description"],
            #                                                                 traceability_data)
            # null_data, update_nulldata = self.nu_data_splited(null_data)
            # eff_data.update(update_nulldata)
            # if len(eff_data) == 0:
            #     eff_data = alert_ini_data

            eff_data = self.gpt.getreply("",self.prompt.generic_prompt+self.prompt.final_contextualized_completion_prompt+"null"+self.prompt.local_knowledge_addition_prompt+"Question:"+str(alert_ini_data)+"Answer：","")
            null_data = ""
            # print("Initial data content: %s", alert_inidata)

            # 获取数据权重（可微调提升效果）
            # alert_score = self.calculate_data_weight(suspicion_item, traceability_data_type)
            # print("Data weight: %s", alert_score)
            #
            # # 打包数据
            # alert_packet = self.pack_data("","", alert_inidata)
            # print("Packed result: %s", alert_packet)

            # 计算最终结果
            calculate_result = self.calculate_final_result(alert_brief, suspicion_item, str(eff_data), null_data)
            print(calculate_result)
            return calculate_result
        except Exception as e:
            print(e)

    def process_alert_suspicion_item_variant2(self, alert_brief, suspicion_item, alert_id, alert_ini_data):

        # def nu_data_splited(data):
        #     null_data = {}
        #     eff_data = {}
        #     for key,value in data.items():
        #         if "NULL" in value.upper():
        #             null_data[key] = value
        #         else:
        #             eff_data[key] = value
        #     return  null_data,eff_data

        """Processes each suspicion item to derive results and auxiliary data types.
        :param
        traceability_data_type: traceability data type which is needed for analysis
        """
        try:
            # 提取辅助数据类型
            traceability_data_type = self.extract_traceability_data_types(suspicion_item)
            # print("Auxiliary data types: %s", traceability_data_type)

            # splited_data = self.alert_data_preprocessing(alert_ini_data)
            traceability_data = alert_ini_data

            # 获取溯源数据内容
            null_data, alert_inidata = self.nu_data_splited(
                self.extract_traceability_data(traceability_data_type, alert_id, traceability_data))
            # with self.lock:
            null_data, eff_data = self.alerinfotgpt.external_info_process_t(alert_inidata, null_data,
                                                                            suspicion_item["description"],
                                                                            traceability_data)
            null_data, update_nulldata = self.nu_data_splited(null_data)
            eff_data.update(update_nulldata)

            # print("Initial data content: %s", alert_inidata)

            # 获取数据权重（可微调提升效果）
            # alert_score = self.calculate_data_weight(suspicion_item, traceability_data_type)
            # print("Data weight: %s", alert_score)
            #
            # # 打包数据
            # alert_packet = self.pack_data("","", alert_inidata)
            # print("Packed result: %s", alert_packet)

            # 计算最终结果
            tmp_result = {str(suspicion_item): str(eff_data)}
            # print(calculate_result)
            return tmp_result
        except Exception as e:
            print(e)

    def extract_traceability_data_types(self, suspicion_item):
        """Extracts auxiliary data types using GPT."""
        while True:
            try:
                return eval(self.extract_json_from_text(self.gpt.getreply(
                    self.prompt_dic['Alert_Selecter_system'],
                    self.prompt_dic['Alert_Selecter_user'].format(suspicion_item),
                    f"This is a knowledge base:{self.factor_kag.traceability_data}"
                )))
            except Exception as e:
                print(e)
                pass

    def extract_traceability_data(self, traceability_data_type, alert_id, traceability_data):
        """Extracts traceability data based on the auxiliary data types."""
        traceability_data = self.alert_traceability_extraction_with_document(traceability_data_type,
                                                                             traceability_data, False)
        # print("traceability_data")
        # Check the traceability data and requirements
        return traceability_data

    def check_for_traceaility_data(self, traceability_data, traceability_data_type):
        """
        check the traceability data and requirements，if traceability data not satisfied with the traceability data,
        require manual data entry.
        :param traceability_data:
        :param traceability_data_type:
        :return: manual data result
        """
        check_result = self.gpt.getreply(self.prompt_dic['Alert_traceability_data_check_system'],
                                         self.prompt_dic['Alert_traceability_data_check_user'].format(
                                             str(traceability_data), str(traceability_data_type)),
                                         ""
                                         )
        if "Yes" in check_result:
            return True
        else:
            return check_result

    def calculate_data_weight(self, suspicion_item, traceability_data_type):
        """Calculates the weight of data based on suspicion item and auxiliary data types."""
        return self.gpt.getreply(
            self.prompt_dic['Alert_Score_system'],
            self.prompt_dic['Alert_Score_user'].format(suspicion_item),
            self.prompt_dic['Alert_Score_user2'].format(traceability_data_type)
        )

    def pack_data(self, suspicion_item, alert_score, alert_inidata):
        """Packages data into a format suitable for further processing."""
        return self.gpt.getreply(
            self.prompt_dic['Alert_packet_system'],
            self.prompt_dic['Alert_packet_user'].format(suspicion_item, alert_score),
            self.prompt_dic['Alert_packet_user2'].format(alert_inidata)
        )

        # return alert_result

    def calculate_final_result(self, alert_brief, suspicion_item, alert_packet, null_data):
        try:
            """Calculates the final result based on the alert packet using a for loop."""
            role_template = {
                "Security_Operations_Expert": "As a security operations expert, you are skilled at analyzing alarms generated by situational awareness equipment. ",
                "Senior_Red_Team_Expert": "As a senior red team expert, your role is to think like an attacker. Analyze the raw data and determine whether the alarm matches known penetration tactics or adversarial behavior. Focus on identifying patterns of exploitation, privilege escalation, or persistence techniques that suggest a potential compromise.",
                "Ordinary_IT_Workers": "You are an IT professional. This alarm comes from the computer you work on. Determine if the behavior in question could result from routine activities, legitimate user actions, or potential misconfigurations that align with your work practices."
            }

            alert_score_result_with_role = {}

            def process_role(role, template):
                """Process a single role and store the result."""
                result = {}
                if len(alert_packet) != 0:
                    reason = self.gpt.getreply(
                        template + self.prompt_dic['Alert_resultCal_system_1'],
                        self.prompt_dic['Alert_resultCal_user'].format(alert_packet),
                        self.prompt_dic['Alert_resultCal_user2']
                    )
                    if "NULL" == reason.upper():
                        judge_result = "unsure"
                    elif "HELLO" in reason.upper():
                        reason = str(alert_packet)
                        judge_result = self.gpt.getreply(
                            self.prompt_dic['Alert_result_judge_system'],
                            "This is the alert that you need to judge" + alert_brief + "\n" + str(reason),
                            "This is a knowledge_base" + self.prompt.knowledge_base
                        )
                    else:
                        judge_result = self.gpt.getreply(
                            self.prompt_dic['Alert_result_judge_system'],
                            "This is the alert that you need to judge" + alert_brief + "\n" + str(reason),
                            "This is a knowledge_base" + self.prompt.knowledge_base
                        )
                    if "YES" in judge_result.upper():
                        result['Result'] = "Yes"
                        result['Reason'] = reason
                        result['raw_result'] = judge_result
                    elif "NO" in judge_result.upper() and "UNSURE" not in judge_result.upper():
                        result['Result'] = "No"
                        result['Reason'] = reason
                        result['raw_result'] = judge_result
                    else:
                        result['Result'] = "unsure"
                        result['Reason'] = reason
                        result['raw_result'] = judge_result
                else:
                    result['Result'] = "unsure"
                    result['Reason'] = "NULL"
                alert_score_result_with_role[role] = result

            # Process each role sequentially using a for loop
            for role, template in role_template.items():
                process_role(role, template)

            final_result = suspicion_item
            final_result['voting_result'] = alert_score_result_with_role
            final_result['alert_packet'] = alert_packet
            final_result['null_data'] = null_data
            return final_result
        except Exception as e:
            print("calculate_final_result error", e)

    def calculate_final_result_variant2(self, alert_brief, suspicion_item, alert_packet, null_data):
        """Calculates the final result based on the alert packet using a for loop."""
        role_template = {
            "variant2": "",
        }

        alert_score_result_with_role = {}

        def process_role(role, template):
            """Process a single role and store the result."""
            result = {}
            if len(alert_packet) != 0:
                # reason = self.gpt.getreply(
                #     template + self.prompt_dic['Alert_resultCal_system_1'],
                #     self.prompt_dic['Alert_resultCal_user'].format(alert_packet),
                #     self.prompt_dic['Alert_resultCal_user2']
                # )
                # if "NULL" == reason.upper():
                #     judge_result = "unsure"
                # else:
                judge_result = self.gpt.getreply(
                    template + self.prompt_dic['Alert_result_judge_system'],
                    "This is the alert that you need to judge" + alert_brief + "\n" + str(alert_packet),
                    ""
                )
                if "YES" in judge_result.upper():
                    result['Result'] = "Yes"
                    result['Reason'] = alert_packet
                elif "NO" in judge_result.upper() and "UNSURE" not in judge_result.upper():
                    result['Result'] = "No"
                    result['Reason'] = alert_packet
                else:
                    result['Result'] = "unsure"
                    result['Reason'] = alert_packet
            else:
                result['Result'] = "unsure"
                result['Reason'] = "NULL"
            alert_score_result_with_role[role] = result

        # Process each role sequentially using a for loop
        for role, template in role_template.items():
            process_role(role, template)

        final_result = suspicion_item
        final_result['voting_result'] = alert_score_result_with_role
        final_result['alert_packet'] = alert_packet
        final_result['null_data'] = null_data
        return final_result

    def format_check(self, suspicion_item, alert_score_result):
        try:
            result = eval(self.extract_json_from_text(self.gpt.getreply(
                """Please help me modify the content to the correct JSON format and output it in the following format:
    ```json
    {
    "type": String,
    "score" Float,
    "description":String,
    "voting_result":{
    "Security_Operations_Expert":{'Result':String(yes or no),'Reason':String},
    "Senior_Red_Team_Expert":{'Result':String(yes or no),'Reason':String},
    "Ordinary_IT_Workers":{'Result':String(yes or no),'Reason':String}
    }
    }
    ```
                """,
                str(suspicion_item) + str(alert_score_result),
                ""
            )))
            # print("[+]",result)
            return result
        except Exception as e:
            print(e)

    def update_calculate_result(self, alert_updaet_result, alert_ini_data):
        """处理警报怀疑项并确定最终结果。"""
        alert_result_tmp = {}
        no_count = 0
        total_count = 0
        while True:
            try:
                # 处理怀疑项并获取所有角色的结果
                # 统计所有角色的 "Yes" 结果
                for key, value in alert_updaet_result.items():
                    for role_result in value['voting_result'].values():
                        if role_result['Result'].upper() == 'UNSURE':
                            continue
                        total_count += 1
                        if role_result['Result'].upper() == 'NO':
                            no_count += 1
                break
            except Exception as e:
                print(e)
                pass

        # 根据 "Yes" 的数量确定最终结果
        if total_count <= 2:
            final_result = "Unsure"
        else:
            final_result = "No" if no_count > total_count / 2 else "Yes"

        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_updaet_result,
            "traceability_data": alert_ini_data
        }

        return alert_result

    def calculate_final_result_splited(self, alert_brief, alert_id, alert_suspicion_tree, alert_ini_data):
        """处理警报怀疑项并确定最终结果。"""
        alert_result_tmp = {}
        no_count = 0
        total_count = 0

        for suspicion_item in alert_suspicion_tree.values():
            while True:
                try:
                    # 处理怀疑项并获取所有角色的结果
                    alert_result_tmp[suspicion_item['type']] = self.process_alert_suspicion_item(
                        alert_brief, suspicion_item, alert_id, alert_ini_data
                    )
                    # 统计所有角色的 "Yes" 结果
                    for role_result in alert_result_tmp[suspicion_item['type']]['voting_result'].values():
                        if role_result['Result'].upper() == 'UNSURE':
                            continue
                        total_count += 1
                        if role_result['Result'].upper() == 'NO':
                            no_count += 1
                    break
                except Exception as e:
                    print(e)
                    pass

        # 根据 "Yes" 的数量确定最终结果
        if total_count <= 2:
            final_result = "Unsure"
        else:
            final_result = "No" if no_count > total_count / 2 else "Yes"

        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_result_tmp,
            "traceability_data": alert_ini_data,
            "alert_brief": alert_brief
        }

        return alert_result

    def calculate_final_result_splited_localintel(self, alert_brief, alert_id, alert_suspicion_tree, alert_ini_data):
        """处理警报怀疑项并确定最终结果。"""
        alert_result_tmp = {}
        no_count = 0
        total_count = 0

        for suspicion_item in alert_suspicion_tree.values():
            while True:
                try:
                    # 处理怀疑项并获取所有角色的结果
                    alert_result_tmp[suspicion_item['type']] = self.process_alert_suspicion_item_localintel(
                        alert_brief, suspicion_item, alert_id, alert_ini_data
                    )
                    # 统计所有角色的 "Yes" 结果
                    for role_result in alert_result_tmp[suspicion_item['type']]['voting_result'].values():
                        if role_result['Result'].upper() == 'UNSURE':
                            continue
                        total_count += 1
                        if role_result['Result'].upper() == 'NO':
                            no_count += 1
                    break
                except Exception as e:
                    print(e)
                    pass

        # 根据 "Yes" 的数量确定最终结果
        if total_count <= 2:
            final_result = "Unsure"
        else:
            final_result = "No" if no_count > total_count / 2 else "Yes"

        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_result_tmp,
            "traceability_data": alert_ini_data,
            "alert_brief": alert_brief
        }

        return alert_result

    def calculate_final_result_splited_variant2(self, alert_brief, alert_id, alert_suspicion_tree, alert_ini_data):
        """处理警报怀疑项并确定最终结果。"""
        alert_result_tmp = {}
        no_count = 0
        total_count = 0

        for suspicion_item in alert_suspicion_tree.values():
            while True:
                try:
                    # 处理怀疑项并获取所有角色的结果
                    alert_result_tmp[suspicion_item['type']] = self.process_alert_suspicion_item_variant2(
                        alert_brief, suspicion_item, alert_id, alert_ini_data
                    )
                    break
                except Exception as e:
                    print(e)
                    pass
        result = {}
        alert_score_result_with_role = {}
        final_result = {}
        judge_result = self.gpt.getreply(
            self.prompt_dic['Alert_result_judge_system'],
            "This is the alert that you need to judge" + str(alert_result_tmp),
            ""
        )
        if "YES" in judge_result.upper():
            result['Result'] = "Yes"
            result['Reason'] = str(alert_result_tmp)
            result['raw_result'] = judge_result
        elif "NO" in judge_result.upper():
            result['Result'] = "No"
            result['Reason'] = str(alert_result_tmp)
            result['raw_result'] = judge_result
        else:
            result['Result'] = "unsure"
            result['Reason'] = str(alert_result_tmp)
            result['raw_result'] = judge_result
        alert_score_result_with_role["variant2"] = result

        # final_result = suspicion_item
        final_result['voting_result'] = alert_score_result_with_role
        # final_result['alert_packet'] = alert_packet
        # final_result['null_data'] = null_data

        # 添加摘要到结果中
        alert_result = {
            "Final Result": result['Result'],
            "No Count": no_count,
            "Total Count": total_count,
            "Details": alert_score_result_with_role,
            "traceability_data": alert_ini_data,
            "alert_brief": alert_brief
        }

        return alert_result

    def variant1(self, alert_id, alert_brief, alert_ini_data):
        """处理警报数据并生成结果的主方法。
        这是variant1：缺少原子化分析策略
        """

        alert_suspicion_tree = eval(self.extract_json_from_text(self.gpt.getreply(
            self.prompt_dic['Alert_tree_system'],
            self.prompt_dic['Alert_tree_user'].format(alert_brief),
            self.prompt_dic['Alert_tree_user2'].format(self.factor_kag)
        )))

        alert_result = {}
        alert_result[alert_id] = self.calculate_final_result_splited(alert_brief, alert_id, alert_suspicion_tree,
                                                                     alert_ini_data)
        return alert_result

    def variant2(self, alert_id, alert_brief, alert_ini_data):
        """
        这是variant2，没有第二个溯源的
        :param alert_id:
        :param alert_brief:
        :param alert_ini_data:
        :return:
        """
        extract_behavioral_entity = self.gpt.getreply(
            self.prompt_dic['Alert_behavioral_entity_system'],
            alert_brief,
            ""
        )
        if "Hello" in extract_behavioral_entity:
            extract_behavioral_entity = alert_brief
        total_count = 0
        no_count = 0
        suspicion_item = {}
        eff_data = alert_ini_data
        null_data = {}
        # alert_result_tmp = {}
        calculate_result = self.calculate_final_result(extract_behavioral_entity, suspicion_item, eff_data, null_data)
        try:
            for role_result in calculate_result['voting_result'].values():
                if role_result['Result'].upper() == 'UNSURE':
                    continue
                total_count += 1
                if role_result['Result'].upper() == 'NO':
                    no_count += 1
        except Exception as e:
            print(e)
            pass

        # 根据 "Yes" 的数量确定最终结果
        if total_count <= 2:
            final_result = "Unsure"
        else:
            final_result = "No" if no_count > total_count / 2 else "Yes"

        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": calculate_result,
            "traceability_data": alert_ini_data,
            "alert_brief": alert_brief
        }
        new_alert_result = {}
        new_alert_result[alert_id] = alert_result

        return new_alert_result

    def variant3(self, alert_id, alert_brief, alert_ini_data):
        """
        这是variant3，没有第三个步骤的
        :param alert_id:
        :param alert_brief:
        :param alert_ini_data:
        :return:
        """
        extract_behavioral_entity = self.gpt.getreply(
            self.prompt_dic['Alert_behavioral_entity_system'],
            alert_brief,
            ""
        )
        if "Hello" in extract_behavioral_entity:
            extract_behavioral_entity = alert_brief
        alert_suspicion_tree = eval(self.extract_json_from_text(self.gpt.getreply(
            self.prompt_dic['Alert_tree_system'],
            self.prompt_dic['Alert_tree_user'].format(extract_behavioral_entity),
            self.prompt_dic['Alert_tree_user2'].format(self.factor_kag)
        )))

        alert_result = {}
        alert_result[alert_id] = self.calculate_final_result_splited_variant2(extract_behavioral_entity, alert_id,
                                                                              alert_suspicion_tree,
                                                                              alert_ini_data)

        return alert_result

    def main_process(self, alert_id, alert_brief, alert_ini_data):
        """
        完整版
        :param alert_id:
        :param alert_brief:
        :param alert_ini_data:
        :return:
        """
        import time
        time1 = time.time()
        extract_behavioral_entity = self.gpt.getreply(
            self.prompt_dic['Alert_behavioral_entity_system'],
            alert_brief,
            ""
        )
        if "Hello" in extract_behavioral_entity:
            extract_behavioral_entity = alert_brief

        alert_suspicion_tree = eval(self.extract_json_from_text(self.gpt.getreply(
            self.prompt_dic['Alert_tree_system'],
            self.prompt_dic['Alert_tree_user'].format(extract_behavioral_entity),
            # self.prompt_dic['Alert_tree_user2'].format(self.factor_kag)
            ""
        )))

        alert_result = {}
        alert_result[alert_id] = self.calculate_final_result_splited(extract_behavioral_entity, alert_id,
                                                                     alert_suspicion_tree,
                                                                     alert_ini_data)

        total_input_tokens, total_output_tokens = self.gpt.get_total_tokens()
        total_cost =  self.gpt.get_total_cost()
        print(f"Total input tokens: {alert_id}:{total_input_tokens}")
        print(f"Total output tokens: {alert_id}:{total_output_tokens}")
        print(f"Total cost: {alert_id}: ${total_cost:.6f}")
        print(f"time,{alert_id}:",time.time() - time1)
        return alert_result

    def localIntel_process(self,alert_id, alert_brief, alert_ini_data):
        extract_behavioral_entity = self.gpt.getreply(
            self.prompt_dic['Alert_behavioral_entity_system'],
            alert_brief,
            ""
        )
        if "Hello" in extract_behavioral_entity:
            extract_behavioral_entity = alert_brief

        total_count = 0
        no_count = 0
        suspicion_item = {}
        null_data = {}
        eff_data = self.gpt.getreply("",
                                     self.prompt.generic_prompt + self.prompt.final_contextualized_completion_prompt + "null" + self.prompt.local_knowledge_addition_prompt + "Question: Try to extract information about" + str(
                                         alert_ini_data) + "Answer：", "")

        calculate_result = self.calculate_final_result(extract_behavioral_entity, suspicion_item, eff_data, null_data)
        try:
            for role_result in calculate_result['voting_result'].values():
                if role_result['Result'].upper() == 'UNSURE':
                    continue
                total_count += 1
                if role_result['Result'].upper() == 'NO':
                    no_count += 1
        except Exception as e:
            print(e)
            pass

        # 根据 "Yes" 的数量确定最终结果
        if total_count <= 2:
            final_result = "Unsure"
        else:
            final_result = "No" if no_count > total_count / 2 else "Yes"

        # 添加摘要到结果中
        alert_result = {
            "Final Result": final_result,
            "No Count": no_count,
            "Total Count": total_count,
            "Details": calculate_result,
            "traceability_data": alert_ini_data,
            "alert_brief": alert_brief
        }
        new_alert_result = {}
        new_alert_result[alert_id] = alert_result

        return new_alert_result


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
            json.dump(existing_data, f, indent=4, ensure_ascii=False)


def process_alert(i, data, filename, exec_type):
    """处理单个警报任务。"""
    while True:
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
            if exec_type == "main":
                result = alertgpt.main_process(alert_id, alert_brief, alert_ini_data)
                print(f"[+]{alert_id}", result)
            elif exec_type == "variant1":
                result = alertgpt.variant1(alert_id, alert_brief, alert_ini_data)
                print(f"[+]{alert_id}", result)
            elif exec_type == "variant2":
                result = alertgpt.variant2(alert_id, alert_brief, alert_ini_data)
                print(f"[+]{alert_id}", result)
            elif exec_type == "variant3":
                result = alertgpt.variant3(alert_id, alert_brief, alert_ini_data)
                print(f"[+]{alert_id}", result)
            elif exec_type == "localIntel":
                result = alertgpt.localIntel_process(alert_id, alert_brief, alert_ini_data)
                print(f"[+]{alert_id}", result)

            # 保存结果到文件
            save_result_to_file(result, filename)
            break
        except Exception as e:
            print(result)
            print(f"[-] Alert ID {alert_id} 失败: {e},retry again")


def test_baseprompt_multithreaded(modle, exec_type, benchmark_type):
    """多线程测试基础提示。"""
    if benchmark_type == "google_Siem":
        # 加载数据
        data = load_json_file(f"../dataset/case.json")
        # 设置文件名
        filename = f"../cache/{modle}/alert_results_{benchmark_type}_combined_unique_data_{exec_type}_case.json"
    elif benchmark_type == "Ngids":
        data = load_json_file(f"../dataset/NGIDS_DS_1000_modified.json")
        # 设置文件名
        filename = f"../cache/{modle}/alert_results_{benchmark_type}_combined_unique_data_{exec_type}_fp.json"

    # 设置线程数

    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(process_alert, i, data, filename, exec_type) for i in range(0,1)]
        for future in concurrent.futures.as_completed(futures):
            # 可选：处理 future 的结果或异常
            pass


# # # # 初始化 Alertgpt 实例
model = "gpt-4o-mini"
alertgpt = Alertgpt(model, False)
#
import time
time1 = time.time()
for exec_type_item in ["main"]:
    # print(f"Process ID: {os.getpid()}")
    # # 运行多线程测试
    test_baseprompt_multithreaded(model, exec_type_item, "google_Siem")
print(time.time()-time1)
