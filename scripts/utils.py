import logging
import requests
import json
import os
from datetime import datetime
import re
from dotenv import load_dotenv
from .verify_files import *

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
    
def re_fetch_errors_journal():
    '''Función para obtener los url de error_journal/errors.json'''
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        errors_log_dir = os.path.join(api_dir, 'error_journal', 'errors.json')
        error_data = verify_json_docs(errors_log_dir, message="No esta creado errors.json")
        url_to_fetch = []

        for i in range(len(error_data)):
            response = error_data[i].get("server_response", "no_data")
            url_to_fetch.append(response[response.index("http"):len(response)])
        return url_to_fetch
    except ValueError as e:
        logger.error(f"Error al cargar errors.json {str(e)}")

def build_journal(name, codes_group, server_response, fetched_url, fetched_date):
    '''Función para crear un JSON que registra los errores al hacer fetch al API'''
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    error_journal_dir = os.path.join(api_dir, 'error_journal', f'{name}.json')

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

def build_url(
        encoded_init_date:str = None, 
        encoded_end_date:str = None, 
        stations_codes:str = None, 
        town_code:str = None):
    '''Función para construir la url de los endpoints'''
    weather_values_url = ""

    if encoded_init_date != None and encoded_end_date != None and stations_codes != None:
        weather_values_url = (
                f'https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/'
                f'fechaini/{encoded_init_date}/fechafin/{encoded_end_date}/estacion/{stations_codes}'
            )
        return(weather_values_url)
    elif town_code != None:
        weather_values_url = (
                f'https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{town_code}'
            )
        return(weather_values_url)
    
def format_historical_weather_data(station_data):
    '''Función para dar formato al JSON de los valores históricos'''
    return {
        "avg_t": station_data.get('tmed', 'no_data'),
        "max_t": station_data.get('tmax', 'no_data'),
        "min_t": station_data.get('tmin', 'no_data'),
        "precip": station_data.get('prec', 'no_data'),
        "avg_vel": station_data.get('velmedia', 'no_data'),
        "max_vel": station_data.get('racha', 'no_data'),
        "avg_rel_hum": station_data.get('hrMedia', 'no_data'),
        "max_rel_hum": station_data.get('hrMax', 'no_data'),
        "min_rel_hum": station_data.get('hrMin', 'no_data'),
                
    }

def format_prediction_weather_data(day_data):
    '''Función para dar formato al JSON de los valores de previsión'''
    return {
        "probPrecipitacion": day_data.get('probPrecipitacion', []),
        "cotaNieveProv": day_data.get('cotaNieveProv', []),
        "estadoCielo": day_data.get('estadoCielo', []),
        "viento": day_data.get('viento', []),
        "rachaMax": day_data.get('rachaMax', []),
        "temperatura": day_data.get('temperatura', {}),
        "sensTermica": day_data.get('sensTermica', {}),
        "humedadRelativa": day_data.get('humedadRelativa', {}),
        "uvMax": day_data.get('uvMax', 'no_data'),
    }

def check_missing_town_codes():
    """
    Función que compara los codigos de los pueblos entre towns_codes.json y prediction_data.json y genera una lista de los codigos de pueblos pendientes
    """
    try:
        # configuramos la ubicacion del archivo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        json_dir = os.path.join(api_dir, 'json')
        
        towns_codes_path = os.path.join(json_dir, 'towns_codes.json')
        prediction_data_path = os.path.join(json_dir, 'prediction_data.json')
        output_path = os.path.join(json_dir, 'pending_towns_codes.json')

        # cargamos towns_codes.json
        towns_codes = verify_json_docs(json_path_dir=towns_codes_path, message="No existe el archivo towns_codes.json")
        logger.info(f"✅ Cargados los {len(towns_codes)} codigos de pueblos de towns_codes.json")
        
        # Cargamos prediction_data.json
        prediction_data = verify_json_docs(json_path_dir=prediction_data_path, message="No existe el archivo prediction_data.json")
        logger.info(f"✅ Cargados {len(prediction_data)} registros en prediction_data.json")

        # Extraemos los IDS existentes de prediction_data.json
        existing_codes = [entry['id'] for entry in prediction_data if 'id' in entry]
        
        # Generamos el diccionario de los codigos pendientes, que no se encuentran en prediction_data.json
        pending_towns = {}
        for code, town in towns_codes.items():
            if int(code) not in existing_codes:
                pending_towns[code] = town

        logger.info(f"Pendientes {len(pending_towns)} municipios en total")

      # Guardamos el JSON en un archivo con la estructura de towns_codes.json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pending_towns, f, indent=4, ensure_ascii=False)
                    
        logger.info(f"📝 Se han guardado {len(pending_towns)} códigos de municipios pendientes en {output_path}")
        return pending_towns
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None
    
def check_missing_group_codes():
    """
    Función que compara los códigos de los grupos entre codes_group.json y weather_data.json
    y genera una lista de los grupos pendientes en pending_group_codes.json
    """
    try:
        # Configuración de rutas
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        json_dir = os.path.join(api_dir, 'json')
        
        codes_group_path = os.path.join(json_dir, 'codes_group.json')
        weather_data_path = os.path.join(json_dir, 'weather_data.json')
        output_path = os.path.join(json_dir, 'pending_group_codes.json')

        # Cargar codes_group.json
        codes_group = verify_json_docs(json_path_dir=codes_group_path, 
                                     message="No existe el archivo codes_group.json")
        logger.info(f"✅ Cargados {len(codes_group)} grupos de estaciones de codes_group.json")
        
        # Cargar weather_data.json (si existe)
        weather_data = {}
        if os.path.exists(weather_data_path):
            weather_data = verify_json_docs(json_path_dir=weather_data_path, 
                                          message="")
            logger.info(f"✅ Cargados {len(weather_data)} estaciones en weather_data.json")
        else:
            logger.info("ℹ️ No existe weather_data.json, todos los grupos se consideran pendientes")

        # Extraer códigos de estaciones existentes en weather_data.json
        existing_codes = set(weather_data.keys())

        # Determinar qué grupos tienen estaciones pendientes
        pending_groups = {}
        
        for group_name, stations_str in codes_group.items():
            group_stations = set(stations_str.split(','))
            
            # Verificar si alguna estación del grupo no está en weather_data
            missing_stations = group_stations - existing_codes
            
            if missing_stations:
                # Si hay estaciones faltantes, añadir el grupo al diccionario pendiente
                pending_groups[group_name] = stations_str

        logger.info(f"📊 Grupos pendientes: {len(pending_groups)}/{len(codes_group)}")
        logger.info(f"ℹ️ Estaciones faltantes: {sum(len(v.split(',')) for v in pending_groups.values())}")

        # Guardar el archivo con los grupos pendientes
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pending_groups, f, indent=4, ensure_ascii=False)
                    
        logger.info(f"📝 Guardados {len(pending_groups)} grupos pendientes en {output_path}")
        return pending_groups
    
    except Exception as e:
        logger.error(f"❌ Error en check_missing_group_codes: {str(e)}", exc_info=True)
        return None