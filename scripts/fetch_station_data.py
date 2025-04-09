import os
import socket
import time
from datetime import datetime, timedelta, timezone
import requests
from http.client import RemoteDisconnected
from dotenv import load_dotenv
from .utils import *
import logging
from requests.exceptions import (
    ConnectionError, Timeout,
    RequestException, HTTPError
)
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
    before_sleep_log
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class RateLimitException(Exception):
    """Excepción para errores de rate limiting con tiempo de espera."""
    def __init__(self, retry_after=120, message=None):
        self.retry_after = retry_after
        msg = message or f"Límite de tasa alcanzado. Reintentar después de {retry_after} segundos."
        super().__init__(msg)

def is_rate_limit_error(response):
    '''Determina si la respuesta indica un error de rate limiting para hacer reintentos'''
    if not hasattr(response, 'status_code'):
        return False
        
    if response.status_code == 429:
        return True
        
    try:
        json_data = response.json()
        return json_data.get('estado') == 429 or json_data.get('status') == 429
    except (ValueError, AttributeError):
        return False
    
# Decorador de tenacity para manejar los RateLimit y reintentar
api_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=10, max=120),
    retry=(
        retry_if_exception(lambda e: isinstance(e, RateLimitException)) |
        retry_if_exception_type(ConnectionError) |
        retry_if_exception_type(Timeout) |
        retry_if_exception_type(RemoteDisconnected) |
        retry_if_exception_type(RequestException) |
        retry_if_exception_type(HTTPError) |
        retry_if_exception_type(socket.gaierror) 
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

@api_retry
def api_request(url, headers=None, timeout=30):
    """Realiza peticiones HTTP con manejo de errores y rate limiting."""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if is_rate_limit_error(response):
            raise RateLimitException(retry_after=61)
            
        response.raise_for_status()
        
        return response.json() if response.content else None
        
    except HTTPError as http_err:
        logger.error(f"Error HTTP {http_err.response.status_code}: {http_err}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise

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

    try:
        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time:
            last_request_time = datetime.fromisoformat(last_request_time)
            elapsed_time = datetime.now(timezone.utc) - last_request_time
            if elapsed_time < timedelta(seconds=1):
                time.sleep(1 - elapsed_time.total_seconds())
        
        # Construir URL y headers
        weather_values_url = build_url(encoded_init_date,encoded_end_date,station_code)
        
        # Verifico que existe AEMET_API_KEY
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None
        
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
            return None
        
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
                return None
            
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
                    # station_info["date"][date] = {
                    #     "avg_t": day_data.get('tmed', 'no_data'),
                    #     "max_t": day_data.get('tmax', 'no_data'),
                    #     "min_t": day_data.get('tmin', 'no_data'),
                    #     "precip": day_data.get('prec', 'no_data'),
                    #     "avg_vel": day_data.get('velmedia', 'no_data'),
                    #     "max_vel": day_data.get('racha', 'no_data'),
                    #     "avg_rel_hum": day_data.get('hrMedia', 'no_data'),
                    #     "max_rel_hum": day_data.get('hrMax', 'no_data'),
                    #     "min_rel_hum": day_data.get('hrMin', 'no_data'),
                    # }

                    station_info["date"][date] = {
                        date: format_historical_weather_data(day_data)
                    }
                
                grouped_station.append(station_info)
            logger.info(f"Información del grupo extraída correctamente")
            return grouped_station
        else:
            error_msg = response.get('descripcion', 'Error desconocido')
            logger.error(f"Error en la API: {error_msg}")
            return None
    
    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=station_code,
            server_status=response.status_code,
            server_response=str(e), 
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date)
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado fetch_station_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=station_code,
            server_status=response.status_code,
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None
    
@api_retry
def fetch_error_data(last_request_time=None):
    """Función para obtener los datos de las estaciones que fallaron anteriormente error_journal/errors.json"""
    response = {}
    grouped_stations = []
    data_url = None
    current_url = None

    try:
        # Obtener la lista de las url que fallaron
        url_list = re_fetch_errors_journal()
        if not url_list:
            logger.info("No hay URL's para procesar")
            return None

        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time:
            last_request_time = datetime.fromisoformat(last_request_time)
            elapsed_time = datetime.now(timezone.utc) - last_request_time
            if elapsed_time < timedelta(seconds=1):
                sleep_time = 1 - elapsed_time.total_seconds()
                time.sleep(sleep_time)

        # Verificar que la API_KEY este configurada
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None
        
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
                # station_info["date"][date] = {
                #     "avg_t": station_data.get('tmed', 'no_data'),
                #     "max_t": station_data.get('tmax', 'no_data'),
                #     "min_t": station_data.get('tmin', 'no_data'),
                #     "precip": station_data.get('prec', 'no_data'),
                #     "avg_vel": station_data.get('velmedia', 'no_data'),
                #     "max_vel": station_data.get('racha', 'no_data'),
                #     "avg_rel_hum": station_data.get('hrMedia', 'no_data'),
                #     "max_rel_hum": station_data.get('hrMax', 'no_data'),
                #     "min_rel_hum": station_data.get('hrMin', 'no_data'),
                # }

                station_info["date"][date] = {
                    date: format_historical_weather_data(station_data)
                }

                grouped_stations.append(station_info)

            logger.info(f"Información del url {i} extraída correctamente")

        return grouped_stations if grouped_stations else None

    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=current_url if current_url else "URL no disponible",
            server_status=response.status_code,
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado en fetch_error_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            name="errors",
            codes_group=current_url if current_url else "URL no disponible",
            server_status=response.status_code,
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None

@api_retry
def fetch_prediction_station_data(town_code, last_request_time=None):
    '''Obtiene los datos de predicción meteorológica para un municipio específico.'''
    api_key = os.getenv("AEMET_API_KEY")
    if not api_key:
        logger.error("API key no configurada")
        return None
    
    # Control de tasa global (1 petición por segundo como mínimo)
    if last_request_time:
        try:
            last_request_time = datetime.fromisoformat(last_request_time)
            elapsed_time = datetime.now(timezone.utc) - last_request_time
            if elapsed_time < timedelta(seconds=1):
                time.sleep(1 - elapsed_time.total_seconds())
        except ValueError as e:
            logger.warning(f"Formato de fecha inválido: {last_request_time} - {str(e)}")

    headers = {
        'accept': 'application/json',
        'api_key': api_key,
        'cache-control': 'no-cache'
    }
    response = {}

    try:
        # Primera petición para obtener URL de los datos
        weather_values_url = build_url(town_code=town_code)
        response = api_request(weather_values_url, headers=headers)
        
        if not response or response.get('estado') != 200:
            error_msg = response.get('descripcion', 'Error desconocido') if response else 'Respuesta vacía'
            logger.error(f"Error en la API: {error_msg}")
            return None
        
        data_url = response.get('datos')
        if not data_url:
            logger.error("No se encontró URL de datos en la respuesta")
            return None
            
        # Segunda petición para los datos reales
        data = api_request(data_url)
        
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.error("Datos de predicción no disponibles o formato incorrecto")
            return None
        
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
        
        return station_info
    
    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        build_journal(
            name="error_prediction",
            codes_group=town_code,
            server_status=response.status_code,
            server_response=str(e),
            fetched_url=data_url if 'data_url' in locals() else "URL no disponible",
            fetched_date=datetime.now(timezone.utc).isoformat()
        )
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado en fetch_prediction_station_data: {str(e)}", exc_info=True)
        build_journal(
            name="error_prediction",
            codes_group=town_code,
            server_status=response.status_code,
            server_response=str(e),
            fetched_url=data_url if 'data_url' in locals() else "URL no disponible",
            fetched_date=datetime.now(timezone.utc).isoformat()
        )
        return None