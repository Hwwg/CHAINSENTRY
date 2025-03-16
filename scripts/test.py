import pandas as pd
from tools.gpt_con import GPTReply
from scripts.alertgpt_v1 import Alertgpt
generic_prompt = """
You are a helpful honest assistant and you answer questions based only on the information that is given to you.
You do not add anything in your answer that is not instructed to you. 
If you cannot answer you simply say you do not know the answer. 
"""
local_knowledge_retrieval_query_prompt = """\n
Question: """
final_contextualized_completion_prompt = """
Given the following global_knowledge that is threat or vulnerability report retrieved from the internet relevant for the question and
current infrastructure details of running applications such as used dependencies, used libraries, used version and use case of that dependency in the application as local_knowledge.
Answer the question from the information provided in global_knowledge and local_knowledge.
Do not add anything that is not given in the global_knowledge or local_knowledge. 
Only include answer without mentioning its information source. 
If there is no relation between the global_knowledge and the local_knowledge, or you cannot understand the context,
then you say more information is required to answer the question, while mentioning what information is required. 

global_knowledge: 
"""
local_knowledge_addition_prompt = """\n
local_knowledge:
"""
eval_dataset_file_path = "/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/baseline/LocalIntel/data/evaluation/LocalIntel_Eval_Dataset.xlsx"
eval_df = pd.read_excel(eval_dataset_file_path)
eval_df = eval_df.drop([37, 27, 26])
eval_df.describe()
questions = list(eval_df['Questions'])
global_knowledge = list(eval_df['Global_Knowledge'])
local_knowledge = list(eval_df['Local_knowledge'])
ground_truth = list(eval_df['Ground_truth'])
final_eval_list = []
def get_final_contextualization_prompt(global_knowledge_str: str, local_knowledge: str, query: str) \
        -> str:
    # global_knowledge_str = '\n'.join([x for x in global_knowledge])
    final_prompt = (generic_prompt + final_contextualized_completion_prompt + global_knowledge_str
                    + local_knowledge_addition_prompt + local_knowledge + local_knowledge_retrieval_query_prompt
                    + query + "\n\nAnswer: ")
    return final_prompt
for i in range(len(questions)):
    test_case_dict = {
        'question': questions[i],
        'global_knowledge': global_knowledge[i],
        'local_knowledge': local_knowledge[i],
        'ground_truth': ground_truth[i],
        'input_prompt': get_final_contextualization_prompt(global_knowledge[i], local_knowledge[i], questions[i])
    }

    final_eval_list.append(test_case_dict)

model = "gpt-4o-mini"
GptReply = GPTReply(model)
alertgpt = Alertgpt(model, False)
completions = []
import concurrent.futures

def process_prompt(prompt,num):
    try:
        result = alertgpt.extract_alert_suspicion_item_localintel(
            "", prompt["question"], "", prompt["global_knowledge"] + prompt["local_knowledge"]
        )
        # print(result)
        return str({num:result})
    except Exception as e:
        print(f"Error occurred: {e} for Prompt: {prompt}")
        return "Error Occurred!"
def process_prompt_directly(prompt,num):
    try:
        result = GptReply.getreply("",prompt["input_prompt"],"")
        # print(result)
        return str({num:result})
    except Exception as e:
        print(f"Error occurred: {e} for Prompt: {prompt}")
        return "Error Occurred!"

# completions = []

# 设定线程数
# num_threads = 1 # 线程数不超过任务数

with concurrent.futures.ThreadPoolExecutor() as executor:
    # 提交所有任务
    future_to_prompt = {executor.submit(process_prompt_directly, final_eval_list[num],num): num for num in range(0,len(final_eval_list))}

    # 获取结果
    for future in concurrent.futures.as_completed(future_to_prompt):
        completions.append(future.result())

print("All tasks completed.")
# sorted_results = sorted(completions, key=lambda x: list(x.keys())[0])  # 按照 num 排序

# eval_df['gpt_4o'] = [list(item.values())[0] for item in sorted_results]
# len(completions)
eval_df['gpt_4o_mini'] = completions
eval_df.describe()
gpt_35_completion_file_path = "../cache/LocalIntel_gpt_4o_mini_Dataset.xlsx"
eval_df.to_excel(gpt_35_completion_file_path)