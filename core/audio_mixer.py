import librosa
import numpy as np
import sounddevice as sd

class AudioLayer:
    def __init__(self, file_path, name):
        self.file_path = file_path
        self.name = name
        self.volume = 1.0
        self.muted = False
        self.solo = False
        # Cargar audio en memoria
        self.data, self.sr = librosa.load(file_path, sr=44100, mono=False)
        self.duration = librosa.get_duration(y=self.data, sr=self.sr)

class AudioMixer:
    def __init__(self, fps=30):
        self.fps = fps
        self.layers = []
        self.bass_data = np.array([])
        self.mid_data = np.array([])
        self.high_data = np.array([])
        self.master_duration = 0.0

    def add_layer(self, file_path, name):
        layer = AudioLayer(file_path, name)
        self.layers.append(layer)
        self.master_duration = max(self.master_duration, layer.duration)
        self._recalculate_analysis()

    def _recalculate_analysis(self):
        """Mezcla las pistas activas y calcula FFT para la reactividad visual."""
        if not self.layers:
            return

        # Mezcla simple (mono) para análisis
        mix = np.zeros(int(self.master_duration * 44100))
        for layer in self.layers:
            if not layer.muted:
                audio_mono = librosa.to_mono(layer.data) * layer.volume
                mix[:len(audio_mono)] += audio_mono

        # Análisis FFT
        hop_length = int(44100 / self.fps)
        S = np.abs(librosa.stft(mix, hop_length=hop_length))
        
        self.bass_data = self._normalize(np.mean(S[1:10, :], axis=0))
        self.mid_data = self._normalize(np.mean(S[10:100, :], axis=0))
        self.high_data = self._normalize(np.mean(S[100:500, :], axis=0))

    def _normalize(self, arr):
        return arr / np.max(arr) if np.max(arr) > 0 else arr

    def get_reactivity(self, current_time):
        frame_idx = int(current_time * self.fps)
        if frame_idx >= len(self.bass_data) or len(self.bass_data) == 0:
            return 0.0, 0.0, 0.0
        return self.bass_data[frame_idx], self.mid_data[frame_idx], self.high_data[frame_idx]