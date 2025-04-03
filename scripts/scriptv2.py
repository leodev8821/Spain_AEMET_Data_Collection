import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from .obtain_ema_code import *
from .fetch_station_data import *
import logging
import time

# Configuración global
DEFAULT_START_DATE = '2025-01-01T00:00:00UTC'
REQUEST_DELAY = 3.0  # segundos entre solicitudes 
STATION_TIMEOUT = 30  # segundos máximo por estación
MAX_RETRIES = 3  # reintentos por estación

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_progress(progress_file):
    """Carga el progreso previo desde archivo si existe"""
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Diccionario {station_code: set(fechas_procesadas)}
                processed_dates = {k: set(v) for k, v in data.get('processed_dates', {}).items()}
                # Datos ya obtenidos
                stations_data = data.get('stations_data', {})
                return processed_dates, stations_data
        except Exception as e:
            logger.warning(f"Error al cargar progreso previo: {e}")
    return defaultdict(set), {}

def save_progress(progress_file, processed_dates, stations_data):
    """Guarda el progreso actual"""
    try:
        progress_data = {
            'processed_dates': {k: list(v) for k, v in processed_dates.items()},
            'stations_data': stations_data
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error al guardar progreso: {e}")

def update_timestamp(stations_data, station_code, date_key):
    """Actualiza el timestamp de actualización para una fecha específica"""
    now = datetime.now(timezone.utc)
    stations_data[station_code]['date'][date_key]['ts_update'] = now.isoformat()

def historical_data():
    """Obtiene la información histórica de las estaciones de meteorología de la AEMET - España"""
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        progress_file = os.path.join(api_dir, 'json', 'progress.json')
        output_file = os.path.join(api_dir, 'json', 'weather_data.json')

        # 2. Obtener códigos de estaciones
        logger.info("Obteniendo códigos de estaciones EMA")
        obtain_stations_EMA_code()

        # Leer los códigos de las estaciones desde JSON
        json_path = os.path.join(api_dir, 'json', 'ema_codes.json')
        with open(json_path, 'r', encoding='utf-8') as archive:
            ema_codes = json.load(archive)

        # 3. Cargar progreso previo
        processed_dates, stations_data = load_progress(progress_file)

        # 4. Configurar rango de fechas
        encoded_init_date = DEFAULT_START_DATE.replace(':', '%3A')
        now = datetime.now(timezone.utc)
        end_date_str = now.strftime('%Y-%m-%dT%H:%M:%S') + 'UTC'
        encoded_end_date = end_date_str.replace(':', '%3A')

        # 5. Procesar estaciones
        total_stations = len(ema_codes)

        for i, (station_name, station_code) in enumerate(ema_codes.items(), 1):
            logger.info(f"[{i}/{total_stations}] Procesando estación: {station_name}")

            # Determinar fechas faltantes para esta estación
            existing_dates = processed_dates.get(station_code, set())

            # Obtener datos de la estación (solo fechas faltantes)
            result = fetch_station_data(
                encoded_init_date,
                encoded_end_date,
                station_code
            )

            # Si no hay información de esa estación, continúa con la siguiente
            if not result:
                logger.warning(f"No se obtuvieron datos para {station_name}")
                continue

            # Asegurarnos de que la estación existe en processed_dates
            if station_code not in processed_dates:
                processed_dates[station_code] = set()

            # Filtrar solo las fechas que no hemos procesado
            new_data = {}
            for date, values in result['date'].items():
                if date not in existing_dates:
                    new_data[date] = {
                        'values': values,
                        'ts_insert': now.isoformat(),
                        'ts_update': now.isoformat()
                    }

            if not new_data:
                logger.info(f"No hay datos nuevos para {station_name}")
                continue

            # Actualizar los datos de la estación
            if station_code not in stations_data:
                stations_data[station_code] = {
                    "town_code": station_code,
                    "province": result["province"],
                    "town": result["town"],
                    "date": {}
                }
            
            # Agregar solo datos nuevos
            stations_data[station_code]['date'].update(new_data)
            
            # Actualizar fechas procesadas
            processed_dates[station_code].update(new_data.keys())

            # Actualizar timestamps para las nuevas fechas
            for date_key in new_data.keys():
                update_timestamp(stations_data, station_code, date_key)

            # Guardar progreso cada 5 estaciones o al final
            if i % 5 == 0 or i == total_stations:
                save_progress(progress_file, processed_dates, stations_data)

            # Una espera para la nueva fetch
            time.sleep(REQUEST_DELAY)

        # 6. Guardar resultados finales
        if stations_data:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(stations_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Datos guardados en {output_file}")
            return stations_data
        
        logger.warning("No se obtuvieron datos válidos")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)