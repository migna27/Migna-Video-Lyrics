import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                             QCheckBox, QLabel, QPushButton, QFileDialog, QComboBox, QColorDialog)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

class SettingsPanel(QWidget):
    audio_selected = pyqtSignal(str, str)
    font_selected = pyqtSignal(str)
    background_selected = pyqtSignal(str)
    
    # Nueva senal que se emite cuando se cambia cualquier estilo de una seccion
    styles_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        # Diccionario global de estilos por seccion
        self.section_styles = {
            "Verso": {"color": "#FFFFFF", "font": "", "anim_in": "fade_in", "anim_active": "scale_pop", "anim_out": "fade_out"},
            "Pre-coro": {"color": "#00FFFF", "font": "", "anim_in": "glitch_reveal", "anim_active": "jitter_nervioso", "anim_out": "glitch_melt"},
            "Coro": {"color": "#FF00FF", "font": "", "anim_in": "zoom_basico", "anim_active": "color_overdrive", "anim_out": "zoom_out_collapse"}
        }
        self.current_editing_sec = "Verso"
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
        """)

        # --- PESTAÑA 1: MEDIA (Global) ---
        tab_media = QWidget()
        media_layout = QVBoxLayout(tab_media)
        
        btn_audio = QPushButton("Cargar Audio")
        btn_audio.setStyleSheet("background-color: #0891b2; color: white; padding: 10px;")
        btn_audio.clicked.connect(self.load_audio)
        self.lbl_audio_status = QLabel("Audio: Ninguno")
        
        btn_font = QPushButton("Cargar Fuente Global")
        btn_font.setStyleSheet("background-color: #333; color: white; padding: 10px;")
        btn_font.clicked.connect(self.load_font)
        self.lbl_font_status = QLabel("Fuente: Default")
        
        btn_bg = QPushButton("Cargar Fondo Global")
        btn_bg.setStyleSheet("background-color: #333; color: white; padding: 10px;")
        btn_bg.clicked.connect(self.load_background)
        self.lbl_bg_status = QLabel("Fondo: Ninguno")

        media_layout.addWidget(btn_audio)
        media_layout.addWidget(self.lbl_audio_status)
        media_layout.addWidget(btn_font)
        media_layout.addWidget(self.lbl_font_status)
        media_layout.addWidget(btn_bg)
        media_layout.addWidget(self.lbl_bg_status)
        media_layout.addStretch()
        self.tabs.addTab(tab_media, "Media")

        # --- PESTAÑA 2: ESTILOS DE SECCIÓN ---
        tab_styles = QWidget()
        styles_layout = QFormLayout(tab_styles)
        
        self.combo_sec_select = QComboBox()
        self.combo_sec_select.addItems(["Verso", "Pre-coro", "Coro"])
        self.combo_sec_select.currentTextChanged.connect(self.load_section_ui)

        self.btn_color = QPushButton("Cambiar Color")
        self.btn_color.clicked.connect(self.pick_color)
        
        self.btn_sec_font = QPushButton("Fuente Especifica")
        self.btn_sec_font.clicked.connect(self.pick_sec_font)

        anim_list_in = ["glitch_reveal", "fade_in", "typewriter", "zoom_basico", "side_sweep"]
        anim_list_act = ["scale_pop", "karaoke_sweep", "jitter_nervioso", "color_overdrive", "invert_flash"]
        anim_list_out = ["system_failure", "fade_out", "blackout_cut", "zoom_out_collapse", "glitch_melt"]

        self.combo_in = QComboBox()
        self.combo_in.addItems(anim_list_in)
        self.combo_in.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_in", v))

        self.combo_active = QComboBox()
        self.combo_active.addItems(anim_list_act)
        self.combo_active.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_active", v))

        self.combo_out = QComboBox()
        self.combo_out.addItems(anim_list_out)
        self.combo_out.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_out", v))

        styles_layout.addRow(QLabel("<b>Editar Sección:</b>", styleSheet="color: #0ff;"), self.combo_sec_select)
        styles_layout.addRow("Color:", self.btn_color)
        styles_layout.addRow("Tipografía:", self.btn_sec_font)
        styles_layout.addRow("Anim Entrada:", self.combo_in)
        styles_layout.addRow("Anim Activa:", self.combo_active)
        styles_layout.addRow("Anim Salida:", self.combo_out)
        self.tabs.addTab(tab_styles, "Secciones")

        # --- PESTAÑA 3: GLOBAL VFX ---
        tab_vfx = QWidget()
        vfx_layout = QFormLayout(tab_vfx)
        self.chk_chromatic = QCheckBox("Aberracion Cromatica")
        self.chk_scanlines = QCheckBox("Scanlines (VHS)")
        self.chk_invert = QCheckBox("Invertir Colores (Beat)")
        self.chk_camera = QCheckBox("Movimiento de Camara")
        vfx_layout.addRow(self.chk_chromatic)
        vfx_layout.addRow(self.chk_scanlines)
        vfx_layout.addRow(self.chk_invert)
        vfx_layout.addRow(self.chk_camera)
        self.tabs.addTab(tab_vfx, "Global VFX")

        layout.addWidget(self.tabs)
        self.load_section_ui("Verso") # Cargar valores iniciales

    def load_audio(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Audio", "", "Audio Files (*.mp3 *.wav)")
        if filepath:
            self.lbl_audio_status.setText(f"Audio: {os.path.basename(filepath)}")
            self.audio_selected.emit(filepath, os.path.basename(filepath))

    def load_font(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Fuente", "", "Fonts (*.ttf *.otf)")
        if filepath:
            self.lbl_font_status.setText(f"Fuente: {os.path.basename(filepath)}")
            self.font_selected.emit(filepath)

    def load_background(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Fondo", "", "Media (*.png *.jpg *.mp4 *.webm)")
        if filepath:
            self.lbl_bg_status.setText(f"Fondo: {os.path.basename(filepath)}")
            self.background_selected.emit(filepath)

    # --- LOGICA DE ESTILOS DE SECCION ---
    def load_section_ui(self, sec_name):
        self.current_editing_sec = sec_name
        styles = self.section_styles[sec_name]
        
        self.btn_color.setStyleSheet(f"background-color: {styles['color']}; color: black;")
        self.combo_in.setCurrentText(styles["anim_in"])
        self.combo_active.setCurrentText(styles["anim_active"])
        self.combo_out.setCurrentText(styles["anim_out"])

    def update_sec_prop(self, prop, value):
        self.section_styles[self.current_editing_sec][prop] = value
        self.styles_updated.emit(self.section_styles)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_color.setStyleSheet(f"background-color: {hex_color}; color: black;")
            self.update_sec_prop("color", hex_color)

    def pick_sec_font(self):
        filepath, _ = QFileDialog.getOpenFileName(self, f"Fuente para {self.current_editing_sec}", "", "Fonts (*.ttf *.otf)")
        if filepath:
            self.update_sec_prop("font", filepath)