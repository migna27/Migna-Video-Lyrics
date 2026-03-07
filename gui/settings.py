from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                             QCheckBox, QLabel, QPlainTextEdit, QPushButton, QFileDialog, QHBoxLayout)
from PyQt6.QtCore import pyqtSignal
import os

class SettingsPanel(QWidget):
    # Señales para avisar a main.py
    font_selected = pyqtSignal(str)
    background_selected = pyqtSignal(str)
    audio_selected = pyqtSignal(str, str) # Nueva señal: (Ruta del archivo, Nombre)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { background: #222; color: gray; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #333; color: #00ffff; font-weight: bold; border-bottom: 2px solid #00ffff; }
            QTabWidget::pane { border: 1px solid #333; background: #1a1a1a; }
        """)

        # Pestaña 1: Medios, Fondos y AUDIO
        tab_media = QWidget()
        media_layout = QVBoxLayout(tab_media)
        
        # --- NUEVO: Botón de Audio ---
        btn_audio = QPushButton("🎵 Cargar Pista de Audio (.mp3/.wav)")
        btn_audio.setStyleSheet("background-color: #0891b2; color: white; font-weight: bold; padding: 12px; border-radius: 4px;")
        btn_audio.clicked.connect(self.load_audio)
        self.lbl_audio_status = QLabel("Audio: Ninguno")
        self.lbl_audio_status.setStyleSheet("color: #00ffff; font-size: 11px; margin-bottom: 10px;")
        
        btn_font = QPushButton("🔤 Cargar Fuente (.ttf)")
        btn_font.setStyleSheet("background-color: #333; color: white; padding: 10px;")
        btn_font.clicked.connect(self.load_font)
        self.lbl_font_status = QLabel("Fuente: Default")
        
        btn_bg = QPushButton("🖼️/🎬 Cargar Fondo (Img/Video)")
        btn_bg.setStyleSheet("background-color: #333; color: white; padding: 10px;")
        btn_bg.clicked.connect(self.load_background)
        self.lbl_bg_status = QLabel("Fondo: Ninguno")
        
        self.lbl_font_status.setStyleSheet("color: gray; font-size: 10px; margin-bottom: 10px;")
        self.lbl_bg_status.setStyleSheet("color: gray; font-size: 10px; margin-bottom: 10px;")

        media_layout.addWidget(btn_audio)
        media_layout.addWidget(self.lbl_audio_status)
        media_layout.addWidget(btn_font)
        media_layout.addWidget(self.lbl_font_status)
        media_layout.addWidget(btn_bg)
        media_layout.addWidget(self.lbl_bg_status)
        media_layout.addStretch()
        self.tabs.addTab(tab_media, "Media")

        # Pestaña 2: Efectos Globales (VFX)
        tab_vfx = QWidget()
        vfx_layout = QFormLayout(tab_vfx)
        self.chk_chromatic = QCheckBox("Aberración Cromática")
        self.chk_scanlines = QCheckBox("Scanlines (VHS)")
        self.chk_invert = QCheckBox("Invertir Colores (Beat)")
        vfx_layout.addRow(self.chk_chromatic)
        vfx_layout.addRow(self.chk_scanlines)
        vfx_layout.addRow(self.chk_invert)
        self.tabs.addTab(tab_vfx, "Global VFX")

        layout.addWidget(self.tabs)

    def load_audio(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Audio", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if filepath:
            filename = os.path.basename(filepath)
            self.lbl_audio_status.setText(f"Audio: {filename}")
            self.lbl_audio_status.setText(f"Cargando análisis de audio... (espera)") # Aviso de carga
            self.audio_selected.emit(filepath, filename)

    def load_font(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Fuente", "", "Fonts (*.ttf *.otf)")
        if filepath:
            self.lbl_font_status.setText(f"Fuente: {os.path.basename(filepath)}")
            self.font_selected.emit(filepath)

    def load_background(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Fondo", "", "Images/Videos (*.png *.jpg *.jpeg *.mp4 *.webm)")
        if filepath:
            self.lbl_bg_status.setText(f"Fondo: {os.path.basename(filepath)}")
            self.background_selected.emit(filepath)