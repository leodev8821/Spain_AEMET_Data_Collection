import os
import time
import logging
import requests
from dotenv import load_dotenv
from tenacity import RetryError
from requests.exceptions import HTTPError
from datetime import datetime, timedelta, timezone
from .utils import *
from .tenacity_config import RateLimitException, api_retry, is_rate_limit_error

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

@api_retry
def api_request(url, headers=None, timeout=(10, 30)):
    """Función principal que realiza los fetchs teniendo en cuenta el RateLimit para reintentos."""
    try:
        # Hace el fethc a la url con los headers y timeout (con ConnectTimeout y ReadTimeout)
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Evalúa si la fetch lanza un RateLimitException, pasándole el tiempo de retry_after
        if is_rate_limit_error(response):
            raise RateLimitException(retry_after=61)
            
        response.raise_for_status()
        
        # Retorna la respuesta o None si no existe
        return response.json() if response.content else None
        
    except HTTPError as http_err:
        logger.error(f"🛑 Error HTTP {http_err.response.status_code}: {http_err}")
        raise
    except requests.ConnectTimeout as e:
        logger.error(f"🛑 Error ConnectTimeout {str(e)}")
        raise
    except ConnectionError as e:
        if "RemoteDisconnected" in str(e):
            logger.error("🛑 El servidor cerró la conexión abruptamente")
        raise
    except requests.ReadTimeout as e:
        logger.error(f"🛑 Error ReadTimeout {str(e)}")
        raise
    except Exception as e:
        logger.error(f"🛑 Error inesperado: {str(e)}")
        raise

def global_rate(last_request_time):
    '''Función para establecer el control de tasa global (1 petición por segundo como mínimo)'''
    try:
        last_request_time = datetime.fromisoformat(last_request_time.replace('Z', '+00:00'))
        elapsed_time = datetime.now(timezone.utc) - last_request_time

        # Si el tiempo transcurrido es menor a 1.5s, espera lo que falta
        if elapsed_time < timedelta(seconds=1.5):
            time.sleep(1.5 - elapsed_time.total_seconds())
        
        # Retorna la nueva marca de tiempo actualizada (en formato ISO)
        return datetime.now(timezone.utc).isoformat()
    
    except ValueError as e:
        logger.warning(f"Formato de fecha inválido: {last_request_time} - {str(e)}")
        # Retorna la hora actual como fallback
        return datetime.now(timezone.utc).isoformat()

