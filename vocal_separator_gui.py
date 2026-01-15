import os
import sys

# Add parent directory to path for imports
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'src'))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QLabel, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from split_vocals import main_func

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int, str, int)
    finished = pyqtSignal(int, str, str, str)
    error = pyqtSignal(int, str, str)

    def __init__(self, task_id, file_path, device="cuda"):
        super().__init__()
        self.task_id = task_id
        self.file_path = file_path
        self.device = device
        self._is_running = True

    def run(self):
        try:
            def progress_callback(status, progress):
                self.progress_updated.emit(self.task_id, status, progress)

            vocal_path, instrumental_path = main_func(
                self.file_path, 
                device=self.device,
                progress_callback=progress_callback
            )
            self.finished.emit(self.task_id, os.path.basename(self.file_path), vocal_path, instrumental_path)
        except Exception as e:
            self.error.emit(self.task_id, os.path.basename(self.file_path), str(e))

    def stop(self):
        self._is_running = False

class FileItemWidget(QWidget):
    def __init__(self, task_id, filename):
        super().__init__()
        self.task_id = task_id
        self.filename = filename
        self.vocal_path = None
        self.instrumental_path = None
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        self.filename_label = QLabel(self.filename)
        self.filename_label.setFixedWidth(200)
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("等待处理")
        self.status_label.setFixedWidth(150)
        layout.addWidget(self.status_label)

        self.vocal_btn = QPushButton("播放人声")
        self.vocal_btn.setEnabled(False)
        self.vocal_btn.clicked.connect(self.play_vocal)
        layout.addWidget(self.vocal_btn)

        self.instrumental_btn = QPushButton("播放伴奏")
        self.instrumental_btn.setEnabled(False)
        self.instrumental_btn.clicked.connect(self.play_instrumental)
        layout.addWidget(self.instrumental_btn)

        self.setLayout(layout)

    def update_progress(self, status, value):
        self.status_label.setText(status)
        self.progress_bar.setValue(value)

    def set_processed(self, vocal_path, instrumental_path):
        self.vocal_path = vocal_path
        self.instrumental_path = instrumental_path
        self.vocal_btn.setEnabled(True)
        self.instrumental_btn.setEnabled(True)
        self.status_label.setText("已完成")

    def play_vocal(self):
        if self.vocal_path:
            os.startfile(self.vocal_path)

    def play_instrumental(self):
        if self.instrumental_path:
            os.startfile(self.instrumental_path)

class VocalSeparatorGUI(QMainWindow):
    def add_file_to_list(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件不存在: {file_path}")
            return

        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        file_name = os.path.basename(file_path)
        self.file_table.setItem(row, 0, QTableWidgetItem(file_name))
        self.file_table.setItem(row, 1, QTableWidgetItem("等待中"))

        progress_bar = QProgressBar()
        progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_bar.setValue(0)
        self.file_table.setCellWidget(row, 2, progress_bar)

        play_vocal_btn = QPushButton("🎤 播放人声")
        play_vocal_btn.setEnabled(False)
        play_vocal_btn.clicked.connect(lambda: self.play_audio(task_id, "vocal"))
        self.file_table.setCellWidget(row, 3, play_vocal_btn)

        play_instrumental_btn = QPushButton("🎵 播放伴奏")
        play_instrumental_btn.setEnabled(False)
        play_instrumental_btn.clicked.connect(lambda: self.play_audio(task_id, "instrumental"))
        self.file_table.setCellWidget(row, 4, play_instrumental_btn)

        self.task_queue.append((task_id, file_path))
        self.process_next_task()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("人声伴奏分离工具")
        self.setGeometry(100, 100, 900, 600)
        self.task_counter = 0
        self.threads = {}
        self.task_queue = []
        self.is_processing = False
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.drag_drop_area = QLabel("将音乐文件拖放到此处，或点击下方按钮选择文件")
        self.drag_drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                font-size: 16px;
                color: #666;
            }
        """)
        self.drag_drop_area.setAcceptDrops(True)
        self.drag_drop_area.dragEnterEvent = self.drag_enter_event
        self.drag_drop_area.dropEvent = self.drop_event
        main_layout.addWidget(self.drag_drop_area)

        self.select_btn = QPushButton("选择音乐文件")
        self.select_btn.clicked.connect(self.select_files)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        main_layout.addWidget(self.select_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.files_list = QListWidget()
        main_layout.addWidget(self.files_list)

        self.setAcceptDrops(True)

    def drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event: QDropEvent):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                self.add_file_to_list(file_path)

    def select_files(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("音频文件 (*.mp3 *.wav *.flac *.m4a *.ogg *.wma)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.add_file_to_list(file_path)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("人声伴奏分离工具")
        self.setGeometry(100, 100, 900, 600)
        self.task_counter = 0
        self.threads = {}
        self.task_queue = []
        self.is_processing = False
        self.init_ui()

    def process_next_task(self):
        if self.is_processing or not self.task_queue:
            return

        self.is_processing = True
        task_id, file_path = self.task_queue.pop(0)
        self.process_file(task_id, file_path)

    def process_file(self, task_id, file_path):
        thread = ProcessingThread(task_id, file_path)
        thread.progress_updated.connect(self.update_progress)
        thread.finished.connect(self.on_processing_finished)
        thread.error.connect(self.on_processing_error)
        self.threads[task_id] = thread
        thread.start()

    def update_progress(self, task_id, status, value):
        for i in range(self.file_table.rowCount()):
            item = self.file_table.item(i, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.file_table.setItem(i, 1, QTableWidgetItem(status))
                progress_bar = self.file_table.cellWidget(i, 2)
                if progress_bar:
                    progress_bar.setValue(value)
                break

    def on_processing_finished(self, task_id, filename, vocal_path, instrumental_path):
        for i in range(self.file_table.rowCount()):
            item = self.file_table.item(i, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.file_table.setItem(i, 1, QTableWidgetItem("已完成"))
                play_vocal_btn = self.file_table.cellWidget(i, 3)
                if play_vocal_btn:
                    play_vocal_btn.setEnabled(True)
                    play_vocal_btn.vocal_path = vocal_path
                play_instrumental_btn = self.file_table.cellWidget(i, 4)
                if play_instrumental_btn:
                    play_instrumental_btn.setEnabled(True)
                    play_instrumental_btn.instrumental_path = instrumental_path
                del self.threads[task_id]
                break
        self.is_processing = False
        self.process_next_task()

    def on_processing_error(self, task_id, filename, error_message):
        for i in range(self.file_table.rowCount()):
            item = self.file_table.item(i, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.file_table.setItem(i, 1, QTableWidgetItem(f"错误: {error_message}"))
                del self.threads[task_id]
                QMessageBox.critical(self, "处理错误", f"文件 {filename} 处理失败:\n{error_message}")
                break
        self.is_processing = False
        self.process_next_task()

    def closeEvent(self, event):
        for thread in self.threads.values():
            thread.stop()
            thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VocalSeparatorGUI()
    window.show()
    sys.exit(app.exec())