#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
iperf3 图形化工具
完整支持所有 iperf3 选项
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
                if self.params["daemon"]:
                    cmd.append("-D")
                if self.params["pid_file"]:
                    cmd.extend(["-I", self.params["pid_file"]])
                if self.params["server_bitrate_limit"]:
                    cmd.extend(["--server-bitrate-limit", self.params["server_bitrate_limit"]])
                if self.params["idle_timeout"]:
                    cmd.extend(["--idle-timeout", str(self.params["idle_timeout"])])
                if self.params["server_max_duration"]:
                    cmd.extend(["--server-max-duration", str(self.params["server_max_duration"])])
                if self.params["rsa_private_key_path"]:
                    cmd.extend(["--rsa-private-key-path", self.params["rsa_private_key_path"]])
                if self.params["authorized_users_path"]:
                    cmd.extend(["--authorized-users-path", self.params["authorized_users_path"]])
                if self.params["time_skew_threshold"]:
                    cmd.extend(["--time-skew-threshold", str(self.params["time_skew_threshold"])])
                if self.params["use_pkcs1_padding"]:
                    cmd.append("--use-pkcs1-padding")
            else:  # client mode
                cmd.extend(["-c", self.params["server_ip"]])
                if self.params["server_port"]:
                    cmd.extend(["-p", str(self.params["server_port"])])
                
                # 通用参数
                if self.params["protocol"] == "udp":
                    cmd.append("-u")
                    if self.params["bandwidth"]:
                        cmd.extend(["-b", self.params["bandwidth"]])
                    if self.params["udp_counters_64bit"]:
                        cmd.append("--udp-counters-64bit")
                    if self.params["repeating_payload"]:
                        cmd.append("--repeating-payload")
                
                # 连接选项
                if self.params["connect_timeout"]:
                    cmd.extend(["--connect-timeout", str(self.params["connect_timeout"])])
                if self.params["bind_dev"]:
                    cmd.extend(["--bind-dev", self.params["bind_dev"]])
                if self.params["bind_host"]:
                    cmd.extend(["-B", self.params["bind_host"]])
                
                # 测试参数
                if self.params["reverse"]:
                    cmd.append("-R")
                if self.params["bidir"]:
                    cmd.append("--bidir")
                
                if self.params["time"]:
                    cmd.extend(["-t", str(self.params["time"])])
                if self.params["bytes"]:
                    cmd.extend(["-n", self.params["bytes"]])
                if self.params["blockcount"]:
                    cmd.extend(["-k", self.params["blockcount"]])
                
                if self.params["parallel"]:
                    cmd.extend(["-P", str(self.params["parallel"])])
                
                if self.params["window_size"]:
                    cmd.extend(["-w", self.params["window_size"]])
                
                if self.params["mss"]:
                    cmd.extend(["-M", str(self.params["mss"])])
                if self.params["no_delay"]:
                    cmd.append("-N")
                
                if self.params["length"]:
                    cmd.extend(["-l", self.params["length"]])
                
                if self.params["cport"]:
                    cmd.extend(["--cport", self.params["cport"]])
                
                if self.params["interval"]:
                    cmd.extend(["-i", str(self.params["interval"])])
                
                if self.params["format"]:
                    cmd.extend(["--format", self.params["format"]])
                
                # 高级选项
                if self.params["pacing_timer"]:
                    cmd.extend(["--pacing-timer", self.params["pacing_timer"]])
                if self.params["omit"]:
                    cmd.extend(["-O", str(self.params["omit"])])
                if self.params["title"]:
                    cmd.extend(["-T", self.params["title"]])
                if self.params["extra_data"]:
                    cmd.extend(["--extra-data", self.params["extra_data"]])
                if self.params["get_server_output"]:
                    cmd.append("--get-server-output")
                if self.params["dont_fragment"]:
                    cmd.append("--dont-fragment")
                
                # 网络选项
                if self.params["ipv4_only"]:
                    cmd.append("-4")
                if self.params["ipv6_only"]:
                    cmd.append("-6")
                if self.params["tos"]:
                    cmd.extend(["-S", str(self.params["tos"])])
                if self.params["dscp"]:
                    cmd.extend(["--dscp", str(self.params["dscp"])])
                
                # 性能选项
                if self.params["zerocopy"]:
                    cmd.append("-Z")
                if self.params["skip_rx_copy"]:
                    cmd.append("--skip-rx-copy")
                
                # 认证选项
                if self.params["username"]:
                    cmd.extend(["--username", self.params["username"]])
                if self.params["rsa_public_key_path"]:
                    cmd.extend(["--rsa-public-key-path", self.params["rsa_public_key_path"]])
                
                # 文件传输
                if self.params["file"]:
                    cmd.extend(["-F", self.params["file"]])
                
                # CPU亲和性
                if self.params["affinity"]:
                    cmd.extend(["-A", self.params["affinity"]])
                
                # 输出选项
                if self.params["json_output"]:
                    cmd.append("-J")
                if self.params["json_stream"]:
                    cmd.append("--json-stream")
                if self.params["json_stream_full_output"]:
                    cmd.append("--json-stream-full-output")
                if self.params["logfile"]:
                    cmd.extend(["--logfile", self.params["logfile"]])
                if self.params["forceflush"]:
                    cmd.append("--forceflush")
                if self.params["timestamps"]:
                    if self.params["timestamps_format"]:
                        cmd.append(f"--timestamps={self.params['timestamps_format']}")
                    else:
                        cmd.append("--timestamps")
                if self.params["rcv_timeout"]:
                    cmd.extend(["--rcv-timeout", str(self.params["rcv_timeout"])])
                
                if self.params["verbose"]:
                    cmd.append("-V")
                if self.params["debug"]:
                    if self.params["debug_level"]:
                        cmd.append(f"--debug={self.params['debug_level']}")
                    else:
                        cmd.append("-d")
                if self.params["version"]:
                    cmd.append("-v")
            
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
        
        # 尝试匹配bytes传输进度
        bytes_pattern = r'\[\s*\d+\]\s+[\d\.]+\s+Bytes\s+([\d\.]+)\s+[KMG]?bits/sec'
        bytes_match = re.search(bytes_pattern, line)
        if bytes_match:
            return 50, "数据传输中..."
        
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
            # 基础设置
            "server_ip": "127.0.0.1",
            "server_port": "5201",
            "protocol": 0,
            "mode": 0,
            "time": 10,
            "parallel": 1,
            "bandwidth": "",
            "window_size": "",
            "mss": 0,
            "length": "",
            "bytes": "",
            "blockcount": "",
            "interval": 1.0,
            "format": 0,
            
            # 高级选项
            "reverse": False,
            "bidir": False,
            "json_output": False,
            "verbose": False,
            "debug": False,
            "debug_level": "",
            "version": False,
            "one_off": False,
            "daemon": False,
            
            # 服务器选项
            "server_bitrate_limit": "",
            "idle_timeout": 0,
            "server_max_duration": 0,
            "rsa_private_key_path": "",
            "authorized_users_path": "",
            "time_skew_threshold": 0.0,
            "use_pkcs1_padding": False,
            
            # 客户端选项
            "connect_timeout": 0,
            "bind_dev": "",
            "bind_host": "",
            "cport": "",
            "pacing_timer": "",
            "omit": 0,
            "title": "",
            "extra_data": "",
            "get_server_output": False,
            "udp_counters_64bit": False,
            "repeating_payload": False,
            "dont_fragment": False,
            
            # 网络选项
            "ipv4_only": False,
            "ipv6_only": False,
            "tos": 0,
            "dscp": 0,
            "no_delay": False,
            
            # 性能选项
            "zerocopy": False,
            "skip_rx_copy": False,
            "rcv_timeout": 0,
            
            # 认证选项
            "username": "",
            "rsa_public_key_path": "",
            
            # 文件选项
            "file": "",
            "pid_file": "",
            "logfile": "",
            
            # 输出选项
            "json_stream": False,
            "json_stream_full_output": False,
            "forceflush": False,
            "timestamps": False,
            "timestamps_format": "",
            
            # 系统选项
            "affinity": "",
            
            # 窗口设置
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
                            # 处理不同类型的值
                            if loaded[key] is None:
                                continue
                            elif isinstance(loaded[key], (int, float, bool, str)):
                                # 对于数值字段，确保是正确类型
                                if key in ["connect_timeout", "idle_timeout", "server_max_duration", 
                                          "omit", "tos", "dscp", "rcv_timeout"]:
                                    if isinstance(loaded[key], str):
                                        if loaded[key].strip() == "":
                                            default_settings[key] = 0
                                        else:
                                            try:
                                                default_settings[key] = int(loaded[key])
                                            except:
                                                default_settings[key] = 0
                                    else:
                                        default_settings[key] = int(loaded[key])
                                elif key in ["time_skew_threshold", "interval"]:
                                    if isinstance(loaded[key], str):
                                        if loaded[key].strip() == "":
                                            default_settings[key] = 0.0 if key == "time_skew_threshold" else 1.0
                                        else:
                                            try:
                                                default_settings[key] = float(loaded[key])
                                            except:
                                                default_settings[key] = 0.0 if key == "time_skew_threshold" else 1.0
                                    else:
                                        default_settings[key] = float(loaded[key])
                                elif key in ["time", "parallel", "mss"]:
                                    if isinstance(loaded[key], str):
                                        if loaded[key].strip() == "":
                                            default_settings[key] = 10 if key == "time" else (1 if key == "parallel" else 0)
                                        else:
                                            try:
                                                default_settings[key] = int(loaded[key])
                                            except:
                                                default_settings[key] = 10 if key == "time" else (1 if key == "parallel" else 0)
                                    else:
                                        default_settings[key] = int(loaded[key])
                                elif key in ["protocol", "mode", "format"]:
                                    if isinstance(loaded[key], str):
                                        # 兼容旧版本字符串格式
                                        if key == "protocol":
                                            if loaded[key].lower() == "tcp":
                                                default_settings[key] = 0
                                            elif loaded[key].lower() == "udp":
                                                default_settings[key] = 1
                                            else:
                                                default_settings[key] = 0
                                        elif key == "mode":
                                            if loaded[key].lower() == "client":
                                                default_settings[key] = 0
                                            elif loaded[key].lower() == "server":
                                                default_settings[key] = 1
                                            else:
                                                default_settings[key] = 0
                                        elif key == "format":
                                            format_map = {"": 0, "k": 0, "m": 1, "g": 2, "t": 3}
                                            default_settings[key] = format_map.get(loaded[key].lower(), 0)
                                    else:
                                        default_settings[key] = int(loaded[key])
                                else:
                                    default_settings[key] = loaded[key]
        except json.JSONDecodeError:
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
        self.setWindowTitle("iperf3 网络性能测试工具 - 完整版")
        self.setMinimumSize(1200, 800)
        
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
        
        # 创建高级选项标签页
        self.create_advanced_tab()
        
        # 创建服务器选项标签页
        self.create_server_tab()
        
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
        self.tab_widget.addTab(test_tab, "基础配置")
        
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
        self.server_ip_edit.setPlaceholderText("仅在客户端模式下需要")
        basic_layout.addWidget(self.server_ip_edit, 0, 3)
        
        # 端口
        basic_layout.addWidget(QLabel("端口:"), 1, 0)
        self.port_edit = QLineEdit()
        self.port_edit.setText("5201")
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
        self.time_spin.setSuffix(" 秒")
        basic_layout.addWidget(self.time_spin, 2, 1)
        
        # 并行流
        basic_layout.addWidget(QLabel("并行流:"), 2, 2)
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 128)
        self.parallel_spin.setValue(1)
        basic_layout.addWidget(self.parallel_spin, 2, 3)
        
        # 带宽限制
        basic_layout.addWidget(QLabel("带宽限制:"), 3, 0)
        self.bandwidth_combo = QComboBox()
        self.bandwidth_combo.addItems(["", "1M", "10M", "100M", "1G", "10G", "100G"])
        self.bandwidth_combo.setEditable(True)
        self.bandwidth_combo.setPlaceholderText("例如: 100M, 1G")
        basic_layout.addWidget(self.bandwidth_combo, 3, 1)
        
        # 窗口大小
        basic_layout.addWidget(QLabel("窗口大小:"), 3, 2)
        self.window_combo = QComboBox()
        self.window_combo.addItems(["", "32K", "64K", "128K", "256K", "512K", "1M", "2M", "4M", "8M"])
        self.window_combo.setEditable(True)
        self.window_combo.setPlaceholderText("例如: 64K, 1M")
        basic_layout.addWidget(self.window_combo, 3, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 传输设置组
        transfer_group = QGroupBox("传输设置")
        transfer_layout = QGridLayout()
        transfer_layout.setSpacing(10)
        
        # 传输数据量
        transfer_layout.addWidget(QLabel("传输数据量:"), 0, 0)
        self.data_amount_edit = QLineEdit()
        self.data_amount_edit.setPlaceholderText("例如: 100M, 1G")
        transfer_layout.addWidget(self.data_amount_edit, 0, 1)
        
        # 块数量
        transfer_layout.addWidget(QLabel("块数量:"), 0, 2)
        self.blockcount_edit = QLineEdit()
        self.blockcount_edit.setPlaceholderText("例如: 1000, 10000")
        transfer_layout.addWidget(self.blockcount_edit, 0, 3)
        
        # 缓冲区长度
        transfer_layout.addWidget(QLabel("缓冲区长度:"), 1, 0)
        self.length_combo = QComboBox()
        self.length_combo.addItems(["", "64K", "128K", "256K", "512K", "1M"])
        self.length_combo.setEditable(True)
        self.length_combo.setPlaceholderText("例如: 128K")
        transfer_layout.addWidget(self.length_combo, 1, 1)
        
        # 报告间隔
        transfer_layout.addWidget(QLabel("报告间隔(秒):"), 1, 2)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 10.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(1.0)
        self.interval_spin.setSuffix(" 秒")
        transfer_layout.addWidget(self.interval_spin, 1, 3)
        
        # 单位格式
        transfer_layout.addWidget(QLabel("单位格式:"), 2, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["自动", "K", "M", "G", "T"])
        transfer_layout.addWidget(self.format_combo, 2, 1)
        
        # MSS
        transfer_layout.addWidget(QLabel("MSS(最大段大小):"), 2, 2)
        self.mss_spin = QSpinBox()
        self.mss_spin.setRange(0, 9000)
        self.mss_spin.setSpecialValueText("默认")
        self.mss_spin.setSuffix(" 字节")
        transfer_layout.addWidget(self.mss_spin, 2, 3)
        
        transfer_group.setLayout(transfer_layout)
        layout.addWidget(transfer_group)
        
        # 占位弹簧
        layout.addStretch()
        
    def create_advanced_tab(self):
        """创建高级选项标签页"""
        advanced_tab = QWidget()
        self.tab_widget.addTab(advanced_tab, "高级选项")
        
        layout = QVBoxLayout(advanced_tab)
        layout.setSpacing(15)
        
        # 客户端高级选项组
        client_group = QGroupBox("客户端高级选项")
        client_layout = QGridLayout()
        client_layout.setSpacing(10)
        
        # 连接超时
        client_layout.addWidget(QLabel("连接超时(ms):"), 0, 0)
        self.connect_timeout_spin = QSpinBox()
        self.connect_timeout_spin.setRange(0, 300000)
        self.connect_timeout_spin.setSpecialValueText("默认")
        self.connect_timeout_spin.setSuffix(" ms")
        client_layout.addWidget(self.connect_timeout_spin, 0, 1)
        
        # 绑定设备
        client_layout.addWidget(QLabel("绑定设备:"), 0, 2)
        self.bind_dev_edit = QLineEdit()
        self.bind_dev_edit.setPlaceholderText("例如: eth0, wlan0")
        client_layout.addWidget(self.bind_dev_edit, 0, 3)
        
        # 绑定主机
        client_layout.addWidget(QLabel("绑定主机:"), 1, 0)
        self.bind_host_edit = QLineEdit()
        self.bind_host_edit.setPlaceholderText("IP地址或主机名")
        client_layout.addWidget(self.bind_host_edit, 1, 1)
        
        # 客户端端口
        client_layout.addWidget(QLabel("客户端端口:"), 1, 2)
        self.cport_edit = QLineEdit()
        self.cport_edit.setPlaceholderText("指定客户端端口")
        client_layout.addWidget(self.cport_edit, 1, 3)
        
        # 省略时间
        client_layout.addWidget(QLabel("省略时间(秒):"), 2, 0)
        self.omit_spin = QSpinBox()
        self.omit_spin.setRange(0, 100)
        self.omit_spin.setSpecialValueText("不省略")
        self.omit_spin.setSuffix(" 秒")
        client_layout.addWidget(self.omit_spin, 2, 1)
        
        # 标题
        client_layout.addWidget(QLabel("输出标题:"), 2, 2)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输出行前缀")
        client_layout.addWidget(self.title_edit, 2, 3)
        
        # 额外数据
        client_layout.addWidget(QLabel("额外数据:"), 3, 0)
        self.extra_data_edit = QLineEdit()
        self.extra_data_edit.setPlaceholderText("包含在JSON中的数据")
        client_layout.addWidget(self.extra_data_edit, 3, 1)
        
        client_group.setLayout(client_layout)
        layout.addWidget(client_group)
        
        # 网络选项组
        network_group = QGroupBox("网络选项")
        network_layout = QGridLayout()
        network_layout.setSpacing(10)
        
        # IP版本
        network_layout.addWidget(QLabel("IP版本:"), 0, 0)
        self.ip_version_combo = QComboBox()
        self.ip_version_combo.addItems(["自动", "仅IPv4", "仅IPv6"])
        network_layout.addWidget(self.ip_version_combo, 0, 1)
        
        # TOS
        network_layout.addWidget(QLabel("TOS(Type of Service):"), 0, 2)
        self.tos_spin = QSpinBox()
        self.tos_spin.setRange(0, 255)
        self.tos_spin.setSpecialValueText("默认")
        network_layout.addWidget(self.tos_spin, 0, 3)
        
        # DSCP
        network_layout.addWidget(QLabel("DSCP:"), 1, 0)
        self.dscp_spin = QSpinBox()
        self.dscp_spin.setRange(0, 63)
        self.dscp_spin.setSpecialValueText("默认")
        network_layout.addWidget(self.dscp_spin, 1, 1)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 性能选项组
        perf_group = QGroupBox("性能选项")
        perf_layout = QGridLayout()
        perf_layout.setSpacing(10)
        
        # 定时器
        perf_layout.addWidget(QLabel("定时器(μs):"), 0, 0)
        self.pacing_timer_edit = QLineEdit()
        self.pacing_timer_edit.setPlaceholderText("例如: 1000")
        perf_layout.addWidget(self.pacing_timer_edit, 0, 1)
        
        # 接收超时
        perf_layout.addWidget(QLabel("接收超时(ms):"), 0, 2)
        self.rcv_timeout_spin = QSpinBox()
        self.rcv_timeout_spin.setRange(0, 300000)
        self.rcv_timeout_spin.setSpecialValueText("默认")
        self.rcv_timeout_spin.setSuffix(" ms")
        perf_layout.addWidget(self.rcv_timeout_spin, 0, 3)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # 选项组
        options_group = QGroupBox("选项")
        options_layout = QGridLayout()
        options_layout.setSpacing(10)
        
        # 第一行复选框
        self.reverse_check = QCheckBox("反向测试")
        options_layout.addWidget(self.reverse_check, 0, 0)
        
        self.bidir_check = QCheckBox("双向测试")
        options_layout.addWidget(self.bidir_check, 0, 1)
        
        self.no_delay_check = QCheckBox("禁用Nagle算法")
        options_layout.addWidget(self.no_delay_check, 0, 2)
        
        self.dont_fragment_check = QCheckBox("不分片(DF标志)")
        options_layout.addWidget(self.dont_fragment_check, 0, 3)
        
        # 第二行复选框
        self.zerocopy_check = QCheckBox("零拷贝")
        options_layout.addWidget(self.zerocopy_check, 1, 0)
        
        self.skip_rx_copy_check = QCheckBox("跳过接收拷贝")
        options_layout.addWidget(self.skip_rx_copy_check, 1, 1)
        
        self.udp_counters_64bit_check = QCheckBox("UDP 64位计数器")
        options_layout.addWidget(self.udp_counters_64bit_check, 1, 2)
        
        self.repeating_payload_check = QCheckBox("重复负载")
        options_layout.addWidget(self.repeating_payload_check, 1, 3)
        
        # 第三行复选框
        self.get_server_output_check = QCheckBox("获取服务器输出")
        options_layout.addWidget(self.get_server_output_check, 2, 0)
        
        self.one_off_check = QCheckBox("单次连接")
        options_layout.addWidget(self.one_off_check, 2, 1)
        
        self.daemon_check = QCheckBox("守护进程模式")
        options_layout.addWidget(self.daemon_check, 2, 2)
        
        self.use_pkcs1_padding_check = QCheckBox("使用PKCS1填充")
        options_layout.addWidget(self.use_pkcs1_padding_check, 2, 3)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 占位弹簧
        layout.addStretch()
        
    def create_server_tab(self):
        """创建服务器选项标签页"""
        server_tab = QWidget()
        self.tab_widget.addTab(server_tab, "服务器选项")
        
        layout = QVBoxLayout(server_tab)
        layout.setSpacing(15)
        
        # 服务器限制组
        limits_group = QGroupBox("服务器限制")
        limits_layout = QGridLayout()
        limits_layout.setSpacing(10)
        
        # 服务器比特率限制
        limits_layout.addWidget(QLabel("服务器比特率限制:"), 0, 0)
        self.server_bitrate_limit_edit = QLineEdit()
        self.server_bitrate_limit_edit.setPlaceholderText("例如: 100M, 1G")
        limits_layout.addWidget(self.server_bitrate_limit_edit, 0, 1)
        
        # 空闲超时
        limits_layout.addWidget(QLabel("空闲超时(秒):"), 0, 2)
        self.idle_timeout_spin = QSpinBox()
        self.idle_timeout_spin.setRange(0, 3600)
        self.idle_timeout_spin.setSpecialValueText("无限制")
        self.idle_timeout_spin.setSuffix(" 秒")
        limits_layout.addWidget(self.idle_timeout_spin, 0, 3)
        
        # 服务器最大持续时间
        limits_layout.addWidget(QLabel("服务器最大持续时间(秒):"), 1, 0)
        self.server_max_duration_spin = QSpinBox()
        self.server_max_duration_spin.setRange(0, 86400)
        self.server_max_duration_spin.setSpecialValueText("无限制")
        self.server_max_duration_spin.setSuffix(" 秒")
        limits_layout.addWidget(self.server_max_duration_spin, 1, 1)
        
        # 时间偏差阈值
        limits_layout.addWidget(QLabel("时间偏差阈值(秒):"), 1, 2)
        self.time_skew_threshold_spin = QDoubleSpinBox()
        self.time_skew_threshold_spin.setRange(0.0, 100.0)
        self.time_skew_threshold_spin.setSpecialValueText("默认")
        self.time_skew_threshold_spin.setSuffix(" 秒")
        limits_layout.addWidget(self.time_skew_threshold_spin, 1, 3)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # 认证选项组
        auth_group = QGroupBox("认证选项")
        auth_layout = QGridLayout()
        auth_layout.setSpacing(10)
        
        # 用户名
        auth_layout.addWidget(QLabel("用户名:"), 0, 0)
        self.username_edit = QLineEdit()
        auth_layout.addWidget(self.username_edit, 0, 1)
        
        # RSA私钥路径
        auth_layout.addWidget(QLabel("RSA私钥路径:"), 0, 2)
        self.rsa_private_key_path_edit = QLineEdit()
        self.rsa_private_key_path_edit.setPlaceholderText("服务器私钥文件路径")
        auth_layout.addWidget(self.rsa_private_key_path_edit, 0, 3)
        
        # RSA公钥路径
        auth_layout.addWidget(QLabel("RSA公钥路径:"), 1, 0)
        self.rsa_public_key_path_edit = QLineEdit()
        self.rsa_public_key_path_edit.setPlaceholderText("客户端公钥文件路径")
        auth_layout.addWidget(self.rsa_public_key_path_edit, 1, 1)
        
        # 授权用户路径
        auth_layout.addWidget(QLabel("授权用户路径:"), 1, 2)
        self.authorized_users_path_edit = QLineEdit()
        self.authorized_users_path_edit.setPlaceholderText("用户配置文件路径")
        auth_layout.addWidget(self.authorized_users_path_edit, 1, 3)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # 文件选项组
        file_group = QGroupBox("文件选项")
        file_layout = QGridLayout()
        file_layout.setSpacing(10)
        
        # 文件传输
        file_layout.addWidget(QLabel("文件传输:"), 0, 0)
        self.file_edit = QLineEdit()
        file_button = QPushButton("浏览...")
        file_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_edit, 0, 1)
        file_layout.addWidget(file_button, 0, 2)
        
        # PID文件
        file_layout.addWidget(QLabel("PID文件:"), 1, 0)
        self.pid_file_edit = QLineEdit()
        pid_file_button = QPushButton("浏览...")
        pid_file_button.clicked.connect(self.browse_pid_file)
        file_layout.addWidget(self.pid_file_edit, 1, 1)
        file_layout.addWidget(pid_file_button, 1, 2)
        
        # 日志文件
        file_layout.addWidget(QLabel("日志文件:"), 2, 0)
        self.logfile_edit = QLineEdit()
        logfile_button = QPushButton("浏览...")
        logfile_button.clicked.connect(self.browse_logfile)
        file_layout.addWidget(self.logfile_edit, 2, 1)
        file_layout.addWidget(logfile_button, 2, 2)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 系统选项组
        system_group = QGroupBox("系统选项")
        system_layout = QGridLayout()
        system_layout.setSpacing(10)
        
        # CPU亲和性
        system_layout.addWidget(QLabel("CPU亲和性:"), 0, 0)
        self.affinity_edit = QLineEdit()
        self.affinity_edit.setPlaceholderText("例如: 0 或 0,1")
        system_layout.addWidget(self.affinity_edit, 0, 1)
        
        # 时间戳格式
        system_layout.addWidget(QLabel("时间戳格式:"), 0, 2)
        self.timestamps_format_edit = QLineEdit()
        self.timestamps_format_edit.setPlaceholderText("strftime格式，例如: %H:%M:%S")
        system_layout.addWidget(self.timestamps_format_edit, 0, 3)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        # 输出选项组
        output_group = QGroupBox("输出选项")
        output_layout = QGridLayout()
        output_layout.setSpacing(10)
        
        # 复选框
        self.json_check = QCheckBox("JSON输出")
        output_layout.addWidget(self.json_check, 0, 0)
        
        self.json_stream_check = QCheckBox("JSON流输出")
        output_layout.addWidget(self.json_stream_check, 0, 1)
        
        self.json_stream_full_output_check = QCheckBox("完整JSON流输出")
        output_layout.addWidget(self.json_stream_full_output_check, 0, 2)
        
        self.verbose_check = QCheckBox("详细输出")
        output_layout.addWidget(self.verbose_check, 0, 3)
        
        self.version_check = QCheckBox("显示版本")
        output_layout.addWidget(self.version_check, 1, 0)
        
        self.debug_check = QCheckBox("调试模式")
        output_layout.addWidget(self.debug_check, 1, 1)
        
        self.forceflush_check = QCheckBox("强制刷新输出")
        output_layout.addWidget(self.forceflush_check, 1, 2)
        
        self.timestamps_check = QCheckBox("时间戳")
        output_layout.addWidget(self.timestamps_check, 1, 3)
        
        # 调试级别
        output_layout.addWidget(QLabel("调试级别:"), 2, 0)
        self.debug_level_combo = QComboBox()
        self.debug_level_combo.addItems(["1", "2", "3", "4"])
        self.debug_level_combo.setCurrentIndex(3)
        output_layout.addWidget(self.debug_level_combo, 2, 1)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
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
            ("包数量:", "packets"),
            ("重传:", "retransmits"),
            ("发送者:", "sender"),
            ("接收者:", "receiver")
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
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "模式", "协议", "服务器", "带宽", "抖动", "丢包", "持续时间", "并行流", "备注"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.clear_history_btn = QPushButton("清空历史")
        self.export_history_btn = QPushButton("导出记录")
        self.load_history_btn = QPushButton("加载历史")
        self.save_result_btn = QPushButton("保存结果")
        
        button_layout.addWidget(self.clear_history_btn)
        button_layout.addWidget(self.export_history_btn)
        button_layout.addWidget(self.load_history_btn)
        button_layout.addWidget(self.save_result_btn)
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
        self.help_btn = QPushButton("帮助")
        
        # 添加到布局
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.reset_btn)
        control_layout.addWidget(self.help_btn)
        
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
        self.save_result_btn.clicked.connect(self.save_result)
        self.help_btn.clicked.connect(self.show_help)
        
        # 模式切换
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        # 协议切换
        self.protocol_combo.currentTextChanged.connect(self.on_protocol_changed)
        
    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "所有文件 (*)"
        )
        if file_path:
            self.file_edit.setText(file_path)
    
    def browse_pid_file(self):
        """浏览PID文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择PID文件", "", "所有文件 (*)"
        )
        if file_path:
            self.pid_file_edit.setText(file_path)
    
    def browse_logfile(self):
        """浏览日志文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择日志文件", "", "日志文件 (*.log);;所有文件 (*)"
        )
        if file_path:
            self.logfile_edit.setText(file_path)
    
    def show_help(self):
        """显示帮助"""
        help_text = """
        iperf3 网络性能测试工具 - 完整版
        
        支持所有 iperf3 选项：
        
        基础选项：
        - -c/-s: 客户端/服务器模式
        - -p: 端口号
        - -t: 测试时间
        - -P: 并行流数量
        - -u: UDP协议
        - -b: 带宽限制
        
        高级选项：
        - -w: TCP窗口大小
        - -M: TCP MSS大小
        - -N: 禁用Nagle算法
        - -R: 反向测试
        - --bidir: 双向测试
        - -4/-6: IPv4/IPv6
        
        服务器选项：
        - -D: 守护进程模式
        - --server-bitrate-limit: 服务器带宽限制
        - --idle-timeout: 空闲超时
        
        认证选项：
        - --username: 用户名
        - --rsa-private-key-path: RSA私钥路径
        
        更多信息请参考 iperf3 官方文档。
        """
        
        QMessageBox.information(self, "帮助", help_text)
    
    def on_mode_changed(self, mode):
        """处理模式切换"""
        is_client = (mode == "客户端")
        self.server_ip_edit.setEnabled(is_client)
        self.time_spin.setEnabled(is_client)
        self.bandwidth_combo.setEnabled(is_client)
        self.reverse_check.setEnabled(is_client)
        self.bidir_check.setEnabled(is_client)
        self.data_amount_edit.setEnabled(is_client)
        self.blockcount_edit.setEnabled(is_client)
        
    def on_protocol_changed(self, protocol):
        """处理协议切换"""
        is_udp = (protocol == "UDP")
        self.udp_counters_64bit_check.setEnabled(is_udp)
        self.repeating_payload_check.setEnabled(is_udp)
        
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
            # 基础参数
            "mode": "server" if self.mode_combo.currentText() == "服务器" else "client",
            "server_ip": self.server_ip_edit.text().strip(),
            "server_port": self.port_edit.text().strip() or "5201",
            "protocol": "udp" if self.protocol_combo.currentText() == "UDP" else "tcp",
            "time": self.time_spin.value(),
            "parallel": self.parallel_spin.value(),
            "bandwidth": self.bandwidth_combo.currentText().strip(),
            "window_size": self.window_combo.currentText().strip(),
            "mss": self.mss_spin.value() if self.mss_spin.value() > 0 else "",
            "length": self.length_combo.currentText().strip(),
            "bytes": self.data_amount_edit.text().strip(),
            "blockcount": self.blockcount_edit.text().strip(),
            "interval": self.interval_spin.value(),
            "format": {"自动": "", "K": "k", "M": "m", "G": "g", "T": "t"}[self.format_combo.currentText()],
            
            # 高级选项
            "reverse": self.reverse_check.isChecked(),
            "bidir": self.bidir_check.isChecked(),
            "connect_timeout": self.connect_timeout_spin.value() if self.connect_timeout_spin.value() > 0 else "",
            "bind_dev": self.bind_dev_edit.text().strip(),
            "bind_host": self.bind_host_edit.text().strip(),
            "cport": self.cport_edit.text().strip(),
            "pacing_timer": self.pacing_timer_edit.text().strip(),
            "omit": self.omit_spin.value() if self.omit_spin.value() > 0 else "",
            "title": self.title_edit.text().strip(),
            "extra_data": self.extra_data_edit.text().strip(),
            "get_server_output": self.get_server_output_check.isChecked(),
            "udp_counters_64bit": self.udp_counters_64bit_check.isChecked(),
            "repeating_payload": self.repeating_payload_check.isChecked(),
            "dont_fragment": self.dont_fragment_check.isChecked(),
            
            # 网络选项
            "ipv4_only": self.ip_version_combo.currentText() == "仅IPv4",
            "ipv6_only": self.ip_version_combo.currentText() == "仅IPv6",
            "tos": self.tos_spin.value() if self.tos_spin.value() > 0 else "",
            "dscp": self.dscp_spin.value() if self.dscp_spin.value() > 0 else "",
            "no_delay": self.no_delay_check.isChecked(),
            
            # 性能选项
            "zerocopy": self.zerocopy_check.isChecked(),
            "skip_rx_copy": self.skip_rx_copy_check.isChecked(),
            "rcv_timeout": self.rcv_timeout_spin.value() if self.rcv_timeout_spin.value() > 0 else "",
            
            # 认证选项
            "username": self.username_edit.text().strip(),
            "rsa_public_key_path": self.rsa_public_key_path_edit.text().strip(),
            
            # 服务器选项
            "one_off": self.one_off_check.isChecked(),
            "daemon": self.daemon_check.isChecked(),
            "server_bitrate_limit": self.server_bitrate_limit_edit.text().strip(),
            "idle_timeout": self.idle_timeout_spin.value() if self.idle_timeout_spin.value() > 0 else "",
            "server_max_duration": self.server_max_duration_spin.value() if self.server_max_duration_spin.value() > 0 else "",
            "rsa_private_key_path": self.rsa_private_key_path_edit.text().strip(),
            "authorized_users_path": self.authorized_users_path_edit.text().strip(),
            "time_skew_threshold": self.time_skew_threshold_spin.value() if self.time_skew_threshold_spin.value() > 0 else "",
            "use_pkcs1_padding": self.use_pkcs1_padding_check.isChecked(),
            
            # 文件选项
            "file": self.file_edit.text().strip(),
            "pid_file": self.pid_file_edit.text().strip(),
            "logfile": self.logfile_edit.text().strip(),
            
            # 输出选项
            "json_output": self.json_check.isChecked(),
            "json_stream": self.json_stream_check.isChecked(),
            "json_stream_full_output": self.json_stream_full_output_check.isChecked(),
            "verbose": self.verbose_check.isChecked(),
            "debug": self.debug_check.isChecked(),
            "debug_level": self.debug_level_combo.currentText() if self.debug_check.isChecked() else "",
            "version": self.version_check.isChecked(),
            "forceflush": self.forceflush_check.isChecked(),
            "timestamps": self.timestamps_check.isChecked(),
            "timestamps_format": self.timestamps_format_edit.text().strip(),
            
            # 系统选项
            "affinity": self.affinity_edit.text().strip()
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
                elif 'Kbits/sec' in line:
                    match = re.search(r'([\d\.]+)\s+Kbits/sec', line)
                    if match:
                        self.stats_labels['bandwidth'].setText(f"{match.group(1)} Kbps")
                
                # 解析抖动
                if 'ms' in line and ('jitter' in line.lower() or 'Jitter' in line):
                    match = re.search(r'[Jj]itter\s*[\:=]\s*([\d\.]+)\s*ms', line)
                    if match:
                        self.stats_labels['jitter'].setText(f"{match.group(1)} ms")
                
                # 解析丢包
                if 'loss' in line.lower():
                    match = re.search(r'([\d\.]+)%', line)
                    if match:
                        self.stats_labels['loss'].setText(f"{match.group(1)}%")
                
                # 解析重传
                if 'retransmits' in line.lower():
                    match = re.search(r'([\d\.]+)', line)
                    if match:
                        self.stats_labels['retransmits'].setText(f"{match.group(1)}")
                
                # 解析数据量
                if 'Bytes' in line and 'bits/sec' in line:
                    match = re.search(r'([\d\.]+)\s+Bytes', line)
                    if match:
                        bytes_value = float(match.group(1))
                        if bytes_value > 1e9:
                            self.stats_labels['bytes'].setText(f"{bytes_value/1e9:.2f} GB")
                        elif bytes_value > 1e6:
                            self.stats_labels['bytes'].setText(f"{bytes_value/1e6:.2f} MB")
                        elif bytes_value > 1e3:
                            self.stats_labels['bytes'].setText(f"{bytes_value/1e3:.2f} KB")
                        else:
                            self.stats_labels['bytes'].setText(f"{bytes_value} Bytes")
                        
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
        
    def save_result(self):
        """保存测试结果"""
        if not self.result_text.toPlainText().strip():
            QMessageBox.warning(self, "警告", "没有测试结果可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存测试结果", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("iperf3 测试结果\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"测试模式: {self.mode_combo.currentText()}\n")
                    f.write(f"协议: {self.protocol_combo.currentText()}\n")
                    f.write(f"服务器: {self.server_ip_edit.text()}\n")
                    f.write(f"端口: {self.port_edit.text()}\n\n")
                    f.write("测试结果:\n")
                    f.write("=" * 50 + "\n")
                    f.write(self.result_text.toPlainText())
                
                QMessageBox.information(self, "成功", f"测试结果已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        config = {
            # 基础设置
            "server_ip": self.server_ip_edit.text(),
            "server_port": self.port_edit.text(),
            "protocol": self.protocol_combo.currentIndex(),
            "mode": self.mode_combo.currentIndex(),
            "time": self.time_spin.value(),
            "parallel": self.parallel_spin.value(),
            "bandwidth": self.bandwidth_combo.currentText(),
            "window_size": self.window_combo.currentText(),
            "mss": self.mss_spin.value(),
            "length": self.length_combo.currentText(),
            "bytes": self.data_amount_edit.text(),
            "blockcount": self.blockcount_edit.text(),
            "interval": self.interval_spin.value(),
            "format": self.format_combo.currentIndex(),
            
            # 高级选项
            "reverse": self.reverse_check.isChecked(),
            "bidir": self.bidir_check.isChecked(),
            "connect_timeout": self.connect_timeout_spin.value(),
            "bind_dev": self.bind_dev_edit.text(),
            "bind_host": self.bind_host_edit.text(),
            "cport": self.cport_edit.text(),
            "pacing_timer": self.pacing_timer_edit.text(),
            "omit": self.omit_spin.value(),
            "title": self.title_edit.text(),
            "extra_data": self.extra_data_edit.text(),
            "get_server_output": self.get_server_output_check.isChecked(),
            "udp_counters_64bit": self.udp_counters_64bit_check.isChecked(),
            "repeating_payload": self.repeating_payload_check.isChecked(),
            "dont_fragment": self.dont_fragment_check.isChecked(),
            
            # 网络选项
            "ipv4_only": self.ip_version_combo.currentIndex() == 1,
            "ipv6_only": self.ip_version_combo.currentIndex() == 2,
            "tos": self.tos_spin.value(),
            "dscp": self.dscp_spin.value(),
            "no_delay": self.no_delay_check.isChecked(),
            
            # 性能选项
            "zerocopy": self.zerocopy_check.isChecked(),
            "skip_rx_copy": self.skip_rx_copy_check.isChecked(),
            "rcv_timeout": self.rcv_timeout_spin.value(),
            
            # 认证选项
            "username": self.username_edit.text(),
            "rsa_public_key_path": self.rsa_public_key_path_edit.text(),
            
            # 服务器选项
            "one_off": self.one_off_check.isChecked(),
            "daemon": self.daemon_check.isChecked(),
            "server_bitrate_limit": self.server_bitrate_limit_edit.text(),
            "idle_timeout": self.idle_timeout_spin.value(),
            "server_max_duration": self.server_max_duration_spin.value(),
            "rsa_private_key_path": self.rsa_private_key_path_edit.text(),
            "authorized_users_path": self.authorized_users_path_edit.text(),
            "time_skew_threshold": self.time_skew_threshold_spin.value(),
            "use_pkcs1_padding": self.use_pkcs1_padding_check.isChecked(),
            
            # 文件选项
            "file": self.file_edit.text(),
            "pid_file": self.pid_file_edit.text(),
            "logfile": self.logfile_edit.text(),
            
            # 输出选项
            "json_output": self.json_check.isChecked(),
            "json_stream": self.json_stream_check.isChecked(),
            "json_stream_full_output": self.json_stream_full_output_check.isChecked(),
            "verbose": self.verbose_check.isChecked(),
            "debug": self.debug_check.isChecked(),
            "debug_level": self.debug_level_combo.currentText(),
            "version": self.version_check.isChecked(),
            "forceflush": self.forceflush_check.isChecked(),
            "timestamps": self.timestamps_check.isChecked(),
            "timestamps_format": self.timestamps_format_edit.text(),
            
            # 系统选项
            "affinity": self.affinity_edit.text()
        }
        
        self.settings_manager.settings.update(config)
        if self.settings_manager.save_all():
            QMessageBox.information(self, "成功", "配置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存配置失败")
    
    def load_config(self):
        """加载配置"""
        # 基础设置
        self.server_ip_edit.setText(str(self.settings_manager.get("server_ip", "")))
        self.port_edit.setText(str(self.settings_manager.get("server_port", "5201")))
        
        # 下拉框
        self.protocol_combo.setCurrentIndex(int(self.settings_manager.get("protocol", 0)))
        self.mode_combo.setCurrentIndex(int(self.settings_manager.get("mode", 0)))
        self.format_combo.setCurrentIndex(int(self.settings_manager.get("format", 0)))
        
        # 数值设置
        self.time_spin.setValue(int(self.settings_manager.get("time", 10)))
        self.parallel_spin.setValue(int(self.settings_manager.get("parallel", 1)))
        self.mss_spin.setValue(int(self.settings_manager.get("mss", 0)))
        self.interval_spin.setValue(float(self.settings_manager.get("interval", 1.0)))
        
        # 文本设置
        self.bandwidth_combo.setCurrentText(str(self.settings_manager.get("bandwidth", "")))
        self.window_combo.setCurrentText(str(self.settings_manager.get("window_size", "")))
        self.length_combo.setCurrentText(str(self.settings_manager.get("length", "")))
        self.data_amount_edit.setText(str(self.settings_manager.get("bytes", "")))
        self.blockcount_edit.setText(str(self.settings_manager.get("blockcount", "")))
        
        # 高级选项 - 修复这里，添加安全转换
        try:
            self.connect_timeout_spin.setValue(int(self.settings_manager.get("connect_timeout", 0)))
        except (ValueError, TypeError):
            self.connect_timeout_spin.setValue(0)
            
        self.bind_dev_edit.setText(str(self.settings_manager.get("bind_dev", "")))
        self.bind_host_edit.setText(str(self.settings_manager.get("bind_host", "")))
        self.cport_edit.setText(str(self.settings_manager.get("cport", "")))
        self.pacing_timer_edit.setText(str(self.settings_manager.get("pacing_timer", "")))
        
        try:
            self.omit_spin.setValue(int(self.settings_manager.get("omit", 0)))
        except (ValueError, TypeError):
            self.omit_spin.setValue(0)
            
        self.title_edit.setText(str(self.settings_manager.get("title", "")))
        self.extra_data_edit.setText(str(self.settings_manager.get("extra_data", "")))
        
        # 网络选项
        ip_version = 0
        if self.settings_manager.get("ipv4_only", False):
            ip_version = 1
        elif self.settings_manager.get("ipv6_only", False):
            ip_version = 2
        self.ip_version_combo.setCurrentIndex(ip_version)
        
        try:
            self.tos_spin.setValue(int(self.settings_manager.get("tos", 0)))
        except (ValueError, TypeError):
            self.tos_spin.setValue(0)
            
        try:
            self.dscp_spin.setValue(int(self.settings_manager.get("dscp", 0)))
        except (ValueError, TypeError):
            self.dscp_spin.setValue(0)
            
        # 服务器选项
        self.server_bitrate_limit_edit.setText(str(self.settings_manager.get("server_bitrate_limit", "")))
        
        try:
            self.idle_timeout_spin.setValue(int(self.settings_manager.get("idle_timeout", 0)))
        except (ValueError, TypeError):
            self.idle_timeout_spin.setValue(0)
            
        try:
            self.server_max_duration_spin.setValue(int(self.settings_manager.get("server_max_duration", 0)))
        except (ValueError, TypeError):
            self.server_max_duration_spin.setValue(0)
            
        try:
            self.time_skew_threshold_spin.setValue(float(self.settings_manager.get("time_skew_threshold", 0.0)))
        except (ValueError, TypeError):
            self.time_skew_threshold_spin.setValue(0.0)
            
        # 认证选项
        self.username_edit.setText(str(self.settings_manager.get("username", "")))
        self.rsa_private_key_path_edit.setText(str(self.settings_manager.get("rsa_private_key_path", "")))
        self.rsa_public_key_path_edit.setText(str(self.settings_manager.get("rsa_public_key_path", "")))
        self.authorized_users_path_edit.setText(str(self.settings_manager.get("authorized_users_path", "")))
        
        # 文件选项
        self.file_edit.setText(str(self.settings_manager.get("file", "")))
        self.pid_file_edit.setText(str(self.settings_manager.get("pid_file", "")))
        self.logfile_edit.setText(str(self.settings_manager.get("logfile", "")))
        
        # 系统选项
        self.affinity_edit.setText(str(self.settings_manager.get("affinity", "")))
        self.timestamps_format_edit.setText(str(self.settings_manager.get("timestamps_format", "")))
        
        # 性能选项
        try:
            self.rcv_timeout_spin.setValue(int(self.settings_manager.get("rcv_timeout", 0)))
        except (ValueError, TypeError):
            self.rcv_timeout_spin.setValue(0)
            
        # 复选框
        self.reverse_check.setChecked(bool(self.settings_manager.get("reverse", False)))
        self.bidir_check.setChecked(bool(self.settings_manager.get("bidir", False)))
        self.get_server_output_check.setChecked(bool(self.settings_manager.get("get_server_output", False)))
        self.udp_counters_64bit_check.setChecked(bool(self.settings_manager.get("udp_counters_64bit", False)))
        self.repeating_payload_check.setChecked(bool(self.settings_manager.get("repeating_payload", False)))
        self.dont_fragment_check.setChecked(bool(self.settings_manager.get("dont_fragment", False)))
        self.no_delay_check.setChecked(bool(self.settings_manager.get("no_delay", False)))
        self.zerocopy_check.setChecked(bool(self.settings_manager.get("zerocopy", False)))
        self.skip_rx_copy_check.setChecked(bool(self.settings_manager.get("skip_rx_copy", False)))
        
        # 服务器复选框
        self.one_off_check.setChecked(bool(self.settings_manager.get("one_off", False)))
        self.daemon_check.setChecked(bool(self.settings_manager.get("daemon", False)))
        self.use_pkcs1_padding_check.setChecked(bool(self.settings_manager.get("use_pkcs1_padding", False)))
        
        # 输出复选框
        self.json_check.setChecked(bool(self.settings_manager.get("json_output", False)))
        self.json_stream_check.setChecked(bool(self.settings_manager.get("json_stream", False)))
        self.json_stream_full_output_check.setChecked(bool(self.settings_manager.get("json_stream_full_output", False)))
        self.verbose_check.setChecked(bool(self.settings_manager.get("verbose", False)))
        self.debug_check.setChecked(bool(self.settings_manager.get("debug", False)))
        self.version_check.setChecked(bool(self.settings_manager.get("version", False)))
        self.forceflush_check.setChecked(bool(self.settings_manager.get("forceflush", False)))
        self.timestamps_check.setChecked(bool(self.settings_manager.get("timestamps", False)))
        
        # 调试级别
        debug_level = str(self.settings_manager.get("debug_level", "4"))
        index = self.debug_level_combo.findText(debug_level)
        if index >= 0:
            self.debug_level_combo.setCurrentIndex(index)
        
        QMessageBox.information(self, "成功", "配置已加载")
        
        # 更新模式相关控件状态
        self.on_mode_changed(self.mode_combo.currentText())
        self.on_protocol_changed(self.protocol_combo.currentText())
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要重置所有配置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings_manager = SettingsManager()
            self.load_config()
    
    def save_to_history(self):
        """保存到历史记录"""
        try:
            bandwidth = self.stats_labels['bandwidth'].text()
            if bandwidth != "--":
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                mode = self.mode_combo.currentText()
                protocol = self.protocol_combo.currentText()
                server = self.server_ip_edit.text()
                jitter = self.stats_labels['jitter'].text()
                loss = self.stats_labels['loss'].text()
                duration = str(self.time_spin.value())
                parallel = str(self.parallel_spin.value())
                
                note = ""
                if self.reverse_check.isChecked():
                    note += "反向 "
                if self.bidir_check.isChecked():
                    note += "双向 "
                
                self.history_table.setItem(row, 0, QTableWidgetItem(current_time))
                self.history_table.setItem(row, 1, QTableWidgetItem(mode))
                self.history_table.setItem(row, 2, QTableWidgetItem(protocol))
                self.history_table.setItem(row, 3, QTableWidgetItem(server))
                self.history_table.setItem(row, 4, QTableWidgetItem(bandwidth))
                self.history_table.setItem(row, 5, QTableWidgetItem(jitter))
                self.history_table.setItem(row, 6, QTableWidgetItem(loss))
                self.history_table.setItem(row, 7, QTableWidgetItem(duration))
                self.history_table.setItem(row, 8, QTableWidgetItem(parallel))
                self.history_table.setItem(row, 9, QTableWidgetItem(note.strip()))
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
                            if len(data) >= 10:
                                row = self.history_table.rowCount()
                                self.history_table.insertRow(row)
                                
                                for col in range(min(10, len(data))):
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
        self.on_protocol_changed(self.protocol_combo.currentText())
    
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
    app.setApplicationName("iperf3 GUI - 完整版")
    app.setOrganizationName("Network Tools")
    
    # 创建并显示主窗口
    window = Iperf3GUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()