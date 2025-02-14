import os
import subprocess
import sys
import json
from pathlib import Path
import onedrive_downloader
from get_urls_only import main as get_urls
from send_to_aria2 import main as send_to_aria2

# 定义缓存目录（在程序运行目录下）
CACHE_DIR = Path('.onedrive_downloader')

def ensure_cache_dir():
    """确保缓存目录存在"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # 在Windows系统下设置隐藏属性
    if os.name == 'nt':
        try:
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ret = ctypes.windll.kernel32.SetFileAttributesW(str(CACHE_DIR), FILE_ATTRIBUTE_HIDDEN)
            if not ret:  # 返回0表示失败
                print(f"设置隐藏属性失败: {ctypes.get_last_error()}")
        except Exception as e:
            print(f"设置隐藏属性时出错: {e}")

def get_onedrive_files():
    """统一处理OneDrive文件获取"""
    share_url = input("请输入OneDrive分享链接：")
    from onedrive_downloader import getFiles
    result = getFiles(share_url, None, 0)
    with open('tmp.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"成功保存{len(result)}条记录")
    return result

def run_step(name, module, required_files=[]):
    print(f"\n{'='*50}")
    print(f"正在执行阶段：{name}")
    print(f"{'='*50}")
    
    try:
        if module == "onedrive":
            get_onedrive_files()
        elif module == "get_urls":
            from get_urls_only import main as get_urls_main
            get_urls_main()
        elif module == "send_aria2":
            from send_to_aria2 import main as aria2_main
            aria2_main()
        print(f"\n{name} 执行完成")
        return True
    except Exception as e:
        print(f"\n{name} 执行失败: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    # 确保缓存目录存在
    ensure_cache_dir()

    # 获取命令行参数
    if len(sys.argv) > 1:
        share_url = sys.argv[1]
    else:
        share_url = input("请输入OneDrive分享链接：").strip()
    
    if not share_url:
        print("链接不能为空")
        return False
    
    try:
        # 获取文件列表
        if not onedrive_downloader.get_onedrive_files(share_url):
            print("获取文件列表失败")
            return False
        
        # 生成下载链接
        get_urls()
        
        # 发送到aria2下载
        send_to_aria2()
        
        return True
    except Exception as e:
        print(f"处理失败: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # 设置系统编码环境
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        input_path = os.path.join("data", "input")  # 跨平台路径
        os.system("clear" if os.name == 'posix' else "cls")  # 自动判断平台
        main()
    except Exception as e:
        print(f"程序发生未捕获异常: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按任意键退出...") 