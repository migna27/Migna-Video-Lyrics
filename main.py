import sys
import os
import cv2
import numpy as np
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer

from core.audio_mixer import AudioMixer
from core.gl_renderer import CanvasVideoRenderer
from core.project_manager import ProjectManager
from core.text_engine import TextEngine
from core.video_exporter import VideoExporter

from gui.launcher import LauncherWidget
from gui.timeline import TimelineEditor
from gui.settings import SettingsPanel

class MignaDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AppMigna - Creative Visual Suite")
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

    def setup_editor_ui(self):
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Core
        self.mixer = AudioMixer(fps=30)
        self.gl_render = CanvasVideoRenderer()
        self.text_engine = TextEngine(width=1920, height=1080)
        
        self.current_time = 0.0
        self.is_playing = False
        self.lyrics_segments = []
        self.bg_video_cap = None
        self.bg_is_video = False

        # --- VARIABLES DE PERSISTENCIA (Rutas de archivos) ---
        self.current_audio_path = None
        self.current_audio_name = None
        self.current_font_path = None
        self.current_bg_path = None

        # --- TOP HEADER ---
        header = QWidget()
        header.setStyleSheet("background-color: #111; border-bottom: 1px solid #333;")
        h_layout = QHBoxLayout(header)
        
        btn_home = QPushButton("🏠")
        btn_home.setFixedSize(30, 30)
        btn_home.clicked.connect(lambda: self.stack.setCurrentWidget(self.launcher))
        
        self.lbl_title = QLabel("<b>MIGNA</b> / Untitled", styleSheet="color: #0ff; font-size: 14px;")
        
        # BOTÓN DE GUARDAR PROYECTO
        btn_save = QPushButton("💾 GUARDAR")
        btn_save.setStyleSheet("background-color: #9333ea; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        btn_save.clicked.connect(self.save_current_project)

        btn_export = QPushButton("🎬 EXPORTAR VIDEO")
        btn_export.setStyleSheet("background-color: #0088ff; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        btn_export.clicked.connect(self.start_export)
        
        h_layout.addWidget(btn_home)
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()
        h_layout.addWidget(btn_save)
        h_layout.addWidget(btn_export)
        layout.addWidget(header)

        # --- ÁREA CENTRAL ---
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

        lp_layout.addWidget(self.settings, stretch=1)
        lp_layout.addWidget(self.timeline, stretch=2)
        c_layout.addWidget(left_panel)
        c_layout.addWidget(self.gl_render, stretch=1)
        layout.addWidget(central_area, stretch=1)

        # --- CONTROLES ---
        controls = QWidget()
        controls.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #333;")
        ctrl_layout = QHBoxLayout(controls)
        self.lbl_time = QLabel("00:00.00")
        self.lbl_time.setStyleSheet("font-family: monospace; color: #00ffff;")
        self.btn_play = QPushButton("▶ PLAY")
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

    # ==========================================
    # LÓGICA DE GUARDADO Y CARGA DE PROYECTOS
    # ==========================================
    def save_current_project(self):
        if not self.current_project_name: return
        
        # Armar la configuración con las rutas actuales
        config = {
            "audio_path": self.current_audio_path,
            "audio_name": self.current_audio_name,
            "font_path": self.current_font_path,
            "bg_path": self.current_bg_path
        }
        
        # Guardar en el JSON usando nuestro ProjectManager
        self.pm.save_project(
            name=self.current_project_name, 
            lyric_data={"segments": self.lyrics_segments}, 
            config=config, 
            event_blocks=[], 
            custom_effects=[]
        )
        print("💾 Proyecto guardado exitosamente.")

    def open_editor(self, project_name):
        self.current_project_name = project_name
        self.lbl_title.setText(f"<b>MIGNA</b> / {project_name}")
        
        try:
            data = self.pm.load_project(project_name)
            print(f"📂 Cargando proyecto: {project_name}")
            
            # 1. Cargar Letras
            lyric_data = data.get("lyricData", {}).get("segments", [])
            if lyric_data:
                self.set_lyrics(lyric_data)
                self.timeline.list_segments.clear()
                for seg in lyric_data:
                    self.timeline.list_segments.addItem(f"[{seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s] {seg.get('text', '')}")
            
            # 2. Cargar Medios Automáticamente
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
            print(f"✨ Iniciando proyecto nuevo: {project_name}")
            # Resetear todo si es nuevo
            self.lyrics_segments = []
            self.current_audio_path = None
            self.current_audio_name = None
            self.current_font_path = None
            self.current_bg_path = None
            self.timeline.list_segments.clear()

        self.stack.setCurrentWidget(self.editor_widget)

    # ==========================================
    # MÉTODOS DE MANEJO DE ARCHIVOS
    # ==========================================
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
        self.settings.lbl_font_status.setText(f"Fuente: {os.path.basename(font_path)}")
        self._force_render_frame()

    def set_lyrics(self, segments):
        self.lyrics_segments = segments
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

    # ==========================================
    # LÓGICA DE EXPORTACIÓN Y REPRODUCCIÓN
    # ==========================================
    def start_export(self):
        if not self.mixer.layers:
            print("⚠️ Necesitas cargar un audio antes de exportar.")
            return

        self.is_playing = False
        self.timer.stop()
        self.btn_play.setText("▶ PLAY")
        sd.stop()

        output_file = f"{self.current_project_name or 'proyecto'}_render.mp4"
        print(f"🎬 Iniciando exportación: {output_file}...")
        
        audio_path = self.mixer.layers[0].file_path
        exporter = VideoExporter(width=1920, height=1080, fps=30)
        exporter.start_export(output_file, is_alpha=False, audio_path=audio_path)

        total_frames = int(self.mixer.master_duration * 30)
        
        for frame_idx in range(total_frames):
            self.current_time = frame_idx / 30.0
            
            self._force_render_frame() 
            self.gl_render.makeCurrent()
            self.gl_render.paintGL()
            self.gl_render.ctx.finish()
            
            rgba_bytes = self.gl_render.read_pixels(1920, 1080)
            exporter.add_frame(rgba_bytes)
            
            if frame_idx % 30 == 0:
                print(f"⏳ Renderizando... {(frame_idx/total_frames)*100:.1f}%")
                QApplication.processEvents() 

        exporter.finish_export()
        print(f"✅ Exportación exitosa. Archivo guardado como: {output_file}")
        self.current_time = 0.0
        self._force_render_frame()

    def toggle_play(self):
        if not self.mixer.layers: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            # CAMBIO AQUÍ: start(0) le dice a PyQt que renderice sin límite de velocidad
            self.timer.start(0) 
            self.btn_play.setText("⏸ PAUSE")
            
            layer = self.mixer.layers[0]
            start_frame = int(self.current_time * layer.sr)
            audio_data = layer.data.T if layer.data.ndim > 1 else layer.data
            sd.play(audio_data[start_frame:], layer.sr)
        else:
            self.timer.stop()
            self.btn_play.setText("▶ PLAY")
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
            if self.bg_is_video:
                self._read_video_frame(seek=False)
        
        bass, mid, high = self.mixer.get_reactivity(self.current_time)
        
        current_text = ""
        for seg in self.lyrics_segments:
            if seg["start"] <= self.current_time <= seg["end"]:
                current_text = seg["text"]
                break
        
        if current_text:
            try:
                rgba_bytes = self.text_engine.render_text_to_bytes(
                    text=current_text, font_path=self.current_font_path,
                    font_size=120 + int(bass * 20),
                    glow_color=(0, 255, 255, int(bass * 255))
                )
                self.gl_render.update_text_texture(rgba_bytes, self.text_engine.width, self.text_engine.height)
            except: pass
        else:
            empty_bytes = b'\x00' * (1920 * 1080 * 4)
            self.gl_render.update_text_texture(empty_bytes, 1920, 1080)

        self.gl_render.vfx["scanlines"] = 1.0 if self.settings.chk_scanlines.isChecked() else 0.0
        self.gl_render.vfx["glitch"] = 1.0 if self.settings.chk_chromatic.isChecked() else 0.0
        self.gl_render.vfx["invert"] = 1.0 if self.settings.chk_invert.isChecked() and bass > 0.8 else 0.0
        
        self.gl_render.time = self.current_time
        self.gl_render.bass = bass
        self.gl_render.update()
        
        if advance_time:
            self.slider.blockSignals(True)
            self.slider.setValue(int(self.current_time * 100))
            self.slider.blockSignals(False)
            mins = int(self.current_time // 60)
            secs = self.current_time % 60
            self.lbl_time.setText(f"{mins:02d}:{secs:05.2f}")

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