from datetime import datetime, timedelta
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    RequestException,
    JSONDecodeError
)
from http.client import RemoteDisconnected
import time
import os
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
    before_sleep_log
)
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RateLimitException(Exception):
    """Excepción personalizada para errores de rate limiting"""
    def __init__(self, retry_after=60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")

def is_rate_limit_error(response):
    """Determina si la respuesta indica un error de rate limiting"""
    try:
        if response.status_code == 429:
            return True
        json_data = response.json()
        return json_data.get('estado') == 429
    except (ValueError, AttributeError):
        return False
    
# Decorador para manejar los RateLimit
api_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=5, max=120),
    retry=(
        retry_if_exception(lambda e: isinstance(e, RateLimitException)) |
        retry_if_exception_type((ConnectionError, Timeout, RemoteDisconnected))
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

def api_request(url, headers=None, timeout=10):
    """Realiza peticiones HTTP con manejo de rate limiting"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if is_rate_limit_error(response):
            retry_after = 61
            raise RateLimitException(retry_after)
        response.raise_for_status()
        return response.json() if response.content else None
    except RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return None

def fetch_station_data(
    encoded_init_date,
    encoded_end_date,
    station_code,
    last_request_time=None
):
    '''Función que obtiene los datos de cada estación y los alamacena en un JSON'''

    @api_retry
    def _fetch_with_retry(url, headers=None):
        """Función interna para manejar los reintentos"""
        return api_request(url, headers=headers, timeout=15)

    try:
        # Control de tasa global (1 petición por segundo como mínimo)
        if last_request_time and (datetime.now() - last_request_time) < timedelta(seconds=1):
            sleep_time = 1 - (datetime.now() - last_request_time).total_seconds()
            time.sleep(sleep_time)
        
        # Construir URL y headers
        weather_values_url = (
            f'https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/'
            f'fechaini/{encoded_init_date}/fechafin/{encoded_end_date}/estacion/{station_code}'
        )
        
        # Verifico que existe AEMET_API_KEY
        api_key = os.getenv("AEMET_API_KEY")
        if not api_key:
            logger.error("API key no configurada")
            return None
        
        headers = {
            'accept': 'application/json',
            'api_key': api_key,
            'cache-control': 'no-cache'
        }
        
        # Primera petición para obtener URL de los datos
        logger.info(f"Obteniendo datos para estación {station_code}")
        response = _fetch_with_retry(weather_values_url, headers=headers)
        if not response:
            logger.error("No se pudo obtener la URL de datos")
            return None
        
        if response.get('estado') == 200:
            data_url = response['datos']
            logger.debug(f"URL de datos obtenida: {data_url}")
            
            # Segunda petición para los datos reales
            data = _fetch_with_retry(data_url)
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning("No se recibieron datos válidos")
                return None
            
            # Procesar datos en el formato específico requerido
            station_info = {
                "town_code": data[0].get('indicativo', 'no_data'),
                "province": data[0].get('provincia', 'no_data'),
                "town": data[0].get('nombre', 'no_data'),
                "date": {}
            }
            
            for day_data in data:
                date = day_data.get('fecha', 'no_data')
                station_info["date"][date] = {
                    "temperature": day_data.get('tmed', 'no_data'),
                    "precipitation": day_data.get('prec', 'no_data'),
                    "hrMedia": day_data.get('hrMedia', 'no_data')
                }
            
            return station_info
        else:
            error_msg = response.get('descripcion', 'Error desconocido')
            logger.error(f"Error en la API: {error_msg}")
            return None
    
    except RateLimitException as e:
        logger.warning(f"Rate limit alcanzado. Esperando {e.retry_after} segundos...")
        time.sleep(e.retry_after)
        return fetch_station_data(encoded_init_date, encoded_end_date, station_code, datetime.now())
    
    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        return None