import os
import subprocess
import sys
import json

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
    steps = [
        {"name": "获取OneDrive文件列表", "module": "onedrive", "required": []},
        {"name": "生成下载链接", "module": "get_urls", "required": ["tmp.json"]},
        {"name": "推送Aria2下载", "module": "send_aria2", "required": ["result.txt"]}
    ]

    for step in steps:
        success = run_step(step["name"], step["module"], step["required"])
        if not success:
            print("\n流程终止，请检查错误信息")
            return

    print("\n所有步骤已完成！")

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