import requests
import vt
vt_key = ""


def file_info(file_md5):
    try:
        with vt.Client(vt_key) as client:
            # 获取文件的威胁信息
            threat_info = client.get_object(f"/files/{file_md5}")
            # 使用字典而不是集合
            package_file = {
                "md5": file_md5,
                "size": threat_info.size,
                "type_tag": threat_info.type_tag,
                "last_analysis_stats": threat_info.last_analysis_stats
            }
            return str(package_file)
        # todo: using LLM restate the search results
    except:
        return f"the file reputation of md5 which value is {file_md5} is a safe file in the vt"

def url_info(threat_url):

    try:
        # 使用上下文管理器确保会话正确关闭
        with vt.Client(vt_key) as client:
            # 获取URL的ID
            url_id = vt.url_id(threat_url)

            # 获取URL威胁信息
            url = client.get_object(f"/urls/{url_id}")

            # 使用字典而不是集合
            package_url = {
                "url":threat_url,
                "times_submitted": url.times_submitted,
                "last_analysis_stats": url.last_analysis_stats
            }

            return str(package_url)
        # return f"the url/ip reputation :{threat_url} is safe"
    except:
        return f"the url/ip reputation:{threat_url} is safe"

# print(file_info("bc566d17914b07abaab3a5a385cc3301"))