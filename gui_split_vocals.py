import sys
import os
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QListWidget, QListWidgetItem,
    QFileDialog, QStyle, QMessageBox, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QFont, QPalette, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


class ProcessingTask(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def __init__(self, input_audio, voice_model=None, device="cuda"):
        super().__init__()
        self.input_audio = input_audio
        self.voice_model = voice_model
        self.device = device

    def run(self):
        try:
            self.log_signal.emit(f"开始处理文件: {self.input_audio}")
            self.status_updated.emit("正在初始化...")
            self.progress_updated.emit(0)
            
            self.log_signal.emit(f"设备: {self.device}")
            self.log_signal.emit(f"RVC模型: {self.voice_model if self.voice_model else '无'}")
            
            from split_vocals import main_func
            self.log_signal.emit("成功导入main_func")
            
            def progress_callback(progress, status):
                self.progress_updated.emit(progress)
                self.status_updated.emit(status)
                self.log_signal.emit(f"[{progress}%] {status}")
            
            self.log_signal.emit("调用main_func...")
            
            vocal, instrumental = main_func(
                self.input_audio, 
                voice_model=self.voice_model, 
                device=self.device,
                progress_callback=progress_callback
            )
            
            self.log_signal.emit(f"main_func返回: vocal={vocal}, instrumental={instrumental}")
            
            if not vocal or not instrumental:
                raise ValueError("main_func返回了空路径")
            
            if not os.path.exists(vocal):
                raise ValueError(f"人声文件不存在: {vocal}")
            
            if not os.path.exists(instrumental):
                raise ValueError(f"伴奏文件不存在: {instrumental}")
                
            self.status_updated.emit("完成")
            self.log_signal.emit("处理完成")
            
            self.finished_signal.emit(vocal, instrumental)
            
        except Exception as e:
            error_msg = str(e)
            self.log_signal.emit(f"发生错误: {error_msg}")
            self.log_signal.emit(f"完整错误信息:\n{traceback.format_exc()}")
            self.error_signal.emit(error_msg)


class TaskItem(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.task = None
        self.vocal_path = None
        self.instrumental_path = None
        self.media_player = None
        self.audio_output = None
        self.current_playing = None
        
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        file_name = os.path.basename(self.file_path)
        file_label = QLabel(f"📁 {file_name}")
        file_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        layout.addWidget(file_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("等待处理...")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        layout.addWidget(self.status_label)
        
        self.log_label = QLabel("")
        self.log_label.setFont(QFont("Consolas", 8))
        self.log_label.setWordWrap(True)
        self.log_label.setMaximumHeight(80)
        self.log_label.setStyleSheet("color: #666; background: #f5f5f5; padding: 6px; border-radius: 4px;")
        layout.addWidget(self.log_label)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.play_vocal_btn = QPushButton("▶ 播放人声")
        self.play_vocal_btn.setEnabled(False)
        self.play_vocal_btn.clicked.connect(self.play_vocal)
        buttons_layout.addWidget(self.play_vocal_btn)
        
        self.play_inst_btn = QPushButton("▶ 播放伴奏")
        self.play_inst_btn.setEnabled(False)
        self.play_inst_btn.clicked.connect(self.play_instrumental)
        buttons_layout.addWidget(self.play_inst_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_playback)
        buttons_layout.addWidget(self.stop_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

    def apply_styles(self):
        self.setStyleSheet("""
            TaskItem {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 4px;
            }
            TaskItem:hover {
                border: 1px solid #4a90e2;
            }
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: #f0f0f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:1 #357abd);
                border-radius: 3px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a9ff2, stop:1 #4589cd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a80d2, stop:1 #2579bd);
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #888888;
            }
        """)

    def start_processing(self, voice_model=None, device="cuda"):
        self.task = ProcessingTask(self.file_path, voice_model, device)
        self.task.progress_updated.connect(self.progress_bar.setValue)
        self.task.status_updated.connect(self.status_label.setText)
        self.task.finished_signal.connect(self.on_finished)
        self.task.error_signal.connect(self.on_error)
        self.task.log_signal.connect(self.log_label.setText)
        self.task.start()

    def on_finished(self, vocal_path, instrumental_path):
        self.vocal_path = vocal_path
        self.instrumental_path = instrumental_path
        self.play_vocal_btn.setEnabled(True)
        self.play_inst_btn.setEnabled(True)
        self.status_label.setText("✅ 处理完成")
        self.log_label.setText(f"人声: {os.path.basename(vocal_path)}\n伴奏: {os.path.basename(instrumental_path)}")

    def on_error(self, error_msg):
        self.status_label.setText(f"❌ 错误: {error_msg}")
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background: #e74c3c; }")

    def play_vocal(self):
        if self.vocal_path and os.path.exists(self.vocal_path):
            self.play_audio(self.vocal_path)
            self.current_playing = "vocal"

    def play_instrumental(self):
        if self.instrumental_path and os.path.exists(self.instrumental_path):
            self.play_audio(self.instrumental_path)
            self.current_playing = "instrumental"

    def play_audio(self, file_path):
        self.media_player.stop()
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()
        self.stop_btn.setEnabled(True)
        
        if self.current_playing == "vocal":
            self.play_vocal_btn.setEnabled(False)
            self.play_inst_btn.setEnabled(True)
        else:
            self.play_vocal_btn.setEnabled(True)
            self.play_inst_btn.setEnabled(False)

    def stop_playback(self):
        self.media_player.stop()
        self.stop_btn.setEnabled(False)
        self.play_vocal_btn.setEnabled(True)
        self.play_inst_btn.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_items = []
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        self.setWindowTitle("🎵 音乐人声分离工具")
        self.setMinimumSize(800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("🎵 音乐人声分离工具")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 8px;")
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("拖拽音频文件到下方区域，或点击按钮选择文件")
        subtitle_label.setFont(QFont("Microsoft YaHei", 10))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 16px;")
        main_layout.addWidget(subtitle_label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        add_file_btn = QPushButton("📂 添加文件")
        add_file_btn.setFont(QFont("Microsoft YaHei", 10))
        add_file_btn.clicked.connect(self.add_files)
        button_layout.addWidget(add_file_btn)
        
        clear_btn = QPushButton("🗑️ 清空列表")
        clear_btn.setFont(QFont("Microsoft YaHei", 10))
        clear_btn.clicked.connect(self.clear_list)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout()
        self.task_layout.setSpacing(8)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.addStretch()
        self.task_container.setLayout(self.task_layout)
        
        scroll_area.setWidget(self.task_container)
        main_layout.addWidget(scroll_area)
        
        central_widget.setLayout(main_layout)
        
        self.setAcceptDrops(True)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #c3cfe2);
            }
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if os.path.isfile(file_path):
                self.add_task(file_path)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "", 
            "音频文件 (*.mp3 *.wav *.flac *.m4a *.ogg *.aac)"
        )
        for file_path in files:
            self.add_task(file_path)

    def add_task(self, file_path):
        task_item = TaskItem(file_path)
        self.task_items.append(task_item)
        
        self.task_layout.insertWidget(self.task_layout.count() - 1, task_item)
        
        task_item.start_processing()

    def clear_list(self):
        for task_item in self.task_items:
            task_item.deleteLater()
        self.task_items.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
