import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                             QCheckBox, QLabel, QPushButton, QFileDialog, QComboBox, QColorDialog, QHBoxLayout, QDoubleSpinBox)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices

class SettingsPanel(QWidget):
    audio_selected = pyqtSignal(str, str)
    font_selected = pyqtSignal(str) 
    background_selected = pyqtSignal(str)
    styles_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        
        self.available_anims = self.load_animations_registry()
        self.fonts_dir = os.path.abspath(os.path.join("assets", "fonts"))
        os.makedirs(self.fonts_dir, exist_ok=True)
        self.available_fonts = self.scan_fonts()

        # NUEVO: Agregados 'color_active' y 'scale' matcheando tu version web
        self.section_styles = {
            "verse": {"color": "#FFFFFF", "color_active": "#00FFFF", "scale": 1.0, "font": "", "anim_in": "fade_in", "anim_active": "scale_pop", "anim_out": "fade_out", "out_mode": "Secuencial (Palabra por palabra)"},
            "bridge": {"color": "#FFFFFF", "color_active": "#FF00FF", "scale": 1.1, "font": "", "anim_in": "elastic_pop", "anim_active": "super_glow", "anim_out": "fly_away", "out_mode": "Simultaneo (Al terminar frase)"},
            "chorus": {"color": "#FFFFFF", "color_active": "#FFFF00", "scale": 1.3, "font": "", "anim_in": "fade_up", "anim_active": "shake_glitch", "anim_out": "fade_down", "out_mode": "Simultaneo (Al terminar frase)"}
        }
        self.current_editing_sec = "verse"
        self.init_ui()

    def load_animations_registry(self):
        anim_path = "assets/animations.json"
        if os.path.exists(anim_path):
            with open(anim_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"in": ["fade_in"], "active": ["scale_pop"], "out": ["fade_out"]}

    def scan_fonts(self):
        fonts = ["Default"]
        if os.path.exists(self.fonts_dir):
            for file in os.listdir(self.fonts_dir):
                if file.lower().endswith(('.ttf', '.otf')):
                    fonts.append(file)
        return fonts

    def get_font_path(self, font_filename):
        if font_filename == "Default" or not font_filename:
            return ""
        return os.path.join(self.fonts_dir, font_filename)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { background: #222; color: gray; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #333; color: #00ffff; font-weight: bold; border-bottom: 2px solid #00ffff; }
            QTabWidget::pane { border: 1px solid #333; background: #1a1a1a; }
            QComboBox, QDoubleSpinBox { background: #333; color: white; padding: 5px; border: 1px solid #555; border-radius: 3px; }
        """)

        # --- PESTAÑA 1: MEDIA (Global) ---
        tab_media = QWidget()
        media_layout = QVBoxLayout(tab_media)
        
        btn_open_assets = QPushButton("Abrir Carpeta de Assets (Fuentes)")
        btn_open_assets.setStyleSheet("background-color: #f59e0b; color: black; font-weight: bold; padding: 10px;")
        btn_open_assets.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.fonts_dir)))

        btn_audio = QPushButton("Cargar Audio")
        btn_audio.setStyleSheet("background-color: #0891b2; color: white; padding: 10px;")
        btn_audio.clicked.connect(self.load_audio)
        self.lbl_audio_status = QLabel("Audio: Ninguno")
        self.lbl_audio_status.setStyleSheet("color: #00ffff; font-size: 11px; margin-bottom: 10px;")
        
        font_layout = QHBoxLayout()
        self.combo_global_font = QComboBox()
        self.combo_global_font.addItems(self.available_fonts)
        self.combo_global_font.currentTextChanged.connect(lambda v: self.font_selected.emit(self.get_font_path(v)))
        
        btn_refresh_fonts = QPushButton("🔄")
        btn_refresh_fonts.setFixedWidth(30)
        btn_refresh_fonts.clicked.connect(self.refresh_font_lists)

        font_layout.addWidget(QLabel("<b>Fuente Global:</b>", styleSheet="color: #ccc;"))
        font_layout.addWidget(self.combo_global_font, stretch=1)
        font_layout.addWidget(btn_refresh_fonts)
        
        btn_bg = QPushButton("Cargar Fondo Global")
        btn_bg.setStyleSheet("background-color: #333; color: white; padding: 10px;")
        btn_bg.clicked.connect(self.load_background)
        self.lbl_bg_status = QLabel("Fondo: Ninguno")
        self.lbl_bg_status.setStyleSheet("color: gray; font-size: 10px; margin-bottom: 10px;")

        media_layout.addWidget(btn_open_assets)
        media_layout.addWidget(btn_audio)
        media_layout.addWidget(self.lbl_audio_status)
        media_layout.addLayout(font_layout)
        media_layout.addSpacing(15)
        media_layout.addWidget(btn_bg)
        media_layout.addWidget(self.lbl_bg_status)
        media_layout.addStretch()
        self.tabs.addTab(tab_media, "Media")

        # --- PESTAÑA 2: ESTILOS DE SECCIÓN ---
        tab_styles = QWidget()
        styles_layout = QFormLayout(tab_styles)
        
        self.combo_sec_select = QComboBox()
        self.combo_sec_select.addItems(["verse", "bridge", "chorus"])
        self.combo_sec_select.currentTextChanged.connect(self.load_section_ui)

        # Controles de Color y Tamaño
        self.btn_color = QPushButton("Color Base")
        self.btn_color.clicked.connect(self.pick_color)
        
        self.btn_color_active = QPushButton("Color Palabra Activa")
        self.btn_color_active.clicked.connect(self.pick_color_active)
        
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.3, 4.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.valueChanged.connect(lambda v: self.update_sec_prop("scale", v))
        
        self.combo_sec_font = QComboBox()
        self.combo_sec_font.addItems(self.available_fonts)
        self.combo_sec_font.currentTextChanged.connect(self.update_sec_font)

        self.combo_in = QComboBox()
        self.combo_in.addItems(self.available_anims.get("in", []))
        self.combo_in.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_in", v))

        self.combo_active = QComboBox()
        self.combo_active.addItems(self.available_anims.get("active", []))
        self.combo_active.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_active", v))

        self.combo_out = QComboBox()
        self.combo_out.addItems(self.available_anims.get("out", []))
        self.combo_out.currentTextChanged.connect(lambda v: self.update_sec_prop("anim_out", v))

        self.combo_out_mode = QComboBox()
        self.combo_out_mode.addItems(["Simultaneo (Al terminar frase)", "Secuencial (Palabra por palabra)"])
        self.combo_out_mode.currentTextChanged.connect(lambda v: self.update_sec_prop("out_mode", v))

        styles_layout.addRow(QLabel("<b>Editar Sección:</b>", styleSheet="color: #0ff;"), self.combo_sec_select)
        styles_layout.addRow("Color Texto:", self.btn_color)
        styles_layout.addRow("Color Activo:", self.btn_color_active)
        styles_layout.addRow("Tamaño (Escala):", self.spin_scale)
        styles_layout.addRow("Tipografía:", self.combo_sec_font) 
        styles_layout.addRow("Modo Salida:", self.combo_out_mode)
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
        self.chk_vignette = QCheckBox("Viñeta (Bordes Oscuros)")
        self.chk_grain = QCheckBox("Ruido de Película (Film Grain)")
        self.chk_camera = QCheckBox("Movimiento de Camara")
        vfx_layout.addRow(self.chk_chromatic)
        vfx_layout.addRow(self.chk_scanlines)
        vfx_layout.addRow(self.chk_invert)
        vfx_layout.addRow(self.chk_vignette)
        vfx_layout.addRow(self.chk_grain)
        vfx_layout.addRow(self.chk_camera)
        self.tabs.addTab(tab_vfx, "Global VFX")

        layout.addWidget(self.tabs)
        self.load_section_ui("verse")

    def refresh_font_lists(self):
        self.available_fonts = self.scan_fonts()
        curr_global = self.combo_global_font.currentText()
        curr_sec = self.combo_sec_font.currentText()
        
        self.combo_global_font.blockSignals(True)
        self.combo_sec_font.blockSignals(True)
        
        self.combo_global_font.clear()
        self.combo_sec_font.clear()
        
        self.combo_global_font.addItems(self.available_fonts)
        self.combo_sec_font.addItems(self.available_fonts)
        
        if curr_global in self.available_fonts: self.combo_global_font.setCurrentText(curr_global)
        if curr_sec in self.available_fonts: self.combo_sec_font.setCurrentText(curr_sec)
        
        self.combo_global_font.blockSignals(False)
        self.combo_sec_font.blockSignals(False)

    def load_audio(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Audio", "", "Audio Files (*.mp3 *.wav)")
        if filepath:
            self.lbl_audio_status.setText(f"Audio: {os.path.basename(filepath)}")
            self.audio_selected.emit(filepath, os.path.basename(filepath))

    def load_background(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Fondo", "", "Media (*.png *.jpg *.mp4 *.webm)")
        if filepath:
            self.lbl_bg_status.setText(f"Fondo: {os.path.basename(filepath)}")
            self.background_selected.emit(filepath)

    def load_section_ui(self, sec_name):
        self.current_editing_sec = sec_name
        styles = self.section_styles[sec_name]
        
        self.btn_color.setStyleSheet(f"background-color: {styles.get('color', '#FFFFFF')}; color: black;")
        self.btn_color_active.setStyleSheet(f"background-color: {styles.get('color_active', '#00FFFF')}; color: black;")
        
        self.spin_scale.blockSignals(True)
        self.spin_scale.setValue(styles.get("scale", 1.0))
        self.spin_scale.blockSignals(False)

        self.combo_in.setCurrentText(styles["anim_in"])
        self.combo_active.setCurrentText(styles["anim_active"])
        self.combo_out.setCurrentText(styles["anim_out"])
        self.combo_out_mode.setCurrentText(styles.get("out_mode", "Simultaneo (Al terminar frase)"))
        
        font_path = styles.get("font", "")
        if font_path:
            font_filename = os.path.basename(font_path)
            if font_filename in self.available_fonts:
                self.combo_sec_font.setCurrentText(font_filename)
            else:
                self.combo_sec_font.setCurrentText("Default")
        else:
            self.combo_sec_font.setCurrentText("Default")

    def update_sec_prop(self, prop, value):
        self.section_styles[self.current_editing_sec][prop] = value
        self.styles_updated.emit(self.section_styles)

    def update_sec_font(self, font_filename):
        path = self.get_font_path(font_filename)
        self.update_sec_prop("font", path)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_color.setStyleSheet(f"background-color: {hex_color}; color: black;")
            self.update_sec_prop("color", hex_color)

    def pick_color_active(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.btn_color_active.setStyleSheet(f"background-color: {hex_color}; color: black;")
            self.update_sec_prop("color_active", hex_color)