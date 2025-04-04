import logging
import requests
import json
import os
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def obtain_stations_EMA_code():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    ema_codes_route = os.path.join(api_dir, 'json', 'ema_codes.json')

    api_key = os.getenv("AEMET_API_KEY")
    all_stations_url = "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones"
    
    headers = {
        'accept': 'application/json',
        'api_key': api_key,
        'cache-control': 'no-cache'
    }
    try:
        # Obtengo el código EMA de las Estaciones y las almaceno en un json
        response = requests.get(all_stations_url, headers=headers).json()
        if response.get('estado') == 200:
            data_url = response.get('datos')
            data = requests.get(data_url).json()

            # Creo el diccionario con la estructura deseada
            station_dict = {station['nombre']: station['indicativo'] for station in data}

            # Almacena la información en /json/ema_codes.json
            with open(ema_codes_route, 'w', encoding='utf-8') as f:
                json.dump(station_dict, f, ensure_ascii=False, indent=4)

            logger.info(f"Datos guardados correctamente en {ema_codes_route}")
        else:
            raise requests.RequestException(f"{response.get('descripcion')}")

    except requests.RequestException as e:
        logger.error(f'Error al realizar la consulta: {e}')