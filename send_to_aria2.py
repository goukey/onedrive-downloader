import os
import json
import requests
from urllib.parse import urlparse
import sys
from pathlib import Path

# 定义缓存目录（在程序运行目录下）
CACHE_DIR = Path('.onedrive_downloader')
CONFIG_FILE = CACHE_DIR / 'aria2_config.json'
INPUT_FILE = CACHE_DIR / 'result.txt'
TEMP_JSON_PATH = CACHE_DIR / 'tmp.json'

def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open('r', encoding='utf-8-sig') as f:
            return json.load(f)
    return None

def save_config(config):
    """保存配置文件"""
    # 确保缓存目录存在
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_FILE.exists():
        backup_path = CONFIG_FILE.with_suffix('.json.bak')
        CONFIG_FILE.rename(backup_path)
        print(f"已备份旧配置到 {backup_path}")
    
    with CONFIG_FILE.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_aria2_config():
    """获取配置信息"""
    saved_config = load_config()
    
    if saved_config:
        print(f"\n当前Aria2配置：")
        print(f"RPC地址: {saved_config['rpc']}")
        print(f"RPC密码: {saved_config['secret']}")
        if input("是否使用当前配置？(y/n, 默认y): ").lower() in ('', 'y'):
            return saved_config
    
    # 手动输入配置
    print("\n请输入Aria2配置信息：")
    while True:
        rpc_url = input("RPC地址 (默认: http://127.0.0.1:6800/jsonrpc): ").strip() or "http://127.0.0.1:6800/jsonrpc"
        
        # 检查RPC地址格式
        if not rpc_url.startswith(('http://', 'https://')):
            print("RPC地址格式错误，必须以http://或https://开头，以/jsonrpc结尾")
            continue
        if not rpc_url.endswith('/jsonrpc'):
            print("RPC地址格式错误，必须以/jsonrpc结尾")
            continue
        
        # 地址格式正确，退出循环
        break
    
    config = {
        'rpc': rpc_url,
        'secret': input("密码 (默认空): ") or ""
    }
    
    # 保存配置提示
    if input("是否保存Aria2配置以便下次使用？(y/n): ").lower() == 'y':
        save_config(config)
        print(f"Aria2配置已保存至 {CONFIG_FILE}")
    
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
    
    if not TEMP_JSON_PATH.exists():
        print("错误：下载列表文件不存在")
        print(f"请先运行前面的步骤生成下载列表")
        input("按任意键退出...")
        return []

    try:
        with TEMP_JSON_PATH.open('r', encoding='utf-8') as f:
            data = json.load(f)
            
        for idx, item in enumerate(data):
            name = item['name'].strip()
            url = item['raw_url'].strip()
            size = item['size']
            downloads.append((idx, name, url, size))
        
        return downloads
    except Exception as e:
        print(f"解析下载列表失败: {str(e)}")
        return []

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

def send_to_aria2(filename, url, config, test_connection=False):
    """发送下载任务到aria2"""
    try:
        server_url = config['rpc']
        secret = config['secret']
        
        # 检查RPC地址格式
        if not server_url.startswith(('http://', 'https://')):
            return {'error': {'message': 'RPC地址格式错误，必须以http://或https://开头，以/jsonrpc结尾'}}
        if not server_url.endswith('/jsonrpc'):
            return {'error': {'message': 'RPC地址格式错误，必须以/jsonrpc结尾'}}
        
        # 尝试发送一个不带token的测试请求
        test_data = {
            'jsonrpc': '2.0',
            'method': 'aria2.getVersion',
            'id': 1,
            'params': []
        }
        try:
            test_response = requests.post(server_url, json=test_data, timeout=5)
            test_result = test_response.json()
            if 'error' in test_result and 'Unauthorized' in str(test_result.get('error', {}).get('message', '')):
                if not secret:
                    return {'error': {'message': '服务端需要密码验证'}}
        except requests.exceptions.ConnectionError:
            return {'error': {'message': 'RPC地址错误或Aria2未启动，请检查：\n1. RPC地址是否正确\n2. Aria2是否已启动'}}
        except requests.exceptions.Timeout:
            return {'error': {'message': 'RPC地址连接超时，请检查地址是否正确'}}
        except Exception:
            pass  # 忽略其他错误，继续执行
        
        # 构建请求数据
        if test_connection:
            data = {
                'jsonrpc': '2.0',
                'method': 'aria2.getVersion',
                'id': 1,
            }
            if secret:
                data['params'] = [f'token:{secret}']
            else:
                data['params'] = []
        else:
            data = {
                'jsonrpc': '2.0',
                'method': 'aria2.addUri',
                'id': 1,
                'params': [[url], {'out': filename}]
            }
            if secret:
                data['params'].insert(0, f'token:{secret}')
        
        # 发送请求
        response = requests.post(server_url, json=data)
        result = response.json()
        
        # 检查密码错误
        error_msg = str(result.get('error', {}).get('message', ''))
        if 'error' in result and 'Unauthorized' in error_msg:
            return {'error': {'message': 'RPC密码错误'}}
        
        return result
        
    except Exception as e:
        return {'error': {'message': str(e)}}

