from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QLineEdit, QMessageBox, QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt

class LauncherWidget(QWidget):
    # Señales para comunicarse con main.py
    project_selected = pyqtSignal(str)
    
    def __init__(self, project_manager):
        super().__init__()
        self.pm = project_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Título
        title = QLabel("APP MIGNA\nCreative Visual Suite")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00ffff; margin-bottom: 20px;")
        layout.addWidget(title)

        container = QHBoxLayout()
        
        # --- PANEL IZQUIERDO: Crear Proyecto ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>Crear Nuevo Proyecto</b>", styleSheet="font-size: 18px;"))
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Nombre del proyecto...")
        self.input_name.setStyleSheet("padding: 10px; background: #1a1a1a; color: white; border: 1px solid #333;")
        left_panel.addWidget(self.input_name)
        
        btn_create = QPushButton("Crear Proyecto ➔")
        btn_create.setStyleSheet("background-color: white; color: black; font-weight: bold; padding: 10px;")
        btn_create.clicked.connect(self.create_project)
        left_panel.addWidget(btn_create)
        left_panel.addStretch()
        container.addLayout(left_panel)

        # --- PANEL DERECHO: Proyectos Recientes ---
        right_panel = QVBoxLayout()
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Almacenamiento Interno</b>", styleSheet="font-size: 18px;"))
        
        btn_import = QPushButton("Importar JSON")
        btn_import.clicked.connect(self.import_project)
        header_layout.addWidget(btn_import)
        right_panel.addLayout(header_layout)

        self.list_projects = QListWidget()
        self.list_projects.setStyleSheet("background: #1a1a1a; color: white; border: 1px solid #333; padding: 5px;")
        self.refresh_list()
        self.list_projects.itemDoubleClicked.connect(self.load_project)
        right_panel.addWidget(self.list_projects)
        
        btn_load = QPushButton("Cargar Seleccionado")
        btn_load.setStyleSheet("background-color: #9333ea; color: white; font-weight: bold; padding: 10px;")
        btn_load.clicked.connect(lambda: self.load_project(self.list_projects.currentItem()))
        right_panel.addWidget(btn_load)
        
        container.addLayout(right_panel)
        layout.addLayout(container)

    def refresh_list(self):
        self.list_projects.clear()
        projects = self.pm.list_projects()
        for p in projects:
            self.list_projects.addItem(p)

    def create_project(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Ingresa un nombre de proyecto válido.")
            return
        # Inicializar proyecto vacío
        self.pm.save_project(name, {"segments": []}, {}, [], [])
        self.project_selected.emit(name)

    def load_project(self, item):
        if item:
            self.project_selected.emit(item.text())

    def import_project(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Importar Proyecto JSON", "", "JSON Files (*.json)")
        if filepath:
            # Lógica de importación (copiar a db_folder)
            QMessageBox.information(self, "Importar", f"Función de importación simulada para {filepath}")