# OneDrive个人版下载器

![GitHub release (latest by date)](https://img.shields.io/github/v/release/goukey/onedrive-downloader?style=flat-square)

**专用于 OneDrive 个人版分享链接** 的批量下载工具。

## 简介
本工具专门用于下载 **OneDrive 个人版分享链接** 中的文件，功能包括：
- 自动获取文件列表
- 生成文件直接下载链接
- 支持推送到aria2下载

生成的下载链接文件(result.txt)中包含文件直链，可以添加到任何下载工具使用。

## 功能特点
- 支持OneDrive文件列表获取
- 支持生成直接下载链接
- 支持推送到aria2下载
- 支持保存aria2配置
- 显示文件大小信息
- 支持选择性下载

## 使用方法

### Windows用户
1. 从[Releases](https://github.com/goukey/onedrive-downloader/releases)页面下载最新版本
2. 双击运行`onedrive_downloader.exe`
3. 按提示操作

### Linux用户（从源码运行）
1. 安装依赖：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
2. 运行程序：`python oneclick_downloader.py`
3. 按提示操作

## 注意事项
- 首次使用需要配置aria2的RPC地址和密码
- 获取的文件直链有效期为1小时，超时需要重新运行程序获取
- ⚠️ **xxx.sharepoint.com 形式的分享链接推荐使用** [OneDriveShareLinkPushAria2](https://github.com/gaowanliang/OneDriveShareLinkPushAria2)

## 环境要求
- Windows用户：Windows 7/8/10/11
- Linux用户：Python 3.6+
- aria2 (需要开启RPC)

## 许可证
MIT License

## 致谢
代码参考了 [OneDriveShareLinkPushAria2](https://github.com/gaowanliang/OneDriveShareLinkPushAria2) [@gaowanliang](https://github.com/gaowanliang) 