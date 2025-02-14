import json
import re
import urllib
import urllib.request

from pprint import pprint
from urllib import parse

import requests
import os
import copy
import sys
import io

from requests.models import codes
from requests.adapters import HTTPAdapter, Retry
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 移除所有全局变量
# 确保没有模块级代码

# 将fileCount改为函数参数传递

header = {
    "sec-ch-ua-mobile": "?0",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36 Edg/90.0.818.51",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "service-worker-navigation-preload": "true",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-dest": "iframe",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
}

# 定义缓存目录（在程序运行目录下）
CACHE_DIR = Path('.onedrive_downloader')
TEMP_JSON_PATH = CACHE_DIR / 'tmp.json'

# 确保缓存目录存在
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 首字母大写
def capitalize(s):
    return s[0].upper() + s[1:]


def newSession():
    s = requests.session()
    retries = Retry(total=5, backoff_factor=0.1)
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def getFiles(originalPath, req=None, layers=0, _id=0):
    fileCount = 0
    filesData = []
    isSharepoint = False
    if "-my" not in originalPath:
        isSharepoint = True
    if req is None:
        req = newSession()
    reqf = req.get(originalPath, headers=header)
    redirectURL = reqf.url
    print(redirectURL)
    rex = re.compile(r"&redeem=(.*)&")
    redeem = rex.search(redirectURL).group(1)

    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(redirectURL).query))
    redirectSplitURL = redirectURL.split("/")
    appid = "1141147648"
    appUuid = "5cbed6ac-a083-4e14-b191-b4ba07653de2"

    relativeFolder = ""
    rootFolder = query["id"]
    for i in rootFolder.split("/"):
        if isSharepoint:
            if i != "Shared Documents":
                relativeFolder += i + "/"
            else:
                relativeFolder += i
                break
        else:
            if i != "Documents":
                relativeFolder += i + "/"
            else:
                relativeFolder += i
                break
    relativeUrl = (
        parse.quote(relativeFolder)
        .replace("/", "%2F")
        .replace("_", "%5F")
        .replace("-", "%2D")
    )
    rootFolderUrl = (
        parse.quote(rootFolder)
        .replace("/", "%2F")
        .replace("_", "%5F")
        .replace("-", "%2D")
    )

    reqf = req.post("https://api-badgerp.svc.ms/v1.0/token", data={"appId": appUuid})

    deviceCode = "5c872a7a-0906-4ccc-a157-2b003598569f"  # 随机生成

    print(reqf.text)
    authData = json.loads(reqf.text)
    drives = relativeFolder.split("!")[0]
    postData = """--{}
Content-Disposition: form-data;name=data
Prefer: HonorNonIndexedQueriesWarningMayFailRandomly, allowthrottleablequeries, Include-Feature=AddToOneDrive;Vault
X-ClientService-ClientTag: ODC Web
Application: ODC Web
Scenario: BrowseFiles
ScenarioType: AUO
X-HTTP-Method-Override: GET
Content-Type: application/json
Authorization: {} {}


--{}--""".format(
        deviceCode, authData["authScheme"], authData["token"], deviceCode
    ).replace(
        "\n", "\r\n"
    )

    authHeaderRaw = [
        {"name": "Accept", "value": "*/*"},
        {"name": "Accept-Encoding", "value": "gzip, deflate, br, zstd"},
        {"name": "Accept-Language", "value": "zh-HK,zh-TW;q=0.5"},
        {"name": "Connection", "value": "keep-alive"},
        {
            "name": "Content-Type",
            "value": "multipart/form-data;boundary={}".format(deviceCode),
        },
        {"name": "Host", "value": "my.microsoftpersonalcontent.com"},
        {"name": "Origin", "value": "https://onedrive.live.com"},
        {"name": "Referer", "value": "https://onedrive.live.com/"},
        {"name": "Sec-Fetch-Dest", "value": "empty"},
        {"name": "Sec-Fetch-Mode", "value": "cors"},
        {"name": "Sec-Fetch-Site", "value": "cross-site"},
        {"name": "TE", "value": "trailers"},
        {
            "name": "User-Agent",
            "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        },
    ]

    authHeader = header
    # 将authHeaderRaw解析成正常的Header
    for i in authHeaderRaw:
        authHeader[i["name"]] = i["value"]

    reqUrl = "https://my.microsoftpersonalcontent.com/_api/v2.0/shares/u!{}/driveitem?%24select=id%2CparentReference".format(
        redeem
    )
    print(reqUrl)
    authDriverHeader = authHeader
    authDriverHeader["Authorization"] = "{} {}".format(
        capitalize(authData["authScheme"]), authData["token"]
    )
    authDriverHeader["Prefer"] = "autoredeem"
    reqf = req.post(
        reqUrl,
        data="%24select=id%2CparentReference",
        headers=authHeader,
    )
    print("ok")

    reqUrl = "https://my.microsoftpersonalcontent.com/_api/v2.0/drives/{}/items/{}children?%24top=100&orderby=folder%2Cname&%24expand=thumbnails%2Ctags&select=*%2Cocr%2CwebDavUrl%2CsharepointIds%2CisRestricted%2CcommentSettings%2CspecialFolder%2CcontainingDrivePolicyScenarioViewpoint&ump=1".format(
        drives.lower(), relativeFolder
    )

    print(reqUrl)
    reqf = req.post(
        reqUrl,
        data=postData.encode("utf-8"),
        headers=authHeader,
    )

    print(reqf.text)

    # 修复文件数据解析逻辑
    try:
        response_data = json.loads(reqf.text)
        if 'value' in response_data:  # 检查实际API响应结构
            filesData = response_data['value']
        else:
            print("无法解析文件列表，响应结构异常:")
            pprint(response_data)
            return []
    except Exception as e:
        print(f"解析API响应失败: {str(e)}")
        return []

    # 添加调试信息
    print(f"当前层级 {layers} 找到 {len(filesData)} 个项目")
    if len(filesData) > 0:
        print("首个项目示例:")
        pprint(filesData[0])
        sample_item = filesData[0]
        print("可用字段列表:", sample_item.keys())

    # 修改文件类型判断逻辑
    collected_files = []
    for item in filesData:
        if 'folder' in item.get('@microsoft.graph.downloadUrl', ''):
            # 处理文件夹
            print("\t" * layers, "文件夹:", item.get('name'))
            sub_query = query.copy()
            sub_query["id"] = os.path.join(sub_query["id"], item.get('name')).replace("\\", "/")
            
            sub_url = "/".join(redirectSplitURL[:-1]) + "/AllItems.aspx?" + urllib.parse.urlencode(sub_query)
            sub_files = getFiles(sub_url, req, layers + 1)
            fileCount += len(sub_files)
            collected_files.extend(sub_files)
        else:
            # 处理文件
            file_info = {
                "name": item.get('name'),
                "size": item.get('size', 0),
                "raw_url": item.get('@content.downloadUrl', '')
            }
            collected_files.append(file_info)
            print("\t" * layers, f"文件[{fileCount}]: {item.get('name')}")

    # 保存文件信息到临时文件
    with TEMP_JSON_PATH.open('w', encoding='utf-8') as f:
        json.dump(collected_files, f, indent=4, ensure_ascii=False)

    return collected_files

def get_onedrive_files(share_url=None):
    """获取OneDrive文件列表"""
    if not share_url:
        share_url = input("请输入OneDrive分享链接：").strip()
    if not share_url:
        print("链接不能为空")
        return False

    try:
        # 调用getFiles函数处理链接
        files = getFiles(share_url)
        if files:
            print(f"成功获取 {len(files)} 个文件")
            return True
        return False
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        return False

def main(share_url=None):
    return get_onedrive_files(share_url)

if __name__ == "__main__":
    main()
