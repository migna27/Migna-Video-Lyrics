import subprocess

class VideoExporter:
    def __init__(self, width=1920, height=1080, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.process = None

    def start_export(self, output_path, is_alpha=False, audio_path=None):
        """Inicia FFmpeg. Si se provee audio_path, lo mezcla con el video."""
        
        # 1. Entrada de video (desde los bytes de Python)
        command = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'rgba',
            '-r', str(self.fps),
            '-i', '-'  # Input 0: stdin
        ]

        # 2. Entrada de audio (archivo original)
        if audio_path:
            command.extend(['-i', audio_path]) # Input 1: archivo de audio

        # 3. Configuración de Códecs
        if is_alpha:
            command.extend(['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0'])
            if audio_path:
                command.extend(['-c:a', 'libopus']) # Audio webm
        else:
            command.extend(['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'fast', '-crf', '18'])
            if audio_path:
                command.extend(['-c:a', 'aac', '-b:a', '192k']) # Audio estándar MP4

        # 4. Mapeo para unir Video y Audio y cortar cuando acabe la música
        if audio_path:
            command.extend(['-map', '0:v:0', '-map', '1:a:0', '-shortest'])

        command.append(output_path)

        # Iniciar proceso silenciando la salida gigante de FFmpeg
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def add_frame(self, rgba_bytes):
        if self.process:
            self.process.stdin.write(rgba_bytes)

    def finish_export(self):
        if self.process:
            self.process.stdin.close()
            self.process.wait()
            print("🎬 Exportación de video y audio completada.")