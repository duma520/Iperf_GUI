#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
iperf3 图形化工具
支持TCP/UDP测试，多线程处理，设置保存，进度显示等功能
"""

import os
import sys
import json
import subprocess
import threading
import time
import re
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QProgressBar,
                             QSplitter, QTabWidget, QMessageBox, QFileDialog,
                             QStatusBar, QSizePolicy, QHeaderView, QTableWidget,
                             QTableWidgetItem)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QSettings, QTimer, 
                          QSize, QRect, QMetaObject, Q_ARG, QByteArray)
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor

# 配置文件路径
CONFIG_FILE = "iperf3_gui_config.json"

class Iperf3Worker(QThread):
    """iperf3工作线程"""
    
    # 信号定义
    output_received = pyqtSignal(str)
    test_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.is_running = True
        self.process = None
        
    def run(self):
        """执行iperf3测试"""
        try:
            # 构建命令参数
            cmd = ["iperf3"]
            
            if self.params["mode"] == "server":
                cmd.extend(["-s"])
                if self.params["server_port"]:
                    cmd.extend(["-p", str(self.params["server_port"])])
                if self.params["one_off"]:
                    cmd.append("-1")
            else:  # client mode
                cmd.extend(["-c", self.params["server_ip"]])
                if self.params["server_port"]:
                    cmd.extend(["-p", str(self.params["server_port"])])
                
                # 通用参数
                if self.params["protocol"] == "udp":
                    cmd.append("-u")
                    if self.params["bandwidth"]:
                        cmd.extend(["-b", self.params["bandwidth"]])
                
                if self.params["reverse"]:
                    cmd.append("-R")
                
                if self.params["time"]:
                    cmd.extend(["-t", str(self.params["time"])])
                
                if self.params["parallel"]:
                    # 修复参数错误：缺少"-P"参数
                    cmd.extend(["-P", str(self.params["parallel"])])
                
                if self.params["window_size"]:
                    cmd.extend(["-w", self.params["window_size"]])
                
                if self.params["mss"]:
                    cmd.extend(["-M", str(self.params["mss"])])
                
                if self.params["num"]:
                    cmd.extend(["-n", self.params["num"]])
                
                if self.params["interval"]:
                    cmd.extend(["-i", str(self.params["interval"])])
                
                if self.params["format"]:
                    cmd.extend(["--format", self.params["format"]])
                
                if self.params["json_output"]:
                    cmd.append("-J")
                
                if self.params["verbose"]:
                    cmd.append("-V")
                
                if self.params["version"]:
                    cmd.append("--version")
                
                if self.params["debug"]:
                    cmd.append("-d")
            
            self.output_received.emit(f"执行命令: {' '.join(cmd)}\n")
            
            # 执行iperf3
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,
                universal_newlines=True
            )
            
            # 读取输出
            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    break
                    
                if line.strip():
                    self.output_received.emit(line)
                    
                    # 解析进度信息
                    progress_info = self.parse_progress(line)
                    if progress_info:
                        self.progress_updated.emit(*progress_info)
            
            # 等待进程结束
            return_code = self.process.wait()
            
            if return_code == 0:
                self.test_completed.emit({"status": "success", "code": return_code})
            else:
                self.error_occurred.emit(f"测试失败，返回码: {return_code}")
                
        except FileNotFoundError:
            self.error_occurred.emit("未找到iperf3程序，请确保已安装iperf3")
        except Exception as e:
            self.error_occurred.emit(f"执行错误: {str(e)}")
    
    def parse_progress(self, line):
        """从输出行解析进度信息"""
        # 匹配iperf3进度输出（示例：[  5]   0.00-1.00   sec  1.10 GBytes  9.42 Gbits/sec）
        pattern = r'\[\s*\d+\]\s+[\d\.]+-([\d\.]+)\s+sec'
        match = re.search(pattern, line)
        if match:
            current_time = float(match.group(1))
            if self.params.get("time"):
                total_time = self.params["time"]
                progress = int((current_time / total_time) * 100)
                return min(progress, 100), f"测试进度: {current_time}/{total_time}秒"
        return None
    
    def stop(self):
        """停止测试"""
        self.is_running = False
        if self.process:
            self.process.terminate()
            self.process.wait()

class SettingsManager:
    """设置管理器"""
    
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.settings = self.load_settings()
    
    def load_settings(self):
        """加载设置"""
        default_settings = {
            "server_ip": "127.0.0.1",
            "server_port": "5201",
            "protocol": 0,  # 索引
            "mode": 0,      # 索引
            "time": 10,
            "parallel": 1,
            "bandwidth": "",
            "window_size": "",
            "mss": 0,       # 改为整数而不是字符串
            "num": "",
            "interval": 1.0,
            "format": 0,    # 索引
            "reverse": False,
            "json_output": False,
            "verbose": False,
            "version": False,
            "debug": False,
            "one_off": False,
            "window_size_custom": "",
            "geometry": None,
            "window_state": None
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并设置，保留默认值用于新增字段
                    for key in default_settings:
                        if key in loaded:
                            # 兼容旧版本：如果是字符串，转换为索引
                            if key == "protocol" and isinstance(loaded[key], str):
                                if loaded[key] == "tcp":
                                    default_settings[key] = 0
                                elif loaded[key] == "udp":
                                    default_settings[key] = 1
                                else:
                                    default_settings[key] = 0
                            elif key == "mode" and isinstance(loaded[key], str):
                                if loaded[key] == "client":
                                    default_settings[key] = 0
                                elif loaded[key] == "server":
                                    default_settings[key] = 1
                                else:
                                    default_settings[key] = 0
                            elif key == "format" and isinstance(loaded[key], str):
                                format_map = {"": 0, "k": 0, "m": 1, "g": 2}
                                default_settings[key] = format_map.get(loaded[key].lower(), 0)
                            elif key == "mss":
                                # 处理mss字段，确保是整数
                                mss_value = loaded[key]
                                if isinstance(mss_value, str):
                                    if mss_value.strip() == "":
                                        default_settings[key] = 0
                                    else:
                                        try:
                                            default_settings[key] = int(mss_value)
                                        except:
                                            default_settings[key] = 0
                                else:
                                    default_settings[key] = int(mss_value)
                            elif key == "time" or key == "parallel":
                                # 确保这些字段是整数
                                value = loaded[key]
                                if isinstance(value, str):
                                    if value.strip() == "":
                                        default_settings[key] = 0 if key == "parallel" else 10
                                    else:
                                        try:
                                            default_settings[key] = int(value)
                                        except:
                                            default_settings[key] = default_settings[key]
                                else:
                                    default_settings[key] = int(value)
                            elif key == "interval":
                                # 确保interval是浮点数
                                value = loaded[key]
                                if isinstance(value, str):
                                    if value.strip() == "":
                                        default_settings[key] = 1.0
                                    else:
                                        try:
                                            default_settings[key] = float(value)
                                        except:
                                            default_settings[key] = 1.0
                                else:
                                    default_settings[key] = float(value)
                            else:
                                default_settings[key] = loaded[key]
        except json.JSONDecodeError:
            # JSON文件损坏，删除并重新创建
            print(f"JSON配置文件损坏，使用默认设置")
            try:
                os.remove(self.config_file)
            except:
                pass
        except Exception as e:
            print(f"加载设置失败: {e}")
        
        return default_settings
    
    def save_settings(self, settings):
        """保存设置"""
        try:
            # 处理window_state，如果是QByteArray则转换为十六进制字符串
            settings_to_save = settings.copy()
            if isinstance(settings_to_save.get("window_state"), QByteArray):
                settings_to_save["window_state"] = settings_to_save["window_state"].toHex().data().decode()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置值"""
        self.settings[key] = value
    
    def save_all(self):
        """保存所有设置"""
        return self.save_settings(self.settings)

