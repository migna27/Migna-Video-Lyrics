
import math
import random
import colorsys

class LyricAnimator:
    def __init__(self):
        # Efectos seleccionados actualmente
        self.anim_in = "glitch_reveal"      # Cambia aquí la animación de entrada
        self.anim_out = "system_failure"    # Cambia aquí la animación de salida
        self.anim_active = "scale_pop"      # Cambia aquí la animación por palabra
        
        self.transition_time = 0.5 # Segundos que dura la entrada/salida

    def process_segment(self, segment, current_time, bass, mid, high):
        start = segment["start"]
        end = segment["end"]
        
        # Progresos globales (0.0 a 1.0) limitados
        progress_in = min(max((current_time - start) / max(self.transition_time, 0.001), 0.0), 1.0)
        progress_out = min(max((end - current_time) / max(self.transition_time, 0.001), 0.0), 1.0)
        
        # Estado Global Base
        g_opacity = 255
        g_offset_x = 0
        g_offset_y = 0
        g_scale = 1.0
        g_visible_ratio = 1.0 # Para typewriter
        g_blur_radius = 0

        # ==========================================
        # 📥 1. ANIMACIONES DE ENTRADA (10)
        # ==========================================
        if current_time < start + self.transition_time:
            if self.anim_in == "fade_in":
                g_opacity = int(progress_in * 255)
            elif self.anim_in == "glitch_reveal":
                g_opacity = 255 if random.random() < progress_in else 50
                if progress_in < 0.8: g_offset_x = random.randint(-20, 20)
            elif self.anim_in == "typewriter":
                g_visible_ratio = progress_in
            elif self.anim_in == "rise_from_void":
                g_opacity = int(progress_in * 255)
                g_offset_y = (1.0 - progress_in) * 150
            elif self.anim_in == "neon_flicker_on":
                g_opacity = 255 if random.random() < (progress_in ** 2) else 30
            elif self.anim_in == "zoom_basico":
                g_scale = 0.5 + (progress_in * 0.5)
                g_opacity = int(progress_in * 255)
            elif self.anim_in == "word_cascade":
                g_opacity = int(progress_in * 255) # El offset se calculará por palabra más abajo
            elif self.anim_in == "cinematic_blur":
                g_opacity = int(progress_in * 255)
                g_blur_radius = int((1.0 - progress_in) * 20)
            elif self.anim_in == "shatter_reverse":
                g_opacity = int(progress_in * 255)
            elif self.anim_in == "side_sweep":
                g_opacity = int(progress_in * 255)
                g_offset_x = -300 * (1.0 - progress_in)

        # ==========================================
        # 📤 2. ANIMACIONES DE SALIDA (10)
        # ==========================================
        elif current_time > end - self.transition_time:
            if self.anim_out == "fade_out":
                g_opacity = int(progress_out * 255)
            elif self.anim_out == "system_failure":
                if progress_out < 0.5: g_scale = progress_out * 2.0
                g_offset_x = random.randint(-50, 50) * (1.0 - progress_out)
                g_opacity = int(progress_out * 255)
            elif self.anim_out == "blackout_cut":
                g_opacity = 255 if bass < 0.7 else 0
            elif self.anim_out == "neon_flicker_off":
                g_opacity = 255 if random.random() < progress_out else 0
            elif self.anim_out == "drop_fade":
                g_opacity = int(progress_out * 255)
                g_offset_y = -(1.0 - progress_out) * 150
            elif self.anim_out == "evaporate":
                g_opacity = int(progress_out * 255)
                g_blur_radius = int((1.0 - progress_out) * 30)
                g_offset_y = (1.0 - progress_out) * -50
            elif self.anim_out == "typewriter_backspace":
                g_visible_ratio = progress_out
            elif self.anim_out == "zoom_out_collapse":
                g_scale = progress_out
                g_opacity = int(progress_out * 255)
            elif self.anim_out == "glitch_melt":
                g_opacity = int(progress_out * 255)
            elif self.anim_out == "word_scatter":
                g_opacity = int(progress_out * 255)

        # ==========================================
        # 🔥 3. ANIMACIONES ACTIVAS POR PALABRA (10)
        # ==========================================
        words_state = []
        words = segment.get("words", [])
        total_words = len(words)
        
        for i, w in enumerate(words):
            w_start = w["start"]
            w_end = w["end"]
            is_active = w_start <= current_time <= w_end
            
            # Estado base individual
            state = {
                "text": w["word"],
                "line": w.get("line_number", 0),
                "color": (255, 255, 255, g_opacity),
                "glow_color": (0, 255, 255, int(g_opacity * 0.6)), # Cyan por defecto
                "scale": g_scale,
                "offset_x": g_offset_x,
                "offset_y": g_offset_y,
                "rotation": 0,
                "ghost_trail": False,
                "chars_visible": int(len(w["word"]) * g_visible_ratio)
            }

            # --- Modificadores de Entrada Especiales (Por Índice) ---
            if current_time < start + self.transition_time:
                if self.anim_in == "word_cascade":
                    delay = i * 0.1
                    w_prog = min(max((progress_in * 1.5) - delay, 0.0), 1.0)
                    state["offset_y"] = (1.0 - w_prog) * 200
                elif self.anim_in == "shatter_reverse":
                    state["offset_x"] = random.randint(-200, 200) * (1.0 - progress_in)
                    state["offset_y"] = random.randint(-200, 200) * (1.0 - progress_in)

            # --- Modificadores de Salida Especiales (Por Índice) ---
            elif current_time > end - self.transition_time:
                if self.anim_out == "glitch_melt":
                    state["offset_y"] += random.randint(0, int((1.0 - progress_out) * 150))
                elif self.anim_out == "word_scatter":
                    angle = (i / max(total_words, 1)) * math.pi * 2
                    dist = (1.0 - progress_out) * 300
                    state["offset_x"] += math.cos(angle) * dist
                    state["offset_y"] += math.sin(angle) * dist

            # --- EFECTOS ACTIVOS DE LA PALABRA ACTUAL ---
            if is_active:
                word_duration = max((w_end - w_start), 0.001)
                w_prog = (current_time - w_start) / word_duration
                
                if self.anim_active == "scale_pop":
                    pop = max(0, 1.0 - (w_prog * 4)) 
                    state["scale"] *= 1.0 + (pop * 0.25) + (bass * 0.15)
                    state["color"] = (0, 255, 255, g_opacity) # Cyan agresivo
                
                elif self.anim_active == "karaoke_sweep":
                    state["chars_visible"] = int(len(w["word"]) * w_prog)
                    state["color"] = (255, 0, 255, g_opacity) # Magenta
                    
                elif self.anim_active == "jitter_nervioso":
                    intensity = high * 25
                    state["offset_x"] += random.uniform(-intensity, intensity)
                    state["offset_y"] += random.uniform(-intensity, intensity)
                    state["color"] = (255, 20, 50, g_opacity) # Rojo alerta
                    
                elif self.anim_active == "neon_pulse_glow":
                    state["glow_color"] = (255, 0, 100, int(g_opacity * bass)) # Resplandor palpita con graves
                    state["scale"] *= 1.0 + (bass * 0.1)
                    
                elif self.anim_active == "invert_flash":
                    if w_prog < 0.15 or bass > 0.85:
                        state["color"] = (0, 0, 0, g_opacity) # Negro
                        state["glow_color"] = (255, 255, 255, g_opacity) # Glow blanco
                        
                elif self.anim_active == "glitch_slice":
                    if random.random() < 0.5:
                        state["offset_x"] += random.choice([-15, 15])
                        state["color"] = random.choice([(0,255,255, g_opacity), (255,0,255, g_opacity)])
                        
                elif self.anim_active == "wave_bounce":
                    jump = math.sin(w_prog * math.pi) * (40 + mid * 60)
                    state["offset_y"] -= jump
                    state["color"] = (255, 255, 0, g_opacity)
                    
                elif self.anim_active == "tilt_yawn":
                    state["rotation"] = math.sin(w_prog * math.pi * 2) * 15 # Rota +- 15 grados
                    
                elif self.anim_active == "color_overdrive":
                    rgb = colorsys.hsv_to_rgb(current_time * 2.0 % 1.0, 1.0, 1.0)
                    state["color"] = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), g_opacity)
                    state["scale"] *= 1.0 + (mid * 0.1)
                    
                elif self.anim_active == "ghost_trail":
                    state["ghost_trail"] = True
                    state["color"] = (255, 255, 255, g_opacity)

            # Si el difuminado está activo (Cinematic/Evaporate) lo añadimos al glow_color
            if g_blur_radius > 0:
                state["glow_radius"] = g_blur_radius

            words_state.append(state)

        return words_state