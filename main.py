import sys
import os
import cv2
import json
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
        
        self.ensure_assets_exist()
        
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

    def ensure_assets_exist(self):
        os.makedirs("assets/fonts", exist_ok=True)
        anim_path = "assets/animations.json"
        if not os.path.exists(anim_path):
            default_anims = {
                "in": ["fade_in", "fade_up", "glitch_reveal", "elastic_pop", "blur_reveal", "typewriter", "zoom_basico", "rise_from_void"],
                "active": ["scale_pop", "super_glow", "karaoke_sweep", "jitter_nervioso", "color_overdrive", "invert_flash", "shake_glitch", "wave_bounce"],
                "out": ["fade_out", "fade_down", "fly_away", "system_failure", "blackout_cut", "zoom_out_collapse"]
            }
            with open(anim_path, "w", encoding="utf-8") as f:
                json.dump(default_anims, f, indent=4)

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
        self.current_project_name = None

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
        self.btn_save.setStyleSheet("background-color: #9333ea; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_save.clicked.connect(self.save_current_project)
        
        self.btn_export = QPushButton("EXPORTAR VIDEO")
        self.btn_export.setStyleSheet("background-color: #0088ff; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
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
        self.timeline.lyrics_loaded.connect(self.set_lyrics) 
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
        self.btn_play.setStyleSheet("background-color: white; color: black; padding: 5px 15px; font-weight: bold;")
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

    def save_current_project(self):
        if not self.current_project_name: return
        config = {
            "audio_path": self.current_audio_path,
            "audio_name": self.current_audio_name,
            "font_path": self.current_font_path,
            "bg_path": self.current_bg_path
        }
        self.pm.save_project(name=self.current_project_name, lyric_data={"segments": self.lyrics_segments}, config=config, event_blocks=[], custom_effects=[])
        print("Proyecto guardado exitosamente.")

    def open_editor(self, project_name):
        self.current_project_name = project_name
        self.lbl_title.setText(f"<b>MIGNA</b> / {project_name}")
        try:
            data = self.pm.load_project(project_name)
            lyric_data = data.get("lyricData", {}).get("segments", [])
            if lyric_data:
                self.set_lyrics(lyric_data)
            else:
                self.set_lyrics([])
            
            config = data.get("config", {})
            audio_path = config.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                self.set_audio(audio_path, config.get("audio_name", "Audio Guardado"))
            font_path = config.get("font_path")
            if font_path and os.path.exists(font_path):
                self.set_custom_font(font_path)
            bg_path = config.get("bg_path")
            if bg_path and os.path.exists(bg_path):
                self.set_background(bg_path)
        except Exception as e:
            self.lyrics_segments = []
            self.current_audio_path = None
            self.current_audio_name = None
            self.current_font_path = None
            self.current_bg_path = None
            self.timeline.update_list_ui([])
            
        self.stack.setCurrentWidget(self.editor_widget)

    def set_audio(self, filepath, filename):
        self.current_audio_path = filepath
        self.current_audio_name = filename
        self.mixer.layers = [] 
        self.mixer.add_layer(filepath, filename)
        duration_sec = self.mixer.master_duration
        self.slider.setRange(0, int(duration_sec * 100))
        self.settings.lbl_audio_status.setText(f"Audio listo: {filename}")
        self._force_render_frame()

    def set_custom_font(self, font_path):
        self.current_font_path = font_path
        self._force_render_frame()

    def set_background(self, filepath):
        self.current_bg_path = filepath
        self.settings.lbl_bg_status.setText(f"Fondo: {os.path.basename(filepath)}")
        ext = filepath.lower().split('.')[-1]
        if ext in ['mp4', 'webm', 'mov']:
            self.bg_is_video = True
            if self.bg_video_cap: self.bg_video_cap.release()
            self.bg_video_cap = cv2.VideoCapture(filepath)
            self._read_video_frame(seek=True)
        else:
            self.bg_is_video = False
            img = cv2.imread(filepath)
            if img is not None:
                frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.gl_render.update_bg_texture(frame_rgb)
                self._force_render_frame()

    def _read_video_frame(self, seek=False):
        if not self.bg_video_cap or not self.bg_video_cap.isOpened(): return
        if seek:
            fps = self.bg_video_cap.get(cv2.CAP_PROP_FPS) or 30
            target_frame = int(self.current_time * fps)
            self.bg_video_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
        ret, frame = self.bg_video_cap.read()
        if not ret:
            self.bg_video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.bg_video_cap.read()
            
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.gl_render.update_bg_texture(frame_rgb)

    def set_lyrics(self, raw_segments):
        sorted_segs = sorted(raw_segments, key=lambda x: x.get("start", 0))
        
        current_section = "verse" 
        for i in range(len(sorted_segs)):
            seg = sorted_segs[i]
            if "section" in seg and seg["section"]:
                current_section = seg["section"].lower()
            
            seg["effective_section"] = current_section
            
            if i < len(sorted_segs) - 1:
                seg["end"] = sorted_segs[i+1]["start"]
            else:
                if "end" not in seg or seg["end"] <= seg["start"]:
                    seg["end"] = seg["start"] + 5.0

        self.lyrics_segments = sorted_segs
        self.timeline.update_list_ui(self.lyrics_segments)
        self._force_render_frame()

    def start_export(self):
        if not self.current_audio_path:
            QMessageBox.warning(self, "Atencion", "Necesitas cargar un audio antes de exportar.")
            return
            
        if self.is_playing: self.toggle_play()

        self.btn_export.setEnabled(False)
        self.btn_export.setText("EXPORTANDO...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        vfx_settings = {
            "scanlines": 1.0 if self.settings.chk_scanlines.isChecked() else 0.0,
            "glitch": 1.0 if self.settings.chk_chromatic.isChecked() else 0.0,
            "invert": 1.0 if self.settings.chk_invert.isChecked() else 0.0,
            "vignette": 1.0 if self.settings.chk_vignette.isChecked() else 0.0,
            "grain": 1.0 if self.settings.chk_grain.isChecked() else 0.0,
            "camera_enabled": self.settings.chk_camera.isChecked()
        }

        self.export_worker = ExportWorker(
            project_name=self.current_project_name,
            audio_path=self.current_audio_path,
            font_path=self.current_font_path,
            bg_path=self.current_bg_path,
            lyrics_segments=self.lyrics_segments,
            vfx_settings=vfx_settings,
            section_styles=self.settings.section_styles
        )

        self.export_worker.progress_updated.connect(self.update_export_progress)
        self.export_worker.finished_success.connect(self.export_success)
        self.export_worker.finished_error.connect(self.export_error)
        self.export_worker.start()

    def update_export_progress(self, frame_actual, total_frames):
        porcentaje = int((frame_actual / total_frames) * 100)
        self.progress_bar.setValue(porcentaje)

    def export_success(self, output_file):
        self.restore_export_ui()
        QMessageBox.information(self, "Exito", f"Exportacion completada.\nArchivo guardado como:\n{output_file}")

    def export_error(self, error_msg):
        self.restore_export_ui()
        QMessageBox.critical(self, "Error de Exportacion", f"Ha ocurrido un error:\n{error_msg}")

    def restore_export_ui(self):
        self.progress_bar.hide()
        self.btn_export.setEnabled(True)
        self.btn_export.setText("EXPORTAR VIDEO")
        self.export_worker = None

    def toggle_play(self):
        if not self.mixer.layers: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start(33) 
            self.btn_play.setText("PAUSE")
            layer = self.mixer.layers[0]
            start_frame = int(self.current_time * layer.sr)
            audio_data = layer.data.T if layer.data.ndim > 1 else layer.data
            sd.play(audio_data[start_frame:], layer.sr)
        else:
            self.timer.stop()
            self.btn_play.setText("PLAY")
            sd.stop()

    def seek_timeline(self, value):
        self.current_time = value / 100.0
        if self.is_playing:
            sd.stop()
            layer = self.mixer.layers[0]
            start_frame = int(self.current_time * layer.sr)
            audio_data = layer.data.T if layer.data.ndim > 1 else layer.data
            sd.play(audio_data[start_frame:], layer.sr)
        self._read_video_frame(seek=True)
        self._force_render_frame()

    def _force_render_frame(self):
        self.game_loop(advance_time=False)

    def game_loop(self, advance_time=True):
        if advance_time:
            self.current_time += 1.0 / 30.0
            if self.mixer.master_duration > 0 and self.current_time >= self.mixer.master_duration:
                self.current_time = 0
                self.toggle_play()
            if self.bg_is_video: self._read_video_frame(seek=False)
        
        bass, mid, high = self.mixer.get_reactivity(self.current_time)
        
        active_segment = None
        for seg in self.lyrics_segments:
            if seg["start"] - self.animator.transition_time <= self.current_time <= seg["end"] + self.animator.transition_time:
                active_segment = seg
                break
        
        if active_segment and active_segment.get("words"):
            try:
                sec_name = active_segment.get("effective_section", "verse")
                style = self.settings.section_styles.get(sec_name, {})
                
                self.animator.anim_in = style.get("anim_in", "fade_in")
                self.animator.anim_active = style.get("anim_active", "scale_pop")
                self.animator.anim_out = style.get("anim_out", "fade_out")
                
                out_mode_str = style.get("out_mode", "Simultaneo")
                out_mode = "simultaneous" if "Simultaneo" in out_mode_str else "sequential"
                
                sec_font = style.get("font", "")
                final_font = sec_font if sec_font and os.path.exists(sec_font) else self.current_font_path
                
                # LEEMOS LOS DOS COLORES Y LA ESCALA DESDE LA UI
                color_inactive = style.get("color", "#FFFFFF")
                color_active = style.get("color_active", "#00FFFF")
                scale_factor = style.get("scale", 1.0)
                
                # LA ESCALA AFECTA EL TAMAÑO BASE DE PILLOW
                base_size = int(100 * scale_factor)

                anim_state = self.animator.process_segment(
                    active_segment, self.current_time, bass, mid, high, out_mode, color_inactive, color_active
                )
                
                rgba_bytes = self.text_engine.render_animated_text_to_bytes(
                    words_state=anim_state, 
                    font_path=final_font,
                    base_font_size=base_size,
                    is_preview=self.is_playing
                )
                self.gl_render.update_text_texture(rgba_bytes, self.text_engine.width, self.text_engine.height)
            except Exception as e:
                print(f"Error render: {e}")
        else:
            self.gl_render.update_text_texture(b'\x00' * (1920 * 1080 * 4), 1920, 1080)

        self.gl_render.vfx["scanlines"] = 1.0 if self.settings.chk_scanlines.isChecked() else 0.0
        self.gl_render.vfx["glitch"] = 1.0 if self.settings.chk_chromatic.isChecked() else 0.0
        self.gl_render.vfx["invert"] = 1.0 if self.settings.chk_invert.isChecked() and bass > 0.8 else 0.0
        self.gl_render.vfx["vignette"] = 1.0 if self.settings.chk_vignette.isChecked() else 0.0
        self.gl_render.vfx["grain"] = 1.0 if self.settings.chk_grain.isChecked() else 0.0
        self.gl_render.camera_enabled = self.settings.chk_camera.isChecked()
        self.gl_render.time = self.current_time
        self.gl_render.bass = bass
        self.gl_render.update()
        
        if advance_time:
            self.slider.blockSignals(True)
            self.slider.setValue(int(self.current_time * 100))
            self.slider.blockSignals(False)
            self.lbl_time.setText(f"{int(self.current_time // 60):02d}:{self.current_time % 60:05.2f}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, Qt.GlobalColor.black)
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, Qt.GlobalColor.black)
    app.setPalette(palette)
    window = MignaDesktopApp()
    window.show()
    sys.exit(app.exec())