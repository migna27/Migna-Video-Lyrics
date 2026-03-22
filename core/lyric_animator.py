import math
import random
import colorsys

class LyricAnimator:
    def __init__(self):
        self.anim_in = "fade_in"      
        self.anim_out = "fade_out"    
        self.anim_active = "scale_pop"      
        self.transition_time = 0.4 

    def _hex_to_rgb(self, hex_str):
        hex_c = hex_str.lstrip('#')
        if len(hex_c) == 6:
            return tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255)

    def process_segment(self, segment, current_time, bass, mid, high, out_mode="simultaneous", color_inactive="#FFFFFF", color_active="#00FFFF"):
        words_state = []
        words = segment.get("words", [])
        seg_end = segment["end"]
        
        in_r, in_g, in_b = self._hex_to_rgb(color_inactive)
        act_r, act_g, act_b = self._hex_to_rgb(color_active)
        
        for i, w in enumerate(words):
            w_start = w["start"]
            w_end = w["end"]
            
            w_in_start = w_start - self.transition_time

            if current_time < w_start:
                phase = "IN"
                prog = max(0.0, min(1.0, (current_time - w_in_start) / self.transition_time))
            elif current_time <= w_end:
                phase = "ACTIVE"
                prog = (current_time - w_start) / max(0.001, w_end - w_start)
            else:
                phase = "OUT"
                if out_mode == "simultaneous":
                    out_start = seg_end - self.transition_time
                    prog = max(0.0, min(1.0, (current_time - out_start) / self.transition_time))
                    if current_time < out_start:
                        phase = "WAITING_OUT"
                else:
                    prog = max(0.0, min(1.0, (current_time - w_end) / self.transition_time))

            alpha = 255
            scale = 1.0
            off_x = 0.0
            off_y = 0.0
            rot = 0.0
            chars_vis = len(w["word"])
            glow_r = 0 
            color_override = None
            glow_override = None
            ghost = False

            if phase == "IN":
                if self.anim_in == "fade_in":
                    alpha = int(prog * 255)
                elif self.anim_in == "fade_up":
                    alpha = int(prog * 255)
                    off_y = (1.0 - prog) * 50
                elif self.anim_in == "glitch_reveal":
                    alpha = 255 if random.random() < prog else 50
                    if prog < 0.8: off_x = random.randint(-20, 20)
                elif self.anim_in == "elastic_pop": 
                    alpha = int(prog * 255)
                    scale = 1.0 + math.sin(prog * math.pi * 2.5) * (1.0 - prog) * 0.5
                elif self.anim_in == "blur_reveal":
                    alpha = int(prog * 255)
                    if prog < 0.2: alpha = 0
                else: 
                    alpha = int(prog * 255)

            elif phase == "ACTIVE" or phase == "WAITING_OUT":
                active_p = prog if phase == "ACTIVE" else 1.0

                if self.anim_active == "scale_pop":
                    pop = max(0, 1.0 - (active_p * 4)) 
                    scale = 1.0 + (pop * 0.25) + (bass * 0.15)
                elif self.anim_active == "super_glow": 
                    intensity = int(bass * 150)
                    glow_r = 10 + int(bass * 20)
                    glow_override = (act_r, act_g, act_b, 100 + intensity)
                    scale = 1.0 + (bass * 0.1)
                elif self.anim_active == "karaoke_sweep":
                    chars_vis = int(len(w["word"]) * active_p)
                elif self.anim_active == "jitter_nervioso":
                    intensity = high * 20
                    off_x += random.uniform(-intensity, intensity)
                    off_y += random.uniform(-intensity, intensity)
                elif self.anim_active == "color_overdrive": 
                    rgb = colorsys.hsv_to_rgb(current_time * 2.0 % 1.0, 1.0, 1.0)
                    color_override = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255)
                elif self.anim_active == "invert_flash":
                    color_override = (255, 255, 255, 255) if mid < 0.7 else (0, 0, 0, 255)
                elif self.anim_active == "wave_bounce":
                    jump = math.sin(active_p * math.pi) * (30 + mid * 40)
                    off_y -= jump

            elif phase == "OUT":
                if prog >= 1.0:
                    alpha = 0
                else:
                    if self.anim_out == "fade_out":
                        alpha = int((1.0 - prog) * 255)
                    elif self.anim_out == "fade_down":
                        alpha = int((1.0 - prog) * 255)
                        off_y = prog * 50
                    elif self.anim_out == "fly_away": 
                        alpha = int((1.0 - prog) * 255)
                        off_y = -(prog * 150)
                        off_x = (prog * 100) if i % 2 == 0 else -(prog * 100)
                    elif self.anim_out == "system_failure":
                        if prog < 0.5: scale = prog * 2.0
                        off_x = random.randint(-50, 50) * (1.0 - prog)
                        alpha = int((1.0 - prog) * 255)
                    elif self.anim_out == "zoom_out_collapse":
                        scale = 1.0 - prog
                        alpha = int((1.0 - prog) * 255)
                    else:
                        alpha = int((1.0 - prog) * 255)

            # --- AQUI ESTA LA MAGIA DEL COLOR ACTIVO ---
            if phase == "ACTIVE":
                base_color = (act_r, act_g, act_b, alpha)
                glow_color = (act_r, act_g, act_b, int(alpha * 0.6))
            else:
                base_color = (in_r, in_g, in_b, alpha)
                glow_color = (in_r, in_g, in_b, int(alpha * 0.6))

            state = {
                "text": w["word"],
                "line": w.get("line_number", 0),
                "color": color_override if color_override else base_color,
                "glow_color": glow_override if glow_override else glow_color,
                "scale": scale,
                "offset_x": off_x,
                "offset_y": off_y,
                "rotation": rot,
                "ghost_trail": ghost,
                "chars_visible": chars_vis,
                "glow_radius": glow_r 
            }
            words_state.append(state)

        return words_state