import logging
import pandas as pd
import os
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

def verify_json_docs(json_path_dir):
    if os.path.exists(json_path_dir):
            with open(json_path_dir, 'r', encoding='utf-8') as f:
                json_info = json.load(f)
                return json_info
    else: 
        raise ValueError("Primero debes general los datos históricos - Opción 2")


def data_to_csv(name):   
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