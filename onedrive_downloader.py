import json
import os
import sys
import io
import urllib.parse
from pprint import pprint
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

# 仅在作为脚本直接运行时包装 stdout，避免 import 时影响 GUI
if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

# 只读请求头模板，禁止原地修改（修复二次解析需重启的问题）
BASE_HEADERS = {
    "sec-ch-ua-mobile": "?0",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36 Edg/90.0.818.51"
    ),
    "accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
    ),
    "service-worker-navigation-preload": "true",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-dest": "iframe",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
}

# 兼容旧代码中的 header 名称（只读别名，请勿对其赋值修改内容）
header = BASE_HEADERS

CACHE_DIR = Path(".onedrive_downloader")
TEMP_JSON_PATH = CACHE_DIR / "tmp.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

APP_UUID = "5cbed6ac-a083-4e14-b191-b4ba07653de2"
DEVICE_CODE = "5c872a7a-0906-4ccc-a157-2b003598569f"


def capitalize(s):
    return s[0].upper() + s[1:]


def newSession():
    s = requests.session()
    retries = Retry(total=5, backoff_factor=0.1)
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def _extract_redeem(redirect_url):
    """从跳转 URL 中解析 redeem 参数。"""
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(redirect_url).query)
    redeem_list = query.get("redeem")
    if not redeem_list or not redeem_list[0]:
        raise ValueError(
            "无法从跳转链接中解析 redeem 参数，请确认分享链接有效且为个人版 1drv.ms 链接"
        )
    return redeem_list[0]


def _build_auth_headers(auth_data, prefer=None):
    """每次请求独立构建 auth 头，绝不污染 BASE_HEADERS。"""
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-HK,zh-TW;q=0.5",
        "Connection": "keep-alive",
        "Content-Type": f"multipart/form-data;boundary={DEVICE_CODE}",
        "Origin": "https://onedrive.live.com",
        "Referer": "https://onedrive.live.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "TE": "trailers",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) "
            "Gecko/20100101 Firefox/135.0"
        ),
        "Authorization": f"{capitalize(auth_data['authScheme'])} {auth_data['token']}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _download_url(item):
    """优先取 Graph 下载字段，回退旧字段名。"""
    return (
        item.get("@microsoft.graph.downloadUrl")
        or item.get("@content.downloadUrl")
        or ""
    )


def getFiles(originalPath, req=None, layers=0, _id=0):
    fileCount = 0
    isSharepoint = "-my" not in originalPath
    if req is None:
        req = newSession()

    # 使用模板副本，避免污染全局头
    reqf = req.get(originalPath, headers=dict(BASE_HEADERS))
    redirectURL = reqf.url
    print(redirectURL)

    redeem = _extract_redeem(redirectURL)

    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(redirectURL).query))
    if "id" not in query:
        raise ValueError("跳转链接中缺少 id 参数，无法定位文件夹")

    redirectSplitURL = redirectURL.split("/")

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

    reqf = req.post(
        "https://api-badgerp.svc.ms/v1.0/token",
        data={"appId": APP_UUID},
        headers=dict(BASE_HEADERS),
    )
    print(reqf.text)
    authData = json.loads(reqf.text)
    if "token" not in authData or "authScheme" not in authData:
        raise ValueError(f"获取 Badger Token 失败: {reqf.text[:200]}")

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
        DEVICE_CODE, authData["authScheme"], authData["token"], DEVICE_CODE
    ).replace("\n", "\r\n")

    # share → driveitem（独立 headers）
    reqUrl = (
        "https://my.microsoftpersonalcontent.com/_api/v2.0/shares/u!{}/driveitem"
        "?%24select=id%2CparentReference"
    ).format(redeem)
    print(reqUrl)
    share_headers = _build_auth_headers(authData, prefer="autoredeem")
    reqf = req.post(
        reqUrl,
        data="%24select=id%2CparentReference",
        headers=share_headers,
    )
    print("ok")

    # 列目录 children
    reqUrl = (
        "https://my.microsoftpersonalcontent.com/_api/v2.0/drives/{}/items/{}children"
        "?%24top=100&orderby=folder%2Cname&%24expand=thumbnails%2Ctags"
        "&select=*%2Cocr%2CwebDavUrl%2CsharepointIds%2CisRestricted%2CcommentSettings"
        "%2CspecialFolder%2CcontainingDrivePolicyScenarioViewpoint&ump=1"
    ).format(drives.lower(), relativeFolder)

    print(reqUrl)
    list_headers = _build_auth_headers(authData)
    reqf = req.post(
        reqUrl,
        data=postData.encode("utf-8"),
        headers=list_headers,
    )

    print(reqf.text)

    try:
        response_data = json.loads(reqf.text)
        if "value" in response_data:
            filesData = response_data["value"]
        else:
            print("无法解析文件列表，响应结构异常:")
            pprint(response_data)
            return []
    except Exception as e:
        print(f"解析API响应失败: {str(e)}")
        return []

    print(f"当前层级 {layers} 找到 {len(filesData)} 个项目")
    if len(filesData) > 0:
        print("首个项目示例:")
        pprint(filesData[0])
        print("可用字段列表:", filesData[0].keys())

    collected_files = []
    for item in filesData:
        # Graph 中文件夹带 folder 属性
        if "folder" in item:
            print("\t" * layers, "文件夹:", item.get("name"))
            sub_query = query.copy()
            sub_query["id"] = os.path.join(sub_query["id"], item.get("name")).replace(
                "\\", "/"
            )
            sub_url = (
                "/".join(redirectSplitURL[:-1])
                + "/AllItems.aspx?"
                + urllib.parse.urlencode(sub_query)
            )
            # 同一分享任务内复用 session；headers 每次重建，不污染
            sub_files = getFiles(sub_url, req, layers + 1)
            fileCount += len(sub_files)
            collected_files.extend(sub_files)
        else:
            raw_url = _download_url(item)
            name = item.get("name")
            if not raw_url:
                print("\t" * layers, f"跳过无直链文件: {name}")
                continue
            file_info = {
                "name": name,
                "size": item.get("size", 0),
                "raw_url": raw_url,
            }
            collected_files.append(file_info)
            print("\t" * layers, f"文件[{fileCount}]: {name}")
            fileCount += 1

    with TEMP_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(collected_files, f, indent=4, ensure_ascii=False)

    return collected_files


def get_onedrive_files(share_url=None):
    """获取OneDrive文件列表。每次调用使用全新 Session。"""
    if not share_url:
        share_url = input("请输入OneDrive分享链接：").strip()
    if not share_url:
        print("链接不能为空")
        return False

    try:
        # 顶层始终新建 Session，避免跨链接复用污染状态
        files = getFiles(share_url, newSession())
        if files:
            print(f"成功获取 {len(files)} 个文件")
            return True
        print("未获取到任何文件")
        return False
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        return False


def main(share_url=None):
    return get_onedrive_files(share_url)


if __name__ == "__main__":
    main()
