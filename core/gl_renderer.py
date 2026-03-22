import moderngl
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
import numpy as np

class CanvasVideoRenderer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        
        self.pending_text_bytes = None
        self.pending_text_size = None
        self.pending_bg_bytes = None
        self.pending_bg_size = None
        
        self.time = 0.0
        self.bass = 0.0
        self.cam_zoom = 1.0
        self.cam_rotate = 0.0
        self.cam_offset = [0.0, 0.0]
        self.vfx = {"vhs": 0.0, "glitch": 0.0, "scanlines": 0.0, "invert": 0.0}
        self.use_bg = False
        
        # VARIABLE DE CONTROL DE CAMARA
        self.camera_enabled = False

    def initializeGL(self):
        self.ctx = moderngl.create_context()
        
        fragment_shader = """
            #version 330
            uniform float u_time;
            uniform float u_bass;
            uniform sampler2D u_text_tex;
            uniform sampler2D u_bg_tex;    
            uniform float u_use_bg;        
            
            uniform float u_cam_zoom;
            uniform float u_cam_rotate;
            uniform vec2 u_cam_offset;
            uniform float u_glitch;
            uniform float u_invert;
            uniform float u_scanlines;

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
                vec3 final_color = mix(bg_color, text_layer.rgb, text_layer.a);

                if (u_scanlines > 0.0) {
                    final_color *= (0.9 + 0.1 * sin(uv.y * 1080.0 + u_time * 10.0));
                }
                if (u_invert > 0.0) final_color = 1.0 - final_color;

                f_color = vec4(final_color, 1.0);
            }
        """
        
        vertex_shader = """
            #version 330
            in vec2 in_vert; out vec2 vUv;
            void main() { vUv = in_vert * 0.5 + 0.5; gl_Position = vec4(in_vert, 0.0, 1.0); }
        """

        self.prog = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        vertices = np.array([-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0], dtype='f4')
        self.vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, '2f', 'in_vert')])
        
        self.text_texture = self.ctx.texture((1920, 1080), 4)
        self.bg_texture = self.ctx.texture((1920, 1080), 3)

        self.render_tex = self.ctx.texture((1920, 1080), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.render_tex])

        screen_fs = """
            #version 330
            uniform sampler2D tex;
            in vec2 vUv; out vec4 f_color;
            void main() { 
                f_color = texture(tex, vec2(vUv.x, vUv.y)); 
            }
        """
        self.screen_prog = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=screen_fs)
        self.screen_vao = self.ctx.vertex_array(self.screen_prog, [(self.vbo, '2f', 'in_vert')])

    def update_text_texture(self, rgba_bytes, width, height):
        self.pending_text_bytes = rgba_bytes
        self.pending_text_size = (width, height)

    def update_bg_texture(self, frame_rgb):
        self.pending_bg_bytes = frame_rgb.tobytes()
        h, w, _ = frame_rgb.shape
        self.pending_bg_size = (w, h)
        self.use_bg = True

    def paintGL(self):
        default_fbo = self.ctx.detect_framebuffer()

        if self.pending_text_bytes is not None:
            w, h = self.pending_text_size
            if self.text_texture.size != (w, h):
                self.text_texture.release()
                self.text_texture = self.ctx.texture((w, h), 4)
            self.text_texture.write(self.pending_text_bytes)
            self.pending_text_bytes = None
            
        if self.pending_bg_bytes is not None:
            w, h = self.pending_bg_size
            if self.bg_texture.size != (w, h):
                self.bg_texture.release()
                self.bg_texture = self.ctx.texture((w, h), 3)
            self.bg_texture.write(self.pending_bg_bytes)
            self.pending_bg_bytes = None

        # CONDICION DE MOVIMIENTO DE CAMARA
        if self.camera_enabled:
            if self.bass > 0.8:
                self.cam_zoom = 1.0 + (self.bass * 0.1)
            else:
                self.cam_zoom = 1.0
            self.cam_offset = [np.sin(self.time) * 0.02, np.cos(self.time * 0.8) * 0.02]
        else:
            self.cam_zoom = 1.0
            self.cam_offset = [0.0, 0.0]

        self.fbo.use()
        self.fbo.clear(0.0, 0.0, 0.0, 1.0)

        self.prog['u_time'].value = self.time
        self.prog['u_bass'].value = self.bass
        self.prog['u_cam_zoom'].value = self.cam_zoom
        self.prog['u_cam_rotate'].value = self.cam_rotate
        self.prog['u_cam_offset'].value = tuple(self.cam_offset)
        self.prog['u_glitch'].value = self.vfx.get("glitch", 0.0)
        self.prog['u_invert'].value = self.vfx.get("invert", 0.0)
        self.prog['u_scanlines'].value = self.vfx.get("scanlines", 0.0)
        self.prog['u_use_bg'].value = 1.0 if self.use_bg else 0.0

        self.text_texture.use(location=0)
        self.prog['u_text_tex'].value = 0
        if self.use_bg:
            self.bg_texture.use(location=1)
            self.prog['u_bg_tex'].value = 1

        self.vao.render(moderngl.TRIANGLE_STRIP)

        default_fbo.use()
        default_fbo.clear(0.0, 0.0, 0.0, 1.0)
        self.render_tex.use(location=0)
        self.screen_prog['tex'].value = 0
        self.screen_vao.render(moderngl.TRIANGLE_STRIP)

    def read_pixels(self, width, height):
        raw = self.fbo.read(components=4, alignment=1)
        img_np = np.frombuffer(raw, dtype=np.uint8).reshape((1080, 1920, 4))
        img_flipped = np.flipud(img_np)
        return img_flipped.tobytes()