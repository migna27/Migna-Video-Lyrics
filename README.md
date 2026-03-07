
# Migna Video Lyrics - Desktop Edition

Una suite visual nativa y acelerada por GPU para la creación de videos con tipografía cinética reactiva al audio. Esta aplicación migra la lógica de una versión anterior basada en la web (React/WebGL) a un entorno de escritorio robusto usando Python, PyQt6 y ModernGL.

## 🚀 Características Principales

* **Renderizado Nativo por GPU:** Uso de `ModernGL` para ejecutar shaders GLSL a máxima velocidad.
* **Exportación Acelerada por Hardware:** Integración con FFmpeg utilizando el codificador **NVIDIA NVENC** (h264_nvenc), permitiendo exportar videos a 1080p en fracciones del tiempo real aprovechando tarjetas gráficas dedicadas (ej. familia RTX).
* **Reactividad de Audio Real:** Análisis de frecuencias mediante `librosa` para controlar el zoom dinámico, resplandor del texto y efectos visuales (Bajos, Medios, Agudos).
* **Fondos Dinámicos:** Soporte para imágenes estáticas y videos (.mp4, .webm) fluidos detrás de los gráficos.
* **Persistencia de Proyectos:** Guardado y carga automática del estado del proyecto, incluyendo rutas de medios y fuentes.

---

## 🛠️ Requisitos del Sistema

1.  **Python 3.10 o superior.**
2.  **FFmpeg (Requisito Indispensable):** El ejecutable real de FFmpeg debe estar instalado en el sistema y agregado a las variables de entorno (PATH). La librería de Python solo actúa como puente.
    * *En Windows (vía PowerShell):* `winget install ffmpeg`
3.  **Tarjeta Gráfica Dedicada (NVIDIA):** El exportador está preconfigurado para usar `h264_nvenc`. (Asegúrate de configurar Windows para que Python use el procesador gráfico de alto rendimiento).

---

## 📦 Instalación

1. Clona o descarga este repositorio.
2. Abre la terminal en la carpeta del proyecto y crea un entorno virtual:
   ```bash
   python -m venv venv
   ```
3. Activa el entorno virtual:
   * En Windows: `venv\Scripts\activate`
   * En macOS/Linux: `source venv/bin/activate`
4. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Ejecución

Con el entorno virtual activado, simplemente ejecuta el lanzador principal:

```bash
python main.py
```

---

## 📄 Estructura del Archivo JSON (Letras)

El programa utiliza un archivo `.json` estructurado para sincronizar las letras con el tiempo exacto de la pista de audio. Puedes importarlo desde la pestaña **Timeline**.

### Formato esperado:
El archivo debe contener un objeto principal con un arreglo llamado `"segments"`. Cada segmento requiere un tiempo de inicio (`start`), tiempo de fin (`end`) y el texto a mostrar (`text`).

**Ejemplo:**
```json
{
  "segments": [
    {
      "id": "1",
      "start": 4.11,
      "end": 12.88,
      "text": "SON LAS 3 Y\n10 DE LA MAÑANA",
      "words": [
        {
          "word": "SON",
          "start": 10.11,
          "end": 10.96
        },
        {
          "word": "LAS",
          "start": 10.96,
          "end": 11.45
        }
      ],
      "section": "verse"
    },
    {
      "id": "2",
      "start": 12.88,
      "end": 15.50,
      "text": "Y AQUÍ VAMOS DE\nNUEVO"
    }
  ]
}
```

*Nota: El motor principal actualmente utiliza los campos `start`, `end` y `text` para el renderizado base. Los arrays internos de `words` permiten futuras implementaciones de animaciones palabra por palabra (karaoke).*
```