from datetime import datetime, timedelta, timezone
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Excepción personalizada para errores de rate limiting
class RateLimitException(Exception):
    def __init__(self, retry_after=61):
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
        retry_if_exception_type((ConnectionError, Timeout, RemoteDisconnected))
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# Realiza peticiones HTTP con manejo de rate limiting
def api_request(url, headers=None, timeout=30):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)

        # Si lanza un error de exceso de peticiones, setea el tiempo para reintento en 61 segundos
        if is_rate_limit_error(response):
            retry_after = 61
            raise RateLimitException(retry_after)
        
        # Lanza cualquier error de fetch
        response.raise_for_status()
        # Retorna la respuesta
        return response.json() if response.content else None
    
    except RequestException as e:
        logger.error(f"Error en la petición HTTP: {str(e)}")
        return e
    except Exception as e:
        logger.error(f"Error inesperado api_request: {str(e)}")
        return e

# Función que obtiene los datos de cada estación y los alamacena en un JSON
def fetch_station_data(
    encoded_init_date,
    encoded_end_date,
    station_code,
    last_request_time=None
):

    # Función interna para manejar los reintentos
    @api_retry
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
        weather_values_url = (
            f'https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/'
            f'fechaini/{encoded_init_date}/fechafin/{encoded_end_date}/estacion/{station_code}'
        )
        
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
        logger.info(f"Obteniendo datos para estación {station_code}")
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
            logger.debug(f"URL de datos obtenida: {data_url}")
            
            # Segunda petición para los datos reales
            data = _fetch_with_retry(data_url)
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.warning("No se recibieron datos válidos")
                return None
            
            # Procesar datos en el formato específico
            station_info = {
                "town_code": data[0].get('indicativo', 'no_data'),
                "province": data[0].get('provincia', 'no_data'),
                "town": data[0].get('nombre', 'no_data'),
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
            
            return station_info
        else:
            error_msg = response.get('descripcion', 'Error desconocido')
            logger.error(f"Error en la API: {error_msg}")
            return None
    
    except RateLimitException as e:
        logger.warning(f"Rate limit alcanzado. Esperando {e.retry_after} segundos...")
        time.sleep(e.retry_after)
        return None
    
    except RetryError as e:
        logger.error(f"Fallo después de múltiples intentos: {str(e)}")
        return None
    
    except Exception as e:
        logger.error(f"Error inesperado fetch_station_data: {str(e)}", exc_info=True)
        return None