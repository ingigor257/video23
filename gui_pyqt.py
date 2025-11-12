# video_uniquifier_gui_pyqt.py - PyQt6 GUI с CSS поддержкой
import sys
import json
import os
import threading
import queue
import random
import shutil
import math
import subprocess
import instaloader
import re
import telebot
from pathlib import Path
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QSlider, QComboBox,
    QCheckBox, QFileDialog, QMessageBox, QScrollArea, QFrame,
    QStackedWidget, QSpinBox, QDoubleSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QVariantAnimation, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor

# === GET SCRIPT DIRECTORY ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# === DEFAULT CONFIG ===
# Config matching video_uniquifier.py behavior
DEFAULT_CONFIG = {
    'input_folder': os.path.join(SCRIPT_DIR, 'input'),
    'output_folder': os.path.join(SCRIPT_DIR, 'output'),
    'music_folder': os.path.join(SCRIPT_DIR, 'music'),
    'instagram_username': '',
    'instagram_password': '',
    'telegram_token': '',
    'add_music': True,
    'copies_per_video': 5,
    # NOTE: Settings below are kept for UI compatibility only
    # Video processing now uses fixed values from video_uniquifier.py
    'angle_zoom_map': {
        '-3': 1.085, '-2': 1.05, '-1': 1.025,
        '1': 1.025, '2': 1.05, '3': 1.085
    },
    'video_settings': {
        'output_resolution': '1080x1920',
        'video_codec': 'libx264',
        'video_preset': 'veryfast',
        'video_crf': 23,
        'audio_codec': 'aac',
        'audio_bitrate': '128k',
        'pixel_format': 'yuv420p'
    },
    'effects_settings': {
        'mirror_probability': 0.5,
        'color_balance_probability': 0.7,
        'brightness_contrast_probability': 0.5,
        'saturation_probability': 0.5,
        'color_balance_range': 0.05,
        'brightness_range': 0.02,
        'contrast_min': 0.98,
        'contrast_max': 1.02,
        'saturation_min': 0.95,
        'saturation_max': 1.05
    }
}

# === CSS STYLES ===
MAIN_STYLESHEET = """
QMainWindow {
    background-color: #0a0e1a;
}

QWidget {
    background-color: #0a0e1a;
    color: #e8eaf0;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
}

/* Base Button Style - без обводки при наведении */
QPushButton {
    background-color: #252b3d;
    color: #e8eaf0;
    border: 2px solid #2a3142;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-height: 40px;
    outline: none;
}

QPushButton:hover {
    background-color: #2d3548;
    border-color: #353c52;
}

QPushButton:pressed {
    background-color: #1e2433;
}

QPushButton:disabled {
    background-color: #1e2433;
    color: #5a6275;
    border-color: #2a3142;
}

QPushButton:focus {
    outline: none;
    border: 2px solid #2a3142;
}

/* Primary Action Buttons */
.btn-primary {
    background-color: #00994d;
    border: 2px solid #007a3d;
}

.btn-primary:hover {
    background-color: #00b35c;
    border: 2px solid #00994d;
}

/* Danger Buttons */
.btn-danger {
    background-color: #cc0033;
    border: 2px solid #990026;
}

.btn-danger:hover {
    background-color: #e6003d;
    border: 2px solid #cc0033;
}

/* Glass Card Style */
.glass-card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #1e2433, stop:1 #1a1f2e);
    border: 1px solid #2a3142;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Settings Input Frame */
.settings-input-frame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #252b3d, stop:1 #1e2433);
    border: none;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.settings-input-frame:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2d3548, stop:1 #252b3d);
}

/* Sidebar */
.sidebar {
    background-color: #151a27;
    border-right: 1px solid #2a3142;
}

/* Text Inputs */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1a1f2e;
    color: #e8eaf0;
    border: 2px solid #2a3142;
    border-radius: 10px;
    padding: 10px 15px;
    font-size: 13px;
    selection-background-color: #00ccff;
}

QLineEdit:hover, QTextEdit:hover {
    border-color: #353c52;
    background-color: #1e2433;
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #00ccff;
    background-color: #252b3d;
}

/* ComboBox */
QComboBox {
    background-color: #1a1f2e;
    color: #e8eaf0;
    border: 2px solid #2a3142;
    border-radius: 10px;
    padding: 10px 15px;
    font-size: 13px;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #353c52;
    background-color: #1e2433;
}

QComboBox:focus {
    border: 2px solid #00ccff;
    background-color: #252b3d;
}

QComboBox::drop-down {
    border: none;
    width: 35px;
    subcontrol-position: right;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e8eaf0;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1e2433;
    color: #e8eaf0;
    selection-background-color: #00ccff;
    selection-color: #ffffff;
    border: 2px solid #2a3142;
    border-radius: 10px;
    padding: 5px;
    outline: none;
}

QComboBox QAbstractItemView::item {
    min-height: 35px;
    padding: 5px 10px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #2a3142;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #00ccff;
    color: #ffffff;
}

/* Sliders */
QSlider {
    background: transparent;
}

QSlider::groove:horizontal {
    height: 10px;
    background: #1a1f2e;
    border: none;
    border-radius: 5px;
}

QSlider::handle:horizontal {
    width: 20px;
    height: 20px;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                                fx:0.5, fy:0.5,
                                stop:0 #00ffff, stop:1 #00ccff);
    border: none;
    border-radius: 10px;
    margin: -5px 0;
}

QSlider::handle:horizontal:hover {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                                fx:0.5, fy:0.5,
                                stop:0 #33ffff, stop:1 #00ddff);
    width: 20px;
    height: 20px;
    border-radius: 10px;
    margin: -5px 0;
}

QSlider::add-page:horizontal {
    background: #1a1f2e;
    border: none;
    border-radius: 5px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00ccff, stop:0.5 #00ffcc, stop:1 #b026ff);
    border: none;
    border-radius: 5px;
}

/* CheckBox */
QCheckBox {
    spacing: 10px;
    color: #e8eaf0;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #2a3142;
    border-radius: 4px;
    background-color: #1a1f2e;
}

QCheckBox::indicator:hover {
    background-color: #252b3d;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00ffff, stop:1 #00ccff);
    border: 2px solid #00ccff;
}

QCheckBox::indicator:checked:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #33ffff, stop:1 #00ddff);
}

/* ScrollBar */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    border: none;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #2a3142;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #00ccff;
}

QScrollBar::add-line:vertical {
    height: 0px;
}

QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

/* Labels */
QLabel {
    color: #e8eaf0;
    background: transparent;
}

.label-title {
    font-size: 32px;
    font-weight: bold;
    color: #00ffff;
}

.label-section {
    font-size: 18px;
    font-weight: bold;
    color: #e8eaf0;
}

.label-secondary {
    color: #8b92a8;
    font-size: 13px;
}

.label-muted {
    color: #5a6275;
    font-size: 11px;
}

/* Status Indicators */
.status-ready {
    color: #00ccff;
}

.status-working {
    color: #ffaa00;
}

.status-error {
    color: #ff0055;
}

.status-success {
    color: #00cc66;
}

/* Progress Bar */
QProgressBar {
    background-color: #252b3d;
    border: 1px solid #2a3142;
    border-radius: 8px;
    text-align: center;
    color: #e8eaf0;
    height: 25px;
}

QProgressBar::chunk {
    background-color: #00ffff;
    border-radius: 7px;
}
"""

class SimpleButton(QPushButton):
    """Простая кнопка без эффектов свечения, только лёгкая анимация при наведении"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Просто кнопка, CSS стили применяются автоматически

class GlowButton(QPushButton):
    """Кнопка с анимированным размытым свечением волной (только для навигации)"""
    def __init__(self, text, parent=None, glow=True):
        super().__init__(text, parent)
        self.glow_enabled = glow

        # Создаём градиент из цветов как в CSS примере
        self.gradient_colors = [
            QColor('#ff0000'),  # Red
            QColor('#ff7300'),  # Orange
            QColor('#fffb00'),  # Yellow
            QColor('#48ff00'),  # Green
            QColor('#00ffd5'),  # Cyan
            QColor('#002bff'),  # Blue
            QColor('#7a00ff'),  # Purple
            QColor('#ff00c8'),  # Pink
            QColor('#ff0000'),  # Red (повтор для зацикливания)
        ]

        # Позиция градиента для анимации (0.0 - 4.0 соответствует background-size: 400%)
        self.gradient_position = 0.0
        self.glow_opacity = 0.0  # Прозрачность свечения (0-1)

        # Эффект тени для свечения
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(30)  # Большое размытие для яркого эффекта
        self.shadow_effect.setOffset(0, 0)  # Центрированное свечение
        self.shadow_effect.setColor(QColor(255, 0, 0, 0))  # Начальный цвет (прозрачный)
        self.setGraphicsEffect(self.shadow_effect)

        if self.glow_enabled:
            # Таймер для анимации движения градиента (как animation: animate 20s linear infinite)
            self.gradient_timer = QTimer(self)
            self.gradient_timer.timeout.connect(self._animate_gradient)
            self.gradient_timer.setInterval(50)  # 50ms = плавная анимация

            # Анимация прозрачности (fade in/out) как transition: opacity .3s
            self.fade_animation = QVariantAnimation(self)
            self.fade_animation.setDuration(300)  # 300ms как в CSS
            self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.fade_animation.valueChanged.connect(self._update_glow_opacity)

    def enterEvent(self, event):
        """Запуск анимации при наведении"""
        if self.glow_enabled and self.isEnabled():
            # Fade in - плавное появление как в CSS (opacity .3s)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
            # Запускаем анимацию градиента
            self.gradient_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Остановка анимации при уходе курсора"""
        if self.glow_enabled:
            # Fade out - плавное исчезновение
            self.fade_animation.setStartValue(self.glow_opacity)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.start()
            # Останавливаем анимацию градиента
            self.gradient_timer.stop()
        super().leaveEvent(event)

    def _update_glow_opacity(self, value):
        """Обновление прозрачности свечения"""
        self.glow_opacity = value
        # Обновляем текущий цвет градиента с новой прозрачностью
        self._update_gradient_color()

    def _get_gradient_color_at_position(self, position):
        """Получить цвет из градиента на определённой позиции (0.0 - 4.0)"""
        # Нормализуем позицию к диапазону цветов
        num_colors = len(self.gradient_colors) - 1  # -1 потому что последний = первому

        # Вычисляем позицию в массиве цветов
        color_position = (position * num_colors / 4.0) % num_colors

        # Получаем индексы соседних цветов
        color_index = int(color_position)
        next_index = (color_index + 1) % len(self.gradient_colors)

        # Интерполируем между двумя цветами
        t = color_position - color_index
        color1 = self.gradient_colors[color_index]
        color2 = self.gradient_colors[next_index]

        r = int(color1.red() + (color2.red() - color1.red()) * t)
        g = int(color1.green() + (color2.green() - color1.green()) * t)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * t)

        return QColor(r, g, b)

    def _update_gradient_color(self):
        """Обновить цвет свечения на основе текущей позиции градиента"""
        color = self._get_gradient_color_at_position(self.gradient_position)
        alpha = int(255 * self.glow_opacity)
        glow_color = QColor(color.red(), color.green(), color.blue(), alpha)
        self.shadow_effect.setColor(glow_color)

    def _animate_gradient(self):
        """Анимация движения градиента (как в CSS @keyframes animate)"""
        # Движение градиента: 0% -> 50% (0 -> 400%) -> 100% (обратно к 0)
        # 20 секунд в CSS = 20000ms, с интервалом 50ms получаем 400 шагов
        # Скорость: 4.0 / 400 = 0.01 за шаг
        speed = 0.01

        self.gradient_position += speed

        # Зациклить позицию (0.0 - 4.0)
        if self.gradient_position >= 4.0:
            self.gradient_position = 0.0

        # Обновить цвет на основе новой позиции
        self._update_gradient_color()


