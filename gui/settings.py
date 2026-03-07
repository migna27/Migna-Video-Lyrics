# gui/settings.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                             QCheckBox, QLabel, QPushButton, QFileDialog, QComboBox)
from PyQt6.QtCore import pyqtSignal, Qt

class SettingsPanel(QWidget):
    # Señales para medios
    font_selected = pyqtSignal(str)
    background_selected = pyqtSignal(str)
    audio_selected = pyqtSignal(str, str)

    # NUEVAS: Señales para las animaciones
    anim_in_changed = pyqtSignal(str)
    anim_out_changed = pyqtSignal(str)
    anim_active_changed = pyqtSignal(str)

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
            QComboBox { background: #333; color: white; padding: 5px; border: 1px solid #555; border-radius: 3px; }
            QComboBox::drop-down { border-left: 1px solid #555; }
        """)

        # --- PESTAÑA 1: MEDIA ---
        tab_media = QWidget()
        media_layout = QVBoxLayout(tab_media)
        
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

        # --- PESTAÑA 2: ANIMACIONES (NUEVA) ---
        tab_anims = QWidget()
        anims_layout = QFormLayout(tab_anims)
        anims_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Dropdown Entrada
        self.combo_in = QComboBox()
        self.combo_in.addItems(["glitch_reveal", "fade_in", "typewriter", "rise_from_void", "neon_flicker_on", "zoom_basico", "word_cascade", "cinematic_blur", "shatter_reverse", "side_sweep"])
        self.combo_in.currentTextChanged.connect(self.anim_in_changed.emit)

        # Dropdown Activa (Palabra por palabra)
        self.combo_active = QComboBox()
        self.combo_active.addItems(["scale_pop", "karaoke_sweep", "jitter_nervioso", "neon_pulse_glow", "invert_flash", "glitch_slice", "wave_bounce", "tilt_yawn", "color_overdrive", "ghost_trail"])
        self.combo_active.currentTextChanged.connect(self.anim_active_changed.emit)

        # Dropdown Salida
        self.combo_out = QComboBox()
        self.combo_out.addItems(["system_failure", "fade_out", "blackout_cut", "neon_flicker_off", "drop_fade", "evaporate", "typewriter_backspace", "zoom_out_collapse", "glitch_melt", "word_scatter"])
        self.combo_out.currentTextChanged.connect(self.anim_out_changed.emit)

        anims_layout.addRow(QLabel("<b>Entrada:</b>", styleSheet="color: #ccc;"), self.combo_in)
        anims_layout.addRow(QLabel("<b>Palabra Activa:</b>", styleSheet="color: #0ff;"), self.combo_active)
        anims_layout.addRow(QLabel("<b>Salida:</b>", styleSheet="color: #ccc;"), self.combo_out)
        self.tabs.addTab(tab_anims, "Animaciones")

        # --- PESTAÑA 3: GLOBAL VFX ---
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
            self.lbl_audio_status.setText(f"Cargando análisis de audio... (espera)")
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