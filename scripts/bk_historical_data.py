def historical_data(final_date):
    '''Obtiene la información histórica de las estaciones de meteorología de la AEMET - España'''
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        
        progress_file_path = os.path.join(api_dir, 'json', 'progress.json')
        output_file_path = os.path.join(api_dir, 'json', 'weather_data.json')
        now = datetime.now(timezone.utc).isoformat()

        # 2. Leer los códigos de las estaciones desde JSON
        logger.info("Obteniendo códigos de estaciones EMA")
        json_path = os.path.join(api_dir, 'json', 'codes_group.json')
        ema_codes = verify_json_docs(json_path_dir=json_path, message="Debes crear primero el archivo de códigos EMA - Opción 1")
        
        # 3. Cargar progreso previo
        processed_dates, stations_data = load_progress(progress_file_path)

        # 4. Configurar rango de fechas
        encoded_init_date = DEFAULT_START_DATE.replace(':', '%3A')
        end_date_str = final_date + 'T00:00:00UTC'
        encoded_end_date = end_date_str.replace(':', '%3A')

        # 5. Procesar estaciones
        total_stations = len(ema_codes)

        for i, (group, stations_codes) in enumerate(ema_codes.items(), 1):
            encoded_stations_codes = stations_codes.replace(',', '%2C')
            logger.info(f"[{i}/{total_stations}] Procesando estaciónes del {group}")

            if stations_codes not in processed_dates:
                processed_dates[stations_codes] = set()

            # Obtener datos de la estación (solo fechas faltantes)
            result = fetch_historical_station_data(
                encoded_init_date,
                encoded_end_date,
                encoded_stations_codes,
                last_request_time=now
            )

            # Si no hay información de esa estación, continúa con la siguiente
            if not result:
                logger.warning(f"No se obtuvieron datos para el {group}")
                continue

            # Iterar sobre cada estación en result
            new_dates_for_group  = set()
            for station_data in result: 
                current_station_code = station_data.get('town_code')
                logger.info(f"Procesando estación: [{current_station_code}]")

                # Filtrar solo las fechas que no hemos procesado
                new_data = {}
                for date, values in station_data['date'].items():
                    if date not in processed_dates[stations_codes]:
                        new_data[date] = {
                            'values': values,
                            'ts_insert': now,
                            'ts_update': now
                        }

                        new_dates_for_group.add(date)

                # Si no hay información nueva para la estación, sigue con la siguiente
                if not new_data:
                    logger.info(f"No hay datos nuevos para {current_station_code}")
                    continue

                # Actualizar los datos de la estación
                if current_station_code not in stations_data:
                    stations_data[current_station_code] = {
                        "town_code": current_station_code,
                        "province": station_data["province"],
                        "town": station_data["town"],
                        "date": {}
                    }
                
                # Agregar solo datos nuevos
                stations_data[current_station_code]['date'].update(new_data)
                
                # Actualizar fechas procesadas
            processed_dates[current_station_code].update(new_dates_for_group)

            # Guardar progreso cada grupo de estaciones o al final
            if i % 1 == 0 or i == total_stations:
                logger.info(f"[{i}] grupo de estaciones guardado en progress")
                save_progress(progress_file_path, processed_dates, stations_data)

            # Una espera para la nueva fetch
            time.sleep(REQUEST_DELAY)

        # 6. Guardar resultados finales
        if stations_data:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(stations_data, f, ensure_ascii=False, indent=4)
            os.remove(progress_file_path)
            logger.info(f"Datos guardados en {output_file_path}")
            return stations_data
        
        logger.warning("No se obtuvieron datos válidos")
        return None
        
    except KeyError as e:
        logger.error(f"Error de key {str(e)}")
    except ValueError as e:
        logger.error(f"Error al acceder al JSON: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado ScriptV3: {str(e)}", exc_info=True)

def load_progress(progress_file: str):
    '''Función para cargar el progreso previo desde archivo si existe'''
    try:
        data = verify_json_docs(
            progress_file,
            "No existe el archivo de progreso. Se empezará desde cero."
        )
        
        processed_dates = defaultdict(set)
        
        # Extraer fechas del formato {"station_group": {"dates": [...]}}
        for station_group, dates_data in data.get("processed_dates", {}).items():
            if not isinstance(dates_data, dict) or "dates" not in dates_data:
                raise ValueError(f"Formato inválido en processed_dates para {station_group}")
            processed_dates[station_group] = set(dates_data["dates"])
        
        stations_data = data.get("stations_data", {})
        return processed_dates, stations_data
    
    except ValueError as e:
        logger.warning(f"Error en el formato del archivo: {e}")
        return defaultdict(set), {}
    except Exception as e:
        logger.warning(f"Error al cargar progreso: {e}")
        return defaultdict(set), {}

def save_progress(progress_file, processed_dates, stations_data):
    '''Función para guardar el progreso de las estaciones consultadas'''
    try:
        # Convertir los sets de fechas a listas y estructurarlos bajo "dates"
        transformed_dates = {
            station_group: {"dates": list(dates)} 
            for station_group, dates in processed_dates.items()
        }
        
        progress_data = {
            "processed_dates": transformed_dates,
            "stations_data": stations_data
        }
        
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=4)
    
    except Exception as e:
        logger.error(f"Error al guardar progreso: {e}")