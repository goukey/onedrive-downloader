from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                            QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QMenu, QMessageBox)
from PyQt6.QtCore import Qt
import sys
import json
import os
from pathlib import Path
import ctypes
import subprocess
import onedrive_downloader
from get_urls_only import main as get_urls
from send_to_aria2 import get_aria2_config, send_to_aria2, load_config, save_config
import requests
try:
    from version import VERSION
except ImportError:
    VERSION = None

# 定义缓存目录（在程序运行目录下）
CACHE_DIR = Path('.onedrive_downloader')
CONFIG_PATH = CACHE_DIR / 'aria2_config.json'
TEMP_JSON_PATH = CACHE_DIR / 'tmp.json'
RESULT_PATH = CACHE_DIR / 'result.txt'

def hide_directory(path):
    """设置文件夹为隐藏属性"""
    if os.name == 'nt':  # Windows系统
        try:
            # 获取文件属性
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ret = ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
            if not ret:  # 返回0表示失败
                print(f"设置隐藏属性失败: {ctypes.get_last_error()}")
        except Exception as e:
            print(f"设置隐藏属性时出错: {e}")

def get_version_from_git():
    """从git tag获取版本号"""
    # 如果存在注入的版本号，优先使用
    if VERSION:
        return VERSION
    
    try:
        # 获取最新的tag
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "v1.0.0"  # 如果获取失败，返回默认版本号

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 从git tag获取版本号
        self.version = get_version_from_git()
        
        # 确保缓存目录存在
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # 设置缓存目录为隐藏
        hide_directory(CACHE_DIR)
        self.setWindowTitle(f"OneDrive个人版下载器 {self.version}")
        self.setMinimumSize(900, 700)
        
        # 设置全局字体
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(11)  # 设置统一字号
        app.setFont(font)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 2px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
            QLabel {
                color: #333;
            }
            QCheckBox {
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # 设置边距
        layout.setSpacing(15)  # 设置控件间距
        main_widget.setLayout(layout)
        
        # 设置状态文本的HTML样式
        self.status_text_style = """
            <style>
            .highlight {
                color: #0078d4;
                font-size: 14pt;
                font-weight: bold;
            }
            .warning {
                color: #ff0000;
                font-size: 16pt;
                font-weight: 900;
            }
            </style>
        """
        
        # OneDrive链接输入
        link_layout = QHBoxLayout()
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("请输入OneDrive个人版分享链接")
        self.link_input.textChanged.connect(self.validate_link)
        self.link_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.link_input.customContextMenuRequested.connect(self.show_context_menu)
        self.get_files_btn = QPushButton("获取文件列表")
        button_style = """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        download_button_style = """
            QPushButton {
                background-color: #d42828;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #be2020;
            }
            QPushButton:pressed {
                background-color: #9e1a1a;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        self.get_files_btn.setStyleSheet(button_style)
        self.get_files_btn.clicked.connect(self.get_file_list)
        self.get_files_btn.setEnabled(False)
        link_layout.addWidget(QLabel("分享链接:"))
        link_layout.addWidget(self.link_input)
        link_layout.addWidget(self.get_files_btn)
        layout.addLayout(link_layout)
        
        # aria2配置
        config_layout = QHBoxLayout()
        self.rpc_input = QLineEdit()
        self.rpc_input.setPlaceholderText("http://127.0.0.1:6800/jsonrpc")
        self.rpc_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rpc_input.customContextMenuRequested.connect(self.show_context_menu)
        self.secret_input = QLineEdit()
        self.secret_input.setPlaceholderText("RPC密码")
        self.secret_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.secret_input.customContextMenuRequested.connect(self.show_context_menu)
        config_layout.addWidget(QLabel("RPC地址:"))
        config_layout.addWidget(self.rpc_input)
        config_layout.addWidget(QLabel("密码:"))
        config_layout.addWidget(self.secret_input)
        layout.addLayout(config_layout)
        
        # 文件列表
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["选择", "文件名", "大小", "状态"])
        # 用于跟踪是否正在批量更新复选框
        self.is_batch_updating = False
        layout.addWidget(self.file_table)
        
        # 修改文件表格的样式
        self.file_table.setShowGrid(False)  # 隐藏网格线
        self.file_table.setAlternatingRowColors(True)  # 启用交替行颜色
        self.file_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
            }
        """)
        self.file_table.verticalHeader().hide()  # 隐藏垂直表头
        self.file_table.setColumnWidth(0, 60)  # 选择列宽度
        self.file_table.setColumnWidth(1, 400)  # 文件名列宽度
        self.file_table.setColumnWidth(2, 100)  # 大小列宽度
        self.file_table.setColumnWidth(3, 150)  # 状态列宽度
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet(button_style)
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_all_btn.setEnabled(False)
        
        # 添加导出直链按钮
        self.export_btn = QPushButton("导出直链")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_links)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c41;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5a2d;
            }
            QPushButton:pressed {
                background-color: #094023;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.download_btn = QPushButton("推送到Aria2")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #d42828;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #be2020;
            }
            QPushButton:pressed {
                background-color: #9e1a1a;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.download_btn)
        layout.addLayout(btn_layout)
        
        # 状态显示
        status_layout = QHBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.status_text.customContextMenuRequested.connect(self.show_text_context_menu)
        self.status_text.setMinimumHeight(150)
        self.status_text.setMaximumHeight(150)
        status_font = self.status_text.font()
        status_font.setPointSize(10)
        self.status_text.setFont(status_font)
        
        # 添加版本号标签
        version_label = QLabel(f"版本 {self.version}")
        version_label.setStyleSheet("""
            QLabel {
                color: #666666;
                padding: 5px;
            }
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        
        status_layout.addWidget(self.status_text)
        status_layout.addWidget(version_label)
        layout.addLayout(status_layout)
        
        # 加载aria2配置
        self.load_aria2_config()
        
        # 显示初始提示信息
        self.show_status(
            self.status_text_style + 
            '<p class="highlight">👉 请先填入<span class="warning">OneDrive个人版</span>分享链接，然后点击"获取文件列表"按钮 👈</p>' +
            '<p class="highlight">支持的链接格式：</p>' +
            '<p class="highlight">• https://1drv.ms/*</p>'
        )
    
    def load_aria2_config(self):
        """加载aria2配置"""
        config = load_config()
        if config:
            reply = QMessageBox.question(
                self,
                '加载配置',
                '检测到已保存的aria2配置：\n'
                f'RPC地址: {config.get("rpc", "")}\n'
                f'RPC密码: {config.get("secret", "")}\n\n'
                '是否使用该配置？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.rpc_input.setText(config.get('rpc', ''))
                self.secret_input.setText(config.get('secret', ''))
    
    def get_file_list(self):
        """获取文件列表"""
        # 禁用按钮，避免重复点击
        self.get_files_btn.setEnabled(False)
        self.link_input.setEnabled(False)
        
        try:
            # 清空文件表格
            self.file_table.setRowCount(0)
            
            # 获取文件列表
            share_url = self.link_input.text().strip()
            if not onedrive_downloader.get_onedrive_files(share_url):
                self.show_status("获取文件列表失败")
                return
            
            # 生成下载链接文件
            get_urls()
            
            # 读取文件列表
            # 确保缓存目录存在
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            try:
                with TEMP_JSON_PATH.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 填充表格
                self.file_table.setRowCount(len(data))
                for i, item in enumerate(data):
                    # 添加复选框
                    chk = QCheckBox()
                    chk.toggled.connect(self.on_checkbox_changed)
                    self.file_table.setCellWidget(i, 0, chk)
                    
                    # 添加文件名
                    self.file_table.setItem(i, 1, QTableWidgetItem(item['name']))
                    
                    # 添加文件大小
                    size_mb = item['size'] / 1024 / 1024
                    self.file_table.setItem(i, 2, QTableWidgetItem(f"{size_mb:.2f}MB"))
                    
                    # 添加状态列
                    self.file_table.setItem(i, 3, QTableWidgetItem("待处理"))
                
                # 启用相关按钮
                self.select_all_btn.setEnabled(True)
                
                # 显示文件总数和大小
                total_size_gb = sum(item['size'] for item in data) / 1024 / 1024 / 1024
                self.show_status(f"已获取 {len(data)} 个文件，总大小: {total_size_gb:.2f}GB")
                
            except Exception as e:
                self.show_status(f"解析文件列表失败: {str(e)}")
                
        except Exception as e:
            self.show_status(f"获取文件列表失败: {str(e)}")
        finally:
            # 恢复按钮状态
            self.get_files_btn.setEnabled(True)
            self.link_input.setEnabled(True)
    
    def on_checkbox_changed(self, checked):
        """复选框状态改变时更新按钮状态"""
        if self.is_batch_updating:
            return
            
        # 检查是否有选中的项目
        has_checked = False
        for i in range(self.file_table.rowCount()):
            chk = self.file_table.cellWidget(i, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                has_checked = True
                break
        
        # 更新下载按钮和导出按钮状态
        self.download_btn.setEnabled(has_checked)
        self.export_btn.setEnabled(has_checked)
        
        # 更新全选按钮文字
        self.select_all_btn.setText("取消选择" if has_checked else "全选")
    
    def select_all_files(self):
        """全选/取消全选"""
        # 检查当前选中状态
        any_checked = False
        for i in range(self.file_table.rowCount()):
            chk = self.file_table.cellWidget(i, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                any_checked = True
                break
        
        # 根据当前状态切换
        new_state = not any_checked
        
        # 更新按钮文字
        self.select_all_btn.setText("取消选择" if new_state else "全选")
        
        # 设置所有复选框状态
        self.is_batch_updating = True
        for i in range(self.file_table.rowCount()):
            chk = self.file_table.cellWidget(i, 0)
            if isinstance(chk, QCheckBox):
                chk.setChecked(new_state)
        self.is_batch_updating = False
        
        # 更新下载按钮和导出按钮状态
        self.download_btn.setEnabled(new_state)
        self.export_btn.setEnabled(new_state)
    
    def download_selected(self):
        """下载选中的文件"""
        selected = []
        for i in range(self.file_table.rowCount()):
            chk = self.file_table.cellWidget(i, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected.append(i)
        
        if not selected:
            self.show_status("请先选择要推送的文件")
            return
        
        # 1. 检查RPC地址是否为空
        rpc_url = self.rpc_input.text().strip()
        if not rpc_url:
            self.show_status("请输入Aria2 RPC地址")
            return
        
        # 2. 检查RPC地址格式
        if not rpc_url.startswith(('http://', 'https://')):
            self.show_status("RPC地址格式错误，必须以http://或https://开头，以/jsonrpc结尾")
            return
        if not rpc_url.endswith('/jsonrpc'):
            self.show_status("RPC地址格式错误，必须以/jsonrpc结尾")
            return
        
        # 构建配置
        config = {
            'rpc': rpc_url,
            'secret': self.secret_input.text().strip()
        }
        
        # 3. 检查RPC服务器是否联通
        try:
            test_data = {
                'jsonrpc': '2.0',
                'method': 'aria2.getVersion',
                'id': 1,
                'params': []
            }
            test_response = requests.post(rpc_url, json=test_data, timeout=5)
            test_result = test_response.json()
        except requests.exceptions.ConnectionError:
            self.show_status("推送失败: RPC地址错误或Aria2未启动，请检查：\n1. RPC地址是否正确\n2. Aria2是否已启动")
            return
        except requests.exceptions.Timeout:
            self.show_status("推送失败: RPC地址连接超时，请检查地址是否正确")
            return
        except Exception as e:
            error_msg = str(e)
            if 'Expecting value' in error_msg:
                self.show_status("推送失败: RPC地址错误或Aria2未启动，请检查：\n1. RPC地址是否正确\n2. Aria2是否已启动")
            else:
                self.show_status(f"推送失败: {error_msg}")
            return
        
        # 4. 检查服务器是否需要密码
        if 'error' in test_result and 'Unauthorized' in str(test_result.get('error', {}).get('message', '')):
            if not self.secret_input.text().strip():
                self.show_status("当前RPC地址需要密码验证，请输入RPC密码")
                return
        
        try:
            # 读取文件列表
            with TEMP_JSON_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 下载选中的文件
            success = 0
            for i in selected:
                item = data[i]
                result = send_to_aria2(item['name'], item['raw_url'], config)
                if 'result' in result:
                    self.file_table.setItem(i, 3, QTableWidgetItem("已成功推送到Aria2"))
                    success += 1
                else:
                    error_msg = result.get('error', {}).get('message', '未知错误')
                    if 'Unauthorized' in str(error_msg):
                        error_msg = 'RPC密码错误'
                        self.show_status("推送失败: Aria2 RPC密码错误")
                        self.file_table.setItem(i, 3, QTableWidgetItem(f"失败: {error_msg}"))
                        return
                    elif 'Connection refused' in str(error_msg):
                        self.show_status("推送失败: Aria2 RPC地址连接失败，请检查地址是否正确或Aria2是否已启动")
                        self.file_table.setItem(i, 3, QTableWidgetItem(f"失败: {error_msg}"))
                        return
                    else:
                        self.show_status(f"推送失败: {error_msg}")
                        self.file_table.setItem(i, 3, QTableWidgetItem(f"失败: {error_msg}"))
                        return
            
            self.show_status(f"推送完成: 成功 {success} 个，失败 {len(selected)-success} 个")
            
            # 第一次推送成功后询问是否保存配置
            if success > 0:
                reply = QMessageBox.question(
                    self, 
                    '保存配置',
                    '是否保存当前的aria2配置？\n'
                    f'RPC地址: {self.rpc_input.text()}\n'
                    f'RPC密码: {self.secret_input.text()}',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    save_config(config)
                    self.show_status("aria2配置已保存")
            
            # 下载成功后清空选择
            self.is_batch_updating = True
            for i in range(self.file_table.rowCount()):
                chk = self.file_table.cellWidget(i, 0)
                if isinstance(chk, QCheckBox):
                    chk.setChecked(False)
            self.is_batch_updating = False
            
            # 更新按钮状态
            self.select_all_btn.setText("全选")
            self.download_btn.setEnabled(False)
            self.export_btn.setEnabled(False)

        except Exception as e:
            error_msg = str(e)
            if 'Connection refused' in error_msg:
                self.show_status("推送失败: RPC地址错误或Aria2未启动，请检查：\n1. RPC地址是否正确\n2. Aria2是否已启动")
            else:
                self.show_status(f"推送失败: {error_msg}")
    
    def show_status(self, msg):
        """显示状态信息"""
        # 如果消息包含HTML标签，则使用HTML格式
        if '<' in msg and '>' in msg:
            self.status_text.setHtml(msg)
        else:
            self.status_text.append(msg)
    
    def validate_link(self, text):
        """验证输入的链接格式"""
        text = text.strip()
        is_valid = text.startswith('https://1drv.ms/')
        self.get_files_btn.setEnabled(is_valid)
        
        # 清空之前的提示
        self.status_text.clear()
        
        if not text:
            # 当输入框为空时显示初始提示
            self.show_status(
                self.status_text_style + 
                '<p class="highlight">👉 请先填入<span class="warning">OneDrive个人版</span>分享链接，然后点击"获取文件列表"按钮 👈</p>' +
                '<p class="highlight">支持的链接格式：</p>' +
                '<p class="highlight">• https://1drv.ms/*</p>'
            )
        elif not is_valid:
            # 清空之前的提示
            self.status_text.clear()
            # 显示格式提示
            self.show_status(
                self.status_text_style + 
                '<p class="highlight">请输入正确的<span class="warning">OneDrive个人版</span>分享链接，格式如: https://1drv.ms/*</p>' +
                '<p class="highlight">请使用分享链接中的短链接格式</p>'
            )
        else:
            # 清除之前的错误提示
            self.status_text.clear()
            self.show_status(
                self.status_text_style + 
                '<p class="highlight">✅ 链接格式正确，请点击"获取文件列表"按钮</p>'
            )
    
    def show_context_menu(self, pos):
        """显示中文右键菜单"""
        input_widget = self.sender()  # 获取触发事件的输入框
        menu = QMenu(self)
        
        # 创建标准动作
        actions = {
            'undo': menu.addAction('撤销'),
            'redo': menu.addAction('重做'),
            None: menu.addSeparator(),  # 第一个分隔线
            'cut': menu.addAction('剪切'),
            'copy': menu.addAction('复制'),
            'paste': menu.addAction('粘贴'),
            None: menu.addSeparator(),  # 第二个分隔线
            'delete': menu.addAction('删除'),
            'select_all': menu.addAction('全选')
        }
        
        # 设置动作快捷键
        actions['undo'].setShortcut('Ctrl+Z')
        actions['redo'].setShortcut('Ctrl+Y')
        actions['cut'].setShortcut('Ctrl+X')
        actions['copy'].setShortcut('Ctrl+C')
        actions['paste'].setShortcut('Ctrl+V')
        actions['select_all'].setShortcut('Ctrl+A')
        
        # 连接动作信号
        actions['undo'].triggered.connect(input_widget.undo)
        actions['redo'].triggered.connect(input_widget.redo)
        actions['cut'].triggered.connect(input_widget.cut)
        actions['copy'].triggered.connect(input_widget.copy)
        actions['paste'].triggered.connect(input_widget.paste)
        actions['delete'].triggered.connect(lambda: input_widget.del_())  # 修改删除操作
        actions['select_all'].triggered.connect(input_widget.selectAll)
        
        # 设置动作状态
        actions['undo'].setEnabled(input_widget.isUndoAvailable())
        actions['redo'].setEnabled(input_widget.isRedoAvailable())
        actions['cut'].setEnabled(input_widget.hasSelectedText())
        actions['copy'].setEnabled(input_widget.hasSelectedText())
        actions['paste'].setEnabled(QApplication.clipboard().text() != '')  # 检查剪贴板是否有文本
        actions['delete'].setEnabled(input_widget.hasSelectedText())
        actions['select_all'].setEnabled(len(input_widget.text()) > 0)
        
        # 显示菜单
        menu.exec(input_widget.mapToGlobal(pos))

    def show_text_context_menu(self, pos):
        """显示文本框的中文右键菜单"""
        text_edit = self.sender()
        menu = QMenu(self)
        
        # 创建标准动作
        actions = {
            'copy': menu.addAction('复制'),
            None: menu.addSeparator(),
            'select_all': menu.addAction('全选')
        }
        
        # 设置动作快捷键
        actions['copy'].setShortcut('Ctrl+C')
        actions['select_all'].setShortcut('Ctrl+A')
        
        # 连接动作信号
        actions['copy'].triggered.connect(text_edit.copy)
        actions['select_all'].triggered.connect(text_edit.selectAll)
        
        # 设置动作状态
        actions['copy'].setEnabled(text_edit.textCursor().hasSelection())
        actions['select_all'].setEnabled(len(text_edit.toPlainText()) > 0)
        
        # 显示菜单
        menu.exec(text_edit.mapToGlobal(pos))

    def export_links(self):
        """导出选中文件的直链"""
        try:
            # 读取文件列表
            with TEMP_JSON_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取选中的文件
            selected = []
            for i in range(self.file_table.rowCount()):
                chk = self.file_table.cellWidget(i, 0)
                if isinstance(chk, QCheckBox) and chk.isChecked():
                    selected.append(i)
            
            if not selected:
                self.show_status("请先选择要导出的文件")
                return
            
            # 导出直链到文件
            with open('直链.txt', 'w', encoding='utf-8') as f:
                for i in selected:
                    item = data[i]
                    name = item['name'].strip()
                    url = item['raw_url'].strip()
                    size_mb = item['size'] / 1024 / 1024
                    f.write(f"文件名：{name}\n")
                    f.write(f"大小：{size_mb:.2f}MB\n")
                    f.write(f"直链：{url}\n")
                    f.write("\n")
            
            # 显示成功提示
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("导出成功")
            msg.setText("直链已导出到软件目录下的'直链.txt'文件中")
            msg.setInformativeText("请注意：直链有效期为1小时，超时后需要重新获取！")
            msg.setDetailedText(f"保存位置：{os.path.abspath('直链.txt')}")
            msg.exec()
            
            self.show_status(f"已导出 {len(selected)} 个文件的直链")
            
            # 导出成功后清空选择
            self.is_batch_updating = True
            for i in range(self.file_table.rowCount()):
                chk = self.file_table.cellWidget(i, 0)
                if isinstance(chk, QCheckBox):
                    chk.setChecked(False)
            self.is_batch_updating = False
            
            # 更新按钮状态
            self.select_all_btn.setText("全选")
            self.download_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            
        except Exception as e:
            self.show_status(f"导出失败: {str(e)}")

def main():
    app = QApplication(sys.argv)
    # 设置中文本地化
    from PyQt6.QtCore import QTranslator, QLocale
    translator = QTranslator()
    translator.load(QLocale(), "qtbase", "_", ":/qt/translations")
    app.installTranslator(translator)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()