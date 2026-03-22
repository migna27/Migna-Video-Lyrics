import os
import cv2
import numpy as np
import moderngl
import threading
import concurrent.futures
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

from core.audio_mixer import AudioMixer
from core.text_engine import TextEngine
from core.lyric_animator import LyricAnimator
from core.video_exporter import VideoExporter

class ExportWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    finished_success = pyqtSignal(str)
    finished_error = pyqtSignal(str)

    def __init__(self, project_name, audio_path, font_path, bg_path, lyrics_segments, vfx_settings, section_styles, fps=30):
        super().__init__()
        self.project_name = project_name
        self.audio_path = audio_path
        self.font_path = font_path
        self.bg_path = bg_path
        self.lyrics_segments = lyrics_segments
        self.vfx_settings = vfx_settings
        self.section_styles = section_styles 
        self.fps = fps
        self.is_running = True
        
        self.lock = threading.Lock()
        self.rendered_frames = 0
        self.total_frames = 0
        self.shared_mixer = None
        self.bg_frame_rgb = None

    def run(self):
        try:
            self.shared_mixer = AudioMixer(fps=self.fps)
            if self.audio_path:
                self.shared_mixer.add_layer(self.audio_path, "audio_export")
            
            self.total_frames = int(self.shared_mixer.master_duration * self.fps)
            if self.total_frames <= 0:
                raise ValueError("El audio no tiene una duracion valida.")

            bg_is_video = False
            if self.bg_path and os.path.exists(self.bg_path):
                ext = self.bg_path.lower().split('.')[-1]
                if ext in ['mp4', 'webm', 'mov']:
                    bg_is_video = True
                else:
                    img = cv2.imread(self.bg_path)
                    if img is not None:
                        self.bg_frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            cores = os.cpu_count() or 4
            cores = max(1, cores - 1)
            if self.total_frames < cores * 30: cores = 1

            frames_per_chunk = self.total_frames // cores
            futures = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
                for i in range(cores):
                    start_f = i * frames_per_chunk
                    end_f = self.total_frames if i == cores - 1 else (i + 1) * frames_per_chunk
                    temp_file = f"temp_chunk_{i}.mp4"
                    futures.append(executor.submit(self._render_chunk, i, start_f, end_f, temp_file, bg_is_video))

            for f in futures: f.result() 

            if not self.is_running:
                self._cleanup_temp_files(cores)
                self.finished_error.emit("Exportacion cancelada por el usuario.")
                return

            self._concatenate_chunks(cores)

        except Exception as e:
            self.finished_error.emit(str(e))

    def _render_chunk(self, chunk_id, start_frame, end_frame, temp_file, bg_is_video):
        ctx = moderngl.create_context(standalone=True)
        text_engine = TextEngine(width=1920, height=1080)
        animator = LyricAnimator()

        # REPLICA EXACTA DEL RENDERIZADOR DE PREVIEW PARA LA EXPORTACION FINAL (GLOW INCORPORADO)
        vertex_shader = """
            #version 330
            in vec2 in_vert; out vec2 vUv;
            void main() { vUv = in_vert * 0.5 + 0.5; gl_Position = vec4(in_vert, 0.0, 1.0); }
        """
        fragment_shader = """
            #version 330
            uniform float u_time;
            uniform float u_bass;
            uniform sampler2D u_text_tex;
            uniform sampler2D u_bg_tex;    
            uniform float u_use_bg;        
            
            // Post-procesado (Bloom)
            uniform sampler2D u_blur_tex_5;
            uniform float u_bloom_intensity;
            
            uniform float u_cam_zoom;
            uniform float u_cam_rotate;
            uniform vec2 u_cam_offset;
            uniform float u_glitch;
            uniform float u_invert;
            uniform float u_scanlines;
            uniform float u_vignette;
            uniform float u_grain;

            in vec2 vUv;
            out vec4 f_color;

            vec2 rotateUV(vec2 uv, float rotation, vec2 mid) {
                return vec2(
                    cos(rotation) * (uv.x - mid.x) + sin(rotation) * (uv.y - mid.y) + mid.x,
                    cos(rotation) * (uv.y - mid.y) - sin(rotation) * (uv.x - mid.x) + mid.y
                );
            }

            void main() {
                vec2 uv = vUv - u_cam_offset;
                uv = rotateUV(uv, u_cam_rotate, vec2(0.5));
                uv = (uv - 0.5) / u_cam_zoom + 0.5;

                if (u_glitch > 0.0 && u_bass > 0.7) {
                    uv.x += sin(uv.y * 50.0 + u_time * 20.0) * 0.02;
                }

                vec3 bg_color;
                if (u_use_bg > 0.5) {
                    bg_color = texture(u_bg_tex, vec2(uv.x, 1.0 - uv.y)).rgb;
                } else {
                    bg_color = vec3(0.05, 0.05, 0.08);
                    bg_color.r += sin(uv.x * 10.0 + u_time) * 0.05 * u_bass;
                }

                vec4 text_layer = texture(u_text_tex, vec2(uv.x, 1.0 - uv.y));
                vec3 blur_layer = texture(u_blur_tex_5, vec2(uv.x, 1.0 - uv.y)).rgb;

                vec3 final_color = mix(bg_color, text_layer.rgb, text_layer.a);
                final_color += blur_layer * text_layer.a * u_bloom_intensity;

                if (u_scanlines > 0.0) {
                    final_color *= (0.9 + 0.1 * sin(uv.y * 1080.0 + u_time * 10.0));
                }
                if (u_vignette > 0.0) {
                    float dist = distance(vUv, vec2(0.5));
                    final_color *= smoothstep(0.8, 0.2, dist * u_vignette);
                }
                if (u_grain > 0.0) {
                    float noise = fract(sin(dot(vUv * u_time, vec2(12.9898, 78.233))) * 43758.5453);
                    final_color += (noise - 0.5) * 0.1 * u_grain;
                }
                if (u_invert > 0.0) final_color = 1.0 - final_color;

                f_color = vec4(final_color, 1.0);
            }
        """
        gaussian_shader = """
            #version 330
            uniform sampler2D tex;
            uniform bool horizontal;
            uniform float u_spread;
            uniform float u_weight[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
            in vec2 vUv; out vec4 f_color;
            void main() {
                vec2 tex_offset = u_spread / textureSize(tex, 0); 
                vec3 result = texture(tex, vUv).rgb * u_weight[0]; 
                if(horizontal) {
                    for(int i = 1; i < 5; ++i) {
                        result += texture(tex, vUv + vec2(tex_offset.x * i, 0.0)).rgb * u_weight[i];
                        result += texture(tex, vUv - vec2(tex_offset.x * i, 0.0)).rgb * u_weight[i];
                    }
                } else {
                    for(int i = 1; i < 5; ++i) {
                        result += texture(tex, vUv + vec2(0.0, tex_offset.y * i)).rgb * u_weight[i];
                        result += texture(tex, vUv - vec2(0.0, tex_offset.y * i)).rgb * u_weight[i];
                    }
                }
                f_color = vec4(result, 1.0);
            }
        """

        prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        blur_prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=gaussian_shader)
        
        vertices = np.array([-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0], dtype='f4')
        vbo = ctx.buffer(vertices)
        vao = ctx.vertex_array(prog, [(vbo, '2f', 'in_vert')])
        blur_vao = ctx.vertex_array(blur_prog, [(vbo, '2f', 'in_vert')])
        
        text_texture = ctx.texture((1920, 1080), 4)
        bg_texture = ctx.texture((1920, 1080), 3) 
        
        fbo_ping = ctx.framebuffer(color_attachments=[ctx.texture((1920, 1080), 3)])
        fbo_pong = ctx.framebuffer(color_attachments=[ctx.texture((1920, 1080), 3)])

        exporter = VideoExporter(width=1920, height=1080, fps=self.fps)
        exporter.start_export(temp_file, is_alpha=False, audio_path=None)

        bg_cap = None
        if bg_is_video:
            bg_cap = cv2.VideoCapture(self.bg_path)
            total_bg_frames = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame % total_bg_frames)

        for frame_idx in range(start_frame, end_frame):
            if not self.is_running:
                break
            
            current_time = frame_idx / float(self.fps)
            use_bg = False

            if bg_is_video and bg_cap:
                ret, frame = bg_cap.read()
                if not ret:
                    bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = bg_cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, _ = frame_rgb.shape
                    if bg_texture.size != (w, h):
                        bg_texture.release()
                        bg_texture = ctx.texture((w, h), 3)
                    bg_texture.write(frame_rgb.tobytes())
                    use_bg = True
            elif self.bg_frame_rgb is not None:
                h, w, _ = self.bg_frame_rgb.shape
                if bg_texture.size != (w, h):
                    bg_texture.release()
                    bg_texture = ctx.texture((w, h), 3)
                bg_texture.write(self.bg_frame_rgb.tobytes())
                use_bg = True

            bass, mid, high = self.shared_mixer.get_reactivity(current_time)
            
            active_segment = None
            for seg in self.lyrics_segments:
                if seg.get("start", 0) - animator.transition_time <= current_time <= seg.get("end", 0) + animator.transition_time:
                    active_segment = seg
                    break
            
            if active_segment and active_segment.get("words"):
                sec_name = active_segment.get("effective_section", "verse")
                style = self.section_styles.get(sec_name, {})
                
                animator.anim_in = style.get("anim_in", "fade_in")
                animator.anim_active = style.get("anim_active", "scale_pop")
                animator.anim_out = style.get("anim_out", "fade_out")
                
                out_mode_str = style.get("out_mode", "Simultaneo")
                out_mode = "simultaneous" if "Simultaneo" in out_mode_str else "sequential"
                
                sec_font = style.get("font", "")
                final_font = sec_font if sec_font and os.path.exists(sec_font) else self.font_path
                
                color_inactive = style.get("color", "#FFFFFF")
                color_active = style.get("color_active", "#00FFFF")
                scale_factor = style.get("scale", 1.0)
                base_size = int(100 * scale_factor)

                anim_state = animator.process_segment(
                    active_segment, current_time, bass, mid, high, out_mode, color_inactive, color_active
                )
                
                rgba_bytes = text_engine.render_animated_text_to_bytes(
                    words_state=anim_state, 
                    font_path=final_font, 
                    base_font_size=base_size, 
                    is_preview=False
                )
                text_texture.write(rgba_bytes)
            else:
                text_texture.write(b'\x00' * (1920 * 1080 * 4))

            if self.vfx_settings.get("camera_enabled", False):
                cam_zoom = 1.0 + (bass * 0.1) if bass > 0.8 else 1.0
                cam_offset = [np.sin(current_time) * 0.02, np.cos(current_time * 0.8) * 0.02]
            else:
                cam_zoom = 1.0
                cam_offset = [0.0, 0.0]

            # PASO 1 BLOOM
            ctx.disable(moderngl.BLEND)
            blur_prog['tex'].value = 0
            
            fbo_ping.use()
            fbo_ping.clear(0, 0, 0, 0)
            text_texture.use(location=0)
            blur_prog['horizontal'].value = True
            blur_prog['u_spread'].value = 2.0
            blur_vao.render(moderngl.TRIANGLE_STRIP)
            
            fbo_pong.use()
            fbo_pong.clear(0, 0, 0, 0)
            fbo_ping.color_attachments[0].use(location=0)
            blur_prog['horizontal'].value = False
            blur_vao.render(moderngl.TRIANGLE_STRIP)

            # PASO 2 COMPOSICION
            fbo_ping.use() 
            fbo_ping.clear(0.0, 0.0, 0.0, 1.0) 

            prog['u_time'].value = current_time
            prog['u_bass'].value = bass
            prog['u_cam_zoom'].value = cam_zoom
            prog['u_cam_rotate'].value = 0.0
            prog['u_cam_offset'].value = tuple(cam_offset)
            prog['u_glitch'].value = self.vfx_settings.get("glitch", 0.0)
            prog['u_invert'].value = self.vfx_settings.get("invert", 0.0)
            prog['u_scanlines'].value = self.vfx_settings.get("scanlines", 0.0)
            prog['u_vignette'].value = self.vfx_settings.get("vignette", 0.0)
            prog['u_grain'].value = self.vfx_settings.get("grain", 0.0)
            prog['u_use_bg'].value = 1.0 if use_bg else 0.0
            prog['u_bloom_intensity'].value = 1.2 + (bass * 2.0) 

            text_texture.use(location=0)
            prog['u_text_tex'].value = 0
            if use_bg:
                bg_texture.use(location=1)
                prog['u_bg_tex'].value = 1
            
            fbo_pong.color_attachments[0].use(location=2)
            prog['u_blur_tex_5'].value = 2

            vao.render(moderngl.TRIANGLE_STRIP)
            ctx.finish()

            raw = fbo_ping.read(components=4, alignment=1)
            img_flipped = np.flipud(np.frombuffer(raw, dtype=np.uint8).reshape((1080, 1920, 4)))
            exporter.add_frame(img_flipped.tobytes())

            with self.lock:
                self.rendered_frames += 1
                if self.rendered_frames % 10 == 0:
                    self.progress_updated.emit(self.rendered_frames, self.total_frames)

        exporter.finish_export()
        if bg_cap:
            bg_cap.release()
        ctx.release()

    def _concatenate_chunks(self, cores):
        txt_path = "chunks.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for i in range(cores):
                f.write(f"file 'temp_chunk_{i}.mp4'\n")

        output_file = f"{self.project_name or 'proyecto'}_render.mp4"

        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', txt_path,
            '-i', self.audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_file
        ]
        
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self._cleanup_temp_files(cores)
        if os.path.exists(txt_path):
            os.remove(txt_path)
        
        self.finished_success.emit(output_file)

    def _cleanup_temp_files(self, cores):
        for i in range(cores):
            try:
                os.remove(f"temp_chunk_{i}.mp4")
            except:
                pass

    def stop(self):
        self.is_running = False