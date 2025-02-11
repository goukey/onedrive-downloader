import os
import json
import requests
from urllib.parse import urlparse
import sys

# 配置参数
CONFIG_FILE = "aria2_config.json"
INPUT_FILE = "result.txt"

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return None

def save_config(config):
    """保存配置文件"""
    if os.path.exists(CONFIG_FILE):
        backup_name = f"{CONFIG_FILE}.bak"
        os.rename(CONFIG_FILE, backup_name)
        print(f"已备份旧配置到 {backup_name}")
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_aria2_config():
    """获取配置信息"""
    saved_config = load_config()
    
    if saved_config:
        print(f"\n当前配置：地址={saved_config['rpc']} 密码={saved_config['secret']}")
        if input("是否使用当前配置？(y/n, 默认y): ").lower() in ('', 'y'):
            return saved_config
    
    # 手动输入配置
    print("\n请输入aria2配置信息：")
    config = {
        'rpc': input("RPC地址 (默认: http://127.0.0.1:6800/jsonrpc): ") 
              or "http://127.0.0.1:6800/jsonrpc",
        'secret': input("密码 (默认空): ") or ""
    }
    
    # 保存配置提示
    if input("是否保存配置以便下次使用？(y/n): ").lower() == 'y':
        save_config(config)
        print(f"配置已保存至 {CONFIG_FILE}")
    
    return config

def read_download_list():
    """正确解析两行一条的记录"""
    try:
        with open('result.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 每两行为一个条目（文件名+URL）
        return [(lines[i].strip(), lines[i+1].strip()) 
               for i in range(0, len(lines), 2)]
    except Exception as e:
        print(f"读取下载列表失败: {str(e)}")
        return []

def parse_downloads():
    """解析下载列表"""
    downloads = []
    
    if not os.path.exists(INPUT_FILE):
        print("错误：下载列表文件不存在")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"文件列表: {os.listdir('.')}")
        input("按任意键退出...")
        sys.exit(1)

    # 添加文件大小显示
    def parse_size(line):
        if line.startswith('# 文件大小:'):
            try:
                return float(line.split(':')[1].strip().replace('MB', ''))
            except:
                return 0
        return None

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8-sig') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        downloads = []
        i = 0
        while i < len(lines):
            name = lines[i]
            i += 1
            
            # 检查是否有大小信息
            size = None
            if i < len(lines) and lines[i].startswith('# 文件大小:'):
                size = parse_size(lines[i])
                i += 1
                
            if i < len(lines):
                url = lines[i]
                i += 1
                downloads.append((len(downloads)+1, name, url, size))
            
            # 跳过空行
            while i < len(lines) and not lines[i].strip():
                i += 1
                
        return downloads
    except Exception as e:
        print(f"解析下载列表失败: {str(e)}")
        raise

def select_files(downloads):
    """交互式选择文件"""
    print("\n可用文件列表：")
    for idx, name, _, _ in downloads:
        print(f"[{idx:2d}] {name}")
    
    while True:
        selection = input("\n请输入要下载的序号（支持格式：1 / 2-5 / 1,3,5-7）：")
        try:
            selected = set()
            # 处理不同格式输入
            for part in selection.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected.update(range(start, end+1))
                else:
                    if part.strip():
                        selected.add(int(part))
            
            # 验证输入有效性
            max_num = len(downloads)
            invalid = [n for n in selected if n < 1 or n > max_num]
            if invalid:
                print(f"错误：包含无效序号 {invalid}，最大可用序号为 {max_num}")
                continue
                
            return [downloads[n-1] for n in sorted(selected)]
        except ValueError:
            print("输入格式错误，请按示例格式输入")

def send_to_aria2(filename, url, config):
    """发送单个任务到aria2"""
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "aria2.addUri",
        "params": [
            f"token:{config['secret']}",
            [url],
            {"out": filename}
        ]
    }
    try:
        response = requests.post(config['rpc'], 
                               data=json.dumps(payload),
                               headers={'Content-Type': 'application/json'},
                               timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    # 获取配置
    config = get_aria2_config()
    
    downloads = parse_downloads()
    if not downloads:
        print("没有找到有效下载项")
        input("按任意键退出...")
        return
    
    # 全量下载提示
    print(f"\n找到 {len(downloads)} 个可用下载项")
    choice = input("是否下载全部文件？(y/n, 默认n): ").strip().lower()
    
    if choice == 'y':
        selected = downloads
    else:
        selected = select_files(downloads)
    
    success = 0
    fail = 0
    fail_list = []
    
    for idx, name, url, size in selected:
        print(f"\n正在添加({idx}/{len(downloads)}): {name}")
        result = send_to_aria2(name, url, config)
        
        if 'result' in result:
            print(f"成功 | 任务ID: {result['result']}")
            success +=1
        else:
            error_msg = result.get('error', '未知错误')
            print(f"失败 | 错误信息: {error_msg}")
            fail_list.append((name, error_msg))
            fail +=1
    
    print(f"\n汇总：成功 {success} 个，失败 {fail} 个")
    if fail_list:
        print("\n失败详情：")
        for name, error in fail_list:
            print(f"· {name}: {error}")
    
    # 添加结束提示
    if success + fail > 0:
        input("\n按回车键退出程序...")

if __name__ == "__main__":
    main() 