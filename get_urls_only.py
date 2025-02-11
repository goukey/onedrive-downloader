import json

# 输入和输出文件路径
INPUT_JSON = 'tmp.json'
OUTPUT_TXT = 'result.txt'

def extract_urls():
    try:
        # 读取JSON文件
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取并格式化数据
        output = []
        for item in data:
            if 'name' in item and 'raw_url' in item:
                output.append(f"{item['name']}\n{item['raw_url']}\n")
        
        # 写入结果文件
        with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
            f.writelines(output)
            
        print(f"成功导出 {len(output)} 条记录到 {OUTPUT_TXT}")
        
    except Exception as e:
        print(f"处理失败: {str(e)}")

def main():
    """新增main函数"""
    try:
        with open('tmp.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with open('result.txt', 'w', encoding='utf-8') as f:
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