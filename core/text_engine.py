import os
from PIL import Image, ImageDraw, ImageFont

class TextEngine:
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self._font_cache = {} 

    def _get_font(self, font_path, size):
        key = (font_path, size)
        if key not in self._font_cache:
            try:
                if os.path.exists(font_path):
                    self._font_cache[key] = ImageFont.truetype(font_path, size)
                else:
                    self._font_cache[key] = ImageFont.load_default()
            except:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def render_animated_text_to_bytes(self, words_state, font_path, base_font_size=80, is_preview=False):
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        if not words_state:
            return img.tobytes()

        draw = ImageDraw.Draw(img)
        font = self._get_font(font_path, int(base_font_size))

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

        total_height = sum(info["height"] for info in lines_info.values())
        current_y = (self.height - total_height) / 2

        for line_num in sorted(lines_info.keys()):
            line_data = lines_info[line_num]
            current_x = (self.width - line_data["width"]) / 2
            
            for word_obj in line_data["words"]:
                w_data = word_obj["data"]
                
                visible_text = w_data["text"][:w_data["chars_visible"]]
                if not visible_text:
                    current_x += word_obj["w"] + space_width
                    continue

                final_x = int(current_x)
                final_y = int(current_y)

                # Tomamos la tupla de color EXACTA que envia el Animator
                custom_color = tuple(w_data["color"])
                
                draw.text((final_x, final_y), visible_text, font=font, fill=custom_color)

                current_x += word_obj["w"] + space_width
            
            current_y += line_data["height"] + 15

        return img.tobytes()