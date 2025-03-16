class logtoolPrompt:
    log_type:str = """
    作为一名专业的网络安全应急响应专家，请你基于该log日志分析其所属类型，例如apache、mysql等，并直接返回类型即可
    """

    log_analysis:str = """
    作为一名专业的网络安全应急响应专家，你擅长分析{}类型的日志，接下来请你撰写判断策略判断该日志是否存在{}内容。关于判断策略你需要注意以下内容：
    请尽可能写清楚判断的策略，例如使用什么正则表达式提取什么，目的是为了判断什么。
    """

    log_analysis_user:str = """
    这是部分日志内容:{}
    这是你之前的判断策略和执行脚本：{}
    这是之前判断策略的输出:{}
    """


    log_script_code:str = """
     作为一名专业的网络安全应急响应专家，你擅长分析{}类型的日志，接下来请你基于以下策略撰写python脚本判断该日志是否存在{}内容，并按照如下格式返回:
     entry point function is : def log_analysis(content):
     ```python
     def log_analysis(content):
        <code>
        return result 
     ```
    """

    log_script_code_user:str = """
    这是你需要转为脚本的策略:{}
    """

    log_result_analysis_system:str = """
     作为一名专业的网络安全应急响应专家，你擅长分析{}类型的日志.接下来我将给你发送部分分析的结果以及执行脚本，请step by step分析执行结果,确保该执行脚本以及执行策略能够不存在逻辑错误后，判断此脚本是否获取到了正确的信息:{}
     如果获取到了该信息，请返回"Yes"，否则返回"No"
     并按照以下格式返回:
     1.Yes/No
     1.该日志脚本分析了是否存在.....具体的代码是:....
     2.分析结果表明......
    
    """

class document_retrieval:
    content_search:str = """
    作为一名专业的网络安全溯源数据分析专家，请帮我找到有关:{}的任何内容，如果未找到，请直接返回"NULL".
    请注意，你在检索文本的过程中，只需要进行模糊匹配，返回任何与上述目的中的主语相关的内容即可。
    """
    content_search_user:str = """
    This is the content:{}
    """
