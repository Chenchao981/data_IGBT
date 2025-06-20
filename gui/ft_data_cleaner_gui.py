c'dcd#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FT数据清洗工具 - GUI版本
功能：集成DC、DVDS、RG三种数据清洗功能，提供统一的图形界面
作者：cc
创建时间：2025-01-20
"""

import sys
import os
import threading
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QRadioButton, QButtonGroup, QGroupBox,
                             QFileDialog, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# 导入现有的清洗器类
project_root = Path(__file__).parent.parent  # 项目根目录
sys.path.append(str(project_root / 'dc_processing'))
sys.path.append(str(project_root / 'dvds_processing'))  
sys.path.append(str(project_root / 'rg_processing'))

from dc_cleaner import DCDataCleaner
from dvds_cleaner import DVDSCleaner
from rg_cleaner import RGCleaner

class DataCleanerWorker(QThread):
    """数据清洗工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str)  # 进度更新信号
    finished = pyqtSignal(str, bool)    # 完成信号 (结果信息, 是否成功)
    error_occurred = pyqtSignal(str)    # 错误信号
    
    def __init__(self, cleaner_type, input_dir, output_dir):
        super().__init__()
        self.cleaner_type = cleaner_type
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.is_cancelled = False
    
    def run(self):
        """运行数据清洗任务"""
        try:
            self.progress_updated.emit(f"开始{self.cleaner_type}数据清洗...")
            
            if self.cleaner_type == "DC":
                self._run_dc_cleaner()
            elif self.cleaner_type == "DVDS":
                self._run_dvds_cleaner()
            elif self.cleaner_type == "RG":
                self._run_rg_cleaner()
            else:
                self.error_occurred.emit("未知的清洗类型")
                return
                
        except Exception as e:
            self.error_occurred.emit(f"清洗过程中发生错误: {str(e)}")
    
    def _run_dc_cleaner(self):
        """运行DC清洗器"""
        try:
            self.progress_updated.emit("正在初始化DC清洗器...")
            cleaner = DCDataCleaner(input_dir=self.input_dir, output_dir=self.output_dir)
            
            self.progress_updated.emit("正在扫描DC文件...")
            success = cleaner.process_all_dc_files()
            
            if success:
                self.progress_updated.emit("DC数据清洗完成！")
                self.finished.emit("DC数据清洗成功完成", True)
            else:
                self.finished.emit("DC数据清洗失败，请查看日志信息", False)
                
        except Exception as e:
            self.error_occurred.emit(f"DC清洗器运行错误: {str(e)}")
    
    def _run_dvds_cleaner(self):
        """运行DVDS清洗器"""
        try:
            self.progress_updated.emit("正在初始化DVDS清洗器...")
            cleaner = DVDSCleaner(base_dir=str(Path(self.input_dir).parent))
            
            # 设置输入和输出目录
            cleaner.dvds_dir = self.input_dir
            cleaner.output_dir = self.output_dir
            
            self.progress_updated.emit("正在处理DVDS数据...")
            output_file = cleaner.process_all()
            
            if output_file:
                self.progress_updated.emit("DVDS数据清洗完成！")
                self.finished.emit(f"DVDS数据清洗成功完成\n输出文件: {os.path.basename(output_file)}", True)
            else:
                self.finished.emit("DVDS数据清洗失败，请查看日志信息", False)
                
        except Exception as e:
            self.error_occurred.emit(f"DVDS清洗器运行错误: {str(e)}")
    
    def _run_rg_cleaner(self):
        """运行RG清洗器"""
        try:
            self.progress_updated.emit("正在初始化RG清洗器...")
            cleaner = RGCleaner(input_dir=self.input_dir, output_dir=self.output_dir)
            
            self.progress_updated.emit("正在处理RG数据...")
            output_file = cleaner.run()
            
            if output_file:
                self.progress_updated.emit("RG数据清洗完成！")
                self.finished.emit(f"RG数据清洗成功完成\n输出文件: {os.path.basename(output_file)}", True)
            else:
                self.finished.emit("RG数据清洗失败，请查看日志信息", False)
                
        except Exception as e:
            self.error_occurred.emit(f"RG清洗器运行错误: {str(e)}")
    
    def cancel(self):
        """取消任务"""
        self.is_cancelled = True
        self.terminate()


