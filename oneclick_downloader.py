import os
import sys
from pathlib import Path

import onedrive_downloader
from get_urls_only import main as get_urls
from send_to_aria2 import main as send_to_aria2

# 统一使用与核心模块相同的缓存目录
CACHE_DIR = Path(".onedrive_downloader")


def ensure_cache_dir():
    """确保缓存目录存在"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        try:
            import ctypes

            FILE_ATTRIBUTE_HIDDEN = 0x02
            ret = ctypes.windll.kernel32.SetFileAttributesW(
                str(CACHE_DIR), FILE_ATTRIBUTE_HIDDEN
            )
            if not ret:
                print(f"设置隐藏属性失败: {ctypes.get_last_error()}")
        except Exception as e:
            print(f"设置隐藏属性时出错: {e}")


def main():
    """主函数：解析分享链 → 生成链接列表 → 推送/导出"""
    ensure_cache_dir()

    if len(sys.argv) > 1:
        share_url = sys.argv[1]
    else:
        share_url = input("请输入OneDrive分享链接：").strip()

    if not share_url:
        print("链接不能为空")
        return False

    try:
        if not onedrive_downloader.get_onedrive_files(share_url):
            print("获取文件列表失败")
            return False

        # 可选：生成 result.txt 便于人工查看
        get_urls()

        # 交互：推送到 Aria2 或导出直链
        send_to_aria2()
        return True
    except Exception as e:
        print(f"处理失败: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        os.system("clear" if os.name == "posix" else "cls")
        main()
    except Exception as e:
        print(f"程序发生未捕获异常: {str(e)}")
        import traceback

        traceback.print_exc()
        input("按任意键退出...")
