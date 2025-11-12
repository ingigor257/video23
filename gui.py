# video_uniquifier_gui.py - Premium Neomorphic Cyberpunk Video Uniquifier
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import queue
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess
import random
import shutil
import math
import instaloader
import re
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# === CYBERPUNK NEOMORPHIC COLOR PALETTE ===
COLORS = {
    'bg_deep': '#0a0e1a',
    'bg_primary': '#0a0e1a',
    'bg_secondary': '#0a0e1a',
    'bg_card': '#1e2433',
    'bg_elevated': '#252b3d',
    'sidebar': '#151a27',
    'glass': 'rgba(30, 36, 51, 0.7)',
    'neon_purple': '#b026ff',
    'neon_blue': '#00d4ff',
    'neon_pink': '#ff1b8d',
    'neon_cyan': '#00ffff',
    'glow_purple': '#8b00ff',
    'glow_blue': '#0099ff',
    'glow_pink': '#ff0066',
    'success': '#00cc66',
    'warning': '#ffaa00',
    'danger': '#ff0055',
    'info': '#00ccff',
    'text_primary': '#e8eaf0',
    'text_secondary': '#8b92a8',
    'text_muted': '#5a6275',
    'border': '#2a3142',
    'shadow': '#000000',
}

DEFAULT_CONFIG = {
    'input_folder': 'input',
    'output_folder': 'output',
    'music_folder': 'music',
    'instagram_username': '',
    'instagram_password': '',
    'telegram_token': '',  # New: Telegram bot token
    'add_music': True,  # New: Option to enable/disable music overlay
    'copies_per_video': 5,  # New default: 5 copies per input video
    'angle_zoom_map': {
        '-3': 1.085,
        '-2': 1.05,
        '-1': 1.025,
        '1': 1.025,
        '2': 1.05,
        '3': 1.085
    },
    'video_settings': {
        'output_resolution': '1080x1920',  # Instagram Reels vertical
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

class ConsoleRedirector:
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue
        
    def write(self, message):
        self.queue.put(message)
        
    def flush(self):
        pass

class NeomorphicButton(ctk.CTkButton):
    """Кнопка с легкой анимацией при наведении"""
    def __init__(self, master, **kwargs):
        defaults = {
            'corner_radius': 12,
            'border_width': 1,
            'border_color': COLORS['border'],
            'fg_color': COLORS['bg_elevated'],
            'hover_color': COLORS['bg_card'],
            'text_color': COLORS['text_primary'],
            'font': ctk.CTkFont(family="Inter", size=13, weight="bold"),
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)

class GlassCard(ctk.CTkFrame):
    """Стеклянная карточка"""
    def __init__(self, master, **kwargs):
        defaults = {
            'corner_radius': 16,
            'fg_color': COLORS['bg_card'],
            'border_width': 1,
            'border_color': COLORS['border']
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)

class VideoUniquifierDashboard:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("◈ VIDEO UNIQUIFIER PRO ◈")
        self.root.geometry("1700x950")
        self.root.configure(fg_color=COLORS['bg_deep'])
        
        self.config_file = Path("video_uniquifier_config.json")
        self.config = self.load_config()
        
        self.log_queue = queue.Queue()
        
        self.is_running = False
        self.is_downloading = False
        self.stop_requested = False
        self.processing_thread = None
        self.download_thread = None
        self.bot = None  # Telegram bot instance
        self.bot_thread = None  # Thread for bot polling
        self.user_states = {}  # For Telegram bot states
        
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.current_video = ""
        
        self.current_section = "dashboard"
        
        self.setup_ui()
        self.show_section("dashboard")
        self.update_stats()
        self.process_log_queue()
        
        sys.stdout = ConsoleRedirector(self.console_text, self.log_queue)
        sys.stderr = ConsoleRedirector(self.console_text, self.log_queue)

        # Auto-start Telegram bot if token exists
        if self.config.get('telegram_token'):
            self.start_telegram_bot()
    
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
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.create_sidebar(main_container)
        
        self.content_area = ctk.CTkFrame(main_container, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True, padx=(20, 0))
        
        self.create_dashboard_section()
        self.create_settings_section()
        self.create_console_section()
    
    def create_sidebar(self, parent):
        sidebar = GlassCard(parent, fg_color=COLORS['sidebar'], width=280)
        sidebar.pack(side="left", fill="y", padx=(0, 0))
        sidebar.pack_propagate(False)
        
        header_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=100)
        header_frame.pack(fill="x", padx=20, pady=(30, 20))
        header_frame.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="◈ VIDEO\nUNIQUIFIER",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
            text_color=COLORS['neon_cyan'],
            justify="center"
        )
        title_label.pack(expand=True)
        
        status_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=80)
        status_frame.pack(fill="x", padx=20, pady=(0, 30))
        
        status_inner = GlassCard(status_frame, fg_color=COLORS['bg_elevated'])
        status_inner.pack(fill="both", expand=True)
        
        indicator_frame = ctk.CTkFrame(status_inner, fg_color="transparent")
        indicator_frame.pack(expand=True, pady=15)
        
        self.status_indicator = ctk.CTkFrame(
            indicator_frame,
            width=12,
            height=12,
            corner_radius=6,
            fg_color=COLORS['info']
        )
        self.status_indicator.pack(side="left", padx=(0, 10))
        
        self.status_label = ctk.CTkLabel(
            indicator_frame,
            text="● ГОТОВА",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLORS['info']
        )
        self.status_label.pack(side="left")
        
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=(0, 30))
        
        self.nav_buttons = {}
        nav_items = [
            ("📊 Dashboard", "dashboard"),
            ("⚙️ Настройки", "settings"),
            ("📝 Консоль", "console"),
        ]
        
        for text, section in nav_items:
            btn = NeomorphicButton(
                nav_frame,
                text=text,
                height=50,
                command=lambda s=section: self.show_section(s)
            )
            btn.pack(fill="x", pady=5)
            self.nav_buttons[section] = btn
        
        stats_card = GlassCard(sidebar, fg_color=COLORS['bg_elevated'])
        stats_card.pack(fill="x", padx=20, pady=(0, 20))
        
        stats_label = ctk.CTkLabel(
            stats_card,
            text="◈ СТАТИСТИКА",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=COLORS['text_secondary']
        )
        stats_label.pack(pady=(15, 10))
        
        self.stat_widgets = {}
        stats_data = [
            ("Обработано", "processed", COLORS['success']),
            ("Ошибок", "failed", COLORS['danger']),
            ("Всего", "total", COLORS['info']),
        ]
        
        for label, key, color in stats_data:
            stat_frame = ctk.CTkFrame(stats_card, fg_color="transparent")
            stat_frame.pack(fill="x", padx=20, pady=5)
            
            stat_label = ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS['text_muted']
            )
            stat_label.pack(side="left")
            
            stat_value = ctk.CTkLabel(
                stat_frame,
                text="0",
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color=color
            )
            stat_value.pack(side="right")
            
            self.stat_widgets[key] = stat_value
        
        ctk.CTkLabel(stats_card, text="", height=15).pack()
    
    def create_dashboard_section(self):
        self.dashboard_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        
        header = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent", height=80)
        header.pack(fill="x", pady=(0, 20))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="◈ ПАНЕЛЬ УПРАВЛЕНИЯ",
            font=ctk.CTkFont(family="Inter", size=32, weight="bold"),
            text_color=COLORS['text_primary']
        )
        title.pack(side="left", pady=20)
        
        self.dashboard_status = ctk.CTkLabel(
            header,
            text="ГОТОВА",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['info']
        )
        self.dashboard_status.pack(side="right", pady=20, padx=20)
        
        stats_container = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 20))
        
        stat_cards_data = [
            ("Входных видео", "0", COLORS['neon_cyan'], "input_count"),
            ("Музыкальных треков", "0", COLORS['neon_purple'], "music_count"),
            ("Будет создано", "0", COLORS['info'], "output_count"),
        ]
        
        for i, (label, value, color, key) in enumerate(stat_cards_data):
            card = GlassCard(stats_container)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 10, 0))
            
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(family="Inter", size=13),
                text_color=COLORS['text_secondary']
            ).pack(pady=(20, 5))
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(family="Inter", size=40, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(0, 20))
            
            setattr(self, f"dashboard_{key}", value_label)
        
        # Вторая строка статистики
        stats_container2 = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_container2.pack(fill="x", pady=(0, 20))
        
        stat_cards_data2 = [
            ("Создано видео", "0", COLORS['success'], "created_count"),
            ("Ошибок", "0", COLORS['danger'], "errors_count"),
        ]
        
        for i, (label, value, color, key) in enumerate(stat_cards_data2):
            card = GlassCard(stats_container2)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 10, 0))
            
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(family="Inter", size=13),
                text_color=COLORS['text_secondary']
            ).pack(pady=(20, 5))
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(family="Inter", size=40, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(0, 20))
            
            setattr(self, f"dashboard_{key}", value_label)
        
        # New: Instagram Download Section
        download_card = GlassCard(self.dashboard_frame)
        download_card.pack(fill="both", expand=True, pady=(20, 20))  # Increased bottom pady for spacing
        
        ctk.CTkLabel(
            download_card,
            text="◈ ЗАГРУЗКА REELS ИЗ INSTAGRAM",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10))
        
        info_label = ctk.CTkLabel(
            download_card,
            text="Вставьте URL Reels или @username (по одному на строку). Требуется instaloader.",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLORS['text_muted']
        )
        info_label.pack(pady=(0, 10))
        
        self.reels_text = ctk.CTkTextbox(
            download_card,
            height=150,
            fg_color=COLORS['bg_elevated'],
            text_color=COLORS['text_primary'],
            font=ctk.CTkFont(family="Inter", size=12)
        )
        self.reels_text.pack(fill="x", padx=20, pady=10)
        
        button_frame = ctk.CTkFrame(download_card, fg_color="transparent")
        button_frame.pack(pady=10)
        
        self.download_btn = NeomorphicButton(
            button_frame,
            text="⬇️ ЗАГРУЗИТЬ",
            width=200,
            height=50,
            fg_color='#00994d',
            hover_color=COLORS['glow_blue'],
            command=lambda: self.start_download(auto_process=False)
        )
        self.download_btn.pack(side="left", padx=10)
        
        self.download_and_process_btn = NeomorphicButton(
            button_frame,
            text="⬇️ ЗАГРУЗИТЬ И ОБРАБОТАТЬ",
            width=300,
            height=50,
            fg_color='#00994d',
            hover_color=COLORS['glow_purple'],
            command=lambda: self.start_download(auto_process=True)
        )
        self.download_and_process_btn.pack(side="left", padx=10)
        
        control_card = GlassCard(self.dashboard_frame)
        control_card.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            control_card,
            text="◈ УПРАВЛЕНИЕ ОБРАБОТКОЙ",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(30, 20))
        
        button_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        button_frame.pack(pady=(0, 30))
        
        self.start_btn = NeomorphicButton(
            button_frame,
            text="▶ ЗАПУСТИТЬ ОБРАБОТКУ",
            width=300,
            height=60,
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            fg_color='#00994d',
            hover_color=COLORS['glow_purple'],
            text_color=COLORS['text_primary'],
            command=self.start_processing
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = NeomorphicButton(
            button_frame,
            text="⏹ ОСТАНОВИТЬ",
            width=200,
            height=60,
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            fg_color='#cc0033',
            hover_color=COLORS['glow_pink'],
            text_color=COLORS['text_primary'],
            command=self.stop_processing,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)
        
        self.current_video_label = ctk.CTkLabel(
            control_card,
            text="",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        )
        self.current_video_label.pack(pady=(10, 30))
    
    def create_settings_section(self):
        self.settings_frame = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        header = ctk.CTkLabel(
            self.settings_frame,
            text="◈ НАСТРОЙКИ УНИКАЛИЗАЦИИ",
            font=ctk.CTkFont(family="Inter", size=32, weight="bold"),
            text_color=COLORS['text_primary']
        )
        header.pack(pady=(0, 30))
        
        folders_card = GlassCard(self.settings_frame)
        folders_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            folders_card,
            text="◈ ПАПКИ",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_cyan']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        self.create_folder_input(folders_card, "Входная папка (input)", "input_folder")
        self.create_folder_input(folders_card, "Выходная папка (output)", "output_folder")
        self.create_folder_input(folders_card, "Папка с музыкой (music)", "music_folder")
        
        ctk.CTkLabel(folders_card, text="", height=10).pack()
        
        # New: Instagram Credentials
        instagram_card = GlassCard(self.settings_frame)
        instagram_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            instagram_card,
            text="◈ УЧЕТНЫЕ ДАННЫЕ INSTAGRAM",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_pink']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        self.create_text_input(instagram_card, "Имя пользователя Instagram", "instagram_username")
        self.create_text_input(instagram_card, "Пароль Instagram", "instagram_password", show="*")
        
        info_label = ctk.CTkLabel(
            instagram_card,
            text="Для скачивания приватного контента. Оставьте пустым для публичного.",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=COLORS['text_muted']
        )
        info_label.pack(padx=30, pady=(0, 10), anchor="w")
        
        ctk.CTkLabel(instagram_card, text="", height=10).pack()
        
        # New: Telegram Bot Section
        telegram_card = GlassCard(self.settings_frame)
        telegram_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            telegram_card,
            text="◈ TELEGRAM BOT",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_blue']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        self.create_text_input(telegram_card, "Telegram Bot Token", "telegram_token")

        button_frame = ctk.CTkFrame(telegram_card, fg_color="transparent")
        button_frame.pack(pady=10, padx=30)

        self.start_bot_btn = NeomorphicButton(
            button_frame,
            text="Запустить бота",
            width=200,
            command=self.start_telegram_bot
        )
        self.start_bot_btn.pack(side="left")

        info_label = ctk.CTkLabel(
            telegram_card,
            text="Telegram бот запускается автоматически при запуске приложения",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=COLORS['text_muted']
        )
        info_label.pack(padx=30, pady=(0, 10), anchor="w")

        ctk.CTkLabel(telegram_card, text="", height=10).pack()
        
        angles_card = GlassCard(self.settings_frame)
        angles_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            angles_card,
            text="◈ УГЛЫ И ЗУМЫ (Angle-to-Zoom Mapping)",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_purple']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        info_label = ctk.CTkLabel(
            angles_card,
            text="Каждому углу соответствует фиксированный зум для скрытия углов",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=COLORS['text_muted']
        )
        info_label.pack(pady=(0, 10), anchor="w", padx=30)
        
        self.angle_entries = {}
        for angle in ['-3', '-2', '-1', '1', '2', '3']:
            self.create_angle_zoom_input(angles_card, angle)
        
        ctk.CTkLabel(angles_card, text="", height=10).pack()
        
        # New: Copies per Video
        copies_card = GlassCard(self.settings_frame)
        copies_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            copies_card,
            text="◈ КОЛИЧЕСТВО КОПИЙ НА ВИДЕО",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_blue']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        self.create_slider_input(copies_card, "Копий на входное видео", "copies_per_video", 1, 20,
                                 "Количество уникальных версий для каждого входного видео (с случайной музыкой)", step=1)
        
        ctk.CTkLabel(copies_card, text="", height=10).pack()
        
        # Video Settings
        video_card = GlassCard(self.settings_frame)
        video_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            video_card,
            text="◈ НАСТРОЙКИ ВИДЕО",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_blue']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        # Output Resolution
        self.create_dropdown_input(video_card, "Разрешение выхода", "output_resolution",
                                   ['1080x1920', '1920x1080', '720x1280', '1280x720'])
        
        # Video Codec
        self.create_dropdown_input(video_card, "Видео кодек", "video_codec",
                                   ['libx264', 'libx265', 'h264_nvenc'])
        
        # Video Preset
        self.create_dropdown_input(video_card, "Пресет скорости", "video_preset",
                                   ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow'])
        
        # CRF
        self.create_slider_input(video_card, "Качество видео (CRF)", "video_crf", 18, 28, 
                                "Чем меньше - тем лучше качество")
        
        # Audio Codec
        self.create_dropdown_input(video_card, "Аудио кодек", "audio_codec",
                                   ['aac', 'libmp3lame', 'libopus'])
        
        # Audio Bitrate
        self.create_dropdown_input(video_card, "Битрейт аудио", "audio_bitrate",
                                   ['96k', '128k', '192k', '256k', '320k'])
        
        # Pixel Format
        self.create_dropdown_input(video_card, "Формат пикселей", "pixel_format",
                                   ['yuv420p', 'yuv422p', 'yuv444p'])
        
        ctk.CTkLabel(video_card, text="", height=10).pack()
        
        # Effects Settings
        effects_card = GlassCard(self.settings_frame)
        effects_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            effects_card,
            text="◈ НАСТРОЙКИ ЭФФЕКТОВ",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLORS['neon_pink']
        ).pack(pady=(20, 15), anchor="w", padx=30)
        
        # New: Add Music Switch
        self.create_switch_input(effects_card, "Накладывать музыку", "add_music",
                                 "Включить/выключить добавление музыки из папки music (если выключено, сохраняется оригинальный звук)")

        # Mirror Probability
        self.create_slider_input(effects_card, "Вероятность зеркалирования", "mirror_probability", 0, 1,
                                "0 = никогда, 1 = всегда", step=0.1)
        
        # Color Balance Probability
        self.create_slider_input(effects_card, "Вероятность цветокоррекции", "color_balance_probability", 0, 1,
                                "0 = никогда, 1 = всегда", step=0.1)
        
        # Brightness/Contrast Probability
        self.create_slider_input(effects_card, "Вероятность яркости/контраста", "brightness_contrast_probability", 0, 1,
                                "0 = никогда, 1 = всегда", step=0.1)
        
        # Saturation Probability
        self.create_slider_input(effects_card, "Вероятность изменения насыщенности", "saturation_probability", 0, 1,
                                "0 = никогда, 1 = всегда", step=0.1)
        
        # Color Balance Range
        self.create_slider_input(effects_card, "Диапазон цветокоррекции", "color_balance_range", 0, 0.15,
                                "Сила изменения цветового баланса", step=0.01)
        
        # Brightness Range
        self.create_slider_input(effects_card, "Диапазон яркости", "brightness_range", 0, 0.1,
                                "Сила изменения яркости", step=0.01)
        
        # Contrast Range
        self.create_range_slider_input(effects_card, "Диапазон контраста", "contrast_min", "contrast_max", 0.8, 1.2)
        
        # Saturation Range
        self.create_range_slider_input(effects_card, "Диапазон насыщенности", "saturation_min", "saturation_max", 0.8, 1.2)

        ctk.CTkLabel(effects_card, text="", height=10).pack()
    
    def create_switch_input(self, parent, label, config_key, description=""):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.pack(fill="x")

        switch = ctk.CTkSwitch(
            switch_frame,
            text="",
            command=self.auto_save_settings
        )
        switch.pack(side="left")
        if self.config.get(config_key, True):
            switch.select()
        setattr(self, f"{config_key}_switch", switch)

        if description:
            desc_label = ctk.CTkLabel(
                switch_frame,
                text=description,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS['text_muted']
            )
            desc_label.pack(anchor="w", padx=10)
    
    def create_text_input(self, parent, label, config_key, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        entry = ctk.CTkEntry(
            frame,
            fg_color=COLORS['bg_elevated'],
            text_color=COLORS['text_primary'],
            font=ctk.CTkFont(family="Inter", size=12),
            show=show
        )
        entry.pack(fill="x")
        entry.insert(0, self.config.get(config_key, ''))
        entry.bind('<KeyRelease>', self.auto_save_settings)
        setattr(self, f"{config_key}_entry", entry)
    
    def create_folder_input(self, parent, label, config_key):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.pack(fill="x")

        entry = ctk.CTkEntry(
            input_frame,
            fg_color=COLORS['bg_elevated'],
            text_color=COLORS['text_primary'],
            font=ctk.CTkFont(family="Inter", size=12)
        )
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, self.config[config_key])
        entry.bind('<KeyRelease>', self.auto_save_settings)
        setattr(self, f"{config_key}_entry", entry)

        btn = NeomorphicButton(
            input_frame,
            text="📁",
            width=50,
            height=30,
            command=lambda: self.browse_folder(config_key)
        )
        btn.pack(side="right", padx=5)
    
    def create_angle_zoom_input(self, parent, angle):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=5)

        label = ctk.CTkLabel(
            frame,
            text=f"Угол {int(angle):+d}° Zoom",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        label.pack(side="left", fill="x", expand=True)

        entry = ctk.CTkEntry(
            frame,
            width=100,
            fg_color=COLORS['bg_elevated'],
            text_color=COLORS['text_primary']
        )
        entry.insert(0, str(self.config['angle_zoom_map'][angle]))
        entry.bind('<KeyRelease>', self.auto_save_settings)
        entry.pack(side="right")

        self.angle_entries[angle] = entry
    
    def create_slider_input(self, parent, label, config_key, min_val, max_val, description="", step=0.01):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        slider_frame = ctk.CTkFrame(frame, fg_color="transparent")
        slider_frame.pack(fill="x")

        slider = ctk.CTkSlider(
            slider_frame,
            from_=min_val,
            to=max_val,
            number_of_steps=int((max_val - min_val) / step),
            progress_color=COLORS['neon_cyan']
        )
        slider.set(self.config['effects_settings'].get(config_key, self.config.get(config_key, (min_val + max_val)/2)))
        slider.pack(side="left", fill="x", expand=True)
        setattr(self, f"{config_key}_slider", slider)

        value_label = ctk.CTkLabel(
            slider_frame,
            text=f"{slider.get():.2f}",
            width=50,
            text_color=COLORS['info']
        )
        value_label.pack(side="right", padx=5)

        def on_slider_change(v):
            value_label.configure(text=f"{v:.2f}")
            self.auto_save_settings()

        slider.configure(command=on_slider_change)

        if description:
            desc_label = ctk.CTkLabel(
                frame,
                text=description,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=COLORS['text_muted']
            )
            desc_label.pack(anchor="w", pady=(5, 0))
    
    def create_range_slider_input(self, parent, label, min_key, max_key, min_val, max_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        min_frame = ctk.CTkFrame(frame, fg_color="transparent")
        min_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(min_frame, text="Min", width=30, text_color=COLORS['text_muted']).pack(side="left")
        min_entry = ctk.CTkEntry(min_frame, width=80, fg_color=COLORS['bg_elevated'])
        min_entry.insert(0, str(self.config['effects_settings'][min_key]))
        min_entry.bind('<KeyRelease>', self.auto_save_settings)
        min_entry.pack(side="left", padx=5)
        setattr(self, f"{min_key}_entry", min_entry)

        max_frame = ctk.CTkFrame(frame, fg_color="transparent")
        max_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(max_frame, text="Max", width=30, text_color=COLORS['text_muted']).pack(side="left")
        max_entry = ctk.CTkEntry(max_frame, width=80, fg_color=COLORS['bg_elevated'])
        max_entry.insert(0, str(self.config['effects_settings'][max_key]))
        max_entry.bind('<KeyRelease>', self.auto_save_settings)
        max_entry.pack(side="left", padx=5)
        setattr(self, f"{max_key}_entry", max_entry)
    
    def create_dropdown_input(self, parent, label, config_key, options):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))

        dropdown = ctk.CTkComboBox(
            frame,
            values=options,
            fg_color=COLORS['bg_elevated'],
            text_color=COLORS['text_primary'],
            command=lambda choice: self.auto_save_settings()
        )
        dropdown.set(self.config['video_settings'][config_key])
        dropdown.pack(fill="x")
        setattr(self, f"{config_key}_dropdown", dropdown)
    
    def create_console_section(self):
        self.console_frame = GlassCard(self.content_area)
        
        header = ctk.CTkLabel(
            self.console_frame,
            text="◈ КОНСОЛЬ",
            font=ctk.CTkFont(family="Inter", size=32, weight="bold"),
            text_color=COLORS['text_primary']
        )
        header.pack(pady=(20, 20), padx=20)
        
        button_frame = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 20), padx=20)
        
        clear_btn = NeomorphicButton(
            button_frame,
            text="🧹 ОЧИСТИТЬ",
            width=150,
            command=self.clear_console
        )
        clear_btn.pack(side="left")
        
        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            height=600,
            fg_color=COLORS['bg_deep'],
            text_color=COLORS['text_primary'],
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.console_text.pack(fill="both", expand=True, padx=20, pady=20)
    
    def show_section(self, section):
        self.dashboard_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.console_frame.pack_forget()
        
        if section == "dashboard":
            self.dashboard_frame.pack(fill="both", expand=True)
        elif section == "settings":
            self.settings_frame.pack(fill="both", expand=True)
        elif section == "console":
            self.console_frame.pack(fill="both", expand=True)
        
        self.current_section = section
    
    def browse_folder(self, config_key):
        folder = filedialog.askdirectory()
        if folder:
            entry = getattr(self, f"{config_key}_entry")
            entry.delete(0, "end")
            entry.insert(0, folder)
            self.auto_save_settings()
    
    def auto_save_settings(self, event=None):
        """Автоматическое сохранение настроек в реальном времени"""
        try:
            self.save_settings(silent=True)
        except Exception as e:
            print(f"Ошибка автосохранения: {str(e)}")

    def save_settings(self, silent=False):
        try:
            self.config['input_folder'] = self.input_folder_entry.get()
            self.config['output_folder'] = self.output_folder_entry.get()
            self.config['music_folder'] = self.music_folder_entry.get()
            self.config['instagram_username'] = self.instagram_username_entry.get()
            self.config['instagram_password'] = self.instagram_password_entry.get()
            self.config['telegram_token'] = self.telegram_token_entry.get()

            self.config['add_music'] = self.add_music_switch.get() == 1

            self.config['copies_per_video'] = int(self.copies_per_video_slider.get())

            for angle, entry in self.angle_entries.items():
                self.config['angle_zoom_map'][angle] = float(entry.get())

            # Video settings
            self.config['video_settings']['output_resolution'] = self.output_resolution_dropdown.get()
            self.config['video_settings']['video_codec'] = self.video_codec_dropdown.get()
            self.config['video_settings']['video_preset'] = self.video_preset_dropdown.get()
            self.config['video_settings']['video_crf'] = int(self.video_crf_slider.get())
            self.config['video_settings']['audio_codec'] = self.audio_codec_dropdown.get()
            self.config['video_settings']['audio_bitrate'] = self.audio_bitrate_dropdown.get()
            self.config['video_settings']['pixel_format'] = self.pixel_format_dropdown.get()

            # Effects settings
            self.config['effects_settings']['mirror_probability'] = float(self.mirror_probability_slider.get())
            self.config['effects_settings']['color_balance_probability'] = float(self.color_balance_probability_slider.get())
            self.config['effects_settings']['brightness_contrast_probability'] = float(self.brightness_contrast_probability_slider.get())
            self.config['effects_settings']['saturation_probability'] = float(self.saturation_probability_slider.get())
            self.config['effects_settings']['color_balance_range'] = float(self.color_balance_range_slider.get())
            self.config['effects_settings']['brightness_range'] = float(self.brightness_range_slider.get())
            self.config['effects_settings']['contrast_min'] = float(self.contrast_min_entry.get())
            self.config['effects_settings']['contrast_max'] = float(self.contrast_max_entry.get())
            self.config['effects_settings']['saturation_min'] = float(self.saturation_min_entry.get())
            self.config['effects_settings']['saturation_max'] = float(self.saturation_max_entry.get())

            self.save_config()
            self.update_stats()

            if not silent:
                messagebox.showinfo("Успех", "Настройки сохранены!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")
    
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
            messagebox.showwarning("Предупреждение", 
                                 f"Нет видео в папке:\n{self.config['input_folder']}")
            return
        
        if self.config['add_music'] and not music_videos:
            messagebox.showwarning("Предупреждение", 
                                 f"Нет музыки в папке:\n{self.config['music_folder']}\n\nПоддерживаемые форматы: mp3, wav, aac, m4a, ogg, flac, mp4, mov, avi, mkv")
            return
        
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = len(input_videos) * self.config['copies_per_video']
        self.stop_requested = False
        
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="● РАБОТАЕТ", text_color=COLORS['warning'])
        self.status_indicator.configure(fg_color=COLORS['warning'])
        
        if hasattr(self, 'dashboard_status'):
            self.dashboard_status.configure(text="АКТИВНА", text_color=COLORS['warning'])
        
        self.processing_thread = threading.Thread(target=self.run_processing, daemon=True)
        self.processing_thread.start()
        
        print("="*85)
        print("◈ ОБРАБОТКА ВИДЕО ЗАПУЩЕНА")
        print("="*85)
    
    def stop_processing(self):
        if not self.is_running:
            return
        
        result = messagebox.askyesno("Подтвердить", 
                                    "Остановить обработку?\n\nТекущее видео завершится.")
        
        if result:
            self.stop_requested = True
            print("\n⏹ ЗАПРОС НА ОСТАНОВКУ...")
            self.status_label.configure(text="● ОСТАНАВЛИВАЕТСЯ", text_color=COLORS['danger'])
            self.status_indicator.configure(fg_color=COLORS['danger'])
            self.stop_btn.configure(state="disabled")
    
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
        filters = []
        effects = self.config['effects_settings']
        
        if random.random() < effects['color_balance_probability']:
            range_val = effects['color_balance_range']
            rs = random.uniform(-range_val, range_val)
            gs = random.uniform(-range_val, range_val)
            bs = random.uniform(-range_val, range_val)
            rm = random.uniform(-range_val, range_val)
            gm = random.uniform(-range_val, range_val)
            bm = random.uniform(-range_val, range_val)
            filters.append(f"colorbalance=rs={rs:.3f}:gs={gs:.3f}:bs={bs:.3f}:rm={rm:.3f}:gm={gm:.3f}:bm={bm:.3f}")
        
        if random.random() < effects['brightness_contrast_probability']:
            brightness = random.uniform(-effects['brightness_range'], effects['brightness_range'])
            contrast = random.uniform(effects['contrast_min'], effects['contrast_max'])
            filters.append(f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}")
        
        if random.random() < effects['saturation_probability']:
            saturation = random.uniform(effects['saturation_min'], effects['saturation_max'])
            filters.append(f"eq=saturation={saturation:.3f}")
        
        return filters
    
    def uniquify_video(self, input_video, music_video, output_video):
        try:
            orig_w, orig_h = self.get_video_resolution(input_video)
            
            angle_zoom_map = {int(k): v for k, v in self.config['angle_zoom_map'].items()}
            angle_degrees = random.choice(list(angle_zoom_map.keys()))
            zoom_factor = angle_zoom_map[angle_degrees]
            angle_radians = angle_degrees * math.pi / 180
            
            # Используем вероятность зеркалирования из настроек
            mirror_prob = self.config['effects_settings']['mirror_probability']
            mirror = random.random() < mirror_prob
            
            # Получаем настройки видео
            video_settings = self.config['video_settings']
            resolution = video_settings['output_resolution'].split('x')
            output_width = int(resolution[0])
            output_height = int(resolution[1])
            
            filter_parts = []
            filter_parts.append(f"rotate={angle_radians:.6f}:fillcolor=black")
            
            zoom_w = int(orig_w / zoom_factor)
            zoom_h = int(orig_h / zoom_factor)
            zoom_w = zoom_w if zoom_w % 2 == 0 else zoom_w - 1
            zoom_h = zoom_h if zoom_h % 2 == 0 else zoom_h - 1
            filter_parts.append(f"crop={zoom_w}:{zoom_h}:(iw-{zoom_w})/2:(ih-{zoom_h})/2")
            
            filter_parts.append(f"scale={output_width}:{output_height}:force_original_aspect_ratio=decrease")
            filter_parts.append(f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2:color=black")
            
            if mirror:
                filter_parts.append("hflip")
            
            random_filters = self.get_random_filters()
            filter_parts.extend(random_filters)
            
            video_filter = ",".join(filter_parts)
            
            add_music = self.config['add_music']
            
            temp_video = output_video if not add_music else output_video.replace('.mp4', '_temp.mp4')
            
            cmd1 = [
                "ffmpeg",
                "-hide_banner", "-loglevel", "error",
                "-i", input_video,
                "-filter:v", video_filter,
                "-c:v", video_settings['video_codec'],
                "-preset", video_settings['video_preset'],
                "-crf", str(video_settings['video_crf']),
                "-pix_fmt", video_settings['pixel_format'],
            ]
            
            if add_music:
                cmd1.append("-an")  # Remove audio if adding music
            else:
                cmd1.extend(["-c:a", video_settings['audio_codec'], "-b:a", video_settings['audio_bitrate']])
            
            cmd1.extend(["-y", temp_video])
            
            subprocess.run(cmd1, check=True)
            
            if add_music:
                cmd2 = [
                    "ffmpeg",
                    "-hide_banner", "-loglevel", "error",
                    "-i", temp_video,
                    "-i", music_video,
                    "-c:v", "copy",
                    "-c:a", video_settings['audio_codec'],
                    "-b:a", video_settings['audio_bitrate'],
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
            music_str = "🎵" if add_music else "🔇"
            print(f"✓ {os.path.basename(output_video)} | Angle: {angle_degrees:+3d}° | Zoom: {zoom_factor:.4f}x | Mirror: {mirror_str} | Music: {music_str}")
            return True
        except Exception as e:
            print(f"✗ {os.path.basename(output_video)} | Error: {str(e)}")
            if 'temp_video' in locals() and os.path.exists(temp_video):
                os.remove(temp_video)
            return False
    
    def run_processing(self):
        try:
            input_folder = self.config['input_folder']
            output_folder = self.config['output_folder']
            music_folder = self.config['music_folder']
            
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            os.makedirs(output_folder, exist_ok=True)
            print("🧹 Папка output очищена\n")
            
            input_videos = self.get_video_files(input_folder)
            music_videos = self.get_audio_files(music_folder) if self.config['add_music'] else []
            
            print(f"\nSource: {len(input_videos)} videos")
            if self.config['add_music']:
                print(f"Music: {len(music_videos)} tracks")
            else:
                print("Music overlay: DISABLED (original audio preserved)")
            print(f"Creating {len(input_videos) * self.config['copies_per_video']} outputs ( {self.config['copies_per_video']} copies per video )\n")
            
            print("Angle-to-Zoom Mapping:")
            for angle, zoom in sorted(self.config['angle_zoom_map'].items(), key=lambda x: int(x[0])):
                angle_int = int(angle)
                zoom_float = float(zoom)
                print(f"  {angle_int:+3d}° → {zoom_float:.4f}x zoom ({(zoom_float-1)*100:.1f}% crop)")
            print()
            
            for i, input_video in enumerate(input_videos, 1):
                if self.stop_requested:
                    print("\n⏹ ОСТАНОВЛЕНО")
                    break
                
                for j in range(1, self.config['copies_per_video'] + 1):
                    if self.stop_requested:
                        break
                    
                    music_video = random.choice(music_videos) if self.config['add_music'] and music_videos else None
                    
                    output_filename = f"{i}.{j}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    self.current_video = output_filename
                    self.root.after(0, lambda: self.current_video_label.configure(
                        text=f"Обрабатывается: {self.current_video}"
                    ))
                    
                    if self.uniquify_video(input_video, music_video, output_path):
                        self.processed_count += 1
                    else:
                        self.failed_count += 1
                    
                    self.root.after(0, self.update_stats)
            
            if not self.stop_requested:
                print("\n" + "="*85)
                print(f"◈ ОБРАБОТКА ЗАВЕРШЕНА")
                print("="*85)
                print(f"✦ Успешно: {self.processed_count}")
                print(f"✧ Ошибок: {self.failed_count}")
                print(f"◈ Всего: {self.processed_count + self.failed_count}")
                print("Format: 1080x1920 vertical | Corners hidden by corresponding zoom!")
                print("="*85)
        
        except Exception as e:
            print(f"\n❌ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.stop_requested = False
            self.current_video = ""
            self.root.after(0, lambda: self.start_btn.configure(state="normal"))
            self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
            self.root.after(0, lambda: self.status_label.configure(text="● ГОТОВА", text_color=COLORS['info']))
            self.root.after(0, lambda: self.status_indicator.configure(fg_color=COLORS['info']))
            self.root.after(0, lambda: self.current_video_label.configure(text=""))
            
            if hasattr(self, 'dashboard_status'):
                self.root.after(0, lambda: self.dashboard_status.configure(text="ГОТОВА", text_color=COLORS['info']))
    
    def start_download(self, auto_process=False):
        if self.is_downloading:
            return
        
        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.download_and_process_btn.configure(state="disabled")
        self.dashboard_status.configure(text="ЗАГРУЗКА", text_color=COLORS['warning'])
        self.status_label.configure(text="● ЗАГРУЗКА", text_color=COLORS['warning'])
        self.status_indicator.configure(fg_color=COLORS['warning'])
        
        self.download_thread = threading.Thread(target=self._download_reels_threaded, args=(auto_process,))
        self.download_thread.start()
    
    def _download_reels_threaded(self, auto_process):
        try:
            downloaded_count = self.download_reels()
            self.root.after(0, lambda: self._finish_download(downloaded_count, auto_process))
        except Exception as e:
            print(f"✗ Ошибка загрузки: {str(e)}")
            self.root.after(0, lambda: self._finish_download(0, auto_process))
    
    def _finish_download(self, downloaded_count, auto_process):
        messagebox.showinfo("Успех", f"Загружено {downloaded_count} видео в {self.config['input_folder']}")
        self.update_stats()
        if auto_process:
            self.start_processing()
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.download_and_process_btn.configure(state="normal")
        self.dashboard_status.configure(text="ГОТОВА", text_color=COLORS['info'])
        self.status_label.configure(text="● ГОТОВА", text_color=COLORS['info'])
        self.status_indicator.configure(fg_color=COLORS['info'])
    
    def download_reels(self):
        inputs = self.reels_text.get("1.0", "end").strip().splitlines()
        if not inputs:
            self.root.after(0, lambda: messagebox.showwarning("Предупреждение", "Нет URL или username для загрузки!"))
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
        loader.save_metadata = False  # Disable JSON metadata
        loader.post_metadata_txt_pattern = ''  # Disable TXT files
        
        username = self.config.get('instagram_username', '')
        password = self.config.get('instagram_password', '')
        if username and password:
            try:
                loader.login(username, password)
                print("✓ Успешный вход в Instagram")
            except Exception as e:
                print(f"✗ Ошибка входа: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось войти в Instagram: {str(e)}"))
                return 0
        
        for line in inputs:
            if not line.strip():
                continue
            
            try:
                if line.startswith('@'):
                    username = line[1:].strip()
                    print(f"⬇️ Загрузка всех видео из аккаунта: {username}")
                    profile = instaloader.Profile.from_username(loader.context, username)
                    for post in profile.get_posts():
                        if post.is_video:
                            loader.download_post(post, target='')
                            downloaded_count += 1
                    print(f"✓ Загружены видео из аккаунта: {username}")
                else:
                    url = line.strip()
                    print(f"⬇️ Загрузка: {url}")
                    match = re.search(r'/(?:p|reel|reels)/([A-Za-z0-9_-]+)/', url)
                    if match:
                        shortcode = match.group(1)
                        try:
                            post = instaloader.Post.from_shortcode(loader.context, shortcode)
                            if post.is_video:
                                loader.download_post(post, target='')
                                downloaded_count += 1
                            print(f"✓ Загружено: {url}")
                        except Exception as instaloader_e:
                            print(f"✗ Ошибка instaloader: {str(instaloader_e)}")
                            # Fallback to yt-dlp with cleaned URL
                            cleaned_url = f"https://www.instagram.com/reel/{shortcode}/"
                            try:
                                cmd = [
                                    "yt-dlp",
                                    "-f", "best[ext=mp4]",
                                    "--no-playlist",
                                    "-o", os.path.join(input_folder, "%(id)s.%(ext)s"),
                                    cleaned_url
                                ]
                                subprocess.run(cmd, check=True)
                                downloaded_count += 1
                                print(f"✓ Загружено (yt-dlp): {cleaned_url}")
                            except Exception as ytdlp_e:
                                print(f"✗ Ошибка yt-dlp: {str(ytdlp_e)}")
                                print(f"✗ Недействительный URL: {url}")
                    else:
                        print(f"✗ Недействительный URL: {url}")
            except Exception as e:
                print(f"✗ Ошибка загрузки {line}: {str(e)}")
        
        # Clean up non-video files
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        for filename in os.listdir(input_folder):
            filepath = os.path.join(input_folder, filename)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename)
                if ext.lower() not in video_extensions:
                    os.remove(filepath)
                    print(f"🗑️ Удален ненужный файл: {filename}")
        
        return downloaded_count
    
    def download_single_instagram(self, input_str, temp_folder):
        downloaded_count = 0
        loader = instaloader.Instaloader()
        loader.dirname_pattern = temp_folder
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
            except Exception as e:
                return 0, f"Ошибка входа в Instagram: {str(e)}"
        
        try:
            if input_str.startswith('@'):
                username = input_str[1:].strip()
                profile = instaloader.Profile.from_username(loader.context, username)
                for post in profile.get_posts():
                    if post.is_video:
                        loader.download_post(post, target='')
                        downloaded_count += 1
            else:
                url = input_str.strip()
                match = re.search(r'/(?:p|reel|reels)/([A-Za-z0-9_-]+)/', url)
                if match:
                    shortcode = match.group(1)
                    try:
                        post = instaloader.Post.from_shortcode(loader.context, shortcode)
                        if post.is_video:
                            loader.download_post(post, target='')
                            downloaded_count += 1
                    except Exception as e:
                        cleaned_url = f"https://www.instagram.com/reel/{shortcode}/"
                        try:
                            cmd = [
                                "yt-dlp",
                                "-f", "best[ext=mp4]",
                                "--no-playlist",
                                "-o", os.path.join(temp_folder, "%(id)s.%(ext)s"),
                                cleaned_url
                            ]
                            subprocess.run(cmd, check=True)
                            downloaded_count += 1
                        except Exception as ytdlp_e:
                            return 0, f"Ошибка загрузки: {str(ytdlp_e)}"
        except Exception as e:
            return 0, f"Ошибка загрузки: {str(e)}"
        
        # Clean up non-video files
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        for filename in os.listdir(temp_folder):
            filepath = os.path.join(temp_folder, filename)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename)
                if ext.lower() not in video_extensions:
                    os.remove(filepath)
        
        return downloaded_count, None
    
    def process_and_send_videos(self, bot, chat_id, input_videos, copies=None):
        if copies is None:
            copies = self.config['copies_per_video']
        
        music_videos = self.get_audio_files(self.config['music_folder']) if self.config['add_music'] else []
        
        output_folder = f"temp_output_{chat_id}"
        for input_video in input_videos:
            for j in range(1, copies + 1):
                music_video = random.choice(music_videos) if self.config['add_music'] and music_videos else None
                output_filename = f"unique_{j}.mp4"
                output_path = os.path.join(output_folder, output_filename)
                
                if self.uniquify_video(input_video, music_video, output_path):
                    with open(output_path, 'rb') as video_file:
                        bot.send_video(chat_id, video_file)
                    os.remove(output_path)
                else:
                    bot.send_message(chat_id, f"Ошибка обработки копии {j}")
        
        # Clean up temp
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
    
    def start_telegram_bot(self):
        token = self.config.get('telegram_token', '')
        if not token:
            messagebox.showerror("Ошибка", "Введите токен Telegram бота в настройках!")
            return
        
        if self.bot:
            messagebox.showinfo("Инфо", "Бот уже запущен!")
            return
        
        self.bot = telebot.TeleBot(token)
        
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.bot.send_message(message.chat.id, "Добро пожаловать! Отправьте видео или URL/@username Instagram для уникализации.")
        
        @self.bot.message_handler(content_types=['video'])
        def handle_video(message):
            self.bot.send_message(message.chat.id, "Обработка видео...")
            temp_folder = f"temp_input_{message.chat.id}"
            os.makedirs(temp_folder, exist_ok=True)
            file_info = self.bot.get_file(message.video.file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)
            input_path = os.path.join(temp_folder, "input.mp4")
            with open(input_path, 'wb') as f:
                f.write(downloaded_file)
            
            self.user_states[message.chat.id] = {'input_folder': temp_folder}
            
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("1", callback_data="copies_1"),
                InlineKeyboardButton("3", callback_data="copies_3"),
                InlineKeyboardButton("5", callback_data="copies_5"),
                InlineKeyboardButton("10", callback_data="copies_10")
            )
            self.bot.send_message(message.chat.id, "Сколько копий?", reply_markup=markup)
        
        @self.bot.message_handler(func=lambda m: True)
        def handle_text(message):
            self.bot.send_message(message.chat.id, "Загрузка с Instagram...")
            temp_folder = f"temp_input_{message.chat.id}"
            os.makedirs(temp_folder, exist_ok=True)
            downloaded_count, error = self.download_single_instagram(message.text, temp_folder)
            if error:
                self.bot.send_message(message.chat.id, error)
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder)
                return
            
            if downloaded_count == 0:
                self.bot.send_message(message.chat.id, "Нет видео загружено")
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder)
                return
            
            self.user_states[message.chat.id] = {'input_folder': temp_folder}
            
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("1", callback_data="copies_1"),
                InlineKeyboardButton("3", callback_data="copies_3"),
                InlineKeyboardButton("5", callback_data="copies_5"),
                InlineKeyboardButton("10", callback_data="copies_10")
            )
            self.bot.send_message(message.chat.id, "Сколько копий для каждого видео?", reply_markup=markup)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            chat_id = call.message.chat.id
            if chat_id in self.user_states:
                data = call.data
                if data.startswith('copies_'):
                    copies = int(data.split('_')[1])
                    state = self.user_states[chat_id]
                    input_folder = state['input_folder']
                    input_videos = self.get_video_files(input_folder)
                    if input_videos:
                        self.bot.send_message(chat_id, f"Обработка с {copies} копиями...")
                        os.makedirs(f"temp_output_{chat_id}", exist_ok=True)
                        self.process_and_send_videos(self.bot, chat_id, input_videos, copies)
                    else:
                        self.bot.send_message(chat_id, "Нет видео для обработки")
                    if os.path.exists(input_folder):
                        shutil.rmtree(input_folder)
                    del self.user_states[chat_id]
        
        self.bot_thread = threading.Thread(target=self.bot.polling, daemon=True)
        self.bot_thread.start()
    
    def update_stats(self):
        self.stat_widgets['processed'].configure(text=str(self.processed_count))
        self.stat_widgets['failed'].configure(text=str(self.failed_count))
        self.stat_widgets['total'].configure(text=str(self.processed_count + self.failed_count))
        
        if hasattr(self, 'dashboard_input_count'):
            try:
                input_videos = self.get_video_files(self.config['input_folder'])
                self.dashboard_input_count.configure(text=str(len(input_videos)))
            except:
                self.dashboard_input_count.configure(text="0")
        
        if hasattr(self, 'dashboard_music_count'):
            try:
                music_videos = self.get_audio_files(self.config['music_folder'])
                self.dashboard_music_count.configure(text=str(len(music_videos)))
            except:
                self.dashboard_music_count.configure(text="0")
        
        if hasattr(self, 'dashboard_output_count'):
            try:
                input_videos = self.get_video_files(self.config['input_folder'])
                music_videos = self.get_audio_files(self.config['music_folder'])
                total = len(input_videos) * self.config['copies_per_video']
                self.dashboard_output_count.configure(text=str(total))
            except:
                self.dashboard_output_count.configure(text="0")
        
        # Обновляем карточки созданных видео и ошибок
        if hasattr(self, 'dashboard_created_count'):
            self.dashboard_created_count.configure(text=str(self.processed_count))
        
        if hasattr(self, 'dashboard_errors_count'):
            self.dashboard_errors_count.configure(text=str(self.failed_count))
    
    def clear_console(self):
        self.console_text.delete("1.0", "end")
    
    def process_log_queue(self):
        messages = []
        try:
            while True:
                messages.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        
        if messages:
            self.console_text.insert("end", ''.join(messages))
            self.console_text.see("end")
            
            lines = int(self.console_text.index('end-1c').split('.')[0])
            if lines > 2000:
                self.console_text.delete('1.0', f'{lines-2000}.0')
        
        self.root.after(100, self.process_log_queue)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VideoUniquifierDashboard()
    app.run()