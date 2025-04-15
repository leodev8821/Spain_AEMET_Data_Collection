from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait,
    wait_combine,
    wait_exponential,
    retry_if_exception,
    retry_if_exception_type,
    wait_random
)
from requests.exceptions import (
    ConnectionError, Timeout, RequestException, HTTPError
)
from http.client import RemoteDisconnected
from xmlrpc.client import ProtocolError
import socket
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)


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

# Clase personalizada que hereda de wait.wait_base
class wait_rate_limit(wait.wait_base):
    '''
    Clase personalizada para gestionar los tiempos de espera entre peticiones.
    Si es RateLimitException el tiempo de espera es el indicado en retry_after
    Si es otra excepción, el tiempo de espera será el wait_combine
    '''
    def __init__(self):
        self.default_wait = wait_combine(
            wait_exponential(multiplier=1, min=4, max=60),
            wait_random(min=1, max=3)
        )

    def __call__(self, retry_state):
        if retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
            if isinstance(exc, RateLimitException):
                return float(exc.retry_after)
            
        return self.default_wait(retry_state)

def custom_before_sleep(retry_state):
    '''Configuración de mensaje personalizado en api_retry'''
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        logger.warning(f"Reintentando después de {retry_state.next_action.sleep:.1f} segundos por {exc.__class__.__name__}...")

# Decorador de tenacity para manejar los RateLimit y reintentar
api_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_rate_limit(),
    retry=(
        retry_if_exception(lambda e: isinstance(e, RateLimitException)) |
        retry_if_exception_type(ConnectionError) |
        retry_if_exception_type(Timeout) |
        retry_if_exception_type(RemoteDisconnected) |
        retry_if_exception_type(RequestException) |
        retry_if_exception_type(HTTPError) |
        retry_if_exception_type(socket.gaierror) |
        retry_if_exception_type(ProtocolError)
    ),
    before_sleep=custom_before_sleep,
    reraise=True
)