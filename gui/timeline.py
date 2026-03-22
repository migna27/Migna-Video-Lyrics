import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QDoubleSpinBox, QComboBox, QFileDialog, 
                             QMessageBox, QScrollArea, QLabel, QFrame, QPlainTextEdit)
from PyQt6.QtCore import pyqtSignal, Qt

# Paleta de colores exacta a tu version de React
SEC_COLORS = {
    "verse": "#3b82f6",   # Blue
    "chorus": "#ec4899",  # Pink
    "bridge": "#eab308",  # Yellow
    "intro": "#6b7280",   # Gray
    "outro": "#ef4444"    # Red
}

SEC_BG = {
    "verse": "rgba(59, 130, 246, 0.15)",
    "chorus": "rgba(236, 72, 153, 0.15)",
    "bridge": "rgba(234, 179, 8, 0.15)",
    "intro": "rgba(107, 114, 128, 0.15)",
    "outro": "rgba(239, 68, 68, 0.15)"
}

class LyricTextEdit(QPlainTextEdit):
    focus_lost = pyqtSignal()
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_lost.emit()

class SectionHeader(QLabel):
    def __init__(self, section_name):
        super().__init__(f" 🏷️ {section_name.upper()} ")
        color = SEC_COLORS.get(section_name.lower(), "#a3a3a3")
        bg = SEC_BG.get(section_name.lower(), "rgba(163, 163, 163, 0.15)")
        self.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 8px;
            margin-bottom: 2px;
            font-size: 11px;
            letter-spacing: 1px;
        """)

class SegmentCard(QFrame):
    update_requested = pyqtSignal(int, dict)
    delete_requested = pyqtSignal(int)
    toggle_section_requested = pyqtSignal(int, str, str)

    def __init__(self, index, segment, effective_section):
        super().__init__()
        self.index = index
        self.segment = segment
        self.effective_section = effective_section
        self.init_ui()

    def init_ui(self):
        color = SEC_COLORS.get(self.effective_section.lower(), "#444444")
        self.setStyleSheet(f"""
            SegmentCard {{
                background-color: #1e1e1e;
                border-radius: 6px;
                border-left: 4px solid {color};
                margin-bottom: 4px;
            }}
            SegmentCard:hover {{
                background-color: #262626;
                border: 1px solid rgba(255,255,255,0.1);
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(4)

        top_layout = QHBoxLayout()
        
        self.start_box = QDoubleSpinBox()
        self.start_box.setRange(0, 1000)
        self.start_box.setDecimals(2)
        self.start_box.setValue(self.segment.get("start", 0))
        self.start_box.setStyleSheet("background-color: #111; color: #ccc; border: 1px solid #333; padding: 2px;")
        self.start_box.editingFinished.connect(lambda: self.update_requested.emit(self.index, {"start": self.start_box.value()}))

        self.end_box = QDoubleSpinBox()
        self.end_box.setRange(0, 1000)
        self.end_box.setDecimals(2)
        self.end_box.setValue(self.segment.get("end", self.segment.get("start", 0) + 2.0))
        self.end_box.setStyleSheet("background-color: #111; color: #ccc; border: 1px solid #333; padding: 2px;")
        self.end_box.editingFinished.connect(lambda: self.update_requested.emit(self.index, {"end": self.end_box.value()}))
        
        top_layout.addWidget(QLabel("De:", styleSheet="color: #666; font-size: 10px;"))
        top_layout.addWidget(self.start_box)
        top_layout.addWidget(QLabel("a", styleSheet="color: #666; font-size: 10px;"))
        top_layout.addWidget(self.end_box)
        top_layout.addStretch()

        if "section" in self.segment:
            self.sec_combo = QComboBox()
            self.sec_combo.addItems(["verse", "chorus", "bridge", "intro", "outro"])
            self.sec_combo.setCurrentText(self.segment["section"])
            self.sec_combo.setStyleSheet("background-color: #333; color: white; font-size: 10px; border-radius: 2px;")
            self.sec_combo.currentTextChanged.connect(lambda v: self.toggle_section_requested.emit(self.index, "change", v))
            top_layout.addWidget(self.sec_combo)

            btn_remove_sec = QPushButton("✖")
            btn_remove_sec.setStyleSheet("color: #ef4444; font-weight: bold; background: transparent; border: none;")
            btn_remove_sec.clicked.connect(lambda: self.toggle_section_requested.emit(self.index, "remove", ""))
            top_layout.addWidget(btn_remove_sec)
        else:
            btn_add_sec = QPushButton("🏷️ Marcar Sección")
            btn_add_sec.setStyleSheet("color: #9ca3af; font-size: 10px; background: #333; padding: 2px 6px; border-radius: 3px;")
            btn_add_sec.clicked.connect(lambda: self.toggle_section_requested.emit(self.index, "add", ""))
            top_layout.addWidget(btn_add_sec)

        btn_del = QPushButton("🗑️")
        btn_del.setStyleSheet("color: #ef4444; background: transparent; border: none; padding: 2px;")
        btn_del.clicked.connect(lambda: self.delete_requested.emit(self.index))
        top_layout.addWidget(btn_del)

        layout.addLayout(top_layout)

        self.text_edit = LyricTextEdit(self.segment.get("text", ""))
        self.text_edit.setFixedHeight(45)
        self.text_edit.setStyleSheet("background-color: transparent; border: none; color: #fff; font-size: 12px;")
        self.text_edit.focus_lost.connect(lambda: self.update_requested.emit(self.index, {"text": self.text_edit.toPlainText().strip()}))
        layout.addWidget(self.text_edit)

class TimelineEditor(QWidget):
    lyrics_loaded = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.segments = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Barra superior con Importar
        top_bar = QHBoxLayout()
        self.btn_import_json = QPushButton("📂 Importar JSON de Letras")
        self.btn_import_json.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_import_json.clicked.connect(self.import_json)
        top_bar.addWidget(self.btn_import_json)
        main_layout.addLayout(top_bar)
        
        # Herramienta de Agregar Linea Rapida
        input_layout = QHBoxLayout()
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0, 1000)
        self.spin_start.setDecimals(2)
        self.spin_start.setStyleSheet("background-color: #222; color: white; padding: 5px;")
        
        self.combo_section = QComboBox()
        self.combo_section.addItems(["Ninguna", "verse", "chorus", "bridge", "intro", "outro"])
        self.combo_section.setStyleSheet("background-color: #222; color: white; padding: 5px;")
        
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Letra de la canción...")
        self.input_text.setStyleSheet("background-color: #222; color: white; padding: 5px;")
        
        self.btn_add = QPushButton("Añadir")
        self.btn_add.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 5px 15px;")
        self.btn_add.clicked.connect(self.add_segment)
        
        input_layout.addWidget(self.spin_start)
        input_layout.addWidget(self.combo_section)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.btn_add)
        main_layout.addLayout(input_layout)
        
        # Area scrolleable para las tarjetas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background-color: #1a1a1a; width: 8px; }
            QScrollBar::handle:vertical { background-color: #444; border-radius: 4px; }
        """)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(2)
        self.scroll_area.setWidget(self.cards_container)
        
        main_layout.addWidget(self.scroll_area)

    def import_json(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Importar Letras JSON", "", "JSON Files (*.json)")
        if not filepath: return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "segments" in data:
                new_segments = data["segments"]
            elif isinstance(data, list):
                new_segments = data
            else:
                raise ValueError("El archivo JSON no tiene un formato valido de letras.")
            
            self.segments = new_segments
            self.lyrics_loaded.emit(self.segments)
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Importacion", f"No se pudo cargar el archivo:\n{str(e)}")

    def add_segment(self):
        text = self.input_text.text().strip()
        if not text: return
        
        start_time = self.spin_start.value()
        
        seg = {
            "start": start_time,
            "end": start_time + 2.0,
            "text": text
        }
        
        sec_val = self.combo_section.currentText()
        if sec_val != "Ninguna":
            seg["section"] = sec_val
            
        self.segments.append(seg)
        self.input_text.clear()
        self.lyrics_loaded.emit(self.segments)

    def on_card_update(self, idx, updates):
        seg = self.segments[idx]
        seg.update(updates)
        
        # Si se edito el texto o los tiempos, recalculamos las palabras logicamente
        if "text" in updates or "start" in updates or "end" in updates:
            text = seg.get("text", "")
            start = seg.get("start", 0)
            end = seg.get("end", start + 2.0)
            words_raw = text.split()
            words = []
            if words_raw:
                dur = max(0.1, end - start) / len(words_raw)
                curr = start
                for w in words_raw:
                    words.append({"word": w, "start": curr, "end": curr+dur, "probability": 1.0, "line_number": 0})
                    curr += dur
            seg["words"] = words

        self.lyrics_loaded.emit(self.segments)

    def on_card_delete(self, idx):
        if idx >= 0 and idx < len(self.segments):
            self.segments.pop(idx)
            self.lyrics_loaded.emit(self.segments)

    def on_card_toggle_section(self, idx, action, value):
        seg = self.segments[idx]
        if action == "add":
            seg["section"] = "verse" 
        elif action == "remove":
            if "section" in seg: del seg["section"]
        elif action == "change":
            seg["section"] = value
        self.lyrics_loaded.emit(self.segments)

    def update_list_ui(self, processed_segments):
        self.segments = processed_segments
        
        # Limpiar layout actual
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        current_section = "verse"
        
        for i, seg in enumerate(self.segments):
            is_new_sec = "section" in seg
            
            if is_new_sec:
                current_section = seg["section"]
                
            # Cabecera Visual
            if is_new_sec or (i == 0 and not is_new_sec):
                self.cards_layout.addWidget(SectionHeader(current_section))
                
            # Tarjeta de Segmento
            card = SegmentCard(i, seg, current_section)
            card.update_requested.connect(self.on_card_update)
            card.delete_requested.connect(self.on_card_delete)
            card.toggle_section_requested.connect(self.on_card_toggle_section)
            self.cards_layout.addWidget(card)