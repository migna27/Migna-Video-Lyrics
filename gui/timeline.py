from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QLineEdit, QDoubleSpinBox, QComboBox)
from PyQt6.QtCore import pyqtSignal

class TimelineEditor(QWidget):
    lyrics_loaded = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.segments = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        input_layout = QHBoxLayout()
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0, 1000)
        self.spin_start.setDecimals(2)
        self.spin_start.setPrefix("Inicio: ")
        
        # Etiqueta de Seccion para esta linea especifica
        self.combo_section = QComboBox()
        self.combo_section.addItems(["Ninguna", "Verso", "Pre-coro", "Coro"])
        self.combo_section.setToolTip("¿Esta linea inicia una nueva seccion musical?")
        
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Letra de la cancion...")
        
        self.btn_add = QPushButton("Añadir")
        self.btn_add.clicked.connect(self.add_segment)
        
        input_layout.addWidget(self.spin_start)
        input_layout.addWidget(self.combo_section)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.btn_add)
        
        layout.addLayout(input_layout)
        
        self.list_segments = QListWidget()
        layout.addWidget(self.list_segments)
        
        btn_delete = QPushButton("Eliminar Seleccionado")
        btn_delete.clicked.connect(self.delete_segment)
        layout.addWidget(btn_delete)

    def add_segment(self):
        text = self.input_text.text().strip()
        if not text: return
        
        # El tiempo Final se calculara automaticamente en main.py
        seg = {
            "start": self.spin_start.value(),
            "end": self.spin_start.value() + 2.0, # Valor placeholder
            "text": text,
            "words": text.split(),
            "section_type": self.combo_section.currentText()
        }
        
        self.segments.append(seg)
        self.input_text.clear()
        self.lyrics_loaded.emit(self.segments)

    def update_list_ui(self, processed_segments):
        # Actualiza la lista visible tras procesar el auto-end
        self.segments = processed_segments
        self.list_segments.clear()
        for seg in self.segments:
            sec = seg.get("section_type", "Ninguna")
            sec_tag = f"[{sec}]" if sec != "Ninguna" else ""
            self.list_segments.addItem(f"{seg['start']:.2f}s - {seg['end']:.2f}s {sec_tag} : {seg['text']}")

    def delete_segment(self):
        row = self.list_segments.currentRow()
        if row >= 0:
            self.segments.pop(row)
            self.lyrics_loaded.emit(self.segments)