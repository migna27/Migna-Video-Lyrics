import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import pyqtSignal

class TimelineEditor(QWidget):
    # Señal que envía los datos parseados a main.py
    lyrics_loaded = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("<b>TIMELINE & LYRICS</b>", styleSheet="color: #00ffff;"))
        
        btn_import_json = QPushButton("📂 Importar JSON")
        btn_import_json.setStyleSheet("background-color: #0891b2; color: white;")
        btn_import_json.clicked.connect(self.import_json)
        
        toolbar.addStretch()
        toolbar.addWidget(btn_import_json)
        layout.addLayout(toolbar)

        self.list_segments = QListWidget()
        self.list_segments.setStyleSheet("""
            QListWidget { background: #111; border: 1px solid #333; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #222; color: #ddd; }
        """)
        layout.addWidget(self.list_segments)

    def import_json(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Importar JSON de Letras", "", "JSON Files (*.json)")
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Asumimos la estructura del proyecto original de React
                segments = data.get("segments", [])
                self.list_segments.clear()
                
                for seg in segments:
                    start = seg.get("start", 0)
                    end = seg.get("end", 0)
                    text = seg.get("text", "")
                    self.list_segments.addItem(f"[{start:.2f}s - {end:.2f}s] {text}")
                
                self.lyrics_loaded.emit(segments)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo leer el JSON:\n{str(e)}")