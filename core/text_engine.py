import os
from PIL import Image, ImageDraw, ImageFont

class TextEngine:
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height

    def render_text_to_bytes(self, text, font_path, font_size=80, text_color=(255, 255, 255, 255), glow_color=(0, 255, 255, 150)):
        """
        Genera una imagen transparente con texto y devuelve los bytes crudos (RGBA) 
        para inyectarlos como textura en ModernGL.
        """
        # 1. Crear un lienzo completamente transparente
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 2. Cargar la fuente. Si falla o no existe, usa la fuente por defecto.
        try:
            if os.path.exists(font_path):
                # Asegurar que el tamaño de fuente sea entero
                font = ImageFont.truetype(font_path, int(font_size))
            else:
                font = ImageFont.load_default()
        except Exception as e:
            print(f"Advertencia: No se pudo cargar la fuente {font_path}. Usando default. Error: {e}")
            font = ImageFont.load_default()

        # 3. Calcular las dimensiones del texto para centrarlo
        # getbbox / textbbox es el método moderno en Pillow para medir texto
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (self.width - text_w) / 2
        y = (self.height - text_h) / 2

        # 4. Dibujar la "sombra" o resplandor (Glow) desplazado
        glow_offset = max(2, int(font_size * 0.05)) # El offset escala con la fuente
        draw.text((x + glow_offset, y + glow_offset), text, font=font, fill=glow_color)
        
        # 5. Dibujar el texto principal encima
        draw.text((x, y), text, font=font, fill=text_color)

        # 6. Convertir a bytes para OpenGL
        return img.tobytes()