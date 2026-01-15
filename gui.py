import sys
import os
import threading
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QProgressBar, QLabel, QFrame, QSplitter, QMessageBox,
    QScrollArea, QGroupBox, QSpinBox, QDoubleSpinBox, QFormLayout,
    QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QPalette
import soundfile as sf
import sounddevice as sd
import numpy as np
import queue
import wave
import pyaudio

from split_vocals import main_func, separate_vocals_two_stage

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str, str)
    status = pyqtSignal(str, str)

class ProcessingWorker(threading.Thread):
    def __init__(self, file_path, voice_model=None, device="cuda", task_id=None):
        super().__init__()
        self.file_path = file_path
        self.voice_model = voice_model
        self.device = device
        self.task_id = task_id
        self.signals = WorkerSignals()
        self._stop_event = threading.Event()
    
    def run(self):
        try:
            self.signals.status.emit(self.task_id, "开始处理...")
            self.signals.progress.emit(10)
            
            self.signals.status.emit(self.task_id, "转换音频格式...")
            self.signals.progress.emit(20)
            
            self.signals.status.emit(self.task_id, "分离人声和伴奏...")
            self.signals.progress.emit(40)
            
            self.signals.status.emit(self.task_id, "第一阶段处理...")
            self.signals.progress.emit(50)
            
            self.signals.status.emit(self.task_id, "第二阶段处理...")
            self.signals.progress.emit(70)
            
            self.signals.status.emit(self.task_id, "第三阶段处理...")
            self.signals.progress.emit(85)
            
            vocal_path, inst_path = main_func(self.file_path, self.voice_model, self.device)
            
            self.signals.progress.emit(100)
            self.signals.finished.emit(self.task_id, vocal_path, inst_path)
            
        except Exception as e:
            self.signals.error.emit(self.task_id, str(e))
    
    def stop(self):
        self._stop_event.set()

