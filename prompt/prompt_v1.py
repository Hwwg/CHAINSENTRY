class alert_prompt:

    traceability_split_methodgen_system:str = """
    As a professional alert event traceability data processor, please generate a Python code snippet to process the following format of traceability data. First, you need to determine the format of the data in the document, and then generate the corresponding Python code for data processing.
    The objectives for the Python code are as follows:
    - Ensure that the semantics of the original traceability data are preserved during the segmentation process. Do not split critical data such as filenames, process names, etc.
    - Under the above conditions, make the segmented traceability data as short as possible.
    - The segmentation result should be a List.
    - If the sample data provided is not in a standard JSON format, declare that the text is not JSON-formatted data and do not process it using JSON.
    Please output the Python code for splitting traceability data in the following format:
    ```python
    def split_text(document):
    {code}
        return List[String(Segmented data segments)]
    ```
    """
    traceability_split_methodgen_user:str = """
    This is the length of the document: {}
    Here is a sample of the document for reference: {}
    """

    alert_description_system:str = """
    As a professional security operations engineer, please provide a detailed analysis of the alert brief, including:
    1. Parsing of all key terms.
    """

    alert_description_user:str = """
    Here is the alert brief that needs to be analyzed: {}
    """

    alert_traceability_restatement_system:str = """
    As a professional security alert data analyst, you need to infer the semantics of the following data and rewrite it to make it narrative content to improve its readability. The following data is the original source data of the SIEM platform alert. Since the traceability data is long, please analyze the meaning of each sentence step by step. To ensure the coherence of the rewritten results, I will provide you with the previously rewritten data. But you only need to output the rewritten results for the current data.
    """

    alert_traceability_restatement_user:str = """
    This is the data that needs to be rephrased: {}
    This is the previously rephrased content: {}
    """

    alert_traceability_combine_system:str = """
    As a professional security operations engineer, here are multiple segments of alert traceability data. Please combine these segments into a coherent and information-dense traceability data report. You do not need to elaborate on the alert-related content; just focus on the runtime state of the target machine.
    """
    alert_traceability_combine_user:str = """
    Here are multiple segments of alert traceability data: {}
    """

    alert_judge_datatype_system:str = """
    As a professional security operations engineer, you are skilled at analyzing alert events and determining the type of traceability data required for analysis. Based on the following alert brief, please identify the type of traceability data required and form a basic reasoning chain. For example:
    - Threat intelligence of a specific file: Requires obtaining threat intelligence of xxx file.
    - Complete process of xx: Requires obtaining the complete process of xx to determine xxx.
    """

    alert_judge_datatype_user:str = """
    Here is the alert brief and description that needs to be analyzed: {}
    """
    # If the complete process of xx does not include any other malicious software or malicious command execution-related processes, and the file threat intelligence executed in the process indicates that the file is reputable, the alert can be preliminarily determined to be a false positive.
    alert_judgedata_extraction_system:str = """
    As a professional security operations engineer, please extract the required data types from the traceability data content.
    """

    alert_judgedata_extraction_user:str = """
    These are the required traceability data: {}
    These are the contents of all traceability data: {}
    """

    alert_inferchain_system:str = """
    As a professional security operations engineer, please form a correct and logically rigorous reasoning chain based on the following traceability data content to determine whether the alert poses a security risk.
    """

    alert_inferchain_user: str = """
    Here is the alert event content: {}
    Here is the traceability data content: {}
    """

    alert_result_judge_system:str = """
    As a professional security operations engineer, please determine whether the alert is a false positive based on the following alert event analysis evidence and reasoning chain. If it is a false positive, output "Yes"; otherwise, output "No".
    """

    alert_result_judge_user:str = """
    Here is the alert event content: {}    
    Here is the reasoning evidence chain: {}
    """

    semantic_proofreading_system:str = """
    As a professional security operation alarm handling expert, please help me check whether the following content contains some information related to traceability data. If it does, please output "Yes", if not, please output "No"
    """

    semantic_proofreading_user: str = """
    This is the traceability data:{}
    """

    extracotr_data_object_format_system:str = """
    Please extract the corresponding data from the original data based on the extracted object content requirements and return it in one of the following different type format:
    1.file type:
    ```json
    {
    "file":str("md5 of file")
    }
    ```
    2.url type:
    ```json
    {
    "url":str("the url like http://xxxxx")
    }
    3.others:
    ```json
    {"Unkonwn":"1"}
    ```
    """

    extracotr_data_object_format_user:str = """
    The object from which data needs to be extracted:{}
    """

    extracotr_data_object_format_user_2: str = """
    This is the original data:{}
    """
    knowledge_base:str = """
    When the following behaviors are clearly shown in the context of the alert information, there is a security risk:
1. The file reputation is marked as suspicious
2. The IP address is a public IP and is marked as suspicious
3. The domain name is marked as suspicious
4. The executed command involves obtaining permissions and crawling sensitive data
    """

    generic_prompt: str = """
        You are a helpful honest assistant and you answer questions based only on the information that is given to you.
    You do not add anything in your answer that is not instructed to you. 
    If you cannot answer you simply say you do not know the answer. 
        """

    final_contextualized_completion_prompt: str = """
        Given the following global_knowledge that is threat or vulnerability report retrieved from the internet relevant for the question and
    current infrastructure details of running applications such as used dependencies, used libraries, used version and use case of that dependency in the application as local_knowledge.
    Answer the question from the information provided in global_knowledge and local_knowledge.
    Do not add anything that is not given in the global_knowledge or local_knowledge. 
    Only include answer without mentioning its information source. 
    If there is no relation between the global_knowledge and the local_knowledge, or you cannot understand the context,
    then you say more information is required to answer the question, while mentioning what information is required. 

    global_knowledge: 
        """

    local_knowledge_addition_prompt: str = """\n
        local_knowledge:
        """