class VideoUniquifierApp(QMainWindow):
    # Сигналы для обновления UI из фоновых потоков
    face_progress_signal = pyqtSignal(int, int)  # (current, total)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("◈ VIDEO UNIQUIFIER PRO ◈")
        self.setGeometry(100, 100, 1700, 950)

        # Load configuration
        self.config_file = Path("video_uniquifier_config.json")
        self.config = self.load_config()

        # Processing state
        self.is_running = False
        self.is_downloading = False
        self.stop_requested = False
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.current_video = ""

        # Telegram bot
        self.bot = None
        self.bot_thread = None
        self.user_states = {}

        # Подключаем сигнал для обновления прогресса генерации
        self.face_progress_signal.connect(self.update_face_progress)

        # List of sliders to disable wheel
        self.sliders = []

        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)

        # Setup UI
        self.setup_ui()

        # Таймер для автоматического обновления статистики каждые 2 секунды
        self.stats_update_timer = QTimer()
        self.stats_update_timer.timeout.connect(self.update_stats)
        self.stats_update_timer.start(2000)  # Обновление каждые 2 секунды

        # Install event filter on sliders
        for slider in self.sliders:
            slider.installEventFilter(self)

        # Auto-start Telegram bot after UI is ready
        if self.config.get('telegram_token'):
            QTimer.singleShot(1000, self.start_telegram_bot)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel and isinstance(obj, QSlider):
            return True  # Ignore wheel events on sliders
        return super().eventFilter(obj, event)

    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    config = DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Sidebar
        self.create_sidebar(main_layout)

        # Content area (stacked widget for different sections)
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)

        # Create sections
        self.create_dashboard_section()
        self.create_settings_section()
        self.create_face_verification_section()
        self.create_console_section()
        self.create_about_section()

        # Show dashboard by default
        self.show_section(0)

    def create_sidebar(self, parent_layout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setProperty("class", "sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)
        sidebar_layout.setSpacing(20)

        # Title in glass card
        title_frame = QFrame()
        title_frame.setProperty("class", "glass-card")
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("◈ VIDEO\nUNIQUIFIER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00ffff;")
        title_layout.addWidget(title)
        sidebar_layout.addWidget(title_frame)

        # Status indicator
        status_frame = QFrame()
        status_frame.setProperty("class", "glass-card")
        status_layout = QHBoxLayout(status_frame)
        self.status_label = QLabel("● ГОТОВА")
        self.status_label.setProperty("class", "status-ready")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(status_frame)

        sidebar_layout.addSpacing(20)

        # Navigation buttons
        nav_items = [
            ("📊 Dashboard", 0),
            ("⚙️ Настройки", 1),
            ("👤 Верификация селфи", 2),
            ("📝 Консоль", 3),
            ("ℹ️ О софте", 4),
        ]

        self.nav_buttons = []
        for text, index in nav_items:
            btn = GlowButton(text, glow=True)  # Навигационные кнопки с blur glow
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, idx=index: self.show_section(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addSpacing(20)

        # Statistics
        stats_frame = QFrame()
        stats_frame.setProperty("class", "glass-card")
        stats_layout = QVBoxLayout(stats_frame)

        stats_title = QLabel("◈ СТАТИСТИКА")
        stats_title.setProperty("class", "label-secondary")
        stats_layout.addWidget(stats_title)

        self.stat_labels = {}
        stats_data = [
            ("Обработано", "processed", "#00cc66"),
            ("Ошибок", "failed", "#ff0055"),
            ("Всего", "total", "#00ccff"),
        ]

        for label_text, key, color in stats_data:
            stat_row = QHBoxLayout()
            label = QLabel(label_text)
            label.setProperty("class", "label-muted")
            value = QLabel("0")
            value.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
            stat_row.addWidget(label)
            stat_row.addStretch()
            stat_row.addWidget(value)
            stats_layout.addLayout(stat_row)
            self.stat_labels[key] = value

        sidebar_layout.addWidget(stats_frame)
        sidebar_layout.addStretch()

        parent_layout.addWidget(sidebar)

    def create_dashboard_section(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)
        layout.setSpacing(20)

        # Header
        header = QLabel("◈ ПАНЕЛЬ УПРАВЛЕНИЯ")
        header.setProperty("class", "label-title")
        layout.addWidget(header)

        # Statistics cards
        stats_row = QHBoxLayout()
        self.dashboard_stats = {}

        stat_cards = [
            ("Входных видео", "input", "#00ffff"),
            ("Музыкальных треков", "music", "#b026ff"),
            ("Будет создано", "output", "#00ccff"),
        ]

        for label_text, key, color in stat_cards:
            card = self.create_stat_card(label_text, "0", color)
            stats_row.addWidget(card)
            self.dashboard_stats[key] = card.findChild(QLabel, "value")

        layout.addLayout(stats_row)

        # Download section
        download_card = QFrame()
        download_card.setProperty("class", "glass-card")
        download_layout = QVBoxLayout(download_card)

        download_title = QLabel("◈ ЗАГРУЗКА REELS ИЗ INSTAGRAM")
        download_title.setProperty("class", "label-section")
        download_layout.addWidget(download_title)

        info = QLabel("Вставьте URL Reels или @username (по одному на строку)")
        info.setProperty("class", "label-muted")
        download_layout.addWidget(info)

        self.reels_text = QTextEdit()
        self.reels_text.setMaximumHeight(150)
        download_layout.addWidget(self.reels_text)

        buttons_row = QHBoxLayout()
        self.download_btn = SimpleButton("⬇️ ЗАГРУЗИТЬ")
        self.download_btn.setProperty("class", "btn-primary")
        self.download_btn.setStyleSheet("background-color: #00994d;")
        self.download_btn.setMinimumHeight(50)
        self.download_btn.clicked.connect(lambda: self.start_download(False))
        buttons_row.addWidget(self.download_btn)

        self.download_process_btn = SimpleButton("⬇️ ЗАГРУЗИТЬ И ОБРАБОТАТЬ")
        self.download_process_btn.setProperty("class", "btn-primary")
        self.download_process_btn.setStyleSheet("background-color: #00994d;")
        self.download_process_btn.setMinimumHeight(50)
        self.download_process_btn.clicked.connect(lambda: self.start_download(True))
        buttons_row.addWidget(self.download_process_btn)

        download_layout.addLayout(buttons_row)
        layout.addWidget(download_card)

        # Control section
        control_card = QFrame()
        control_card.setProperty("class", "glass-card")
        control_layout = QVBoxLayout(control_card)

        control_title = QLabel("◈ УПРАВЛЕНИЕ ОБРАБОТКОЙ")
        control_title.setProperty("class", "label-section")
        control_layout.addWidget(control_title)

        control_buttons = QHBoxLayout()
        self.start_btn = SimpleButton("▶ ЗАПУСТИТЬ ОБРАБОТКУ")
        self.start_btn.setProperty("class", "btn-primary")
        self.start_btn.setStyleSheet("background-color: #00994d; font-size: 16px;")
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setMinimumWidth(300)
        self.start_btn.clicked.connect(self.start_processing)
        control_buttons.addWidget(self.start_btn)

        self.stop_btn = SimpleButton("⏹ ОСТАНОВИТЬ")
        self.stop_btn.setProperty("class", "btn-danger")
        self.stop_btn.setStyleSheet("background-color: #cc0033; font-size: 16px;")
        self.stop_btn.setMinimumHeight(60)
        self.stop_btn.setMinimumWidth(200)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        control_buttons.addWidget(self.stop_btn)

        control_layout.addLayout(control_buttons)

        self.current_video_label = QLabel("")
        self.current_video_label.setProperty("class", "label-secondary")
        self.current_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.current_video_label)

        layout.addWidget(control_card)
        layout.addStretch()

        scroll.setWidget(dashboard)
        self.content_stack.addWidget(scroll)

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setProperty("class", "glass-card")
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setProperty("class", "label-secondary")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"color: {color}; font-size: 40px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(value_label)

        return card

    def create_settings_section(self):
        """Создание полного раздела настроек"""
        settings_widget = QWidget()
        main_layout = QVBoxLayout(settings_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        settings_content = QWidget()
        layout = QVBoxLayout(settings_content)
        layout.setSpacing(20)

        # Header
        header = QLabel("◈ НАСТРОЙКИ")
        header.setProperty("class", "label-title")
        layout.addWidget(header)

        # === FOLDERS ===
        folders_card = QFrame()
        folders_card.setProperty("class", "glass-card")
        folders_layout = QVBoxLayout(folders_card)

        folders_title = QLabel("◈ ПАПКИ")
        folders_title.setProperty("class", "label-section")
        folders_layout.addWidget(folders_title)

        self.create_folder_input(folders_layout, "Папка с входными видео", "input_folder")
        self.create_folder_input(folders_layout, "Папка для выходных видео", "output_folder")
        self.create_folder_input(folders_layout, "Папка с музыкой", "music_folder")

        layout.addWidget(folders_card)

        # === INSTAGRAM ===
        instagram_card = QFrame()
        instagram_card.setProperty("class", "glass-card")
        instagram_layout = QVBoxLayout(instagram_card)

        instagram_title = QLabel("◈ INSTAGRAM")
        instagram_title.setProperty("class", "label-section")
        instagram_layout.addWidget(instagram_title)

        self.create_text_input(instagram_layout, "Instagram Username", "instagram_username")
        self.create_text_input(instagram_layout, "Instagram Password", "instagram_password", password=True)

        layout.addWidget(instagram_card)

        # === TELEGRAM ===
        telegram_card = QFrame()
        telegram_card.setProperty("class", "glass-card")
        telegram_layout = QVBoxLayout(telegram_card)

        telegram_title = QLabel("◈ TELEGRAM BOT")
        telegram_title.setProperty("class", "label-section")
        telegram_layout.addWidget(telegram_title)

        self.create_text_input(telegram_layout, "Telegram Bot Token", "telegram_token")

        telegram_info = QLabel("Бот принимает видео или Instagram ссылки, обрабатывает с настройками из скрипта и отправляет готовые видео обратно.\nБот автоматически запускается при старте если введён токен.")
        telegram_info.setProperty("class", "label-muted")
        telegram_info.setWordWrap(True)
        telegram_layout.addWidget(telegram_info)

        # Bot status
        self.bot_status_label = QLabel("● НЕ ЗАПУЩЕН")
        self.bot_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff4444; margin-top: 10px;")
        telegram_layout.addWidget(self.bot_status_label)

        layout.addWidget(telegram_card)

        # === ANGLE-ZOOM MAPPING ===
        angles_card = QFrame()
        angles_card.setProperty("class", "glass-card")
        angles_layout = QVBoxLayout(angles_card)

        angles_title = QLabel("◈ УГЛЫ И ЗУМЫ (Angle-to-Zoom Mapping)")
        angles_title.setProperty("class", "label-section")
        angles_layout.addWidget(angles_title)

        angles_info = QLabel("Каждому углу соответствует свой зум, чтобы скрыть углы после поворота")
        angles_info.setProperty("class", "label-muted")
        angles_info.setWordWrap(True)
        angles_layout.addWidget(angles_info)

        self.angle_entries = {}
        for angle in [-3, -2, -1, 1, 2, 3]:
            self.create_angle_zoom_input(angles_layout, angle)

        layout.addWidget(angles_card)

        # === COPIES ===
        copies_card = QFrame()
        copies_card.setProperty("class", "glass-card")
        copies_layout = QVBoxLayout(copies_card)

        copies_title = QLabel("◈ КОЛИЧЕСТВО КОПИЙ")
        copies_title.setProperty("class", "label-section")
        copies_layout.addWidget(copies_title)

        self.create_slider_input(copies_layout, "Количество копий на видео", "copies_per_video", 1, 100, step=1)

        # Add music switch in a proper frame
        self.create_checkbox_input(copies_layout, "Добавлять музыку к видео", "add_music",
                                   "Если выключено, оригинальный звук видео будет сохранён")

        layout.addWidget(copies_card)

        # === VIDEO SETTINGS ===
        video_card = QFrame()
        video_card.setProperty("class", "glass-card")
        video_layout = QVBoxLayout(video_card)

        video_title = QLabel("◈ НАСТРОЙКИ ВИДЕО")
        video_title.setProperty("class", "label-section")
        video_layout.addWidget(video_title)

        self.create_dropdown_input(video_layout, "Разрешение выхода", "output_resolution",
                                   ["1920x1080", "1280x720", "720x1280", "1080x1920"])
        self.create_dropdown_input(video_layout, "Видеокодек", "video_codec",
                                   ["libx264", "libx265", "libvpx-vp9"])
        self.create_dropdown_input(video_layout, "Preset", "video_preset",
                                   ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.create_slider_input(video_layout, "CRF (качество)", "video_crf", 0, 51)
        self.create_dropdown_input(video_layout, "Аудиокодек", "audio_codec",
                                   ["aac", "libmp3lame", "libopus"])
        self.create_dropdown_input(video_layout, "Битрейт аудио", "audio_bitrate",
                                   ["128k", "192k", "256k", "320k"])
        self.create_dropdown_input(video_layout, "Pixel Format", "pixel_format",
                                   ["yuv420p", "yuv444p", "rgb24"])

        layout.addWidget(video_card)

        # === EFFECTS SETTINGS ===
        effects_card = QFrame()
        effects_card.setProperty("class", "glass-card")
        effects_layout = QVBoxLayout(effects_card)

        effects_title = QLabel("◈ НАСТРОЙКИ ЭФФЕКТОВ")
        effects_title.setProperty("class", "label-section")
        effects_layout.addWidget(effects_title)

        self.create_slider_input(effects_layout, "Вероятность зеркала", "mirror_probability", 0, 1, step=0.1)
        self.create_slider_input(effects_layout, "Вероятность цветокоррекции", "color_balance_probability", 0, 1, step=0.1)
        self.create_slider_input(effects_layout, "Вероятность яркость/контраст", "brightness_contrast_probability", 0, 1, step=0.1)
        self.create_slider_input(effects_layout, "Вероятность насыщенности", "saturation_probability", 0, 1, step=0.1)
        self.create_slider_input(effects_layout, "Диапазон цветокоррекции", "color_balance_range", 0, 0.1, step=0.01)
        self.create_slider_input(effects_layout, "Диапазон яркости", "brightness_range", 0, 0.1, step=0.01)

        # Range inputs for contrast and saturation
        self.create_range_slider_input(effects_layout, "Диапазон контраста", "contrast_min", "contrast_max")
        self.create_range_slider_input(effects_layout, "Диапазон насыщенности", "saturation_min", "saturation_max")

        layout.addWidget(effects_card)
        layout.addStretch()

        scroll.setWidget(settings_content)
        main_layout.addWidget(scroll)

        self.content_stack.addWidget(settings_widget)

    def create_face_verification_section(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        face_widget = QWidget()
        layout = QVBoxLayout(face_widget)
        layout.setSpacing(20)

        # Header
        header = QLabel("◈ ВЕРИФИКАЦИЯ СЕЛФИ")
        header.setProperty("class", "label-title")
        layout.addWidget(header)

        # Description
        desc_card = QFrame()
        desc_card.setProperty("class", "glass-card")
        desc_layout = QVBoxLayout(desc_card)

        desc_label = QLabel("Генерация уникальных фотографий селфи с помощью AI\n(thispersondoesnotexist.com)")
        desc_label.setProperty("class", "label-secondary")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_layout.addWidget(desc_label)

        layout.addWidget(desc_card)

        # Settings card
        settings_card = QFrame()
        settings_card.setProperty("class", "glass-card")
        settings_layout = QVBoxLayout(settings_card)

        settings_title = QLabel("◈ НАСТРОЙКИ ГЕНЕРАЦИИ")
        settings_title.setProperty("class", "label-section")
        settings_layout.addWidget(settings_title)

        # Output folder
        folder_frame = QFrame()
        folder_frame.setProperty("class", "settings-input-frame")
        folder_layout = QVBoxLayout(folder_frame)
        folder_layout.setContentsMargins(15, 12, 15, 12)
        folder_layout.setSpacing(8)

        folder_label = QLabel("Папка для сохранения фото")
        folder_label.setProperty("class", "label-secondary")
        folder_layout.addWidget(folder_label)

        folder_input_layout = QHBoxLayout()
        folder_input_layout.setSpacing(10)

        self.face_output_folder_entry = QLineEdit()
        self.face_output_folder_entry.setText("faces")
        self.face_output_folder_entry.setPlaceholderText("Выберите папку...")
        folder_input_layout.addWidget(self.face_output_folder_entry)

        browse_btn = SimpleButton("📁 Обзор")
        browse_btn.setMinimumWidth(90)
        browse_btn.setMaximumHeight(38)
        browse_btn.clicked.connect(self.browse_face_folder)
        folder_input_layout.addWidget(browse_btn)

        folder_layout.addLayout(folder_input_layout)
        settings_layout.addWidget(folder_frame)

        # Count selector
        count_frame = QFrame()
        count_frame.setProperty("class", "settings-input-frame")
        count_layout = QVBoxLayout(count_frame)
        count_layout.setContentsMargins(15, 20, 15, 20)
        count_layout.setSpacing(10)

        count_header = QHBoxLayout()
        count_label = QLabel("Количество фото для генерации")
        count_label.setProperty("class", "label-secondary")
        count_header.addWidget(count_label)

        self.face_count_value_label = QLabel("100")
        self.face_count_value_label.setMinimumWidth(60)
        self.face_count_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.face_count_value_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #00ffff;
            background-color: #1a1f2e;
            border: 1px solid #2a3142;
            border-radius: 6px;
            padding: 4px 10px;
        """)
        count_header.addWidget(self.face_count_value_label)
        count_layout.addLayout(count_header)

        # Slider
        self.face_count_slider = QSlider(Qt.Orientation.Horizontal)
        self.face_count_slider.setMinimum(1)
        self.face_count_slider.setMaximum(500)
        self.face_count_slider.setValue(100)
        self.face_count_slider.setSingleStep(1)  # Шаг = 1 (только целые числа)
        self.face_count_slider.setPageStep(10)   # Большой шаг при Page Up/Down
        self.face_count_slider.valueChanged.connect(lambda v: self.face_count_value_label.setText(str(v)))
        self.face_count_slider.installEventFilter(self)  # Отключаем колесико мыши
        count_layout.addWidget(self.face_count_slider)

        # Min/Max labels
        minmax_layout = QHBoxLayout()
        min_label = QLabel("1")
        min_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        minmax_layout.addWidget(min_label)
        minmax_layout.addStretch()
        max_label = QLabel("500")
        max_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        minmax_layout.addWidget(max_label)
        count_layout.addLayout(minmax_layout)

        settings_layout.addWidget(count_frame)
        layout.addWidget(settings_card)

        # Control card
        control_card = QFrame()
        control_card.setProperty("class", "glass-card")
        control_layout = QVBoxLayout(control_card)

        control_title = QLabel("◈ ГЕНЕРАЦИЯ")
        control_title.setProperty("class", "label-section")
        control_layout.addWidget(control_title)

        # Progress bar
        self.face_progress = QProgressBar()
        self.face_progress.setValue(0)
        self.face_progress.setTextVisible(True)
        self.face_progress.setFormat("%v / %m")
        control_layout.addWidget(self.face_progress)

        # Status label
        self.face_status_label = QLabel("")
        self.face_status_label.setProperty("class", "label-secondary")
        self.face_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.face_status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.face_start_btn = SimpleButton("▶ НАЧАТЬ ГЕНЕРАЦИЮ")
        self.face_start_btn.setProperty("class", "btn-primary")
        self.face_start_btn.setStyleSheet("background-color: #00994d; font-size: 16px;")
        self.face_start_btn.setMinimumHeight(60)
        self.face_start_btn.setMinimumWidth(300)
        self.face_start_btn.clicked.connect(self.start_face_generation)
        button_layout.addWidget(self.face_start_btn)

        self.face_stop_btn = SimpleButton("⏹ ОСТАНОВИТЬ")
        self.face_stop_btn.setProperty("class", "btn-danger")
        self.face_stop_btn.setStyleSheet("background-color: #cc0033; font-size: 16px;")
        self.face_stop_btn.setMinimumHeight(60)
        self.face_stop_btn.setMinimumWidth(200)
        self.face_stop_btn.setEnabled(False)
        self.face_stop_btn.clicked.connect(self.stop_face_generation)
        button_layout.addWidget(self.face_stop_btn)

        control_layout.addLayout(button_layout)
        layout.addWidget(control_card)
        layout.addStretch()

        scroll.setWidget(face_widget)
        self.content_stack.addWidget(scroll)

    def browse_face_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения фото")
        if folder:
            self.face_output_folder_entry.setText(folder)

    def start_face_generation(self):
        if hasattr(self, 'face_generation_running') and self.face_generation_running:
            return

        output_folder = self.face_output_folder_entry.text()
        count = self.face_count_slider.value()

        if not output_folder:
            QMessageBox.warning(self, "Предупреждение", "Укажите папку для сохранения фото!")
            return

        os.makedirs(output_folder, exist_ok=True)

        self.face_generation_running = True
        self.face_stop_requested = False
        self.face_start_btn.setEnabled(False)
        self.face_stop_btn.setEnabled(True)
        self.face_progress.setMaximum(count)
        self.face_progress.setValue(0)
        self.face_status_label.setText("Генерация началась...")

        # Запускаем генерацию в отдельном потоке
        face_thread = threading.Thread(target=self.run_face_generation, args=(output_folder, count), daemon=True)
        face_thread.start()

    def run_face_generation(self, output_folder, count):
        try:
            import requests
            from PIL import Image
            from io import BytesIO
            import time

            self.log(f"◈ ГЕНЕРАЦИЯ {count} ФОТО СЕЛФИ")
            self.log(f"Папка: {output_folder}\n")

            for i in range(1, count + 1):
                if hasattr(self, 'face_stop_requested') and self.face_stop_requested:
                    self.log("\n⏹ ГЕНЕРАЦИЯ ОСТАНОВЛЕНА")
                    break

                try:
                    # Скачиваем уникальное фото
                    url = "https://thispersondoesnotexist.com/"
                    response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})

                    # Сохраняем как .jpg
                    img = Image.open(BytesIO(response.content))
                    path = os.path.join(output_folder, f"face_{i:03}.jpg")
                    img.save(path)

                    self.log(f"✅ {i}/{count} сохранено: {os.path.basename(path)}")

                    # Отправляем сигнал для обновления GUI
                    self.face_progress_signal.emit(i, count)

                    time.sleep(1.5)  # Пауза, чтобы не блокнули
                except Exception as e:
                    self.log(f"❌ Ошибка при загрузке {i}: {e}")

            if not (hasattr(self, 'face_stop_requested') and self.face_stop_requested):
                self.log(f"\n✓ ГЕНЕРАЦИЯ ЗАВЕРШЕНА: {count} фото")
                QTimer.singleShot(0, lambda c=count: self.face_status_label.setText(f"Завершено! Сгенерировано {c} фото"))

        except Exception as e:
            self.log(f"❌ ОШИБКА ГЕНЕРАЦИИ: {str(e)}")
            QTimer.singleShot(0, lambda: self.face_status_label.setText("Ошибка генерации!"))
        finally:
            # Обновляем GUI в главном потоке
            QTimer.singleShot(0, lambda: self.finalize_face_generation())

    def update_face_progress(self, current, total):
        """Обновить прогресс генерации (вызывается через сигнал в главном потоке)"""
        self.face_progress.setValue(current)
        self.face_status_label.setText(f"Сгенерировано {current} из {total}")

    def finalize_face_generation(self):
        """Завершить генерацию и восстановить кнопки (вызывается в главном потоке)"""
        self.face_generation_running = False
        self.face_start_btn.setEnabled(True)
        self.face_stop_btn.setEnabled(False)

    def stop_face_generation(self):
        if not (hasattr(self, 'face_generation_running') and self.face_generation_running):
            return

        result = QMessageBox.question(self, "Подтвердить",
                                     "Остановить генерацию?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if result == QMessageBox.StandardButton.Yes:
            self.face_stop_requested = True
            self.log("\n⏹ ЗАПРОС НА ОСТАНОВКУ ГЕНЕРАЦИИ...")
            self.face_status_label.setText("Останавливается...")
            self.face_stop_btn.setEnabled(False)

    def create_console_section(self):
        console_widget = QWidget()
        layout = QVBoxLayout(console_widget)

        header = QLabel("◈ КОНСОЛЬ")
        header.setProperty("class", "label-title")
        layout.addWidget(header)

        clear_btn = QPushButton("🧹 ОЧИСТИТЬ")
        clear_btn.setMaximumWidth(150)
        clear_btn.clicked.connect(self.clear_console)
        layout.addWidget(clear_btn)

        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        layout.addWidget(self.console_text)

        self.content_stack.addWidget(console_widget)

    def create_about_section(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("◈ О СОФТЕ")
        header.setProperty("class", "label-title")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Main info card
        info_card = QFrame()
        info_card.setProperty("class", "glass-card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(25)
        info_layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel("💻 Instagram Video Uniquifier")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #00ffff;
            background: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(title_label)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("background-color: #2a3142; max-height: 2px;")
        info_layout.addWidget(separator1)

        # Description
        desc_label = QLabel(
            "💻 Данный софт разработан с помощью вайбкодинга.\n\n"
            "Если вы заметили ошибки, баги или другие проблемы — пишите мне в личные сообщения в Telegram: @motion_igor.\n\n"
            "Изначально основа софта была взята у @blopinski,\n"
            "а я доработал её, добавив графический интерфейс и дополнительные функции."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            font-size: 14px;
            line-height: 1.6;
            color: #e8eaf0;
            background: transparent;
            padding: 10px;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(desc_label)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #2a3142; max-height: 2px;")
        info_layout.addWidget(separator2)

        # Features section
        features_title = QLabel("✨ Основные функции:")
        features_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #00ccff;
            background: transparent;
            margin-top: 10px;
        """)
        info_layout.addWidget(features_title)

        features_text = QLabel(
            "• Загрузка видео из Instagram (по URL или @username)\n"
            "• Уникализация видео с различными эффектами\n"
            "• Поворот, зум, зеркалирование\n"
            "• Цветокоррекция и фильтры\n"
            "• Наложение музыки\n"
            "• Генерация AI-фото для верификации селфи\n"
            "• Автоматическая обработка с множественными копиями\n"
            "• Telegram бот для управления"
        )
        features_text.setWordWrap(True)
        features_text.setStyleSheet("""
            font-size: 13px;
            line-height: 1.8;
            color: #c8cad0;
            background: transparent;
            padding: 10px 10px 10px 20px;
        """)
        info_layout.addWidget(features_text)

        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setStyleSheet("background-color: #2a3142; max-height: 2px;")
        info_layout.addWidget(separator3)

        # Contacts section
        contacts_title = QLabel("📬 Контакты:")
        contacts_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #00ccff;
            background: transparent;
            margin-top: 10px;
        """)
        info_layout.addWidget(contacts_title)

        telegram_btn = SimpleButton("📱 Написать в Telegram: @motion_igor")
        telegram_btn.setStyleSheet("""
            QPushButton {
                background-color: #0088cc;
                border: 2px solid #00aaff;
                border-radius: 12px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 30px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #00aaff;
                border-color: #00ccff;
            }
            QPushButton:pressed {
                background-color: #006699;
            }
        """)
        telegram_btn.clicked.connect(lambda: self.open_telegram_contact())
        info_layout.addWidget(telegram_btn)

        # Credits
        credits_label = QLabel(
            "\n© 2025 Instagram Video Uniquifier\n"
            "Based on original work by @blopinski\n"
            "Enhanced by @motion_igor"
        )
        credits_label.setStyleSheet("""
            font-size: 11px;
            color: #6b7280;
            background: transparent;
        """)
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(credits_label)

        layout.addWidget(info_card)
        layout.addStretch()

        scroll.setWidget(about_widget)
        self.content_stack.addWidget(scroll)

    def open_telegram_contact(self):
        import webbrowser
        webbrowser.open("https://t.me/motion_igor")
        self.log("📱 Открыта ссылка на Telegram: @motion_igor")

    def show_section(self, index):
        self.content_stack.setCurrentIndex(index)

    def clear_console(self):
        self.console_text.clear()

    def log(self, message):
        self.console_text.append(message)

    def start_download(self, auto_process):
        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_btn.setEnabled(False)

        urls_text = self.reels_text.toPlainText().strip()
        if not urls_text:
            QMessageBox.warning(self, "Предупреждение", "Введите URL или @username для загрузки!")
            self.is_downloading = False
            self.download_btn.setEnabled(True)
            return

        self.log("Загрузка начата...")
        self.status_label.setText("● ЗАГРУЗКА")
        self.status_label.setProperty("class", "status-working")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffaa00;")

        # Запускаем загрузку в отдельном потоке
        download_thread = threading.Thread(target=self._download_reels_threaded, args=(auto_process,), daemon=True)
        download_thread.start()

    def _download_reels_threaded(self, auto_process):
        try:
            downloaded_count = self.download_reels()
            self.log(f"✓ Загружено {downloaded_count} видео")

            # Показываем уведомление о загрузке в главном потоке через QTimer
            if downloaded_count > 0:
                QTimer.singleShot(0, lambda: self.show_download_success(downloaded_count))
                # Обновляем статистику
                self.update_stats()
            else:
                QTimer.singleShot(0, lambda: self.show_download_warning())

            if auto_process and downloaded_count > 0:
                self.start_processing()
        except Exception as e:
            self.log(f"✗ Ошибка загрузки: {str(e)}")
            QTimer.singleShot(0, lambda: self.show_download_error(str(e)))
        finally:
            self.is_downloading = False
            self.download_btn.setEnabled(True)
            self.status_label.setText("● ГОТОВА")
            self.status_label.setProperty("class", "status-ready")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ccff;")

    def show_download_success(self, count):
        """Показать уведомление об успешной загрузке (вызывается в главном потоке)"""
        QMessageBox.information(
            self,
            "Загрузка завершена",
            f"✅ Успешно загружено {count} видео из Instagram!\n\nВидео сохранены в папку:\n{self.config['input_folder']}"
        )

    def show_download_warning(self):
        """Показать предупреждение о пустой загрузке (вызывается в главном потоке)"""
        QMessageBox.warning(
            self,
            "Нет загрузок",
            "⚠️ Не удалось загрузить видео.\nПроверьте URL или имя пользователя."
        )

    def show_download_error(self, error_msg):
        """Показать ошибку загрузки (вызывается в главном потоке)"""
        QMessageBox.critical(
            self,
            "Ошибка загрузки",
            f"❌ Произошла ошибка при загрузке:\n\n{error_msg}"
        )

    def download_reels(self):
        inputs = self.reels_text.toPlainText().strip().splitlines()
        if not inputs:
            return 0

        input_folder = self.config['input_folder']
        os.makedirs(input_folder, exist_ok=True)

        downloaded_count = 0
        loader = instaloader.Instaloader()
        loader.dirname_pattern = input_folder
        loader.filename_pattern = '{shortcode}'
        loader.download_pictures = False
        loader.download_geotags = False
        loader.download_comments = False
        loader.download_video_thumbnails = False
        loader.save_metadata = False
        loader.post_metadata_txt_pattern = ''

        username = self.config.get('instagram_username', '')
        password = self.config.get('instagram_password', '')
        if username and password:
            try:
                loader.login(username, password)
                self.log("✓ Успешный вход в Instagram")
            except Exception as e:
                self.log(f"✗ Ошибка входа: {str(e)}")
                return 0

        for line in inputs:
            if not line.strip():
                continue

            try:
                if line.startswith('@'):
                    username = line[1:].strip()
                    self.log(f"⬇️ Загрузка всех видео из аккаунта: {username}")
                    profile = instaloader.Profile.from_username(loader.context, username)
                    for post in profile.get_posts():
                        if post.is_video:
                            loader.download_post(post, target='')
                            downloaded_count += 1
                    self.log(f"✓ Загружены видео из аккаунта: {username}")
                else:
                    url = line.strip()
                    self.log(f"⬇️ Загрузка: {url}")
                    match = re.search(r'/(?:p|reel|reels)/([A-Za-z0-9_-]+)/', url)
                    if match:
                        shortcode = match.group(1)
                        try:
                            post = instaloader.Post.from_shortcode(loader.context, shortcode)
                            if post.is_video:
                                loader.download_post(post, target='')
                                downloaded_count += 1
                            self.log(f"✓ Загружено: {url}")
                        except Exception as e:
                            self.log(f"✗ Ошибка: {str(e)}")
                    else:
                        self.log(f"✗ Недействительный URL: {url}")
            except Exception as e:
                self.log(f"✗ Ошибка загрузки {line}: {str(e)}")

        # Очистка ненужных файлов
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        for filename in os.listdir(input_folder):
            filepath = os.path.join(input_folder, filename)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename)
                if ext.lower() not in video_extensions:
                    os.remove(filepath)

        return downloaded_count

    def start_processing(self):
        if self.is_running:
            return

        os.makedirs(self.config['input_folder'], exist_ok=True)
        os.makedirs(self.config['output_folder'], exist_ok=True)
        if self.config['add_music']:
            os.makedirs(self.config['music_folder'], exist_ok=True)

        input_videos = self.get_video_files(self.config['input_folder'])
        music_videos = self.get_audio_files(self.config['music_folder']) if self.config['add_music'] else []

        if not input_videos:
            QMessageBox.warning(self, "Предупреждение",
                               f"Нет видео в папке:\n{self.config['input_folder']}")
            return

        if self.config['add_music'] and not music_videos:
            QMessageBox.warning(self, "Предупреждение",
                               f"Нет музыки в папке:\n{self.config['music_folder']}")
            return

        self.processed_count = 0
        self.failed_count = 0
        self.total_count = len(input_videos) * self.config['copies_per_video']
        self.stop_requested = False

        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("● РАБОТАЕТ")
        self.status_label.setProperty("class", "status-working")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffaa00;")

        processing_thread = threading.Thread(target=self.run_processing, daemon=True)
        processing_thread.start()

        self.log("="*85)
        self.log("◈ ОБРАБОТКА ВИДЕО ЗАПУЩЕНА")
        self.log("="*85)

    def run_processing(self):
        """Обработка видео - точная копия из gui.py"""
        try:
            input_folder = self.config['input_folder']
            output_folder = self.config['output_folder']
            music_folder = self.config['music_folder']

            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            os.makedirs(output_folder, exist_ok=True)
            self.log("🧹 Папка output очищена\n")

            input_videos = self.get_video_files(input_folder)
            music_videos = self.get_audio_files(music_folder) if self.config['add_music'] else []

            self.log(f"\nSource: {len(input_videos)} videos")
            if self.config['add_music']:
                self.log(f"Music: {len(music_videos)} tracks")
            else:
                self.log("Music overlay: DISABLED (original audio preserved)")
            self.log(f"Creating {len(input_videos) * self.config['copies_per_video']} outputs ( {self.config['copies_per_video']} copies per video )\n")

            self.log("Angle-to-Zoom Mapping:")
            for angle, zoom in sorted(self.config['angle_zoom_map'].items(), key=lambda x: int(x[0])):
                angle_int = int(angle)
                zoom_float = float(zoom)
                self.log(f"  {angle_int:+3d}° → {zoom_float:.4f}x zoom ({(zoom_float-1)*100:.1f}% crop)")
            self.log("")

            for i, input_video in enumerate(input_videos, 1):
                if self.stop_requested:
                    self.log("\n⏹ ОСТАНОВЛЕНО")
                    break

                for j in range(1, self.config['copies_per_video'] + 1):
                    if self.stop_requested:
                        break

                    music_video = random.choice(music_videos) if self.config['add_music'] and music_videos else None

                    output_filename = f"{i}.{j}.mp4"
                    output_path = os.path.join(output_folder, output_filename)

                    # Аналог self.root.after из gui.py - просто сохраняем в переменную
                    self.current_video = output_filename

                    if self.uniquify_video(input_video, music_video, output_path):
                        self.processed_count += 1
                    else:
                        self.failed_count += 1

            if not self.stop_requested:
                self.log("\n" + "="*85)
                self.log(f"◈ ОБРАБОТКА ЗАВЕРШЕНА")
                self.log("="*85)
                self.log(f"✦ Успешно: {self.processed_count}")
                self.log(f"✧ Ошибок: {self.failed_count}")
                self.log(f"◈ Всего: {self.processed_count + self.failed_count}")
                self.log("Format: 1080x1920 vertical | Corners hidden by corresponding zoom!")
                self.log("="*85)

        except Exception as e:
            self.log(f"\n❌ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.stop_requested = False
            self.current_video = ""

    def stop_processing(self):
        if not self.is_running:
            return

        result = QMessageBox.question(self, "Подтвердить",
                                     "Остановить обработку?\n\nТекущее видео завершится.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if result == QMessageBox.StandardButton.Yes:
            self.stop_requested = True
            self.log("\n⏹ ЗАПРОС НА ОСТАНОВКУ...")
            self.status_label.setText("● ОСТАНАВЛИВАЕТСЯ")
            self.status_label.setProperty("class", "status-error")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff0055;")
            self.stop_btn.setEnabled(False)

    def get_video_files(self, folder):
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        files = {}
        try:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in video_extensions:
                        key = filepath.lower()
                        files[key] = filepath
        except:
            pass
        return sorted(files.values())

    def get_audio_files(self, folder):
        audio_extensions = ['.mp3', '.wav', '.aac', '.m4a', '.ogg', '.flac', '.mp4', '.mov', '.avi', '.mkv']
        files = {}
        try:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in audio_extensions:
                        key = filepath.lower()
                        files[key] = filepath
        except:
            pass
        return sorted(files.values())

    def get_video_resolution(self, video_path):
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            width = data['streams'][0]['width']
            height = data['streams'][0]['height']
            return width, height
        except:
            return 1920, 1080

    def get_random_filters(self):
        """Random video filters - simple version from video_uniquifier.py"""
        filters = []
        if random.random() > 0.3:
            rs = random.uniform(-0.05, 0.05)
            gs = random.uniform(-0.05, 0.05)
            bs = random.uniform(-0.05, 0.05)
            rm = random.uniform(-0.05, 0.05)
            gm = random.uniform(-0.05, 0.05)
            bm = random.uniform(-0.05, 0.05)
            filters.append(f"colorbalance=rs={rs:.3f}:gs={gs:.3f}:bs={bs:.3f}:rm={rm:.3f}:gm={gm:.3f}:bm={bm:.3f}")
        if random.random() > 0.5:
            brightness = random.uniform(-0.02, 0.02)
            contrast = random.uniform(0.98, 1.02)
            filters.append(f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}")
        if random.random() > 0.5:
            saturation = random.uniform(0.95, 1.05)
            filters.append(f"eq=saturation={saturation:.3f}")
        return filters

    def uniquify_video(self, input_video, music_video, output_video):
        """
        Process video with:
        1. Random angle selection from ANGLE_ZOOM_MAP
        2. Corresponding fixed zoom for that angle
        3. All other uniquification (mirror, filters, etc.)
        Simple version from video_uniquifier.py
        """
        # Fixed angle-to-zoom mapping
        ANGLE_ZOOM_MAP = {
            -3: 1.085,  # 8.5% zoom for 3° left
            -2: 1.05,   # 5% zoom for 2° left
            -1: 1.025,  # 2.5% zoom for 1° left
            1: 1.025,   # 2.5% zoom for 1° right
            2: 1.05,    # 5% zoom for 2° right
            3: 1.085,   # 8.5% zoom for 3° right
        }

        try:
            # Get original resolution
            orig_w, orig_h = self.get_video_resolution(input_video)

            # SELECT ONE RANDOM ANGLE with its fixed zoom
            angle_degrees = random.choice(list(ANGLE_ZOOM_MAP.keys()))
            zoom_factor = ANGLE_ZOOM_MAP[angle_degrees]
            angle_radians = angle_degrees * math.pi / 180

            # Random parameters (rest of uniquification)
            mirror = random.random() > 0.5

            # Build filter chain
            filter_parts = []

            # 1. Rotate with black background
            filter_parts.append(f"rotate={angle_radians:.6f}:fillcolor=black")

            # 2. Apply zoom corresponding to this angle to hide corners
            zoom_w = int(orig_w / zoom_factor)
            zoom_h = int(orig_h / zoom_factor)
            zoom_w = zoom_w if zoom_w % 2 == 0 else zoom_w - 1
            zoom_h = zoom_h if zoom_h % 2 == 0 else zoom_h - 1
            filter_parts.append(f"crop={zoom_w}:{zoom_h}:(iw-{zoom_w})/2:(ih-{zoom_h})/2")

            # 3. Scale to VERTICAL 1080x1920 (Instagram Reels format)
            filter_parts.append("scale=1080:1920:force_original_aspect_ratio=decrease")
            filter_parts.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")

            # 4. Mirror if needed
            if mirror:
                filter_parts.append("hflip")

            # 5. Add random visual filters
            random_filters = self.get_random_filters()
            filter_parts.extend(random_filters)

            video_filter = ",".join(filter_parts)

            # Check if we should add music from config
            add_music = self.config.get('add_music', True)

            # Step 1: Process video without audio
            temp_video = output_video.replace('.mp4', '_temp.mp4') if add_music else output_video
            cmd1 = [
                "ffmpeg",
                "-hide_banner", "-loglevel", "error",
                "-i", input_video,
                "-filter:v", video_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
            ]

            if add_music:
                cmd1.append("-an")

            cmd1.extend(["-y", temp_video])

            subprocess.run(cmd1, check=True)

            # Step 2: Add audio from music video (if add_music is True)
            if add_music and music_video:
                cmd2 = [
                    "ffmpeg",
                    "-hide_banner", "-loglevel", "error",
                    "-i", temp_video,
                    "-i", music_video,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    "-map_metadata", "-1",
                    "-movflags", "+faststart",
                    "-y",
                    output_video
                ]

                subprocess.run(cmd2, check=True)
                if os.path.exists(temp_video):
                    os.remove(temp_video)

            mirror_str = "🔀" if mirror else "  "
            self.log(f"✓ {os.path.basename(output_video)} | Angle: {angle_degrees:+3d}° | Zoom: {zoom_factor:.4f}x | Mirror: {mirror_str}")
            return True
        except Exception as e:
            self.log(f"✗ {os.path.basename(output_video)} | Error: {str(e)}")
            if 'temp_video' in locals() and os.path.exists(temp_video):
                os.remove(temp_video)
            return False

    def start_telegram_bot(self):
        self.log("Telegram бот запускается автоматически...")

    # === HELPER METHODS FOR SETTINGS ===

    def create_text_input(self, parent, label, config_key, password=False):
        """Создать текстовое поле ввода"""
        from PyQt6.QtWidgets import QLineEdit

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        label_widget = QLabel(label)
        label_widget.setProperty("class", "label-secondary")
        label_widget.setStyleSheet("font-size: 13px; font-weight: bold; color: #a0a8b8;")
        layout.addWidget(label_widget)

        entry = QLineEdit()
        entry.setText(self.config.get(config_key, ''))
        entry.setPlaceholderText(f"Введите {label.lower()}...")
        if password:
            entry.setEchoMode(QLineEdit.EchoMode.Password)
        entry.textChanged.connect(self.auto_save_settings)
        layout.addWidget(entry)

        parent.addWidget(frame)
        setattr(self, f"{config_key}_entry", entry)

    def create_folder_input(self, parent, label, config_key):
        """Создать поле выбора папки"""
        from PyQt6.QtWidgets import QLineEdit, QFileDialog

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        label_widget = QLabel(label)
        label_widget.setProperty("class", "label-secondary")
        label_widget.setStyleSheet("font-size: 13px; font-weight: bold; color: #a0a8b8;")
        layout.addWidget(label_widget)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        entry = QLineEdit()
        entry.setText(self.config.get(config_key, ''))
        entry.setPlaceholderText("Выберите папку...")
        entry.textChanged.connect(self.auto_save_settings)
        input_layout.addWidget(entry)

        browse_btn = SimpleButton("📁 Обзор")
        browse_btn.setMinimumWidth(90)
        browse_btn.setMaximumHeight(38)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3142;
                border: 2px solid #353c52;
                border-radius: 8px;
                font-size: 12px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #353c52;
                border-color: #00ccff;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(config_key))
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        parent.addWidget(frame)
        setattr(self, f"{config_key}_entry", entry)

    def create_angle_zoom_input(self, parent, angle):
        """Создать поле для угол-зум маппинга"""
        from PyQt6.QtWidgets import QLineEdit

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"Угол {int(angle):+d}° Zoom")
        label.setProperty("class", "label-secondary")
        label.setMinimumWidth(150)
        layout.addWidget(label)

        entry = QLineEdit()
        entry.setText(str(self.config.get('angle_zoom_map', {}).get(str(angle), 1.0)))
        entry.setMaximumWidth(100)
        entry.textChanged.connect(self.auto_save_settings)
        layout.addWidget(entry)
        layout.addStretch()

        parent.addWidget(frame)
        self.angle_entries[str(angle)] = entry

    def create_slider_input(self, parent, label, config_key, min_val, max_val, step=0.1):
        """Создать слайдер"""
        from PyQt6.QtWidgets import QSlider

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(10)

        # Header with label and value
        header_layout = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setProperty("class", "label-secondary")
        label_widget.setStyleSheet("font-size: 13px; font-weight: bold; color: #a0a8b8;")
        header_layout.addWidget(label_widget)

        # Получить значение из конфига
        if config_key in ['video_crf', 'copies_per_video']:
            value = self.config.get(config_key, (min_val + max_val) / 2)
        else:
            value = self.config.get('effects_settings', {}).get(config_key, (min_val + max_val) / 2)

        value_label = QLabel(f"{value:.2f}" if step < 1 else f"{int(value)}")
        value_label.setMinimumWidth(60)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #00ffff;
            background-color: #1a1f2e;
            border: 1px solid #2a3142;
            border-radius: 6px;
            padding: 4px 10px;
        """)
        header_layout.addWidget(value_label)
        layout.addLayout(header_layout)

        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        # Для целых чисел (step >= 1) используем прямые значения
        if step >= 1:
            slider.setMinimum(int(min_val))
            slider.setMaximum(int(max_val))
            slider.setValue(int(value))
            slider.setSingleStep(int(step))
        else:
            # Для дробных значений (step < 1) используем деление
            slider.setMinimum(int(min_val / step))
            slider.setMaximum(int(max_val / step))
            slider.setValue(int(value / step))
        slider.valueChanged.connect(self.auto_save_settings)
        layout.addWidget(slider)

        # Min/Max labels
        minmax_layout = QHBoxLayout()
        min_label = QLabel(str(min_val))
        min_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        minmax_layout.addWidget(min_label)
        minmax_layout.addStretch()
        max_label = QLabel(str(max_val))
        max_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        minmax_layout.addWidget(max_label)
        layout.addLayout(minmax_layout)

        def update_label(val):
            if step < 1:
                value_label.setText(f"{val * step:.2f}")
            else:
                # Для целых значений не умножаем на step
                value_label.setText(f"{int(val)}")

        slider.valueChanged.connect(update_label)

        parent.addWidget(frame)
        setattr(self, f"{config_key}_slider", slider)
        self.sliders.append(slider)

    def create_dropdown_input(self, parent, label, config_key, options):
        """Создать выпадающий список"""
        from PyQt6.QtWidgets import QComboBox

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        label_widget = QLabel(label)
        label_widget.setProperty("class", "label-secondary")
        label_widget.setStyleSheet("font-size: 13px; font-weight: bold; color: #a0a8b8;")
        layout.addWidget(label_widget)

        dropdown = QComboBox()
        dropdown.addItems(options)

        current_value = self.config.get('video_settings', {}).get(config_key, options[0])
        index = options.index(current_value) if current_value in options else 0
        dropdown.setCurrentIndex(index)

        dropdown.currentIndexChanged.connect(self.auto_save_settings)
        layout.addWidget(dropdown)

        parent.addWidget(frame)
        setattr(self, f"{config_key}_dropdown", dropdown)

    def create_range_slider_input(self, parent, label, min_key, max_key):
        """Создать два поля для минимума и максимума"""
        from PyQt6.QtWidgets import QLineEdit

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        label_widget = QLabel(label)
        label_widget.setProperty("class", "label-secondary")
        layout.addWidget(label_widget)

        min_layout = QHBoxLayout()
        min_label = QLabel("Min")
        min_label.setMinimumWidth(40)
        min_layout.addWidget(min_label)

        min_entry = QLineEdit()
        min_entry.setText(str(self.config.get('effects_settings', {}).get(min_key, 0.8)))
        min_entry.setMaximumWidth(100)
        min_entry.textChanged.connect(self.auto_save_settings)
        min_layout.addWidget(min_entry)
        min_layout.addStretch()
        layout.addLayout(min_layout)

        max_layout = QHBoxLayout()
        max_label = QLabel("Max")
        max_label.setMinimumWidth(40)
        max_layout.addWidget(max_label)

        max_entry = QLineEdit()
        max_entry.setText(str(self.config.get('effects_settings', {}).get(max_key, 1.2)))
        max_entry.setMaximumWidth(100)
        max_entry.textChanged.connect(self.auto_save_settings)
        max_layout.addWidget(max_entry)
        max_layout.addStretch()
        layout.addLayout(max_layout)

        parent.addWidget(frame)
        setattr(self, f"{min_key}_entry", min_entry)
        setattr(self, f"{max_key}_entry", max_entry)

    def create_checkbox_input(self, parent, label, config_key, description=""):
        """Создать чекбокс с описанием"""
        from PyQt6.QtWidgets import QCheckBox

        frame = QFrame()
        frame.setProperty("class", "settings-input-frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Main checkbox row
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(12)

        checkbox = QCheckBox()
        checkbox.setChecked(self.config.get(config_key, True))
        checkbox.setStyleSheet("""
            QCheckBox {
                background: transparent;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border: 2px solid #2a3142;
                border-radius: 6px;
                background-color: #1a1f2e;
            }
            QCheckBox::indicator:hover {
                background-color: #252b3d;
                border-color: #353c52;
            }
            QCheckBox::indicator:checked {
                background-color: #00ccff;
                border: 2px solid #00ccff;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #33ffff;
                border: 2px solid #00ddff;
            }
        """)

        # Add checkmark using QPainter
        from PyQt6.QtGui import QPainter, QPen, QColor
        from PyQt6.QtCore import QPoint

        original_paint = checkbox.paintEvent

        def paint_with_checkmark(event):
            original_paint(event)
            if checkbox.isChecked():
                painter = QPainter(checkbox)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                pen = QPen(QColor(255, 255, 255), 2.2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

                # Draw checkmark (centered in the box)
                # Short line (left part of checkmark)
                painter.drawLine(QPoint(7, 11), QPoint(10, 14))
                # Long line (right part of checkmark)
                painter.drawLine(QPoint(10, 14), QPoint(17, 7))
                painter.end()

        checkbox.paintEvent = paint_with_checkmark
        checkbox.stateChanged.connect(self.auto_save_settings)
        checkbox_layout.addWidget(checkbox)

        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #e8eaf0;
            background: transparent;
        """)
        checkbox_layout.addWidget(label_widget)
        checkbox_layout.addStretch()

        layout.addLayout(checkbox_layout)

        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                font-size: 11px;
                color: #6b7280;
                background: transparent;
                padding-left: 36px;
            """)
            layout.addWidget(desc_label)

        parent.addWidget(frame)
        setattr(self, f"{config_key}_switch", checkbox)

    def browse_folder(self, config_key):
        """Открыть диалог выбора папки"""
        from PyQt6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            entry = getattr(self, f"{config_key}_entry")
            entry.setText(folder)
            self.auto_save_settings()

    def auto_save_settings(self):
        """Автосохранение настроек"""
        try:
            # Folders
            if hasattr(self, 'input_folder_entry'):
                self.config['input_folder'] = self.input_folder_entry.text()
            if hasattr(self, 'output_folder_entry'):
                self.config['output_folder'] = self.output_folder_entry.text()
            if hasattr(self, 'music_folder_entry'):
                self.config['music_folder'] = self.music_folder_entry.text()

            # Instagram
            if hasattr(self, 'instagram_username_entry'):
                self.config['instagram_username'] = self.instagram_username_entry.text()
            if hasattr(self, 'instagram_password_entry'):
                self.config['instagram_password'] = self.instagram_password_entry.text()

            # Telegram
            if hasattr(self, 'telegram_token_entry'):
                self.config['telegram_token'] = self.telegram_token_entry.text()

            # Music switch
            if hasattr(self, 'add_music_switch'):
                self.config['add_music'] = self.add_music_switch.isChecked()

            # Copies (целое число)
            if hasattr(self, 'copies_per_video_slider'):
                self.config['copies_per_video'] = int(self.copies_per_video_slider.value())

            # Angles
            if hasattr(self, 'angle_entries'):
                for angle, entry in self.angle_entries.items():
                    try:
                        self.config['angle_zoom_map'][str(angle)] = float(entry.text())
                    except:
                        pass

            # Video settings
            if hasattr(self, 'output_resolution_dropdown'):
                self.config['video_settings']['output_resolution'] = self.output_resolution_dropdown.currentText()
            if hasattr(self, 'video_codec_dropdown'):
                self.config['video_settings']['video_codec'] = self.video_codec_dropdown.currentText()
            if hasattr(self, 'video_preset_dropdown'):
                self.config['video_settings']['video_preset'] = self.video_preset_dropdown.currentText()
            if hasattr(self, 'video_crf_slider'):
                self.config['video_settings']['video_crf'] = self.video_crf_slider.value()
            if hasattr(self, 'audio_codec_dropdown'):
                self.config['video_settings']['audio_codec'] = self.audio_codec_dropdown.currentText()
            if hasattr(self, 'audio_bitrate_dropdown'):
                self.config['video_settings']['audio_bitrate'] = self.audio_bitrate_dropdown.currentText()
            if hasattr(self, 'pixel_format_dropdown'):
                self.config['video_settings']['pixel_format'] = self.pixel_format_dropdown.currentText()

            # Effects settings
            effects_sliders = [
                'mirror_probability', 'color_balance_probability',
                'brightness_contrast_probability', 'saturation_probability',
                'color_balance_range', 'brightness_range'
            ]
            for key in effects_sliders:
                slider_attr = f"{key}_slider"
                if hasattr(self, slider_attr):
                    slider = getattr(self, slider_attr)
                    step = 0.01 if 'range' in key else 0.1
                    self.config['effects_settings'][key] = slider.value() * step

            # Range entries
            range_keys = [('contrast_min', 'contrast_max'), ('saturation_min', 'saturation_max')]
            for min_key, max_key in range_keys:
                if hasattr(self, f"{min_key}_entry"):
                    try:
                        self.config['effects_settings'][min_key] = float(getattr(self, f"{min_key}_entry").text())
                    except:
                        pass
                if hasattr(self, f"{max_key}_entry"):
                    try:
                        self.config['effects_settings'][max_key] = float(getattr(self, f"{max_key}_entry").text())
                    except:
                        pass

            self.save_config()
        except Exception as e:
            print(f"Ошибка автосохранения: {e}")

    def update_stats(self):
        if hasattr(self, 'dashboard_stats'):
            # Подсчет видео
            input_count = 0
            music_count = 0
            output_count = 0

            if os.path.exists(self.config.get('input_folder', '')):
                try:
                    input_count = len([f for f in os.listdir(self.config['input_folder'])
                                      if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))])
                except:
                    input_count = 0

            if os.path.exists(self.config.get('music_folder', '')):
                try:
                    music_count = len([f for f in os.listdir(self.config['music_folder'])
                                      if f.endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'))])
                except:
                    music_count = 0

            # "Будет создано" = количество входных видео × количество копий
            copies_per_video = self.config.get('copies_per_video', 1)
            will_be_created = input_count * copies_per_video

            self.dashboard_stats['input'].setText(str(input_count))
            self.dashboard_stats['music'].setText(str(music_count))
            self.dashboard_stats['output'].setText(str(will_be_created))

        # Обновляем текущее обрабатываемое видео (аналог gui.py)
        if hasattr(self, 'current_video_label') and hasattr(self, 'current_video'):
            if self.current_video:
                self.current_video_label.setText(f"Обрабатывается: {self.current_video}")
            elif not self.is_running:
                self.current_video_label.setText("")

        # Обновляем кнопки и статус если обработка завершена (аналог gui.py)
        if hasattr(self, 'start_btn') and hasattr(self, 'stop_btn') and hasattr(self, 'status_label'):
            if not self.is_running and self.start_btn and not self.start_btn.isEnabled():
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.status_label.setText("● ГОТОВА")
                self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ccff;")

    # ============================================================
    # TELEGRAM BOT METHODS
    # ============================================================

    def start_telegram_bot(self):
        """Запуск Telegram бота"""
        if not self.config.get('telegram_token'):
            self.log("⚠️ Telegram токен не указан. Бот не запущен.")
            return

        if self.bot_thread and self.bot_thread.is_alive():
            self.log("📱 Telegram бот уже запущен!")
            return

        try:
            self.bot = telebot.TeleBot(self.config['telegram_token'])
            self.setup_bot_handlers()

            # Запуск бота в отдельном потоке
            self.bot_thread = threading.Thread(target=self.run_telegram_bot, daemon=True)
            self.bot_thread.start()

            # Обновляем UI
            QTimer.singleShot(0, lambda: self.update_bot_status(True))
            self.log("📱 Telegram бот запущен!")

        except Exception as e:
            self.log(f"❌ Ошибка запуска бота: {str(e)}")
            QTimer.singleShot(0, lambda: self.update_bot_status(False))

    def update_bot_status(self, running):
        """Обновление статуса бота в UI"""
        if running:
            self.bot_status_label.setText("● РАБОТАЕТ")
            self.bot_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #00ff00; margin-top: 10px;")
        else:
            self.bot_status_label.setText("● НЕ ЗАПУЩЕН")
            self.bot_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff4444; margin-top: 10px;")

    def run_telegram_bot(self):
        """Запуск polling бота"""
        try:
            self.bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            QTimer.singleShot(0, lambda: self.log(f"❌ Ошибка бота: {str(e)}"))
            QTimer.singleShot(0, lambda: self.update_bot_status(False))

    def setup_bot_handlers(self):
        """Настройка обработчиков команд бота (логика из gui.py с красивым оформлением)"""

        @self.bot.message_handler(commands=['start'])
        def start(message):
            welcome_msg = (
                "🎬 <b>VIDEO UNIQUIFIER BOT</b>\n\n"
                "✨ Добро пожаловать!\n\n"
                "📤 <b>Отправьте мне:</b>\n"
                "• Видео файл\n"
                "• Instagram URL\n"
                "• @username Instagram\n\n"
                "⚙️ <b>Текущие настройки:</b>\n"
                f"• Музыка: {'✅ Да' if self.config.get('add_music') else '❌ Нет'}\n"
                f"• Разрешение: {self.config.get('output_resolution', '1080x1920')}\n\n"
                "🎯 После загрузки выберите количество копий!"
            )
            self.bot.send_message(message.chat.id, welcome_msg, parse_mode='HTML')

        @self.bot.message_handler(content_types=['video'])
        def handle_video(message):
            chat_id = message.chat.id
            self.bot.send_message(chat_id, "⏬ <b>Загружаю видео...</b>", parse_mode='HTML')

            temp_folder = f"temp_input_{chat_id}"
            os.makedirs(temp_folder, exist_ok=True)
            file_info = self.bot.get_file(message.video.file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)
            input_path = os.path.join(temp_folder, "input.mp4")

            with open(input_path, 'wb') as f:
                f.write(downloaded_file)

            self.user_states[chat_id] = {'input_folder': temp_folder, 'waiting_for_copies': False}

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("1️⃣", callback_data="copies_1"),
                InlineKeyboardButton("3️⃣", callback_data="copies_3"),
                InlineKeyboardButton("5️⃣", callback_data="copies_5"),
                InlineKeyboardButton("🔟", callback_data="copies_10")
            )
            markup.row(
                InlineKeyboardButton("✏️ Свой вариант (1-100)", callback_data="copies_custom")
            )
            self.bot.send_message(chat_id, "📊 <b>Сколько копий создать?</b>", reply_markup=markup, parse_mode='HTML')

        @self.bot.message_handler(func=lambda m: True)
        def handle_text(message):
            chat_id = message.chat.id
            text = message.text.strip()

            # Проверяем, ждем ли мы ввод количества копий
            if chat_id in self.user_states and self.user_states[chat_id].get('waiting_for_copies'):
                try:
                    copies = int(text)
                    if 1 <= copies <= 100:
                        state = self.user_states[chat_id]
                        input_folder = state['input_folder']
                        input_videos = self.get_video_files(input_folder)

                        if input_videos:
                            self.bot.send_message(chat_id, f"⚙️ <b>Обработка {len(input_videos)} видео с {copies} копиями...</b>", parse_mode='HTML')
                            self.process_and_send_videos_for_bot(chat_id, input_videos, copies)
                        else:
                            self.bot.send_message(chat_id, "❌ <b>Нет видео для обработки</b>", parse_mode='HTML')

                        if os.path.exists(input_folder):
                            shutil.rmtree(input_folder)
                        del self.user_states[chat_id]
                    else:
                        self.bot.send_message(chat_id, "❌ <b>Число должно быть от 1 до 100</b>\n\nПопробуйте ещё раз:", parse_mode='HTML')
                except ValueError:
                    self.bot.send_message(chat_id, "❌ <b>Введите корректное число от 1 до 100</b>", parse_mode='HTML')
                return

            if 'instagram.com' in text or text.startswith('@'):
                self.bot.send_message(chat_id, "📥 <b>Загрузка с Instagram...</b>", parse_mode='HTML')
                temp_folder = f"temp_input_{chat_id}"
                os.makedirs(temp_folder, exist_ok=True)

                downloaded_count, error = self.download_single_instagram(text, temp_folder)

                if error:
                    self.bot.send_message(chat_id, f"❌ <b>Ошибка:</b> {error}", parse_mode='HTML')
                    if os.path.exists(temp_folder):
                        shutil.rmtree(temp_folder)
                    return

                if downloaded_count == 0:
                    self.bot.send_message(chat_id, "❌ <b>Нет видео для загрузки</b>", parse_mode='HTML')
                    if os.path.exists(temp_folder):
                        shutil.rmtree(temp_folder)
                    return

                self.user_states[chat_id] = {'input_folder': temp_folder, 'waiting_for_copies': False}

                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("1️⃣", callback_data="copies_1"),
                    InlineKeyboardButton("3️⃣", callback_data="copies_3"),
                    InlineKeyboardButton("5️⃣", callback_data="copies_5"),
                    InlineKeyboardButton("🔟", callback_data="copies_10")
                )
                markup.row(
                    InlineKeyboardButton("✏️ Свой вариант (1-100)", callback_data="copies_custom")
                )
                self.bot.send_message(chat_id, f"✅ <b>Загружено {downloaded_count} видео!</b>\n\n📊 Сколько копий для каждого видео?", reply_markup=markup, parse_mode='HTML')
            else:
                self.bot.send_message(chat_id, "❓ <b>Неизвестный формат</b>\n\nОтправьте видео, Instagram URL или @username", parse_mode='HTML')

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            chat_id = call.message.chat.id

            if chat_id in self.user_states:
                data = call.data
                if data == 'copies_custom':
                    # Запрашиваем ввод числа
                    self.user_states[chat_id]['waiting_for_copies'] = True
                    self.bot.send_message(chat_id, "✏️ <b>Введите количество копий (от 1 до 100):</b>", parse_mode='HTML')
                elif data.startswith('copies_'):
                    copies = int(data.split('_')[1])
                    state = self.user_states[chat_id]
                    input_folder = state['input_folder']
                    input_videos = self.get_video_files(input_folder)

                    if input_videos:
                        self.bot.send_message(chat_id, f"⚙️ <b>Обработка {len(input_videos)} видео с {copies} копиями...</b>", parse_mode='HTML')
                        self.process_and_send_videos_for_bot(chat_id, input_videos, copies)
                    else:
                        self.bot.send_message(chat_id, "❌ <b>Нет видео для обработки</b>", parse_mode='HTML')

                    if os.path.exists(input_folder):
                        shutil.rmtree(input_folder)
                    del self.user_states[chat_id]

    def process_and_send_videos_for_bot(self, chat_id, input_videos, copies):
        """Обработка и отправка видео в Telegram (из gui.py)"""
        try:
            music_videos = self.get_audio_files(self.config['music_folder']) if self.config['add_music'] else []
            output_folder = f"temp_output_{chat_id}"
            os.makedirs(output_folder, exist_ok=True)

            total_videos = len(input_videos) * copies
            sent_count = 0

            for input_video in input_videos:
                for j in range(1, copies + 1):
                    music_video = random.choice(music_videos) if self.config['add_music'] and music_videos else None
                    output_filename = f"unique_{j}.mp4"
                    output_path = os.path.join(output_folder, output_filename)

                    if self.uniquify_video(input_video, music_video, output_path):
                        with open(output_path, 'rb') as video_file:
                            sent_count += 1
                            # Отправляем с поддержкой стриминга и увеличенным таймаутом
                            self.bot.send_video(
                                chat_id,
                                video_file,
                                caption=f"📹 <b>Видео {sent_count}/{total_videos}</b>",
                                parse_mode='HTML',
                                supports_streaming=True,
                                timeout=120
                            )
                        os.remove(output_path)
                        QTimer.singleShot(0, lambda c=sent_count, t=total_videos: self.log(f"📱 Бот: отправлено {c}/{t}"))
                    else:
                        self.bot.send_message(chat_id, f"⚠️ Ошибка обработки копии {j}")

            self.bot.send_message(chat_id, f"🎉 <b>Готово!</b>\n\n✅ Отправлено {sent_count} видео из {total_videos}", parse_mode='HTML')

            # Очистка
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)

        except Exception as e:
            self.bot.send_message(chat_id, f"❌ <b>Ошибка:</b> {str(e)}", parse_mode='HTML')
            QTimer.singleShot(0, lambda: self.log(f"❌ Ошибка бота: {str(e)}"))



def main():
    app = QApplication(sys.argv)
    window = VideoUniquifierApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()