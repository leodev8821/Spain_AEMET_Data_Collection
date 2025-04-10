import json
import os
import logging

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

def check_missing_town_codes():
    """
    Comprar los codigos de los pueblos entre towns_codes.json y prediction_progress.json y genera una lista de los codigos de pueblos pendientes
    """
    try:
        # configuramos la ubicacion del archivo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        json_dir = os.path.join(api_dir, 'json')
        
        towns_codes_path = os.path.join(json_dir, 'towns_codes.json')
        prediction_progress_path = os.path.join(json_dir, 'prediction_progress.json')
        output_path = os.path.join(json_dir, 'pending_towns_codes.json')

        # cargamos towns_codes.json
        with open(towns_codes_path, 'r', encoding='utf-8') as f:
            towns_codes = json.load(f)
        logger.info(f"Cargados {len(towns_codes)} los codigos de pueblos de towns_codes.json")
        
        # Cargamos prediction_progress.json
        with open(prediction_progress_path, 'r', encoding='utf-8') as f:
            prediction_progress = json.load(f)
        logger.info(f"Cargados {len(prediction_progress)} los codigos de pueblos de prediction_progress.json")

        # Extraemos los IDS existentes de prediction_progress.json
        existing_codes = [entry['id'] for entry in prediction_progress if 'id' in entry]
        logger.info(f"encontrados {len(existing_codes)} los codigos de pueblos validos de prediction_progress.json")
        
        # Generamos el diccionario de los codigos pendientes , que no se encuentran en prediction_progress.json
        pending_towns = {}
        for code, town in towns_codes.items():
            if int(code) not in existing_codes:
                pending_towns[code] = town

        logger.info(f"Encontrados {len(pending_towns)} los codigos de pueblos pendientes")

      # Guardamos el JSON en un archivo con la estructura de towns_codes.json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pending_towns, f, indent=4, ensure_ascii=False)
                    
        logger.info(f"Successfully saved {len(pending_towns)} pending town codes to {output_path}")
        return pending_towns
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    check_missing_town_codes()