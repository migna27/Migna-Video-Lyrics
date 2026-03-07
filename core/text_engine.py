import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class TextEngine:
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height

    def render_animated_text_to_bytes(self, words_state, font_path, base_font_size=80):
        # Lienzo principal transparente
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        if not words_state:
            return img.tobytes()

        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype(font_path, int(base_font_size)) if os.path.exists(font_path) else ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # Medir estructura
        lines_info = {}
        for w in words_state:
            line = w["line"]
            full_text = w["text"]
            
            bbox = draw.textbbox((0, 0), full_text, font=font)
            w_width = bbox[2] - bbox[0]
            w_height = bbox[3] - bbox[1]
            
            if line not in lines_info:
                lines_info[line] = {"width": 0, "height": w_height, "words": []}
            
            space_width = draw.textbbox((0,0), " ", font=font)[2]
            lines_info[line]["width"] += w_width + space_width
            lines_info[line]["words"].append({"data": w, "w": w_width, "h": w_height})

        # Centrado Vertical Global
        total_height = sum(info["height"] for info in lines_info.values())
        current_y = (self.height - total_height) / 2

        # Dibujar
        for line_num in sorted(lines_info.keys()):
            line_data = lines_info[line_num]
            current_x = (self.width - line_data["width"]) / 2
            
            for word_obj in line_data["words"]:
                w_data = word_obj["data"]
                original_w = word_obj["w"]
                
                # Texto cortado por animaciones de Typewriter / Karaoke Sweep
                visible_text = w_data["text"][:w_data["chars_visible"]]
                if not visible_text:
                    current_x += original_w + space_width
                    continue

                # Preparar Fuente Escalada
                c_font = font
                if w_data["scale"] != 1.0:
                    try: c_font = ImageFont.truetype(font_path, int(base_font_size * max(0.1, w_data["scale"])))
                    except: pass

                # Posición Final
                final_x = int(current_x + w_data["offset_x"])
                final_y = int(current_y + w_data["offset_y"])

                # --- RENDER DE PALABRA CON ROTACIÓN Y EFECTOS ---
                # Para soportar rotaciones y blur sin dañar el layout general, 
                # dibujamos la palabra en un lienzo temporal pequeño.
                temp_size = (int(original_w * 2.5), int(word_obj["h"] * 2.5))
                temp_img = Image.new('RGBA', temp_size, (0, 0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                
                cx, cy = temp_size[0]//4, temp_size[1]//4
                glow_offset = max(2, int(base_font_size * 0.05))
                
                # 1. Rastro Fantasma (Ghost Trail)
                if w_data.get("ghost_trail"):
                    temp_draw.text((cx - 20, cy), visible_text, font=c_font, fill=(w_data["color"][0], w_data["color"][1], w_data["color"][2], int(w_data["color"][3] * 0.3)))
                    temp_draw.text((cx + 20, cy), visible_text, font=c_font, fill=(w_data["color"][0], w_data["color"][1], w_data["color"][2], int(w_data["color"][3] * 0.3)))

                # 2. Resplandor (Glow)
                temp_draw.text((cx + glow_offset, cy + glow_offset), visible_text, font=c_font, fill=w_data["glow_color"])
                
                # 3. Texto Principal
                temp_draw.text((cx, cy), visible_text, font=c_font, fill=w_data["color"])

                # 4. Blur Cinematico (Opcional)
                if w_data.get("glow_radius", 0) > 0:
                    temp_img = temp_img.filter(ImageFilter.GaussianBlur(w_data["glow_radius"]))

                # 5. Rotación
                if w_data["rotation"] != 0:
                    temp_img = temp_img.rotate(w_data["rotation"], resample=Image.BICUBIC, center=(cx + original_w//2, cy + word_obj["h"]//2))

                # Pegar el lienzo temporal en el principal
                img.alpha_composite(temp_img, (final_x - cx, final_y - cy))
                
                # Avanzar cursor en X
                current_x += original_w + space_width
            
            # Avanzar cursor en Y
            current_y += line_data["height"] + 15

        return img.tobytes()