import pandas as pd
import os
import json

def data_to_csv(name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    temp_csv_dir = os.path.join(api_dir, 'csv')
    all_data_dir = os.path.join(api_dir, 'json', 'weather_data.json')
    ema_codes_dir = os.path.join(api_dir, 'json', 'ema_codes.json')

    with open(all_data_dir, 'r', encoding='utf-8') as f:
        station_info = json.load(f)

    with open(ema_codes_dir, 'r', encoding='utf-8') as f:
        ema_codes = json.load(f)

    all_dfs = []

    # Solo se usan los 'ema_codes' existentes
    for town, code in ema_codes.items():
        if code in station_info:  # Verificar si el código existe
            data = []
            print(f"Procesando {town} ({code})...")
            
            for date, values in station_info[code]['date'].items():
                name_str = values['values'][name]
                
                # Verificar si el valor del campo es un número
                if name_str == 'no_data' or name_str == 'Ip' or name_str == 'Acum':
                    unit_name = name_str
                else:
                    unit_name = float(str(name_str).replace(',', '.'))
                # Fecha;Codigo_municipio;Provincia;Municipio;Hora;<Datos>;ts_insert;ts_update
                data.append({
                        'date': date,
                        'province': station_info[code]['province'],
                        'town': station_info[code]['town'],
                        name: unit_name,
                        'ts_insert': values['ts_insert'],
                        'ts_update': values['ts_update']
                })
            
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

        print(f"Archivo de {name} creado correctamente en {temp_csv_dir} ")
        return None
    else:
        print("No hay datos válidos para procesar")
        return None