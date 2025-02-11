# OneDrive 下载器

一个用于从OneDrive批量下载文件的工具。

## 简介
这个工具可以帮助你从OneDrive批量下载文件，支持获取文件列表、生成直接下载链接，并可以直接推送到aria2进行下载。

## 功能特点
- 支持OneDrive文件列表获取
- 支持生成直接下载链接
- 支持推送到aria2下载
- 支持保存aria2配置
- 显示文件大小信息
- 支持选择性下载

## 使用方法
1. 安装依赖：`pip install -r requirements.txt`
2. 运行程序：`python oneclick_downloader.py`
3. 按提示操作

## 注意事项
- 需要提前安装并配置好aria2
- 首次使用需要配置aria2的RPC地址和密码

## 环境要求
- Python 3.6+
- aria2 (需要开启RPC)

## 许可证
MIT License 