class ana_info:
    extract_method_system:str = """
    As a professional network security intrusion alarm analysis expert, please determine the specific acquisition method based on the following data types and return them in the format specified in the knowledge base.
    If there is no matching tool in the knowledge base, return ```NULL``` directly
    """

    extract_method_user:str = """
    This is the alert description:{}
    This is the type of data that needs to be analyzed:{}
    This is the traceability data :{}
    """

    extract_method_user2:str = """
    This is the knowledge base:
    If you want to use virustotal to obtain file-related or url-related threat intelligence, please use:
```json
{"method":"vt","data_type":String("file" or "url"),"value":List[String(md5 of the file or the value of url)]}
```
    If you need to query some documents to know whether certain operations are allowed like "Previous Activity of the xxx"," "xxx Account Information",if you want to use this ,Please describe the purpose of your search as clearly as possible like.
    example of description search purpose:
    information of xxx(specific name) user
    Using the following format to search:
```json
{"method":"document","data_type":String("search"),"value":List[String(Search purpose)]}
```
    """



class localintel:
    generic_prompt: str= """
    You are a helpful honest assistant and you answer questions based only on the information that is given to you.
You do not add anything in your answer that is not instructed to you. 
If you cannot answer you simply say you do not know the answer. 
    """

    final_contextualized_completion_prompt:str = """
    Given the following global_knowledge that is threat or vulnerability report retrieved from the internet relevant for the question and
current infrastructure details of running applications such as used dependencies, used libraries, used version and use case of that dependency in the application as local_knowledge.
Answer the question from the information provided in global_knowledge and local_knowledge.
Do not add anything that is not given in the global_knowledge or local_knowledge. 
Only include answer without mentioning its information source. 
If there is no relation between the global_knowledge and the local_knowledge, or you cannot understand the context,
then you say more information is required to answer the question, while mentioning what information is required. 

global_knowledge: 
    """


    local_knowledge_addition_prompt:str  = """\n
    local_knowledge:
    """
