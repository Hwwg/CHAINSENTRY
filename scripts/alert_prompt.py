from tools.gpt_con import GPTReply
import json
# import pandas as pd

# 替换下面的文件路径为你的Excel文件的实际路径
file_path = '../dataset/测试集.xlsx'

# 使用pandas的read_excel函数读取数据
# 这里假设你的Excel文件中的数据在第一个sheet上
# data = pd.read_excel(file_path)
gpt = GPTReply("gpt-4o")
# 显示数据的前几行以确认内容
# print(data.columns)
# i = 10


def load_json_file(path):
    with open(path, "r") as f:
        return json.load(f)
"""Fetches alert data from the dataset file based on the alert ID."""
data = load_json_file("../dataset/datasouce_alert.json")
result_fail = []
def test_baseprompt():
    for i in range(100,180):
        try:
            alert_brief = data[i]['alert_ini_content']['mute_content_real']
            alert_ini_data = str(data[i]['ini_data'])
            print(alert_brief)


            alert_data = str(alert_brief) + str(alert_ini_data)
            # print( str(data['description'][i]) )
            # print(alert_data)

            Alert_inidatatype_extraction = gpt.getreply(
                "Please determine if the alert is a false positive. Output only in the format: {'Yes': 'Reason'} or {'No': 'Reason'}.",
                alert_data,
                ""
            )
            print("[+]",Alert_inidatatype_extraction)
        except:
            result_fail.append(i)
test_baseprompt()