def main():
    # 获取配置
    config = get_aria2_config()
    
    downloads = parse_downloads()
    if not downloads:
        print("没有找到有效的文件")
        input("按任意键退出...")
        return
    
    # 全量下载提示
    print(f"\n找到 {len(downloads)} 个文件")
    print("\n请选择操作：")
    print("1. 推送到Aria2")
    print("2. 导出直链")
    choice = input("请输入选项(1/2): ").strip()
    
    if choice == '2':
        # 导出直链功能
        export_choice = input("\n是否导出全部文件的直链？(y/n, 默认n): ").strip().lower()
        if export_choice == 'y':
            selected = downloads
        else:
            selected = select_files(downloads)
        
        if not selected:
            print("未选择任何文件")
            input("按任意键退出...")
            return
        
        try:
            with open('直链.txt', 'w', encoding='utf-8') as f:
                for idx, name, url, size in selected:
                    size_mb = size / 1024 / 1024
                    f.write(f"文件名：{name}\n")
                    f.write(f"大小：{size_mb:.2f}MB\n")
                    f.write(f"直链：{url}\n")
                    f.write("\n")
            
            print(f"\n已成功导出 {len(selected)} 个文件的直链到 直链.txt")
            print("\n请注意：直链有效期为1小时，超时后需要重新获取！")
            print(f"保存位置：{os.path.abspath('直链.txt')}")
            
        except Exception as e:
            print(f"\n导出失败: {str(e)}")
        
        input("\n按回车键退出程序...")
        return
    
    # 推送到Aria2功能
    push_choice = input("\n是否推送全部文件到Aria2？(y/n, 默认n): ").strip().lower()
    if push_choice == 'y':
        selected = downloads
    else:
        selected = select_files(downloads)
    
    if not selected:
        print("未选择任何文件")
        input("按任意键退出...")
        return
    
    success = 0
    fail = 0
    fail_list = []
    
    for idx, name, url, size in selected:
        print(f"\n正在推送到Aria2({idx}/{len(downloads)}): {name}")
        result = send_to_aria2(name, url, config)
        
        if 'result' in result:
            print(f"推送成功 | 任务ID: {result['result']}")
            success +=1
        else:
            error_msg = result.get('error', '未知错误')
            print(f"推送失败 | 错误信息: {error_msg}")
            fail_list.append((name, error_msg))
            fail +=1
    
    print(f"\n推送汇总：成功 {success} 个，失败 {fail} 个")
    if fail_list:
        print("\n推送失败详情：")
        for name, error in fail_list:
            print(f"· {name}: {error}")
    
    # 如果有成功推送的文件，询问是否保存配置
    if success > 0:
        saved_config = load_config()
        if not saved_config or (
            saved_config.get('rpc') != config['rpc'] or 
            saved_config.get('secret') != config['secret']
        ):
            if input("\n是否保存当前的Aria2配置？(y/n): ").lower() == 'y':
                save_config(config)
                print(f"Aria2配置已保存至 {CONFIG_FILE}")
    
    # 添加结束提示
    if success + fail > 0:
        input("\n按回车键退出程序...")

if __name__ == "__main__":
    main() 