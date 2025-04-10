import logging
import json
import os
import pandas as pd
from .utils import verify_json_docs

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

def safe_get_value(data, key, default=0):
    '''Función para reemplazar strings vacíos con 0'''
    value = data.get(key, default)
    return default if value == "" else value

def process_prediction_data(prediction_weather_data: list, name: str, key: str, value: str, extra_fields: list) -> list:
    """
    Procesa los datos de predicción meteorológica para convertirlos en formato CSV.
    
    Args:
        prediction_weather_data: Lista de diccionarios con los datos meteorológicos
        name: Nombre de la métrica a procesar
        key: Clave principal en los datos JSON
        value: Clave del valor principal en los datos JSON
        extra_fields: Lista de campos adicionales a incluir
        
    Returns:
        Lista de diccionarios con los datos procesados para CSV
    """
    processed_data = []
    
    for entry in prediction_weather_data:
        row = {
            'id': entry['id'],
            'town': entry['town'],
            'province': entry['province'],
            'fetched_date': entry['fetched'][:10]
        }
        
        # Procesar las predicciones para cada día
        for day in ['day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6', 'day_7']:
            if day in entry['prediction']:
                day_data = entry['prediction'][day]
                date_key = next(iter(day_data.keys()))  # Obtiene la primera clave (timestamp)
                row[f'{day}_date'] = date_key[:10]  # Solo la fecha
                
                if key in day_data[date_key]:
                    metric_data = day_data[date_key][key]
                    
                    # Para métricas con estructura compleja (temperatura, sensTermica, humedadRelativa)
                    if name in ['temperatura', 'sens_termica', 'humedad_relativa']:
                        row[f'{day}_maxima'] = metric_data.get('maxima', 0)
                        row[f'{day}_minima'] = metric_data.get('minima', 0)
                        
                        for dato in metric_data.get('dato', []):
                            hora = dato.get('hora', '')
                            val = dato.get('value', 0)
                            row[f'{day}_hora{hora}'] = val
                    
                    # Para estado_cielo (con descripción)
                    elif name == "estado_cielo":
                        if isinstance(metric_data, list):
                            for val in metric_data:
                                periodo = val.get('periodo', '').replace('-', '_')  # 00-24 -> 00_24
                                row_val = safe_get_value(val, 'value', "")
                                row_desc = val.get('descripcion', "")
                                
                                # Solo agregar si hay datos
                                if row_val != "" or row_desc != "":
                                    row[f'{day}_{periodo}_value'] = row_val
                                    row[f'{day}_{periodo}_desc'] = row_desc

                    elif name == "viento":
                        if isinstance(metric_data, list):
                            for val in metric_data:
                                periodo = val.get('periodo', '').replace('-', '_')
                                velocidad = safe_get_value(val, 'velocidad', 0)
                                direccion = val.get('direccion', '')
                                
                                # Solo agregar si hay datos relevantes
                                if velocidad != 0 or direccion != "":
                                    row[f'{day}_{periodo}_velocidad'] = velocidad
                                    row[f'{day}_{periodo}_direccion'] = direccion
                    
                    # Para otras métricas simples
                    else:
                        if isinstance(metric_data, list):
                            for i, val in enumerate(metric_data, start=1):
                                if isinstance(val, dict):
                                    row[f'{day}_value{i}'] = safe_get_value(val, value)
                                    # Agregar campos extra si existen
                                    for field in extra_fields:
                                        if field in val:
                                            row[f'{day}_{field}{i}'] = val[field]
                                else:
                                    row[f'{day}_value{i}'] = val if val != "" else 0
                        else:
                            row[f'{day}_value'] = safe_get_value(metric_data, value)
        
        processed_data.append(row)
    
    return processed_data

def predictions_to_csv(name: str):
    '''Función para crear los csv de las predicciones'''
    match name:
        case "precipitaciones":
            key = "probPrecipitacion"
            value = "value"
            extra_fields = []
        case "cota_nieve":
            key = "cotaNieveProv"
            value = "value"
            extra_fields = []
        case "estado_cielo":
            key = "estadoCielo"
            value = "value"
            extra_fields = ["descripcion"]
        case "viento":
            key = "viento"
            value = "velocidad"
            extra_fields = ["direccion"]
        case "racha_max":
            key = "rachaMax"
            value = "value"
            extra_fields = []
        case "temperatura":
            key = "temperatura"
            value = None
            extra_fields = []
        case "sens_termica":
            key = "sensTermica"
            value = None
            extra_fields = []
        case "humedad_relativa":
            key = "humedadRelativa"
            value = None
            extra_fields = []

    try:
        # Configuración de directorios
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        prediction_csv_dir = os.path.join(api_dir, 'csv', 'prediction')
        prediction_weather_dir = os.path.join(api_dir, 'json', f'prediction_progress.json')
        
        os.makedirs(prediction_csv_dir, exist_ok=True)

        # Cargar los datos
        with open(prediction_weather_dir, 'r', encoding='utf-8') as f:
            prediction_weather_data = json.load(f)

        # Procesar los datos
        processed_data = process_prediction_data(
            prediction_weather_data,
            name,
            key,
            value,
            extra_fields
        )

        # Convertir a DataFrame y guardar
        df = pd.DataFrame(processed_data)
        csv_path = os.path.join(prediction_csv_dir, f'prediccion_{name}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"📝 Archivo prediccion_{name}.csv creado en {csv_path}")
        
    except Exception as e:
        logger.error(f"❌ Error al procesar los datos: {str(e)}")
        return None
    
def process_historical_data(all_data: dict, ema_codes: dict, keys: list) -> list:
    """
    Prepara los datos históricos para ser convertidos a CSV.
    
    Args:
        all_data: Diccionario con todos los datos meteorológicos
        ema_codes: Diccionario con los códigos EMA y sus localidades
        keys: Lista de claves a procesar para cada entrada
        
    Returns:
        Lista de DataFrames con los datos procesados
    """
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
    
    return all_dfs

def historical_data_to_csv(name: str):
    '''Función para crear los csv de los datos históricos'''
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
        # Configuración de directorios
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        temp_csv_dir = os.path.join(api_dir, 'csv', 'historical')
        all_data_dir = os.path.join(api_dir, 'json', 'weather_data.json')
        ema_codes_dir = os.path.join(api_dir, 'json', 'ema_codes.json')

        os.makedirs(temp_csv_dir, exist_ok=True)

        # Cargar los datos
        all_data = verify_json_docs(all_data_dir, message="No esta creado weather_codes.json")
        ema_codes = verify_json_docs(ema_codes_dir, message="No esta creado ema_codes.json")

        # Preparar los datos para CSV
        all_dfs = process_historical_data(all_data, ema_codes, keys)

        # Combinar todos los DataFrames en uno solo y guardar
        if all_dfs:
            df_final = pd.concat(all_dfs, ignore_index=True)
            temp_csv = os.path.join(temp_csv_dir, f'{name}_historico.csv')

            df_final.to_csv(
                temp_csv, 
                sep=',',
                encoding='utf-8',
                header=True,
                decimal='.',
                index=False
            )

            logger.info(f"📝 Archivo de {name} creado correctamente en {temp_csv_dir}")
        else:
            logger.info("No hay datos válidos para procesar")
            
    except ValueError as e:
        logger.error(f"Error al acceder al JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")