class Iperf3GUI(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.worker = None
        self.init_ui()
        self.load_settings()
        self.setup_connections()
        
    def init_ui(self):
        """初始化界面"""
        # 设置窗口属性
        self.setWindowTitle("iperf3 网络性能测试工具")
        self.setMinimumSize(1000, 700)
        
        # 尝试设置图标
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建测试配置标签页
        self.create_test_tab()
        
        # 创建结果标签页
        self.create_result_tab()
        
        # 创建历史记录标签页
        self.create_history_tab()
        
        # 创建底部控制区域
        self.create_bottom_controls(main_layout)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()
        
        # 应用样式
        self.apply_styles()
        
    def create_test_tab(self):
        """创建测试配置标签页"""
        test_tab = QWidget()
        self.tab_widget.addTab(test_tab, "测试配置")
        
        layout = QVBoxLayout(test_tab)
        layout.setSpacing(15)
        
        # 基础设置组
        basic_group = QGroupBox("基础设置")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(10)
        
        # 测试模式
        basic_layout.addWidget(QLabel("测试模式:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["客户端", "服务器"])
        basic_layout.addWidget(self.mode_combo, 0, 1)
        
        # 服务器地址
        basic_layout.addWidget(QLabel("服务器地址:"), 0, 2)
        self.server_ip_edit = QLineEdit()
        basic_layout.addWidget(self.server_ip_edit, 0, 3)
        
        # 端口
        basic_layout.addWidget(QLabel("端口:"), 1, 0)
        self.port_edit = QLineEdit()
        basic_layout.addWidget(self.port_edit, 1, 1)
        
        # 协议
        basic_layout.addWidget(QLabel("协议:"), 1, 2)
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["TCP", "UDP"])
        basic_layout.addWidget(self.protocol_combo, 1, 3)
        
        # 测试时间
        basic_layout.addWidget(QLabel("测试时间(秒):"), 2, 0)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 3600)
        self.time_spin.setValue(10)
        basic_layout.addWidget(self.time_spin, 2, 1)
        
        # 并行流
        basic_layout.addWidget(QLabel("并行流:"), 2, 2)
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 128)
        self.parallel_spin.setValue(1)
        basic_layout.addWidget(self.parallel_spin, 2, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QGridLayout()
        advanced_layout.setSpacing(10)
        
        # 带宽限制
        advanced_layout.addWidget(QLabel("带宽限制:"), 0, 0)
        self.bandwidth_combo = QComboBox()
        self.bandwidth_combo.addItems(["", "1M", "10M", "100M", "1G", "10G"])
        self.bandwidth_combo.setEditable(True)
        advanced_layout.addWidget(self.bandwidth_combo, 0, 1)
        
        # 窗口大小
        advanced_layout.addWidget(QLabel("窗口大小:"), 0, 2)
        self.window_combo = QComboBox()
        self.window_combo.addItems(["", "32K", "64K", "128K", "256K", "512K", "1M"])
        self.window_combo.setEditable(True)
        advanced_layout.addWidget(self.window_combo, 0, 3)
        
        # MSS
        advanced_layout.addWidget(QLabel("MSS:"), 1, 0)
        self.mss_spin = QSpinBox()
        self.mss_spin.setRange(0, 9000)
        self.mss_spin.setSpecialValueText("默认")
        advanced_layout.addWidget(self.mss_spin, 1, 1)
        
        # 数据量
        advanced_layout.addWidget(QLabel("传输数据量:"), 1, 2)
        self.data_amount_edit = QLineEdit()
        advanced_layout.addWidget(self.data_amount_edit, 1, 3)
        
        # 报告间隔
        advanced_layout.addWidget(QLabel("报告间隔(秒):"), 2, 0)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 10.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(1.0)
        advanced_layout.addWidget(self.interval_spin, 2, 1)
        
        # 单位格式
        advanced_layout.addWidget(QLabel("单位格式:"), 2, 2)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["自动", "K", "M", "G"])
        advanced_layout.addWidget(self.format_combo, 2, 3)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 选项组
        options_group = QGroupBox("选项")
        options_layout = QGridLayout()
        options_layout.setSpacing(10)
        
        # 复选框
        self.reverse_check = QCheckBox("反向测试")
        options_layout.addWidget(self.reverse_check, 0, 0)
        
        self.json_check = QCheckBox("JSON输出")
        options_layout.addWidget(self.json_check, 0, 1)
        
        self.verbose_check = QCheckBox("详细输出")
        options_layout.addWidget(self.verbose_check, 0, 2)
        
        self.version_check = QCheckBox("显示版本")
        options_layout.addWidget(self.version_check, 0, 3)
        
        self.debug_check = QCheckBox("调试模式")
        options_layout.addWidget(self.debug_check, 1, 0)
        
        self.one_off_check = QCheckBox("单次连接")
        options_layout.addWidget(self.one_off_check, 1, 1)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 占位弹簧
        layout.addStretch()
        
    def create_result_tab(self):
        """创建结果标签页"""
        result_tab = QWidget()
        self.tab_widget.addTab(result_tab, "测试结果")
        
        layout = QVBoxLayout(result_tab)
        
        # 结果文本区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_text)
        
        # 结果统计区域
        stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        stats_fields = [
            ("带宽:", "bandwidth"),
            ("抖动:", "jitter"),
            ("丢包:", "loss"),
            ("时间:", "duration"),
            ("数据量:", "bytes"),
            ("包数量:", "packets")
        ]
        
        for i, (label_text, key) in enumerate(stats_fields):
            row = i // 3
            col = (i % 3) * 2
            stats_layout.addWidget(QLabel(label_text), row, col)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            stats_layout.addWidget(value_label, row, col + 1)
            self.stats_labels[key] = value_label
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
    def create_history_tab(self):
        """创建历史记录标签页"""
        history_tab = QWidget()
        self.tab_widget.addTab(history_tab, "历史记录")
        
        layout = QVBoxLayout(history_tab)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "模式", "协议", "服务器", "带宽", "抖动", "丢包"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.clear_history_btn = QPushButton("清空历史")
        self.export_history_btn = QPushButton("导出记录")
        self.load_history_btn = QPushButton("加载历史")
        
        button_layout.addWidget(self.clear_history_btn)
        button_layout.addWidget(self.export_history_btn)
        button_layout.addWidget(self.load_history_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def create_bottom_controls(self, parent_layout):
        """创建底部控制区域"""
        control_layout = QHBoxLayout()
        
        # 开始/停止按钮
        self.start_btn = QPushButton("开始测试")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #219653;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        self.stop_btn = QPushButton("停止测试")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        # 保存/加载按钮
        self.save_btn = QPushButton("保存配置")
        self.load_btn = QPushButton("加载配置")
        self.reset_btn = QPushButton("重置配置")
        
        # 添加到布局
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.reset_btn)
        
        parent_layout.addLayout(control_layout)
        
    def setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        self.start_btn.clicked.connect(self.start_test)
        self.stop_btn.clicked.connect(self.stop_test)
        self.save_btn.clicked.connect(self.save_config)
        self.load_btn.clicked.connect(self.load_config)
        self.reset_btn.clicked.connect(self.reset_config)
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.export_history_btn.clicked.connect(self.export_history)
        self.load_history_btn.clicked.connect(self.load_history)
        
        # 模式切换
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
    def on_mode_changed(self, mode):
        """处理模式切换"""
        is_client = (mode == "客户端")
        self.server_ip_edit.setEnabled(is_client)
        self.time_spin.setEnabled(is_client)
        self.bandwidth_combo.setEnabled(is_client)
        self.reverse_check.setEnabled(is_client)
        
    def start_test(self):
        """开始测试"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "测试正在进行中")
            return
        
        # 验证输入
        if not self.validate_input():
            return
        
        # 准备参数
        params = self.get_test_params()
        
        # 创建并启动工作线程
        self.worker = Iperf3Worker(params)
        self.worker.output_received.connect(self.append_output)
        self.worker.test_completed.connect(self.on_test_completed)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.error_occurred.connect(self.on_test_error)
        
        # 更新界面状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("测试进行中...")
        
        # 清空结果
        self.result_text.clear()
        for label in self.stats_labels.values():
            label.setText("--")
        
        # 开始测试
        self.worker.start()
        
    def stop_test(self):
        """停止测试"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.status_bar.showMessage("测试已停止")
            
        self.reset_ui_state()
        
    def validate_input(self):
        """验证输入"""
        mode = self.mode_combo.currentText()
        
        if mode == "客户端":
            server_ip = self.server_ip_edit.text().strip()
            if not server_ip:
                QMessageBox.warning(self, "输入错误", "请输入服务器地址")
                self.server_ip_edit.setFocus()
                return False
        
        port = self.port_edit.text().strip()
        if port and not port.isdigit():
            QMessageBox.warning(self, "输入错误", "端口必须是数字")
            self.port_edit.setFocus()
            return False
        
        return True
    
    def get_test_params(self):
        """获取测试参数"""
        params = {
            "mode": "server" if self.mode_combo.currentText() == "服务器" else "client",
            "server_ip": self.server_ip_edit.text().strip(),
            "server_port": self.port_edit.text().strip() or "5201",
            "protocol": "udp" if self.protocol_combo.currentText() == "UDP" else "tcp",
            "time": self.time_spin.value(),
            "parallel": self.parallel_spin.value(),
            "bandwidth": self.bandwidth_combo.currentText().strip(),
            "window_size": self.window_combo.currentText().strip(),
            "mss": self.mss_spin.value() if self.mss_spin.value() > 0 else "",
            "num": self.data_amount_edit.text().strip(),
            "interval": self.interval_spin.value(),
            "format": {"自动": "", "K": "k", "M": "m", "G": "g"}[self.format_combo.currentText()],
            "reverse": self.reverse_check.isChecked(),
            "json_output": self.json_check.isChecked(),
            "verbose": self.verbose_check.isChecked(),
            "version": self.version_check.isChecked(),
            "debug": self.debug_check.isChecked(),
            "one_off": self.one_off_check.isChecked()
        }
        
        return params
    
    def append_output(self, text):
        """追加输出文本"""
        self.result_text.moveCursor(QTextCursor.End)
        self.result_text.insertPlainText(text)
        self.result_text.ensureCursorVisible()
        
        # 尝试解析结果
        self.parse_results(text)
        
    def parse_results(self, text):
        """解析测试结果"""
        try:
            # 简化的结果解析
            lines = text.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                # 解析带宽
                if 'Gbits/sec' in line:
                    match = re.search(r'([\d\.]+)\s+Gbits/sec', line)
                    if match:
                        self.stats_labels['bandwidth'].setText(f"{match.group(1)} Gbps")
                elif 'Mbits/sec' in line:
                    match = re.search(r'([\d\.]+)\s+Mbits/sec', line)
                    if match:
                        self.stats_labels['bandwidth'].setText(f"{match.group(1)} Mbps")
                
                # 解析抖动
                if 'ms' in line and 'jitter' in line.lower():
                    match = re.search(r'jitter\s*[\:=]\s*([\d\.]+)\s*ms', line, re.IGNORECASE)
                    if match:
                        self.stats_labels['jitter'].setText(f"{match.group(1)} ms")
                
                # 解析丢包
                if 'loss' in line.lower():
                    match = re.search(r'([\d\.]+)%', line)
                    if match:
                        self.stats_labels['loss'].setText(f"{match.group(1)}%")
                        
        except Exception as e:
            print(f"解析结果错误: {e}")
    
    def update_progress(self, progress, message):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_bar.showMessage(message)
        
    def on_test_completed(self, result):
        """测试完成处理"""
        self.status_bar.showMessage("测试完成")
        self.reset_ui_state()
        
        # 保存到历史记录
        self.save_to_history()
        
        # 显示完成消息
        if result["status"] == "success":
            QMessageBox.information(self, "完成", "测试完成")
    
    def on_test_error(self, error_message):
        """测试错误处理"""
        self.append_output(f"\n错误: {error_message}\n")
        self.status_bar.showMessage("测试出错")
        self.reset_ui_state()
        QMessageBox.critical(self, "错误", error_message)
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.hide()
        
    def save_config(self):
        """保存配置"""
        config = {
            "server_ip": self.server_ip_edit.text(),
            "server_port": self.port_edit.text(),
            "protocol": self.protocol_combo.currentIndex(),
            "mode": self.mode_combo.currentIndex(),
            "time": self.time_spin.value(),
            "parallel": self.parallel_spin.value(),
            "bandwidth": self.bandwidth_combo.currentText(),
            "window_size": self.window_combo.currentText(),
            "mss": self.mss_spin.value(),
            "num": self.data_amount_edit.text(),
            "interval": self.interval_spin.value(),
            "format": self.format_combo.currentIndex(),
            "reverse": self.reverse_check.isChecked(),
            "json_output": self.json_check.isChecked(),
            "verbose": self.verbose_check.isChecked(),
            "version": self.version_check.isChecked(),
            "debug": self.debug_check.isChecked(),
            "one_off": self.one_off_check.isChecked()
        }
        
        self.settings_manager.settings.update(config)
        if self.settings_manager.save_all():
            QMessageBox.information(self, "成功", "配置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存配置失败")
    
    def load_config(self):
        """加载配置"""
        # 处理字符串类型的设置
        server_ip = self.settings_manager.get("server_ip", "")
        if server_ip is None:
            server_ip = ""
        self.server_ip_edit.setText(str(server_ip))
        
        server_port = self.settings_manager.get("server_port", "")
        if server_port is None:
            server_port = "5201"
        self.port_edit.setText(str(server_port))
        
        # 协议：处理字符串和索引两种情况
        protocol = self.settings_manager.get("protocol", 0)
        if isinstance(protocol, str):
            if protocol.lower() == "tcp":
                self.protocol_combo.setCurrentIndex(0)
            elif protocol.lower() == "udp":
                self.protocol_combo.setCurrentIndex(1)
            else:
                self.protocol_combo.setCurrentIndex(0)
        else:
            try:
                self.protocol_combo.setCurrentIndex(int(protocol))
            except:
                self.protocol_combo.setCurrentIndex(0)
        
        # 模式：处理字符串和索引两种情况
        mode = self.settings_manager.get("mode", 0)
        if isinstance(mode, str):
            if mode.lower() == "client":
                self.mode_combo.setCurrentIndex(0)
            elif mode.lower() == "server":
                self.mode_combo.setCurrentIndex(1)
            else:
                self.mode_combo.setCurrentIndex(0)
        else:
            try:
                self.mode_combo.setCurrentIndex(int(mode))
            except:
                self.mode_combo.setCurrentIndex(0)
        
        # 处理数值类型的设置
        try:
            self.time_spin.setValue(int(self.settings_manager.get("time", 10)))
        except:
            self.time_spin.setValue(10)
        
        try:
            self.parallel_spin.setValue(int(self.settings_manager.get("parallel", 1)))
        except:
            self.parallel_spin.setValue(1)
        
        # 处理字符串类型的设置
        bandwidth = self.settings_manager.get("bandwidth", "")
        if bandwidth is None:
            bandwidth = ""
        self.bandwidth_combo.setCurrentText(str(bandwidth))
        
        window_size = self.settings_manager.get("window_size", "")
        if window_size is None:
            window_size = ""
        self.window_combo.setCurrentText(str(window_size))
        
        # 处理mss
        mss_value = self.settings_manager.get("mss", 0)
        try:
            if isinstance(mss_value, str):
                if mss_value.strip() == "":
                    self.mss_spin.setValue(0)
                else:
                    self.mss_spin.setValue(int(mss_value))
            else:
                self.mss_spin.setValue(int(mss_value))
        except:
            self.mss_spin.setValue(0)
        
        # 处理其他字符串设置
        num_value = self.settings_manager.get("num", "")
        if num_value is None:
            num_value = ""
        self.data_amount_edit.setText(str(num_value))
        
        # 处理interval
        try:
            interval_value = self.settings_manager.get("interval", 1.0)
            if isinstance(interval_value, str):
                if interval_value.strip() == "":
                    self.interval_spin.setValue(1.0)
                else:
                    self.interval_spin.setValue(float(interval_value))
            else:
                self.interval_spin.setValue(float(interval_value))
        except:
            self.interval_spin.setValue(1.0)
        
        # 单位格式
        format_index = self.settings_manager.get("format", 0)
        try:
            if isinstance(format_index, str):
                # 兼容旧版本字符串格式
                format_map = {"": 0, "k": 0, "m": 1, "g": 2}
                format_index = format_map.get(format_index.lower(), 0)
            self.format_combo.setCurrentIndex(int(format_index))
        except:
            self.format_combo.setCurrentIndex(0)
        
        # 处理布尔值设置
        try:
            self.reverse_check.setChecked(bool(self.settings_manager.get("reverse", False)))
            self.json_check.setChecked(bool(self.settings_manager.get("json_output", False)))
            self.verbose_check.setChecked(bool(self.settings_manager.get("verbose", False)))
            self.version_check.setChecked(bool(self.settings_manager.get("version", False)))
            self.debug_check.setChecked(bool(self.settings_manager.get("debug", False)))
            self.one_off_check.setChecked(bool(self.settings_manager.get("one_off", False)))
        except:
            pass
        
        QMessageBox.information(self, "成功", "配置已加载")
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要重置所有配置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            defaults = {
                "server_ip": "127.0.0.1",
                "server_port": "5201",
                "protocol": 0,
                "mode": 0,
                "time": 10,
                "parallel": 1,
                "bandwidth": "",
                "window_size": "",
                "mss": 0,
                "num": "",
                "interval": 1.0,
                "format": 0,
                "reverse": False,
                "json_output": False,
                "verbose": False,
                "version": False,
                "debug": False,
                "one_off": False
            }
            
            self.settings_manager.settings.update(defaults)
            self.load_config()
    
    def save_to_history(self):
        """保存到历史记录"""
        try:
            # 从统计标签获取数据
            bandwidth = self.stats_labels['bandwidth'].text()
            jitter = self.stats_labels['jitter'].text()
            loss = self.stats_labels['loss'].text()
            
            if bandwidth != "--":
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                mode = self.mode_combo.currentText()
                protocol = self.protocol_combo.currentText()
                server = self.server_ip_edit.text()
                
                self.history_table.setItem(row, 0, QTableWidgetItem(current_time))
                self.history_table.setItem(row, 1, QTableWidgetItem(mode))
                self.history_table.setItem(row, 2, QTableWidgetItem(protocol))
                self.history_table.setItem(row, 3, QTableWidgetItem(server))
                self.history_table.setItem(row, 4, QTableWidgetItem(bandwidth))
                self.history_table.setItem(row, 5, QTableWidgetItem(jitter))
                self.history_table.setItem(row, 6, QTableWidgetItem(loss))
        except Exception as e:
            print(f"保存历史记录错误: {e}")
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要清空历史记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.history_table.setRowCount(0)
    
    def export_history(self):
        """导出历史记录"""
        if self.history_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有历史记录可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出历史记录", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 写入表头
                    headers = []
                    for col in range(self.history_table.columnCount()):
                        headers.append(self.history_table.horizontalHeaderItem(col).text())
                    f.write(','.join(headers) + '\n')
                    
                    # 写入数据
                    for row in range(self.history_table.rowCount()):
                        row_data = []
                        for col in range(self.history_table.columnCount()):
                            item = self.history_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        f.write(','.join(row_data) + '\n')
                
                QMessageBox.information(self, "成功", f"历史记录已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def load_history(self):
        """加载历史记录"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载历史记录", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    if len(lines) > 0:
                        self.history_table.setRowCount(0)
                        
                        for i, line in enumerate(lines[1:]):  # 跳过表头
                            data = line.strip().split(',')
                            if len(data) >= 7:
                                row = self.history_table.rowCount()
                                self.history_table.insertRow(row)
                                
                                for col in range(min(7, len(data))):
                                    self.history_table.setItem(row, col, QTableWidgetItem(data[col]))
                
                QMessageBox.information(self, "成功", "历史记录已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
    
    def apply_styles(self):
        """应用样式"""
        style = """
        QMainWindow {
            background-color: #f5f6fa;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #dcdde1;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLabel {
            color: #2c3e50;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            min-height: 25px;
        }
        QTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background-color: white;
        }
        QTableWidget {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background-color: white;
            gridline-color: #ecf0f1;
        }
        QHeaderView::section {
            background-color: #3498db;
            color: white;
            padding: 5px;
            border: none;
        }
        QStatusBar {
            background-color: #34495e;
            color: white;
        }
        QTabWidget::pane {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #ecf0f1;
            padding: 8px 15px;
            margin-right: 2px;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        QTabBar::tab:selected {
            background-color: #3498db;
            color: white;
        }
        """
        self.setStyleSheet(style)
    
    def load_settings(self):
        """加载窗口设置"""
        geometry = self.settings_manager.get("geometry")
        if geometry and isinstance(geometry, list) and len(geometry) == 4:
            self.setGeometry(*geometry)
        
        window_state = self.settings_manager.get("window_state")
        if window_state and isinstance(window_state, str):
            try:
                # 将十六进制字符串转换回QByteArray
                byte_array = QByteArray.fromHex(window_state.encode())
                self.restoreState(byte_array)
            except:
                pass
        
        # 加载配置
        self.load_config()
        
        # 更新模式相关控件状态
        self.on_mode_changed(self.mode_combo.currentText())
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 保存窗口状态
        self.settings_manager.set("geometry", [
            self.geometry().x(),
            self.geometry().y(),
            self.geometry().width(),
            self.geometry().height()
        ])
        
        # 保存窗口状态为QByteArray
        window_state = self.saveState()
        self.settings_manager.set("window_state", window_state)
        
        # 保存当前配置
        self.save_config()
        
        # 停止正在运行的测试
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        # 保存所有设置
        self.settings_manager.save_all()
        
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用名称
    app.setApplicationName("iperf3 GUI")
    app.setOrganizationName("Network Tools")
    
    # 创建并显示主窗口
    window = Iperf3GUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()