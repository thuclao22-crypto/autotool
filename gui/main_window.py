import sys
import os
import cv2
import traceback
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QSlider, QComboBox, QFrame, 
                             QScrollArea, QColorDialog, QFontComboBox, QSpinBox,
                             QButtonGroup, QApplication, QFileDialog, QLineEdit, 
                             QGridLayout, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QProgressBar) 
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtGui import QImage, QPixmap
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- LỚP WORKER THREAD (CHẠY NGẦM KHÔNG GÂY ĐƠ GIAO DIỆN) ---
class WorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e) + "\n" + traceback.format_exc())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoSubtitle Pro - Professional Edition V2.2 (Ultimate)")
        self.setMinimumSize(1400, 950)
        
        # Áp dụng Giao diện Dark Mode Toàn cục (Modern Aesthetics)
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.container_layout = QVBoxLayout(central_widget)

        # --- NHẬP DỮ LIỆU ĐẦU VÀO & ĐẦU RA ---
        io_frame = QFrame()
        io_frame.setObjectName("ioFrame")
        io_layout = QGridLayout(io_frame)
        
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Chọn file video hoặc thư mục...")
        io_layout.addWidget(QLabel("Nguồn đầu vào:"), 0, 0)
        io_layout.addWidget(self.input_path_edit, 0, 1)
        
        btn_input_file = QPushButton("Chọn 1 Video"); btn_input_file.clicked.connect(self.select_input_file)
        btn_input_folder = QPushButton("Chọn Folder"); btn_input_folder.clicked.connect(self.select_input_folder)
        io_layout.addWidget(btn_input_file, 0, 2)
        io_layout.addWidget(btn_input_folder, 0, 3)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Chọn thư mục lưu kết quả...")
        io_layout.addWidget(QLabel("Nơi lưu video:"), 1, 0)
        io_layout.addWidget(self.output_path_edit, 1, 1)
        
        btn_output = QPushButton("Chọn nơi lưu"); btn_output.clicked.connect(self.select_output_folder)
        io_layout.addWidget(btn_output, 1, 2)
        
        self.container_layout.addWidget(io_frame)

        # --- NỘI DUNG CHÍNH ---
        main_layout = QHBoxLayout()
        self.container_layout.addLayout(main_layout)
        
        # --- KHỐI 1: SIDEBAR ---
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setFixedWidth(460)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setStyleSheet("border: none;")
        
        container = QWidget()
        self.sidebar_layout = QVBoxLayout(container)
        
        # A. BỘ XỬ LÝ DIỆN MẠO
        self.add_section_title("A. BỘ XỬ LÝ DIỆN MẠO (STYLING ENGINE)")
        
        self.sidebar_layout.addWidget(QLabel("Phông chữ (.ttf, .otf):"))
        self.font_combo = QFontComboBox()
        self.sidebar_layout.addWidget(self.font_combo)
        
        size_layout = QHBoxLayout()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 500); self.font_size_spin.setValue(50)
        size_layout.addWidget(QLabel("Kích thước (px):"))
        size_layout.addWidget(self.font_size_spin)
        self.sidebar_layout.addLayout(size_layout)

        self.sidebar_layout.addWidget(QLabel("Màu sắc chính (Primary Color):"))
        color_action_layout = QHBoxLayout()
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(60, 30)
        self.color_preview.setStyleSheet("background-color: #FFFF00; border: 1px solid #555; border-radius: 4px;")
        self.btn_pick_color = QPushButton("Mở bảng màu")
        self.btn_pick_color.clicked.connect(self.open_advanced_color_dialog)
        color_action_layout.addWidget(self.color_preview)
        color_action_layout.addWidget(self.btn_pick_color)
        self.sidebar_layout.addLayout(color_action_layout)

        self.sidebar_layout.addWidget(QLabel("Viền chữ (Stroke):"))
        self.stroke_combo = QComboBox()
        self.stroke_combo.addItems(["Đen", "Trắng", "Vàng", "Đỏ", "Xanh dương", "Xanh lá", "Hồng", "Tím", "Cam", "Xám/Bạc"])
        self.sidebar_layout.addWidget(self.stroke_combo)

        self.sidebar_layout.addWidget(QLabel("Kiểu Đổ Bóng (Shadow):"))
        self.shadow_combo = QComboBox()
        self.shadow_combo.addItems(["Không", "Shadow đen nhẹ", "Shadow đậm", "Shadow mềm", "Shadow màu + Glow", "Shadow rất nhẹ", "Shadow dày lệch mạnh"])
        self.sidebar_layout.addWidget(self.shadow_combo)

        self.sidebar_layout.addWidget(QLabel("Nền chữ (Background/Box):"))
        self.box_combo = QComboBox()
        self.box_combo.addItems(["Không", "Box đen mờ", "Box đỏ/xanh", "Box neon", "Box trắng mờ", "Box bo góc mềm", "Highlight vàng"])
        self.sidebar_layout.addWidget(self.box_combo)
        

        # CẤU HÌNH NGÔN NGỮ
        self.add_section_title("CẤU HÌNH NGÔN NGỮ")
        
        self.sidebar_layout.addWidget(QLabel("Chất lượng nhận diện AI:"))
        self.model_size_combo = QComboBox()
        self.model_size_combo.addItems(["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"])
        self.model_size_combo.setCurrentText("base")
        self.sidebar_layout.addWidget(self.model_size_combo)
        
        self.sidebar_layout.addWidget(QLabel("Ngôn ngữ 1 (Gốc):"))
        self.lang1_combo = QComboBox()
        self.lang1_combo.addItems(["Tự động nhận diện", "Tiếng Việt", "Tiếng Anh", "Tiếng Đức", "Tiếng Nhật", "Tiếng Hàn", "Tiếng Trung"])
        self.sidebar_layout.addWidget(self.lang1_combo)

        # --- CẤU HÌNH API KEY (CLOUD AI HYBRID) ---
        self.add_section_title("API KEY (TÙY CHỌN CLOUD AI)")

        api_key_frame = QFrame()
        api_key_frame.setObjectName("apiKeyFrame")
        api_key_layout = QVBoxLayout(api_key_frame)
        api_key_layout.setContentsMargins(8, 8, 8, 8)
        api_key_layout.setSpacing(6)

        # Ô nhập Gemini API Key
        api_key_layout.addWidget(QLabel("Google Gemini API Key:"))
        self.gemini_api_key_edit = QLineEdit()
        self.gemini_api_key_edit.setPlaceholderText("Nhập AIzaSy... để kích hoạt Gemini AI")
        self.gemini_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addWidget(self.gemini_api_key_edit)

        # Ô nhập OpenAI API Key
        api_key_layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setPlaceholderText("Nhập sk-... để kích hoạt OpenAI GPT")
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addWidget(self.openai_api_key_edit)

        # Nhãn thông báo trạng thái API
        self.api_status_label = QLabel("Trạng thái: Chế độ Offline (Whisper Local)")
        self.api_status_label.setStyleSheet("color: #95a5a6; font-size: 11px; font-style: italic;")
        api_key_layout.addWidget(self.api_status_label)

        self.sidebar_layout.addWidget(api_key_frame)

        # Kết nối sự kiện thay đổi để cập nhật nhãn trạng thái ngay lập tức
        self.gemini_api_key_edit.textChanged.connect(self.update_api_status_label)
        self.openai_api_key_edit.textChanged.connect(self.update_api_status_label)

        self.sidebar_layout.addWidget(QLabel("Chất lượng Video đầu ra:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "720p (HD) - Tối ưu tốc độ, Bitrate thấp",
            "1080p (Full HD) - Sắc nét chuẩn, Khuyến nghị",
            "2K/4K (Ultra HD) - Chất lượng cao, Bản đẹp"
        ])
        self.quality_combo.setCurrentText("1080p (Full HD) - Sắc nét chuẩn, Khuyến nghị")
        self.sidebar_layout.addWidget(self.quality_combo)

        self.check_bilingual = QCheckBox("Kích hoạt phụ đề song ngữ")
        self.check_bilingual.toggled.connect(self.toggle_bilingual_options)
        self.sidebar_layout.addWidget(self.check_bilingual)

        self.bilingual_container = QWidget()
        self.bilingual_vbox = QVBoxLayout(self.bilingual_container)
        self.bilingual_vbox.setContentsMargins(0, 5, 0, 5)

        self.bilingual_vbox.addWidget(QLabel("Ngôn ngữ 2 (Phụ):"))
        self.lang2_combo = QComboBox()
        self.lang2_combo.addItems(["Tiếng Anh", "Tiếng Việt", "Tiếng Đức", "Tiếng Nhật", "Tiếng Hàn", "Tiếng Trung"])
        self.bilingual_vbox.addWidget(self.lang2_combo)
        
        self.sidebar_layout.addWidget(self.bilingual_container)
        self.bilingual_container.setVisible(False) 

        percent_layout = QHBoxLayout()
        self.label_percent = QLabel("Tỷ lệ size ngôn ngữ phụ: 80%")
        percent_layout.addWidget(self.label_percent)
        
        self.sub_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.sub_size_slider.setRange(40, 100)
        self.sub_size_slider.setValue(80)
        self.sub_size_slider.valueChanged.connect(self.update_percent_label)
        
        self.sidebar_layout.addLayout(percent_layout)
        self.sidebar_layout.addWidget(self.sub_size_slider)

        # B. ĐỊNH VỊ & CĂN CHỈNH
        self.add_section_title("B. ĐỊNH VỊ & CĂN CHỈNH")
        
        self.sidebar_layout.addWidget(QLabel("Căn chỉnh lề (Alignment):"))
        align_btn_layout = QHBoxLayout()
        
        self.alignment_group = QButtonGroup(self)
        self.btn_align_left = QPushButton("Trái")
        self.btn_align_center = QPushButton("Giữa")
        self.btn_align_right = QPushButton("Phải")
        
        for btn in [self.btn_align_left, self.btn_align_center, self.btn_align_right]:
            btn.setCheckable(True)
            self.alignment_group.addButton(btn)
            align_btn_layout.addWidget(btn)
        
        self.btn_align_center.setChecked(True)
        self.sidebar_layout.addLayout(align_btn_layout)

        self.sidebar_layout.addWidget(QLabel("Vị trí có sẵn (Quick Presets):"))
        self.pos_combo = QComboBox()
        self.pos_combo.addItems([
            "Top Left", "Top Center", "Top Right",
            "Center Left", "Center", "Center Right",
            "Bottom Left", "Bottom Center", "Bottom Right",
            "Upper Third Left", "Upper Third Center", "Upper Third Right",
            "Lower Third Left", "Lower Third Center", "Lower Third Right"
        ])
        self.pos_combo.setCurrentText("Bottom Center")
        self.sidebar_layout.addWidget(self.pos_combo)

        # C. BỘ TẠO HIỆU ỨNG
        self.add_section_title("C. BỘ TẠO HIỆU ỨNG (ANIMATION)")
        
        self.sidebar_layout.addWidget(QLabel("Hiệu ứng VÀO (In):"))
        self.anim_in = QComboBox()
        self.anim_in.addItems(["Không có", "Rõ dần", "Ném ra", "Máy đánh chữ retro"])
        self.sidebar_layout.addWidget(self.anim_in)

        self.sidebar_layout.addWidget(QLabel("Hiệu ứng RA (Out):"))
        self.anim_out = QComboBox()
        self.anim_out.addItems(["Không có", "Làm mờ", "Quét lên", "Rơi trượt"])
        self.sidebar_layout.addWidget(self.anim_out)
        
        self.sidebar_layout.addWidget(QLabel("Thời gian hiệu ứng (Automation):"))
        self.effect_dur_label = QLabel("0.500s")
        self.effect_dur_slider = QSlider(Qt.Orientation.Horizontal)
        self.effect_dur_slider.setRange(0, 3000) 
        self.effect_dur_slider.setValue(500) 
        self.effect_dur_slider.valueChanged.connect(lambda v: self.effect_dur_label.setText(f"{v/1000:.3f}s"))
        
        eff_layout = QHBoxLayout()
        eff_layout.addWidget(self.effect_dur_slider)
        eff_layout.addWidget(self.effect_dur_label)
        self.sidebar_layout.addLayout(eff_layout)
        
        # D. TÍNH NĂNG NÂNG CAO
        self.add_section_title("D. TÍNH NĂNG NÂNG CAO")
        self.check_word_by_word = QCheckBox("Hiệu ứng chữ nhảy từng từ (Word-by-word)")
        self.check_word_by_word.setStyleSheet("font-weight: bold; color: white;")
        self.sidebar_layout.addWidget(self.check_word_by_word)
        
        self.check_bypass_copyright = QCheckBox("Kích hoạt né bản quyền video (Bypass Copyright)")
        self.check_bypass_copyright.setStyleSheet("font-weight: bold; color: white;")
        self.sidebar_layout.addWidget(self.check_bypass_copyright)

        self.sidebar_layout.addStretch()
        sidebar_scroll.setWidget(container)

        # --- KHỐI 2: PREVIEW & TIMELINE ---
        preview_container = QWidget()
        right_layout = QVBoxLayout(preview_container)

        self.video_preview = QLabel("MÀN HÌNH TRÌNH PHÁT\n(Click vào dòng phụ đề bên dưới để xem)")
        self.video_preview.setObjectName("videoPreview")
        self.video_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.video_preview, 5)
        
        ratio_frame = QFrame()
        ratio_layout = QVBoxLayout(ratio_frame)
        ratio_layout.addWidget(QLabel("<b>LỰA CHỌN TỶ LỆ KHUNG HÌNH:</b>"))
        
        grid = QGridLayout()
        ratios = [
            ("16:9 YouTube, PC, TV", 0, 0), ("9:16 TikTok, Shorts", 0, 1), ("1:1 Instagram", 0, 2),
            ("4:3 Retro", 1, 0), ("2.35:1 Phim điện ảnh", 1, 1), ("1.85:1 Phim chuẩn", 1, 2),
            ("2:1 Netflix style", 2, 0), ("3:4 Ảnh dọc", 2, 1), ("5.8-inch Mobile", 2, 2)
        ]
        
        self.ratio_group = QButtonGroup(self)
        for text, r, c in ratios:
            btn = QPushButton(text)
            btn.setCheckable(True)
            self.ratio_group.addButton(btn)
            grid.addWidget(btn, r, c)
            
        ratio_layout.addLayout(grid)
        right_layout.addWidget(ratio_frame)

        # Bảng phụ đề tương tác
        self.subtitle_table = QTableWidget()
        self.subtitle_table.setColumnCount(3)
        self.subtitle_table.setHorizontalHeaderLabels(["Bắt đầu", "Kết thúc", "Nội dung"])
        self.subtitle_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.subtitle_table.setFixedHeight(200)
        # Bắt sự kiện Click để lấy frame hình ảnh đồng bộ
        self.subtitle_table.itemSelectionChanged.connect(self.on_table_row_clicked)
        right_layout.addWidget(self.subtitle_table)
        
        # Nút bấm hành động
        btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton("1. ĐỌC & TRÍCH XUẤT PHỤ ĐỀ")
        self.btn_scan.setObjectName("btnScan")
        self.btn_scan.clicked.connect(self.handle_scan_only)
        self.btn_scan.setFixedHeight(50)
        
        self.btn_render = QPushButton("2. GHÉP PHỤ ĐỀ VÀO VIDEO")
        self.btn_render.setObjectName("btnRender")
        self.btn_render.clicked.connect(self.handle_render_only)
        self.btn_render.setFixedHeight(50)
        
        btn_layout.addWidget(self.btn_scan)
        btn_layout.addWidget(self.btn_render)
        right_layout.addLayout(btn_layout)

        main_layout.addWidget(sidebar_scroll)
        main_layout.addWidget(preview_container)
        
        # THANH TIẾN TRÌNH (Progress Bar) Đáy màn hình
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("Trạng thái: Sẵn sàng")
        self.container_layout.addWidget(self.progress_bar)
        
        # Biến trạng thái Multi-threading
        self.worker = None

    def apply_dark_theme(self):
        """Áp dụng Giao diện Dark Mode Pro toàn cục"""
        dark_qss = """
        QMainWindow, QWidget { background-color: #1e1e1e; color: #ecf0f1; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        QLabel { color: #ecf0f1; font-size: 13px; }
        QLineEdit, QSpinBox, QComboBox { background-color: #2c3e50; border: 1px solid #34495e; border-radius: 4px; padding: 6px; color: white; }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #3498db; }
        QPushButton { background-color: #34495e; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-weight: bold; }
        QPushButton:hover { background-color: #3b536b; }
        QPushButton:pressed { background-color: #2c3e50; }
        QPushButton:checked { background-color: #3498db; }
        QFrame#ioFrame { border: 1px solid #34495e; border-radius: 6px; margin-bottom: 10px; }
        QFrame#apiKeyFrame { background-color: #1a2332; border: 1px solid #2e4057; border-radius: 6px; }
        QLabel#videoPreview { background-color: #000000; border: 2px dashed #555; border-radius: 8px; font-size: 16px; color: #7f8c8d; }
        QTableWidget { background-color: #2c3e50; gridline-color: #34495e; border: 1px solid #34495e; border-radius: 4px; selection-background-color: #3498db; color: white; }
        QHeaderView::section { background-color: #1abc9c; color: white; padding: 4px; border: 1px solid #16a085; font-weight: bold; }
        QScrollBar:vertical { background: #2c3e50; width: 12px; border-radius: 6px; }
        QScrollBar::handle:vertical { background: #3498db; border-radius: 6px; }
        QSlider::groove:horizontal { background: #34495e; height: 8px; border-radius: 4px; }
        QSlider::handle:horizontal { background: #e74c3c; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
        QPushButton#btnScan { background-color: #3498db; font-size: 14px; border-radius: 6px; }
        QPushButton#btnScan:hover { background-color: #2980b9; }
        QPushButton#btnRender { background-color: #2ecc71; font-size: 14px; border-radius: 6px; color: #1e1e1e; }
        QPushButton#btnRender:hover { background-color: #27ae60; }
        QProgressBar { background-color: #2c3e50; border: 1px solid #34495e; border-radius: 4px; text-align: center; font-weight: bold; color: white; }
        QProgressBar::chunk { background-color: #e67e22; border-radius: 3px; }
        """
        self.setStyleSheet(dark_qss)

    def add_section_title(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; color: #1abc9c; margin-top: 15px; font-size: 14px; border-bottom: 1px solid #34495e; padding-bottom: 5px;")
        self.sidebar_layout.addWidget(label)

    def select_input_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Chọn Video", "", "Video Files (*.mp4 *.avi *.mkv)")
        if file: 
            self.input_path_edit.setText(file)
            self.update_video_preview(file)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư mục Video")
        if folder: 
            self.input_path_edit.setText(folder)
            files = [f for f in os.listdir(folder) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]
            if files:
                first_video = os.path.join(folder, files[0])
                self.update_video_preview(first_video)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Nơi lưu")
        if folder: self.output_path_edit.setText(folder)
    
    def open_advanced_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color
            self.color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555; border-radius: 4px;")
            
    # --- ĐA LUỒNG: SCAN QUÉT PHỤ ĐỀ ---
    def handle_scan_only(self):
        input_path = self.input_path_edit.text().strip()
        if not input_path or not os.path.exists(input_path):
            self.set_progress("Lỗi: Đường dẫn không tồn tại!", 0)
            return

        target_file = input_path
        if os.path.isdir(input_path):
            video_files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                           if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
            if not video_files:
                self.set_progress("Lỗi: Không có video trong thư mục!", 0)
                return
            target_file = video_files[0]
            
        self.set_progress("Đang chạy AI trích xuất phụ đề ngầm (Không đơ máy)...", 20)
        self.btn_scan.setEnabled(False)
        self.btn_render.setEnabled(False)
        
        # Trích xuất cấu hình UI từ luồng chính
        model_size = self.model_size_combo.currentText()
        source_lang = self.lang1_combo.currentText()
        gemini_key = self.gemini_api_key_edit.text().strip()
        openai_key = self.openai_api_key_edit.text().strip()
        
        # Khởi chạy đa luồng
        self.worker = WorkerThread(self.run_audio_module, target_file, model_size, source_lang, gemini_key, openai_key)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()

    def run_audio_module(self, video_path, model_size, source_lang, gemini_key, openai_key):
        from core.module_1_audio import TranscriptionModule
        transcriber = TranscriptionModule(model_size=model_size)
        result = transcriber.transcribe(
            video_path,
            selected_lang=source_lang,
            gemini_key=gemini_key,
            openai_key=openai_key,
            word_timestamps=True
        )
        if len(result) == 4:
            srt_path, lang, srt_list, api_error = result
        else:
            srt_path, lang, srt_list = result
            api_error = False
        return {"srt_list": srt_list, "api_error": api_error}

    def update_api_status_label(self):
        """Cập nhật nhãn trạng thái API Key ngay khi người dùng nhập liệu"""
        gemini = self.gemini_api_key_edit.text().strip()
        openai = self.openai_api_key_edit.text().strip()
        if gemini:
            self.api_status_label.setText("✅ Đang dùng: Google Gemini AI (Cloud 95%)")
            self.api_status_label.setStyleSheet("color: #1abc9c; font-size: 11px; font-weight: bold;")
        elif openai:
            self.api_status_label.setText("✅ Đang dùng: OpenAI GPT-4o Mini (Cloud 95%)")
            self.api_status_label.setStyleSheet("color: #3498db; font-size: 11px; font-weight: bold;")
        else:
            self.api_status_label.setText("Trạng thái: Chế độ Offline (Whisper Local)")
            self.api_status_label.setStyleSheet("color: #95a5a6; font-size: 11px; font-style: italic;")

    def on_scan_finished(self, result_data):
        if isinstance(result_data, dict):
            api_error = result_data.get("api_error", False)
            srt_list = result_data.get("srt_list", [])
            if api_error:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "CẢNH BÁO", "CẢNH BÁO: Khóa API Key bạn nhập đã bị nhà phát triển khóa hoặc hết hạn! Hệ thống buộc phải dùng bộ nghe offline Whisper Local nên độ chính xác tiếng Việt sẽ bị giảm sút. Vui lòng kiểm tra hoặc thay mã API Key mới!")
        else:
            srt_list = result_data
            
        self.display_srt_to_table(srt_list)
        self.set_progress(f"Đã quét xong {len(srt_list)} câu phụ đề. Mời duyệt trên bảng!", 100)
        self.btn_scan.setEnabled(True)
        self.btn_render.setEnabled(True)

    # --- ĐA LUỒNG: RENDER VIDEO ---
    def handle_render_only(self):
        input_path = self.input_path_edit.text().strip()
        output_base = self.output_path_edit.text().strip()
        
        if not output_base:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "LỖI CẢNH BÁO", "Bạn bắt buộc phải bấm nút 'Chọn nơi lưu' để thiết lập thư mục chứa video thành phẩm trước thì hệ thống mới được phép kích hoạt tính năng Xuất video edit hoàn chỉnh!")
            return

        if not input_path or not os.path.exists(input_path):
            self.set_progress("Lỗi: Đường dẫn không hợp lệ!", 0)
            return

        table_data = self.get_srt_from_table()
        if not table_data:
            self.set_progress("Lỗi: Bảng phụ đề trống! Vui lòng bấm Nút 1 để quét trước.", 0)
            return

        style_config = {
            "font_size": self.font_size_spin.value(),
            "primary_color": self.current_color.name() if hasattr(self, 'current_color') else "#ffffff",
            "font_path": self.font_combo.currentFont().family(),
            "position_preset": self.pos_combo.currentText(),
            "box_type": self.box_combo.currentText(),
            "stroke_combo": self.stroke_combo.currentText(),
            "shadow_combo": self.shadow_combo.currentText(),
            "ratio_combo": self.ratio_group.checkedButton().text() if self.ratio_group.checkedButton() else "16:9",
            "align_combo": self.alignment_group.checkedButton().text() if self.alignment_group.checkedButton() else "Giữa",
            "sub_size_ratio": self.sub_size_slider.value() / 100,
            "is_bilingual": self.check_bilingual.isChecked(),
            "target_lang": self.lang2_combo.currentText(),
            "anim_in": self.anim_in.currentText(),
            "anim_out": self.anim_out.currentText(),
            "effect_duration": self.effect_dur_slider.value() / 1000.0,
            "is_word_by_word": self.check_word_by_word.isChecked(),
            "is_bypass_copyright": self.check_bypass_copyright.isChecked(),
            "video_quality": self.quality_combo.currentText(),
            "source_lang": self.lang1_combo.currentText(),
            "model_size": self.model_size_combo.currentText(),
            "gemini_key": self.gemini_api_key_edit.text().strip(),
            "openai_key": self.openai_api_key_edit.text().strip()
        }

        self.set_progress("Đang chạy Engine Render Video ngầm (Không đơ máy)...", 20)
        self.btn_scan.setEnabled(False)
        self.btn_render.setEnabled(False)

        # Chạy đa luồng
        self.worker = WorkerThread(self.run_render_module, input_path, output_base, style_config, table_data)
        self.worker.finished.connect(self.on_render_finished)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()

    def run_render_module(self, input_path, output_base, style_config, srt_data1):
        from core.module_1_audio import TranscriptionModule
        from core.module_2_render import RenderingModule
        renderer = RenderingModule()

        video_files = []
        if os.path.isdir(input_path):
            video_files = [os.path.join(input_path, f) for f in os.listdir(input_path)
                           if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
        else:
            video_files = [input_path]

        total = len(video_files)
        source_lang = style_config.get("source_lang", "Tự động nhận diện")
        gemini_key = style_config.get("gemini_key", "")
        openai_key = style_config.get("openai_key", "")
        model_size = style_config.get("model_size", "base")
        
        # BUG HIỆU NĂNG: Chỉ load Model 1 lần duy nhất cho toàn bộ folder
        transcriber = None
        if os.path.isdir(input_path):
            print(f"--- Đang tải mô hình nhận diện giọng nói ({model_size}) vào bộ nhớ... ---")
            transcriber = TranscriptionModule(model_size=model_size)

        for idx, v_path in enumerate(video_files):
            filename = os.path.basename(v_path)
            out_name = f"subbed_{filename}"
            current_output = os.path.join(output_base, out_name) if output_base else os.path.join("outputs", out_name)

            # --- XỬ LÝ ĐỘNG TỪNG VIDEO ---
            if os.path.isdir(input_path):
                # Folder mode: transcribe riêng để lấy SRT chính xác của từng video
                print(f"\n>>> [{idx+1}/{total}] Đang quét phụ đề: {filename}")
                result = transcriber.transcribe(
                    v_path,
                    selected_lang=source_lang,
                    gemini_key=gemini_key,
                    openai_key=openai_key,
                    word_timestamps=True
                )
                if len(result) == 4:
                    srt_path, detected_lang, current_srt, api_error = result
                else:
                    srt_path, detected_lang, current_srt = result
                    
                # Cập nhật source_lang thực tế nếu đang ở chế độ tự động nhận diện
                if source_lang == "Tự động nhận diện" and detected_lang:
                    style_config["detected_lang"] = detected_lang
            else:
                # File đơn: dùng bảng chữ đã có sẵn trên bảng duyệt
                current_srt = srt_data1

            # Xử lý song ngữ dựa trên SRT của chính video này
            srt_data2 = None
            if style_config.get("is_bilingual"):
                srt_data2 = renderer.auto_translate_srt(current_srt, style_config["target_lang"])

            print(f">>> [{idx+1}/{total}] Đang Render: {filename}")
            renderer.render_video(v_path, current_srt, style_config, current_output, srt_data2=srt_data2)

            # GIẢI PHÓNG RAM bắt buộc cuối mỗi vòng lặp
            import gc
            gc.collect()
            print(f">>> [{idx+1}/{total}] Hoàn thành: {out_name} | RAM đã được dọn sạch.")

        return f"Hoàn thành Render {total} video thành công!"


    def on_render_finished(self, msg):
        self.set_progress(msg, 100)
        self.btn_scan.setEnabled(True)
        self.btn_render.setEnabled(True)
        
    def on_worker_error(self, err):
        self.set_progress("Lỗi hệ thống: Xem chi tiết trong Terminal", 0)
        print("WORKER ERROR:", err)
        self.btn_scan.setEnabled(True)
        self.btn_render.setEnabled(True)

    def set_progress(self, text, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(text)

    # --- TRÌNH XEM TRƯỚC PHỤ ĐỀ (INTERACTIVE PREVIEW) ---
    def on_table_row_clicked(self):
        """Bắt sự kiện click vào bảng, lấy timestamp và cập nhật màn hình Preview"""
        selected_items = self.subtitle_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        start_time_str = self.subtitle_table.item(row, 0).text() # Ví dụ: 00:00:05,500
        
        input_path = self.input_path_edit.text().strip()
        video_path = input_path
        if os.path.isdir(input_path):
            files = [f for f in os.listdir(input_path) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]
            if files: video_path = os.path.join(input_path, files[0])
            
        if os.path.exists(video_path):
            self.update_video_preview(video_path, time_str=start_time_str)

    def time_to_seconds(self, time_str):
        try:
            clean = time_str.strip().replace(',', '.')
            p = clean.split(':')
            return float(p[0])*3600 + float(p[1])*60 + float(p[2])
        except: return 0.0

    def update_video_preview(self, video_path, time_str=None):
        cap = cv2.VideoCapture(video_path)
        if time_str:
            seconds = self.time_to_seconds(time_str)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                frame_no = int(seconds * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            qt_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)
            self.video_preview.setPixmap(pixmap.scaled(self.video_preview.size(), Qt.AspectRatioMode.KeepAspectRatio))
        cap.release()

    # --- TIỆN ÍCH KHÁC ---
    def toggle_bilingual_options(self, checked):
        self.bilingual_container.setVisible(checked)

    def update_percent_label(self, value):
        self.label_percent.setText(f"Tỷ lệ size ngôn ngữ phụ: {value}%")   
        
    def display_srt_to_table(self, srt_data):
        self.subtitle_table.setRowCount(len(srt_data))
        for i, item in enumerate(srt_data):
            self.subtitle_table.setItem(i, 0, QTableWidgetItem(item.get('start', '')))
            self.subtitle_table.setItem(i, 1, QTableWidgetItem(item.get('end', '')))
            
            # Lưu trữ list words của từ đơn lẻ vào UserRole
            content_item = QTableWidgetItem(item.get('text', ''))
            content_item.setData(Qt.ItemDataRole.UserRole, item.get('words', []))
            self.subtitle_table.setItem(i, 2, content_item)

    def get_srt_from_table(self):
        updated_srt = []
        for i in range(self.subtitle_table.rowCount()):
            text_item = self.subtitle_table.item(i, 2)
            words = text_item.data(Qt.ItemDataRole.UserRole) if text_item else []
            if words is None:
                words = []
            updated_srt.append({
                'start': self.subtitle_table.item(i, 0).text(),
                'end': self.subtitle_table.item(i, 1).text(),
                'text': text_item.text() if text_item else '',
                'words': words
            })
        return updated_srt    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())