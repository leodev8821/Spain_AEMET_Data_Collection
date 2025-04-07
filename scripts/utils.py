import logging
import requests
import json
import os
from datetime import datetime, timezone
import re
from dotenv import load_dotenv
import pandas as pd
from collections import defaultdict

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def obtain_and_group_stations_codes():
    '''Función para obtener los códigos EMA desde la API, hacer grupos de 25 códigos y almacenarlos en archivos JSON'''
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    ema_codes_route = os.path.join(api_dir, 'json', 'ema_codes.json')
    ema_codes_grouped = os.path.join(api_dir, 'json', 'codes_group.json')

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

            # Con los datos obtenidos, se crea un nuevo json donde se forman los grupos de 25
            new_grouped_dict = {}
            group_size = 25
            ema_codes = list(station_dict.values())

            for i in range(0, len(ema_codes), group_size):
                start = i
                end = min(i + group_size, len(ema_codes))
                values_group = ema_codes[start:end]
                key = f"grupo_{i // group_size + 1}"
                new_grouped_dict[key] = ",".join(values_group)

            with open(ema_codes_grouped, 'w', encoding='utf-8') as f:
                        json.dump(new_grouped_dict, f, ensure_ascii=False, indent=4)

            logger.info(f"Datos guardados correctamente en {ema_codes_route}")
            logger.info(f"Grupos de 25 códigos creados correctamente en {ema_codes_grouped}")
        else:
            raise requests.RequestException(f"{response.get('descripcion')}")

    except requests.RequestException as e:
        logger.error(f'Error al realizar la consulta: {e}')

def date_validation(date_str: str):
    '''Función para validar del formato de la fecha introducida por el usuario'''
    try:
        # Verificar formato básico con regex
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False, "Formato inválido. Debe ser YYYY-MM-DD"
        
        # Validar que sea una fecha válida
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    
    except ValueError:
        return False, "Fecha inválida. Por favor, ingrese una fecha correcta."
    
def verify_json_docs(json_path_dir:str, message: str):
    '''Función para verificar la existencia de un archivo JSON'''
    if os.path.exists(json_path_dir):
            with open(json_path_dir, 'r', encoding='utf-8') as f:
                json_info = json.load(f)
                return json_info
    else: 
        raise ValueError(message)


def data_to_csv(name: str):
    '''Función para guardar la información en un archivo CSV'''
    match name:
        case "precipitaciones":
            keys = ["precip"]
        case "viento":
            keys = ["avg_vel", "max_vel"]
        case "temperatura":
            keys = ["avg_t", "max_t", "min_t"]
        case "humedad_relativa":
            keys = ["avg_rel_hum", "max_rel_hum", "min_rel_hum"]

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        temp_csv_dir = os.path.join(api_dir, 'csv')
        all_data_dir = os.path.join(api_dir, 'json', 'weather_data.json')
        ema_codes_dir = os.path.join(api_dir, 'json', 'ema_codes.json')

        os.makedirs(os.path.dirname(temp_csv_dir), exist_ok=True)

        all_data = verify_json_docs(all_data_dir)
        ema_codes = verify_json_docs(ema_codes_dir)

        all_dfs = []

        # Solo se usan los 'ema_codes' existentes
        for town, code in ema_codes.items():
            if code in all_data:  # Verificar si el código existe
                data = []
                logger.info(f"Procesando {town} ({code})...")
                
                for date, values in all_data[code]['date'].items():

                    common_fields = {
                            'date': date,
                            'province': all_data[code]['province'],
                            'town': all_data[code]['town'],
                            'ts_insert': values['ts_insert'],
                            'ts_update': values['ts_update']
                    }

                    for key in keys:
                        name_str = values['values'][key]

                        # Verificar si el valor del campo es un número
                        if name_str == 'no_data' or name_str == 'Ip' or name_str == 'Acum':
                            common_fields[key] = name_str
                        else:
                            common_fields[key] = float(str(name_str).replace(',', '.'))
                    
                    data.append(common_fields)
                
                # Crear DataFrame y agregarlo a la lista
                if data:
                    df = pd.DataFrame(data)
                    all_dfs.append(df)

        # Combinar todos los DataFrames en uno solo
        if all_dfs:
            df_final = pd.concat(all_dfs, ignore_index=True)

            temp_csv = os.path.join(temp_csv_dir, f'{name}.csv')

            df_final.to_csv(
                temp_csv, 
                sep=',',
                encoding='utf-8',
                header=True,
                decimal='.',
                index=False
            )

            logger.info(f"Archivo de {name} creado correctamente en {temp_csv_dir} ")
            return None
        else:
            logger.info("No hay datos válidos para procesar")
            return None
    except ValueError as e:
        logger.error(f"Error al acceder al JSON: {str(e)}")

def build_journal(codes_group, server_response, fetched_url, fetched_date):
    '''Función para crear un JSON que registra los errores al hacer fetch al API'''
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    error_journal_dir = os.path.join(api_dir, 'error_journal', 'errors.json')

    os.makedirs(os.path.dirname(error_journal_dir), exist_ok=True)

    json_format = {
        "station_code": codes_group,
        "url": fetched_url,
        "server_response": str(server_response),
        "fetched_date": fetched_date
    }

    try:
        # Verificar si el archivo existe y cargar datos (o lista vacía si no existe)
        existing_data = verify_json_docs(
            error_journal_dir,
            "No existe el archivo de errores. Se creará uno nuevo."
        )
        if not isinstance(existing_data, list):
            existing_data = []
        existing_data.append(json_format)
    except ValueError:
        # Si el archivo no existe, empezar con una lista nueva
        existing_data = [json_format]
    
    # Guardar los datos actualizados
    with open(error_journal_dir, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"No se recibieron datos válidos. Ver --> {error_journal_dir}")
    return None

def load_progress(progress_file: str):
    '''Función para cargar el progreso previo desde archivo si existe'''
    try:
        # Verificar y cargar el archivo de progreso
        data = verify_json_docs(
            progress_file,
            "No existe el archivo de progreso. Se empezará desde cero."
        )
        # Convertir las listas de fechas a sets
        processed_dates = {k: set(v) for k, v in data.get('processed_dates', {}).items()}
        stations_data = data.get('stations_data', {})
        return processed_dates, stations_data
    except ValueError as e:
        logger.warning(f"{e}")
        return defaultdict(set), {}
    except Exception as e:
        logger.warning(f"Error al cargar progreso previo: {e}")
        return defaultdict(set), {}

def save_progress(progress_file, processed_dates, stations_data):
    '''Función para guardar el progreso actual'''
    try:
        progress_data = {
            'processed_dates': {k: list(v) for k, v in processed_dates.items()},
            'stations_data': stations_data
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error al guardar progreso: {e}")

def update_timestamp(stations_data, station_code, date_key):
    '''Función para actualiza el timestamp de updatedAt para la fecha actual en string'''
    now = datetime.now(timezone.utc).isoformat()
    stations_data[station_code]['date'][date_key]['ts_update'] = now