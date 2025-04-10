import logging
import json
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

def verify_json_docs(json_path_dir:str, message: str):
    '''Función para verificar la existencia de un archivo JSON'''
    if os.path.exists(json_path_dir):
        with open(json_path_dir, 'r', encoding='utf-8') as f:
            json_info = json.load(f)
            return json_info
    else: 
        raise ValueError(message)