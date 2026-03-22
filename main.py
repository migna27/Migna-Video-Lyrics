import sys
import os
import cv2
import numpy as np
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QStackedWidget,
                             QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QTimer

from core.audio_mixer import AudioMixer
from core.gl_renderer import CanvasVideoRenderer
from core.project_manager import ProjectManager
from core.text_engine import TextEngine
from core.video_exporter import VideoExporter
from core.lyric_animator import LyricAnimator
from core.export_worker import ExportWorker 

from gui.launcher import LauncherWidget
from gui.timeline import TimelineEditor
from gui.settings import SettingsPanel

class MignaDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AppMigna Video lyrics")
        self.resize(1280, 800)
        self.pm = ProjectManager(db_folder="db")
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.launcher = LauncherWidget(self.pm)
        self.launcher.project_selected.connect(self.open_editor)
        self.stack.addWidget(self.launcher)
        
        self.editor_widget = QWidget()
        self.setup_editor_ui()
        self.stack.addWidget(self.editor_widget)
        self.export_worker = None

    def setup_editor_ui(self):
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.mixer = AudioMixer(fps=30)
        self.gl_render = CanvasVideoRenderer()
        self.text_engine = TextEngine(width=1920, height=1080)
        self.animator = LyricAnimator()
        
        self.current_time = 0.0
        self.is_playing = False
        self.lyrics_segments = []
        self.bg_video_cap = None
        self.bg_is_video = False

        self.current_audio_path = None
        self.current_audio_name = None
        self.current_font_path = None
        self.current_bg_path = None

        header = QWidget()
        header.setStyleSheet("background-color: #111; border-bottom: 1px solid #333;")
        h_layout = QHBoxLayout(header)
        
        self.btn_home = QPushButton("INICIO")
        self.btn_home.setFixedSize(60, 30)
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentWidget(self.launcher))
        self.lbl_title = QLabel("<b>MIGNA</b> / Untitled", styleSheet="color: #0ff; font-size: 14px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        
        self.btn_save = QPushButton("GUARDAR")
        self.btn_save.clicked.connect(self.save_current_project)
        self.btn_export = QPushButton("EXPORTAR VIDEO")
        self.btn_export.clicked.connect(self.start_export)
        
        h_layout.addWidget(self.btn_home)
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        h_layout.addWidget(self.progress_bar)
        h_layout.addWidget(self.btn_save)
        h_layout.addWidget(self.btn_export)
        layout.addWidget(header)

        central_area = QWidget()
        c_layout = QHBoxLayout(central_area)
        
        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0,0,0,0)
        
        self.settings = SettingsPanel()
        self.timeline = TimelineEditor()
        
        self.settings.audio_selected.connect(self.set_audio)
        self.settings.font_selected.connect(self.set_custom_font)
        self.settings.background_selected.connect(self.set_background)
        self.timeline.lyrics_loaded.connect(self.set_lyrics) # CONECTADO A LA NUEVA MAGIA
        self.settings.styles_updated.connect(self._force_render_frame)

        lp_layout.addWidget(self.settings, stretch=1)
        lp_layout.addWidget(self.timeline, stretch=2)
        c_layout.addWidget(left_panel)
        c_layout.addWidget(self.gl_render, stretch=1)
        layout.addWidget(central_area, stretch=1)

        controls = QWidget()
        controls.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #333;")
        ctrl_layout = QHBoxLayout(controls)
        self.lbl_time = QLabel("00:00.00")
        self.lbl_time.setStyleSheet("font-family: monospace; color: #00ffff;")
        self.btn_play = QPushButton("PLAY")
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.seek_timeline)
        
        ctrl_layout.addWidget(self.lbl_time)
        ctrl_layout.addWidget(self.slider)
        ctrl_layout.addWidget(self.btn_play)
        layout.addWidget(controls)

        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)

    # ... (Manten metodos save_current_project, open_editor, set_audio, set_custom_font, set_background iguales) ...

    # ====================================================
    # FASE 6.2: ALGORITMO DE AUTO-SECCIONES Y AUTO-FINALES
    # ====================================================
    def set_lyrics(self, raw_segments):
        # 1. Ordenar por tiempo para asegurar la cronologia
        sorted_segs = sorted(raw_segments, key=lambda x: x.get("start", 0))
        
        current_section = "Verso"
        for i in range(len(sorted_segs)):
            seg = sorted_segs[i]
            
            # Herencia de Seccion: Si marca un cambio, actualizar el actual
            if seg.get("section_type") and seg.get("section_type") != "Ninguna":
                current_section = seg["section_type"]
            
            # Guardamos la seccion efectiva que rige esta linea
            seg["effective_section"] = current_section
            
            # Algoritmo Auto-End: El fin es el inicio del siguiente bloque
            if i < len(sorted_segs) - 1:
                seg["end"] = sorted_segs[i+1]["start"]
            else:
                # El ultimo bloque dura 5 segundos por defecto
                seg["end"] = seg["start"] + 5.0

        self.lyrics_segments = sorted_segs
        # Actualiza la UI para mostrar los nuevos tiempos calculados
        self.timeline.update_list_ui(self.lyrics_segments)
        self._force_render_frame()

    # ... (Metodos de Exportacion se mantienen, solo se envia section_styles) ...

    def start_export(self):
        if not self.current_audio_path: return
        if self.is_playing: self.toggle_play()

        self.btn_export.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        vfx_settings = {
            "scanlines": 1.0 if self.settings.chk_scanlines.isChecked() else 0.0,
            "glitch": 1.0 if self.settings.chk_chromatic.isChecked() else 0.0,
            "invert": 1.0 if self.settings.chk_invert.isChecked() else 0.0,
            "camera_enabled": self.settings.chk_camera.isChecked()
        }

        # Pasamos ademas el diccionario de estilos
        self.export_worker = ExportWorker(
            project_name=self.current_project_name,
            audio_path=self.current_audio_path,
            font_path=self.current_font_path,
            bg_path=self.current_bg_path,
            lyrics_segments=self.lyrics_segments,
            vfx_settings=vfx_settings,
            section_styles=self.settings.section_styles # NUEVO
        )

        self.export_worker.progress_updated.connect(self.update_export_progress)
        self.export_worker.finished_success.connect(self.export_success)
        self.export_worker.finished_error.connect(self.export_error)
        self.export_worker.start()

    # ... (Funciones de UI de exportacion y reproduccion igual) ...

    def game_loop(self, advance_time=True):
        if advance_time:
            self.current_time += 1.0 / 30.0
            if self.bg_is_video: self._read_video_frame(seek=False)
        
        bass, mid, high = self.mixer.get_reactivity(self.current_time)
        
        active_segment = None
        for seg in self.lyrics_segments:
            if seg["start"] - self.animator.transition_time <= self.current_time <= seg["end"] + self.animator.transition_time:
                active_segment = seg
                break
        
        if active_segment and active_segment.get("words"):
            try:
                # OBTENER ESTILO DE LA SECCION ACTIVA
                sec_name = active_segment.get("effective_section", "Verso")
                style = self.settings.section_styles.get(sec_name, {})
                
                # Anulacion dinamica del animador
                self.animator.anim_in = style.get("anim_in", "fade_in")
                self.animator.anim_active = style.get("anim_active", "scale_pop")
                self.animator.anim_out = style.get("anim_out", "fade_out")
                
                # Extraer Color y Fuente
                sec_font = style.get("font", "")
                final_font = sec_font if sec_font and os.path.exists(sec_font) else self.current_font_path
                color_hex = style.get("color", "#FFFFFF")

                anim_state = self.animator.process_segment(active_segment, self.current_time, bass, mid, high)
                
                # INYECTAMOS EL COLOR (Ver instruccion final)
                rgba_bytes = self.text_engine.render_animated_text_to_bytes(
                    words_state=anim_state, 
                    font_path=final_font,
                    base_font_size=100,
                    is_preview=self.is_playing,
                    color_hex=color_hex # PARAMETRO NUEVO
                )
                self.gl_render.update_text_texture(rgba_bytes, self.text_engine.width, self.text_engine.height)
            except Exception as e:
                print(f"Error render: {e}")
        else:
            self.gl_render.update_text_texture(b'\x00' * (1920 * 1080 * 4), 1920, 1080)

        self.gl_render.vfx["scanlines"] = 1.0 if self.settings.chk_scanlines.isChecked() else 0.0
        self.gl_render.vfx["glitch"] = 1.0 if self.settings.chk_chromatic.isChecked() else 0.0
        self.gl_render.vfx["invert"] = 1.0 if self.settings.chk_invert.isChecked() and bass > 0.8 else 0.0
        self.gl_render.camera_enabled = self.settings.chk_camera.isChecked()
        self.gl_render.time = self.current_time
        self.gl_render.bass = bass
        self.gl_render.update()
        
        if advance_time:
            self.slider.blockSignals(True)
            self.slider.setValue(int(self.current_time * 100))
            self.slider.blockSignals(False)
            self.lbl_time.setText(f"{int(self.current_time // 60):02d}:{self.current_time % 60:05.2f}")