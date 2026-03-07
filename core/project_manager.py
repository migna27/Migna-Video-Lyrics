import os
import json
import time

class ProjectManager:
    def __init__(self, db_folder="db"):
        self.db_folder = db_folder
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

    def list_projects(self):
        """Devuelve una lista con los nombres de los proyectos guardados."""
        projects = []
        for filename in os.listdir(self.db_folder):
            if filename.endswith(".json"):
                projects.append(filename.replace(".json", ""))
        return projects

    def save_project(self, name, lyric_data, config, event_blocks, custom_effects):
        """Guarda el estado completo del proyecto en un archivo JSON."""
        filepath = os.path.join(self.db_folder, f"{name}.json")
        
        project_data = {
            "version": "1.0",
            "type": "video-lyrics-desktop",
            "timestamp": time.time(),
            "name": name,
            "lyricData": lyric_data,
            "config": config,
            "eventBlocks": event_blocks,
            "customEffects": custom_effects
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=4)
        print(f"Proyecto '{name}' guardado exitosamente en {filepath}")

    def load_project(self, name):
        """Carga un proyecto desde el almacenamiento local."""
        filepath = os.path.join(self.db_folder, f"{name}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"El proyecto {name} no existe.")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)