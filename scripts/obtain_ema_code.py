import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def obtain_stations_EMA_code():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    api_key = os.getenv("AEMET_API_KEY")
    all_stations_url = "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones"
    
    headers = {
        'accept': 'application/json',
        'api_key': api_key,
        'cache-control': 'no-cache'
    }
    try:
        # Obtengo el código EMA de las Estaciones y las almaceno en un json
        ema_codes_route = os.path.join(api_dir, 'json', 'ema_codes.json')
        response = requests.get(all_stations_url, headers=headers).json()
        data_url = response['datos']
        data = requests.get(data_url).json()

        # Creo el diccionario con la estructura deseada
        station_dict = {station['nombre']: station['indicativo'] for station in data}

        # Almacena la información en /json/ema_codes.json
        with open(ema_codes_route, 'w', encoding='utf-8') as f:
            json.dump(station_dict, f, ensure_ascii=False, indent=4)

        print(f"Datos guardados correctamente en {ema_codes_route}")

    except requests.RequestException as e:
        print(f'Error al realizar la consulta: {e}')