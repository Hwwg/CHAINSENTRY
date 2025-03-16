"""
首先判断日志类型、然后确定提取模板
"""
import re
import subprocess
import tempfile

from tools.gpt_con import GPTReply
from prompt.log_prompt import logtoolPrompt
from evalplus.sanitize import sanitize

class LogTools:
    def __init__(self,module):
        self.gpt = GPTReply(module)
        self.graph_rag = ""
        self.prompt = logtoolPrompt()

    @staticmethod
    def extract_code_from_text(data):
        """Extracts JSON content from text if wrapped in ```json code blocks."""
        code_regexp_pattern = re.compile(r"```python\n(.*?)```", re.DOTALL)
        matches = re.findall(code_regexp_pattern, data)
        return matches[0] if matches else data


    def code_execution(self,code,log_content):
        code_template = """import re
%s
print(log_analysis(\"\"\"%s\"\"\"))
        """

        code =code_template % (code, log_content)
        with tempfile.NamedTemporaryFile(suffix=".py", delete=True, mode='w') as temp_file:
            temp_file.write(code)
            temp_file.flush()
            temp_file_path = temp_file.name
        # 使用subprocess来执行该代码文件
            try:
                result = subprocess.run(
                    ["python", temp_file_path],
                    capture_output=True, text=True,timeout=30
                )
                test_result = result.stdout if result.returncode == 0 else result.stderr
                if "Error" in test_result:
                    return test_result
                else:
                    return test_result
            except Exception as e:
                return f"The script took too long to execute"

    def long_content_analysis(self):
        pass

    def log_result_analysis(self,log_type,script_result,analysis_aim,script_code):
        log_result = self.gpt.getreply(self.prompt.log_result_analysis_system.format(log_type,analysis_aim),script_code,script_result[:200])
        return log_result

    def log_analysis(self,log_type,log_content,analysis_aim):
        log_strategies = "当前是第一次判断，因此没有历史判断内容"
        result_analysis = "当前是第一次判断，因此没有历史判断内容"
        script_code = ""
        while True:
            log_strategies = self.gpt.getreply(self.prompt.log_analysis.format(log_type,analysis_aim),
                                                self.prompt.log_analysis_user.format(log_content[:100],log_strategies+"\n"+script_code,result_analysis),
                                               "")
            log_script_code = self.gpt.getreply(self.prompt.log_script_code.format(log_type,analysis_aim),
                                                self.prompt.log_script_code_user.format(log_strategies),
                                                "")
            script_code = sanitize(log_script_code,entry_point="log_analysis")
            code_result =self.code_execution(script_code,log_content)
            print("code_result",code_result)
            result_analysis = self.log_result_analysis(log_type,code_result,analysis_aim,script_code)
            if "YES" in result_analysis.upper():
                break
        print(result_analysis+"\r\n"+"原始脚本输出:\r\n"+code_result)
        return result_analysis+code_result


    def log_process(self,log_contents,analysis_aim):
        """
        1.分析日志类型
        2.确定
        :return:
        """
        log_type_analysis = self.gpt.getreply(self.prompt.log_type,log_contents.split("\n")[1],"")

        log_analysis_result = self.log_analysis(log_type_analysis,log_contents,analysis_aim)

        return log_analysis_result

with open("../../dataset/auth.log.1","r") as f:
    data =f.read()
logtools = LogTools("gpt-4o-mini")
logtools.log_process(data,"")