class FTDataCleanerGUI(QMainWindow):
    """FT数据清洗工具主界面"""
    
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.init_ui()
        self.setup_default_paths()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("FT数据清洗工具")
        self.setGeometry(100, 100, 600, 500)
        
        # 设置应用程序图标（如果有的话）
        # self.setWindowIcon(QIcon('icon.png'))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题标签
        title_label = QLabel("FT数据清洗工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 清洗类型选择组
        self.create_cleaner_type_group(main_layout)
        
        # 文件夹选择组
        self.create_folder_selection_group(main_layout)
        
        # 操作按钮组
        self.create_action_buttons_group(main_layout)
        
        # 处理状态显示区域
        self.create_status_display_group(main_layout)
        
        # 设置样式
        self.set_styles()
    
    def create_cleaner_type_group(self, main_layout):
        """创建清洗类型选择组"""
        type_group = QGroupBox("清洗类型选择")
        type_layout = QHBoxLayout(type_group)
        
        # 创建单选按钮组
        self.cleaner_button_group = QButtonGroup()
        
        self.dc_radio = QRadioButton("DC")
        self.dvds_radio = QRadioButton("DVDS")
        self.rg_radio = QRadioButton("RG")
        
        # 默认选择DC
        self.dc_radio.setChecked(True)
        
        # 添加到按钮组
        self.cleaner_button_group.addButton(self.dc_radio)
        self.cleaner_button_group.addButton(self.dvds_radio)
        self.cleaner_button_group.addButton(self.rg_radio)
        
        # 连接信号，当清洗类型改变时更新默认路径
        self.dc_radio.toggled.connect(self.on_cleaner_type_changed)
        self.dvds_radio.toggled.connect(self.on_cleaner_type_changed)
        self.rg_radio.toggled.connect(self.on_cleaner_type_changed)
        
        # 添加到布局
        type_layout.addWidget(self.dc_radio)
        type_layout.addWidget(self.dvds_radio)
        type_layout.addWidget(self.rg_radio)
        type_layout.addStretch()
        
        main_layout.addWidget(type_group)
    
    def create_folder_selection_group(self, main_layout):
        """创建文件夹选择组"""
        folder_group = QGroupBox("文件夹选择")
        folder_layout = QVBoxLayout(folder_group)
        
        # 数据文件夹选择
        input_layout = QHBoxLayout()
        input_label = QLabel("数据文件夹:")
        input_label.setMinimumWidth(100)
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("选择包含源数据的文件夹...")
        self.input_browse_btn = QPushButton("选择文件夹...")
        self.input_browse_btn.clicked.connect(self.browse_input_folder)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_btn)
        
        # 输出文件夹选择
        output_layout = QHBoxLayout()
        output_label = QLabel("输出文件夹:")
        output_label.setMinimumWidth(100)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出清洗后数据的文件夹...")
        self.output_browse_btn = QPushButton("选择文件夹...")
        self.output_browse_btn.clicked.connect(self.browse_output_folder)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)
        
        folder_layout.addLayout(input_layout)
        folder_layout.addLayout(output_layout)
        
        main_layout.addWidget(folder_group)
    
    def create_action_buttons_group(self, main_layout):
        """创建操作按钮组"""
        button_layout = QHBoxLayout()
        
        # 开始清洗按钮
        self.start_btn = QPushButton("🚀 开始清洗数据")
        self.start_btn.clicked.connect(self.start_cleaning)
        self.start_btn.setMinimumHeight(40)
        
        # 生成图表按钮（暂时禁用）
        self.chart_btn = QPushButton("📊 生成图表")
        self.chart_btn.setEnabled(False)
        self.chart_btn.setMinimumHeight(40)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.chart_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_status_display_group(self, main_layout):
        """创建状态显示组"""
        status_group = QGroupBox("处理状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态文本显示
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlaceholderText("等待用户操作...")
        
        status_layout.addWidget(self.status_text)
        main_layout.addWidget(status_group)
    
    def set_styles(self):
        """设置界面样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QRadioButton {
                spacing: 5px;
            }
            QLabel {
                color: #333;
            }
        """)
        
        # 设置开始按钮特殊样式
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
    
    def setup_default_paths(self):
        """设置默认路径"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        
        # 设置默认输入路径为项目的ASEData/DC目录
        default_input_path = project_root / "ASEData" / "DC"
        # 设置默认输出路径为项目的output目录
        default_output_path = project_root / "output"
        
        # 如果ASEData目录不存在，回退到桌面
        if not default_input_path.parent.exists():
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            self.input_path_edit.setText(desktop_path)
            self.output_path_edit.setText(desktop_path)
            self.log_message(f"ASEData目录不存在，默认路径设置为桌面: {desktop_path}")
        else:
            self.input_path_edit.setText(str(default_input_path))
            self.output_path_edit.setText(str(default_output_path))
            self.log_message(f"默认输入路径: {default_input_path}")
            self.log_message(f"默认输出路径: {default_output_path}")
    
    def browse_input_folder(self):
        """浏览选择输入文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "选择包含源数据的文件夹",
            self.input_path_edit.text() or os.path.expanduser("~/Desktop")
        )
        if folder:
            self.input_path_edit.setText(folder)
            self.log_message(f"输入文件夹: {folder}")
    
    def browse_output_folder(self):
        """浏览选择输出文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "选择输出文件夹",
            self.output_path_edit.text() or os.path.expanduser("~/Desktop")
        )
        if folder:
            self.output_path_edit.setText(folder)
            self.log_message(f"输出文件夹: {folder}")
    
    def get_selected_cleaner_type(self):
        """获取选中的清洗类型"""
        if self.dc_radio.isChecked():
            return "DC"
        elif self.dvds_radio.isChecked():
            return "DVDS"
        elif self.rg_radio.isChecked():
            return "RG"
        return None
    
    def on_cleaner_type_changed(self):
        """当清洗类型改变时更新默认输入路径"""
        cleaner_type = self.get_selected_cleaner_type()
        if cleaner_type:
            project_root = Path(__file__).parent.parent
            default_input_path = project_root / "ASEData" / cleaner_type
            
            # 只有当前路径是项目内的ASEData路径时才自动切换
            current_path = Path(self.input_path_edit.text())
            try:
                # 检查当前路径是否在项目的ASEData目录下
                if current_path.parent.name == "ASEData":
                    self.input_path_edit.setText(str(default_input_path))
                    self.log_message(f"切换到{cleaner_type}模式，输入路径: {default_input_path}")
            except:
                pass  # 如果路径无效，忽略自动切换
    
    def start_cleaning(self):
        """开始数据清洗过程"""
        # 验证输入
        if not self.validate_inputs():
            return
        
        # 获取参数
        cleaner_type = self.get_selected_cleaner_type()
        input_dir = self.input_path_edit.text().strip()
        output_dir = self.output_path_edit.text().strip()
        
        # 检查输入目录是否存在
        if not os.path.exists(input_dir):
            QMessageBox.warning(
                self, 
                "目录不存在", 
                f"输入目录不存在:\n{input_dir}\n\n请选择正确的数据文件夹"
            )
            return
        
        # 禁用开始按钮
        self.start_btn.setEnabled(False)
        self.start_btn.setText("清洗中...")
        
        # 清空状态显示
        self.status_text.clear()
        
        # 创建并启动工作线程
        self.worker_thread = DataCleanerWorker(cleaner_type, input_dir, output_dir)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.finished.connect(self.cleaning_finished)
        self.worker_thread.error_occurred.connect(self.cleaning_error)
        self.worker_thread.start()
        
        self.log_message(f"开始{cleaner_type}数据清洗...")
        self.log_message(f"输入目录: {input_dir}")
        self.log_message(f"输出目录: {output_dir}")
    
    def validate_inputs(self):
        """验证输入参数"""
        if not self.input_path_edit.text().strip():
            QMessageBox.warning(self, "警告", "请选择数据文件夹")
            return False
        
        if not self.output_path_edit.text().strip():
            QMessageBox.warning(self, "警告", "请选择输出文件夹")
            return False
        
        if not self.get_selected_cleaner_type():
            QMessageBox.warning(self, "警告", "请选择清洗类型")
            return False
        
        return True
    
    def update_progress(self, message):
        """更新进度信息"""
        self.log_message(message)
    
    def cleaning_finished(self, message, success):
        """清洗完成"""
        self.log_message(message)
        
        # 恢复开始按钮
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🚀 开始清洗数据")
        
        # 显示结果消息
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)
    
    def cleaning_error(self, error_message):
        """清洗出错"""
        self.log_message(f"错误: {error_message}")
        
        # 恢复开始按钮
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🚀 开始清洗数据")
        
        # 显示错误消息
        QMessageBox.critical(self, "错误", error_message)
    
    def log_message(self, message):
        """记录消息到状态显示区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.status_text.append(formatted_message)
        
        # 自动滚动到底部
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                "确认", 
                "数据清洗正在进行中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker_thread.cancel()
                self.worker_thread.wait(3000)  # 等待3秒
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("FT数据清洗工具")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("cc")
    
    # 创建主窗口
    window = FTDataCleanerGUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()