@api_retry
def fetch_historical_station_data(
    encoded_init_date,
    encoded_end_date,
    station_code,
    last_request_time=None
):
    '''Función que obtiene los datos de cada estación y los alamacena en un JSON'''
    response = {}
    data = None
    data_url = None
    new_last_request_time = last_request_time

    try:
        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time is None:
            last_request_time = datetime.now(timezone.utc).isoformat()
        else:
            last_request_time = global_rate(last_request_time)
        
        # Construir URL y headers
        weather_values_url = build_url(encoded_init_date,encoded_end_date,station_code)
        
        # Verifico que existe AEMET_API_KEY
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None, new_last_request_time
        
        # Headers requeridos por la API
        headers = {
            'accept': 'application/json',
            'api_key': api_key,
            'cache-control': 'no-cache'
        }
        
        # Primera petición para obtener URL de los datos
        logger.info(f"Obteniendo datos del grupo...")
        response = api_request(weather_values_url, headers=headers)

        # Si response es una excepción (RateLimitException, RequestException, etc.)
        if isinstance(response, Exception):
            raise response
        
        # Si no hay respuesta válida
        if not response:
            logger.error("No se pudo obtener la URL de datos")
            return None, new_last_request_time
        
        # Si hay respuesta correcta, obtengo la url para el siguiente fetch
        if response.get('estado') == 200:
            data_url = response.get('datos')
            
            # Segunda petición para los datos reales
            data = api_request(data_url)

            if not data or not isinstance(data, list) or len(data) == 0:
                fetched_date = datetime.now(timezone.utc).isoformat()
                build_journal(
                    name="errors",
                    codes_group=station_code,
                    server_response=data, 
                    fetched_url=data_url,
                    fetched_date=fetched_date
                )
                return None, new_last_request_time
            
            grouped_station = []
            for i in range(len(data)):
                # Procesar datos en el formato específico
                station_info = {
                    "town_code": data[i].get('indicativo', 'no_data'),
                    "province": data[i].get('provincia', 'no_data'),
                    "town": data[i].get('nombre', 'no_data'),
                    "date": {}
                }

                # Recorre la fecha para insertar los datos
                for day_data in data:
                    date = day_data.get('fecha', 'no_data')

                    station_info["date"][date] = {
                        date: format_historical_weather_data(day_data)
                    }
                
                grouped_station.append(station_info)
            logger.info(f"Información del grupo extraída correctamente")
            return grouped_station, datetime.now(timezone.utc).isoformat()
        else:
            logger.error(f"Error en la API: {response.get('descripcion', 'Error desconocido')}")
            return None, new_last_request_time
    
    except RetryError as e:
        # Despues de 5 intentos, se crea la entrada en error_journal/errors.json
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=station_code,
            server_response=str(e), 
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date)
        return None, last_request_time
    
    except Exception as e:
        logger.error(f"Error inesperado fetch_station_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=station_code,
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None, last_request_time
    
@api_retry
def fetch_error_data(last_request_time=None):
    """Función para obtener los datos de las estaciones que fallaron (historicos) en error_journal/errors.json"""
    response = {}
    grouped_stations = []
    data_url = None
    current_url = None
    new_last_request_time = last_request_time

    try:
        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time is None:
            last_request_time = datetime.now(timezone.utc).isoformat()
        else:
            last_request_time = global_rate(last_request_time)

        # Obtener la lista de las url que fallaron
        url_list = re_fetch_errors_journal()
        if not url_list:
            logger.info("No hay URL's para procesar")
            return None, new_last_request_time

        # Verificar que la API_KEY este configurada
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None, new_last_request_time
        
        # Configuración de los headers
        headers = {
            'accept': 'application/json',
            'api_key': api_key,
            'cache-control': 'no-cache'
        }

        # Procesar cada url que falló
        i=0
        for url in url_list:
            i += 1
            current_url = url
            logger.info(f"Procesando [{i}/{len(url_list)}]")
            
            # Primera petición para obtner la url con los datos
            response = api_request(url, headers=headers)

            if isinstance(response, Exception):
                raise response
            if not response:
                logger.error("No se pudo obtener la URL de datos")
                continue
            
            # Verifica la respuesta de la API
            if response.get('estado') != 200:
                error_msg = response.get('descripcion', 'Error desconocido')
                logger.error(f"Error en la API: {error_msg}")
                continue

            data_url = response.get('datos')
            if not data_url:
                logger.error("No se encontró URL de datos en la respuesta")
                continue

            # Segunda petición para obtener los datos
            data = api_request(data_url)
            
            # Validación de data
            if not data or not isinstance(data, list):
                logger.error("Datos no válidos o vacíos recibidos")
                fetched_date = datetime.now(timezone.utc).isoformat()
                build_journal(
                    name="errors",
                    codes_group=url,
                    server_response=data,
                    fetched_url=data_url,
                    fetched_date=fetched_date
                )
                continue

            # Procesar la información obtenida en data
            for station_data in data:
                if not isinstance(station_data, dict):
                    continue

                station_info = {
                    "town_code": station_data.get('indicativo', 'no_data'),
                    "province": station_data.get('provincia', 'no_data'),
                    "town": station_data.get('nombre', 'no_data'),
                    "date": {}
                }

                date = station_data.get('fecha', 'no_data')

                station_info["date"][date] = {
                    date: format_historical_weather_data(station_data)
                }

                grouped_stations.append(station_info)

            logger.info(f"✅ Información del url {i} extraída correctamente")
            new_last_request_time = datetime.now(timezone.utc).isoformat()

        return (grouped_stations if grouped_stations else None), new_last_request_time

    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=current_url if current_url else "URL no disponible",
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None, new_last_request_time
    
    except Exception as e:
        logger.error(f"Error inesperado en fetch_error_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=current_url if current_url else "URL no disponible",
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None, new_last_request_time

@api_retry
def fetch_prediction_station_data(town_code, last_request_time=None):
    '''Obtiene los datos de predicción meteorológica para un municipio específico.'''
    new_last_request_time = last_request_time
    response = {}

    try:
        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time is None:
            last_request_time = datetime.now(timezone.utc).isoformat()
        else:
            last_request_time = global_rate(last_request_time)

        # Verificar la API_KEY
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None, new_last_request_time
        
        headers = {
            'accept': 'application/json',
            'api_key': api_key,
            'cache-control': 'no-cache'
        }

        # Primera petición para obtener URL de los datos
        weather_values_url = build_url(town_code=town_code)
        response = api_request(weather_values_url, headers=headers)
        
        if not response or response.get('estado') != 200:
            error_msg = response.get('descripcion', 'Error desconocido') if response else 'Respuesta vacía'
            logger.error(f"Error en la API: {error_msg}")
            return None, new_last_request_time
        
        data_url = response.get('datos')

        if not data_url:
            logger.error("No se encontró URL de datos en la respuesta")
            return None, new_last_request_time
            
        # Segunda petición para los datos reales
        data = api_request(data_url)
        
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.error("Datos de predicción no disponibles o formato incorrecto")
            build_journal(name="prediction_error",codes_group=town_code,server_response=data,fetched_date=last_request_time)
            return None, new_last_request_time
        
        # Procesar datos de predicción
        station_info = {
            "id": data[0].get("id", "no_data"),
            "town": data[0].get('nombre', 'no_data'),
            "province": data[0].get('provincia', 'no_data'),
            "elaborated": data[0].get('elaborado', 'no_data'),
            "fetched": datetime.now(timezone.utc).isoformat(),
            "prediction": {}
        }

        for i, day in enumerate(data[0]['prediccion']['dia'], start=1):
            fecha = day.get('fecha', 'no_data')
            station_info["prediction"][f"day_{i}"] = {
                fecha: format_prediction_weather_data(day)
            }
        
        return station_info, datetime.now(timezone.utc).isoformat()
    
    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        build_journal(
            name="error_prediction",
            codes_group=town_code,
            server_response=str(e),
            fetched_url=data_url if 'data_url' in locals() else "URL no disponible",
            fetched_date=datetime.now(timezone.utc).isoformat()
        )
        return None, new_last_request_time
    
    except Exception as e:
        logger.error(f"Error inesperado en fetch_prediction_station_data: {str(e)}", exc_info=True)
        build_journal(
            name="error_prediction",
            codes_group=town_code,
            server_response=str(e),
            fetched_url=data_url if 'data_url' in locals() else "URL no disponible",
            fetched_date=datetime.now(timezone.utc).isoformat()
        )
        return None, new_last_request_time