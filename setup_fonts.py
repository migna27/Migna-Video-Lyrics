import os
import urllib.request
import zipfile

# Lista de fuentes con IDs estandarizados para la API
FONTS_TO_DOWNLOAD = [
    "roboto", "open-sans", "lato", "montserrat", "poppins", 
    "inter", "raleway", "noto-sans", "ubuntu", "quicksand", "nunito",
    "bebas-neue", "anton", "oswald", "teko", "fjalla-one", 
    "righteous", "bangers", "black-ops-one", "permanent-marker", "exo-2",
    "dancing-script", "pacifico", "caveat", "lobster", "great-vibes",
    "satisfy", "amatic-sc", "parisienne", "sacramento", "playfair-display", "cinzel",
    "creepster", "nosifer", "eater", "butcherman", "metal-mania",
    "flavors", "piedra", "rye", "eczar", "rubik-glitch",
    "orbitron", "press-start-2p", "vt323", "share-tech-mono", "silkscreen",
    "audiowide", "rajdhani", "dotgothic16", "bungee"
]

def download_and_extract_fonts():
    fonts_dir = os.path.abspath(os.path.join("assets", "fonts"))
    os.makedirs(fonts_dir, exist_ok=True)
    temp_zip = "temp_font.zip"

    print(f"Preparando la descarga de {len(FONTS_TO_DOWNLOAD)} fuentes en {fonts_dir}...\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    exitosas = 0
    fallidas = 0

    for font_id in FONTS_TO_DOWNLOAD:
        # Usamos la API de Webfonts Helper configurada para devolver un ZIP con los TTF
        url = f"https://gwfh.mranftl.com/api/fonts/{font_id}?download=zip&subsets=latin&variants=regular&formats=ttf"
        
        try:
            print(f"Descargando: {font_id}...")
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response, open(temp_zip, 'wb') as out_file:
                out_file.write(response.read())
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.lower().endswith('.ttf'):
                        file_info.filename = os.path.basename(file_info.filename)
                        if file_info.filename: 
                            zip_ref.extract(file_info, fonts_dir)
                            
            print("  -> Instalada!")
            exitosas += 1
        except Exception as e:
            print(f"  -> Error al descargar {font_id}: {e}")
            fallidas += 1

    if os.path.exists(temp_zip):
        os.remove(temp_zip)
        
    print("\n" + "="*40)
    print(f"PROCESO TERMINADO")
    print(f"Fuentes instaladas exitosamente: {exitosas}")
    if fallidas > 0:
        print(f"Fuentes que fallaron: {fallidas}")
    print("="*40)
    print("Abre tu aplicacion Migna. Las fuentes ya estaran listas en los menus!")

if __name__ == "__main__":
    download_and_extract_fonts()