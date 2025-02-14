import json
from pathlib import Path

# 定义缓存目录（在程序运行目录下）
CACHE_DIR = Path('.onedrive_downloader')
TEMP_JSON_PATH = CACHE_DIR / 'tmp.json'
RESULT_PATH = CACHE_DIR / 'result.txt'

def main():
    """新增main函数"""
    try:
        with TEMP_JSON_PATH.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with RESULT_PATH.open('w', encoding='utf-8') as f:
            for item in data:
                name = item['name'].strip()
                url = item['raw_url'].strip()
                size_mb = item['size'] / 1024 / 1024
                f.write(f"{name}\n")
                f.write(f"# 文件大小: {size_mb:.2f}MB\n")
                f.write(f"{url}\n\n")
        
        total_size_gb = sum(item['size'] for item in data) / 1024 / 1024 / 1024
        print(f"成功生成 {len(data)} 条下载链接")
        print(f"总文件大小: {total_size_gb:.2f}GB")
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 