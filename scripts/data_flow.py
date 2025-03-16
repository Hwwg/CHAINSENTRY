from tools.gpt_con import GPTReply
import json
import re
import shlex
import subprocess

with open("/dataset/wrong_data/converted_data_with_is_safe.json", "r") as f:
    data = json.load(f)

Gptreply = GPTReply("gpt-4o-mini")

prompt = """
请你作为一个名专业wireshark使用者，帮我生成用于在`NGIDS.pcap`中提取以下ip的tshark命令:
```bash
<code>
```
"""
user_prompt = """
这是要提取的ip地址：{}
"""
with open("/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/scripts/dns_log.txt","r") as f:
    other_info = f.read()
code_regexp_pattern = re.compile(r"```bash\n(.*?)```", re.DOTALL)
# matches = re.findall(code_regexp_pattern, data)
for key,value in data.items():
    tmp_result = {}
    # tmp_result[key] = value
    # while True:
    #     wireshark_command_raw = Gptreply.getreply(prompt,user_prompt.format(value['ini_data']),"")
    #     if "```bash" not in wireshark_command_raw:
    #         pass
    #     else:
    #         break
    # matches = re.findall(code_regexp_pattern, wireshark_command_raw)
    # wireshark_command = matches[0] if matches else data
    # command_list = shlex.split(wireshark_command)
    # result = subprocess.run(command_list, capture_output=True, text=True)
    # print(result.stdout)
    # print(result.stdout)
    # data[key]['wireshark_flow_command'] = wireshark_command
    data[key]['ini_data'] = other_info
    # data[key]['wireshark_flow'] = result.stdout+result.stdout
    # tmp_result[key]['wireshark_flow_command'] = wireshark_command
    # tmp_result[key]['wireshark_flow'] = result.stdout+result.stdout
    # with open("/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/dataset/converted_data_with_data_flow.jsonl","a+") as f:
    #     json.dump(tmp_result, f, ensure_ascii=False)
    #     f.write("\n")  # 每条数据换行，确保 JSON 对象分隔

with open("/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/dataset/converted_data_with_new_ini_data.json","w") as f:
    data = json.dump(data, f, indent=4,ensure_ascii=False)
