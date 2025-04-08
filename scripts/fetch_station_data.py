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
    ConnectionError,
    Timeout,
    RequestException
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

# Excepción personalizada para errores de rate limiting
class RateLimitException(Exception):
    def __init__(self, retry_after=120):
        self.retry_after = retry_after
        super().__init__(f"Límite alcanzado. Reintentar después de  {retry_after} segundos.")

# Determina si la respuesta indica un error de rate limiting para hacer reintentos
def is_rate_limit_error(response):
    try:
        if response.status_code == 429:
            return True
        json_data = response.json()
        return json_data.get('estado') == 429
    except (ValueError, AttributeError):
        return False
    
# Decorador de tenacity para manejar los RateLimit y reintentar
api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=10, max=61),
    retry=(
        retry_if_exception(lambda e: isinstance(e, RateLimitException)) |
        retry_if_exception_type((ConnectionError, Timeout, RemoteDisconnected)) |
        retry_if_exception_type(socket.gaierror)
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# Realiza peticiones HTTP con manejo de rate limiting
def api_request(url, headers=None, timeout=30, max_attempts=4):
    @retry(stop=stop_after_attempt(max_attempts),
          wait=wait_exponential(multiplier=1, min=10, max=120),
          retry=retry_if_exception_type((
              ConnectionError,
              Timeout,
              RemoteDisconnected,
              requests.exceptions.ConnectionError,
              requests.exceptions.HTTPError
          )))
    def _request():
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"Error HTTP {response.status_code}: {http_err}")
                if response.status_code == 429:
                    retry_after = 61
                    raise RateLimitException(retry_after=retry_after)
                raise
            return response.json() if response.content else None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error de conexión: {str(e)}")
            raise
        except socket.gaierror as e:
            logger.error(f"Error de resolución DNS: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición HTTP: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error en la petición: {str(e)}")
            raise

    return _request()

# Función que obtiene los datos de cada estación y los alamacena en un JSON
@api_retry
def fetch_station_data(
    encoded_init_date,
    encoded_end_date,
    station_code,
    last_request_time=None
):
    
    data = None
    data_url = None

    # Función interna para manejar los reintentos
    def _fetch_with_retry(url, headers=None):
        return api_request(url, headers=headers)

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
        response = _fetch_with_retry(weather_values_url, headers=headers)

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
            data = _fetch_with_retry(data_url)

            if not data or not isinstance(data, list) or len(data) == 0:
                fetched_date = datetime.now(timezone.utc).isoformat()
                build_journal(codes_group=station_code, server_response=data, fetched_url=data_url,fetched_date=fetched_date)
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
                    station_info["date"][date] = {
                        "avg_t": day_data.get('tmed', 'no_data'),
                        "max_t": day_data.get('tmax', 'no_data'),
                        "min_t": day_data.get('tmin', 'no_data'),
                        "precip": day_data.get('prec', 'no_data'),
                        "avg_vel": day_data.get('velmedia', 'no_data'),
                        "max_vel": day_data.get('racha', 'no_data'),
                        "avg_rel_hum": day_data.get('hrMedia', 'no_data'),
                        "max_rel_hum": day_data.get('hrMax', 'no_data'),
                        "min_rel_hum": day_data.get('hrMin', 'no_data'),
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
            codes_group=station_code, 
            server_response=str(e), 
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date)
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado fetch_station_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            codes_group=station_code, 
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None
    

def fetch_error_data(last_request_time=None):
    """Función para obtener los datos de las estaciones que fallaron anteriormente error_journal/errors.json"""
    grouped_stations = []
    data_url = None
    current_url = None

    # Función interna para reintentos
    def _fetch_with_retry(url, headers=None):
        return api_request(url, headers=headers)

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
            response = _fetch_with_retry(url, headers=headers)

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
            data = _fetch_with_retry(data_url)
            
            # Validación de data
            if not data or not isinstance(data, list):
                logger.error("Datos no válidos o vacíos recibidos")
                fetched_date = datetime.now(timezone.utc).isoformat()
                build_journal(
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

                grouped_stations.append(station_info)

            logger.info(f"Información del url {i} extraída correctamente")

        return grouped_stations if grouped_stations else None

    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            codes_group=current_url if current_url else "URL no disponible",
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado en fetch_error_data: {str(e)}", exc_info=True)
        fetched_date = datetime.now(timezone.utc).isoformat()
        build_journal(
            codes_group=current_url if current_url else "URL no disponible",
            server_response=str(e),
            fetched_url=data_url if data_url else "URL no disponible",
            fetched_date=fetched_date
        )
        return None