class AudioPlayer(QObject):
    def __init__(self):
        super().__init__()
        self.player_thread = None
        self._stop_event = threading.Event()
    
    def play_audio(self, file_path, parent=None):
        if not os.path.exists(file_path):
            if parent:
                QMessageBox.warning(parent, "错误", f"文件不存在: {file_path}")
            return
        
        print(f"尝试播放: {file_path}")
        
        self._stop_event.set()
        if self.player_thread and self.player_thread.is_alive():
            self.player_thread.join(timeout=1)
        self._stop_event.clear()
        
        def play():
            try:
                wf = wave.open(file_path, 'rb')
                
                p = pyaudio.PyAudio()
                
                stream = p.open(
                    format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                chunk = 1024
                data = wf.readframes(chunk)
                
                while data and not self._stop_event.is_set():
                    stream.write(data)
                    data = wf.readframes(chunk)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
                wf.close()
                
                print("播放完成")
                
            except Exception as e:
                print(f"播放错误: {str(e)}")
                import traceback
                traceback.print_exc()
        
        self.player_thread = threading.Thread(target=play, daemon=True)
        self.player_thread.start()
    
    def stop(self):
        self._stop_event.set()

class TaskWidget(QFrame):
    def __init__(self, file_path, task_id):
        super().__init__()
        self.file_path = file_path
        self.task_id = task_id
        self.vocal_path = None
        self.inst_path = None
        
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.file_label = QLabel(f"🎵 {os.path.basename(self.file_path)}")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(self.file_label)
        
        self.status_label = QLabel("等待处理...")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 10pt;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                background-color: #3a3a3a;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #00ff00;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.buttons_layout = QHBoxLayout()
        self.play_vocal_btn = QPushButton("🎤 播放人声")
        self.play_vocal_btn.setEnabled(False)
        self.play_vocal_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.buttons_layout.addWidget(self.play_vocal_btn)
        
        self.play_inst_btn = QPushButton("🎹 播放伴奏")
        self.play_inst_btn.setEnabled(False)
        self.play_inst_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.buttons_layout.addWidget(self.play_inst_btn)
        
        layout.addLayout(self.buttons_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def set_finished(self, vocal_path, inst_path):
        self.vocal_path = vocal_path
        self.inst_path = inst_path
        self.status_label.setText("✓ 处理完成")
        self.status_label.setStyleSheet("color: #00ff00; font-size: 10pt; font-weight: bold;")
        self.play_vocal_btn.setEnabled(True)
        self.play_inst_btn.setEnabled(True)
    
    def set_error(self, error):
        self.status_label.setText(f"✗ 错误: {error}")
        self.status_label.setStyleSheet("color: #ff0000; font-size: 10pt;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                background-color: #3a3a3a;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #ff0000;
                border-radius: 3px;
            }
        """)

class DropArea(QFrame):
    files_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border: 3px dashed #555555;
                border-radius: 10px;
                padding: 40px;
            }
            QFrame:hover {
                border-color: #00ff00;
                background-color: #333333;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("📁 拖拽音乐文件到这里\n或点击选择文件")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14pt;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.label)
        
        self.setLayout(layout)
        
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #333333;
                    border: 3px solid #00ff00;
                    border-radius: 10px;
                    padding: 40px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border: 3px dashed #555555;
                border-radius: 10px;
                padding: 40px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac', '.wma')):
                    files.append(file_path)
        
        if files:
            self.files_dropped.emit(files)
            
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border: 3px dashed #555555;
                border-radius: 10px;
                padding: 40px;
            }
        """)
        event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker_threads = []
        self.task_widgets = {}
        self.audio_player = AudioPlayer()
        self.task_counter = 0
        self.max_workers = 2
        self.voice_model = None
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🎵 音乐人声分离工具")
        self.setGeometry(100, 100, 900, 700)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        title = QLabel("🎶 音乐人声分离工具")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24pt; font-weight: bold; color: #4CAF50; padding: 20px;")
        main_layout.addWidget(title)
        
        settings_group = QGroupBox("设置选项")
        settings_group.setStyleSheet("""
            QGroupBox {
                background-color: #2c2c2c;
                border: 2px solid #555555;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 5px;
            }
        """)
        settings_layout = QFormLayout()
        
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 4)
        self.thread_spin.setValue(self.max_workers)
        self.thread_spin.valueChanged.connect(self.update_max_workers)
        settings_layout.addRow("同时处理任务数:", self.thread_spin)
        
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"])
        self.device_combo.setCurrentText("cuda")
        settings_layout.addRow("计算设备:", self.device_combo)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.add_files)
        main_layout.addWidget(self.drop_area)
        
        select_btn = QPushButton("📂 选择音频文件")
        select_btn.clicked.connect(self.select_files)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        main_layout.addWidget(select_btn)
        
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: 2px solid #555555;
                border-radius: 10px;
            }
        """)
        
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.addStretch()
        self.tasks_scroll.setWidget(self.tasks_container)
        main_layout.addWidget(self.tasks_scroll, stretch=1)
        
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2c2c2c;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)
        self.status_bar.showMessage("就绪")
    
    def update_max_workers(self, value):
        self.max_workers = value
        self.process_queue()
    
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.flac *.m4a *.ogg *.aac *.wma)"
        )
        if files:
            self.add_files(files)
    
    def add_files(self, files):
        for file_path in files:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}"
            
            task_widget = TaskWidget(file_path, task_id)
            self.task_widgets[task_id] = task_widget
            
            self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, task_widget)
            
            task_widget.play_vocal_btn.clicked.connect(
                lambda checked, tw=task_widget: self.play_output(tw, is_vocal=True)
            )
            task_widget.play_inst_btn.clicked.connect(
                lambda checked, tw=task_widget: self.play_output(tw, is_vocal=False)
            )
        
        self.status_bar.showMessage(f"已添加 {len(files)} 个文件到队列")
        self.process_queue()
    
    def process_queue(self):
        active_workers = [w for w in self.worker_threads if w.is_alive()]
        
        if len(active_workers) >= self.max_workers:
            return
        
        pending_tasks = [
            (tid, tw) for tid, tw in self.task_widgets.items()
            if tw.progress_bar.value() == 0 and tw.status_label.text() == "等待处理..."
        ]
        
        if not pending_tasks:
            return
        
        task_id, task_widget = pending_tasks[0]
        
        worker = ProcessingWorker(
            task_widget.file_path,
            voice_model=self.voice_model,
            device=self.device_combo.currentText(),
            task_id=task_id
        )
        
        worker.signals.progress.connect(
            lambda value, tid=task_id: self.update_progress(tid, value)
        )
        worker.signals.finished.connect(self.on_task_finished)
        worker.signals.error.connect(self.on_task_error)
        worker.signals.status.connect(self.update_status)
        
        worker.start()
        self.worker_threads.append(worker)
        
        self.status_bar.showMessage(f"正在处理: {len(active_workers) + 1}/{self.max_workers} 任务")
    
    def update_progress(self, task_id, value):
        if task_id in self.task_widgets:
            self.task_widgets[task_id].update_progress(value)
    
    def update_status(self, task_id, status):
        if task_id in self.task_widgets:
            self.task_widgets[task_id].update_status(status)
    
    def on_task_finished(self, task_id, vocal_path, inst_path):
        if task_id in self.task_widgets:
            self.task_widgets[task_id].set_finished(vocal_path, inst_path)
        
        active_workers = [w for w in self.worker_threads if w.is_alive()]
        self.status_bar.showMessage(f"任务完成: {len(active_workers)}/{self.max_workers} 任务进行中")
        
        QTimer.singleShot(100, self.process_queue)
    
    def on_task_error(self, task_id, error):
        if task_id in self.task_widgets:
            self.task_widgets[task_id].set_error(error)
        
        active_workers = [w for w in self.worker_threads if w.is_alive()]
        self.status_bar.showMessage(f"任务失败: {len(active_workers)}/{self.max_workers} 任务进行中")
        
        QTimer.singleShot(100, self.process_queue)
    
    def play_output(self, task_widget, is_vocal):
        if is_vocal:
            if task_widget.vocal_path and os.path.exists(task_widget.vocal_path):
                self.audio_player.play_audio(task_widget.vocal_path, self)
                self.status_bar.showMessage(f"正在播放人声: {os.path.basename(task_widget.vocal_path)}")
            else:
                QMessageBox.warning(self, "错误", "人声文件不存在或未生成")
        else:
            if task_widget.inst_path and os.path.exists(task_widget.inst_path):
                self.audio_player.play_audio(task_widget.inst_path, self)
                self.status_bar.showMessage(f"正在播放伴奏: {os.path.basename(task_widget.inst_path)}")
            else:
                QMessageBox.warning(self, "错误", "伴奏文件不存在或未生成")
    
    def closeEvent(self, event):
        for worker in self.worker_threads:
            if worker.is_alive():
                reply = QMessageBox.question(
                    self,
                    "确认退出",
                    "有任务正在处理中，确定要退出吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    event.ignore()
                    return
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
