import re
import subprocess
import tempfile
import threading

from tools.gpt_con import GPTReply
from prompt.log_prompt import document_retrieval
from evalplus.sanitize import sanitize

class Doretrieval:
    def __init__(self,module,filename):
        self.gpt = GPTReply(module)
        self.graph_rag = ""
        self.prompt = document_retrieval()
        self.document = self.op_file(filename)
        self.lock = threading.Lock()

    def op_file(self,filename):
        with open(filename,"r") as f:
            return f.read()
    def document_splited(self, document_content):
        """
        将文档内容按段落分割。
        """
        # 根据换行符分割文档内容为段落
        document_list = document_content.split("\n\n")  # 假设段落之间有两个换行符
        # 去除每个段落的首尾空格，并过滤空段落
        return [paragraph.strip() for paragraph in document_list if paragraph.strip()]

    def info_retrieval_process(self,search_aim):
        with self.lock:
            document_list = self.document_splited(self.document)
            summrise_result = ""
            for do_item in document_list:
                search_result = self.gpt.getreply(self.prompt.content_search.format(search_aim),self.prompt.content_search_user.format(do_item),"")
                if "NULL" in search_result.upper():
                    pass
                else:
                    summrise_result+=search_result+"\r\n"
            return summrise_result
