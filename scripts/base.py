from tools.gpt_con import GPTReply

class base_gpt:
    def __init__(self,module):
        self.gpt = GPTReply(module)

    #用来打包要发送的数据
    def messages_package(self):
        return None

    def main_process(self,dataset):
        # result = self.gpt.getreply(self.messages_package())
        pass