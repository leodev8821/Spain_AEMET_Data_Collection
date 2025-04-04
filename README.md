# Aplicación de Datos Históricos de la AEMET - España

# Requisitos
1. Obtener la API Key la [AEMET](https://opendata.aemet.es/centrodedescargas/altaUsuario) para poder usar la aplicación y almacenarla en el archivo ```.env``` con el nombre **AEMET_API_KEY**
2. En tu entorno virtual (preferiblemente) instalar los paquetes necesarios incluidos en el **requirements.txt**:
```
    pip3 install -r requirements.txt
```

# Ejecución
Ejecutar la aplicación mediante el comando 
```python 
    python -m main
```

# Menú de la aplicación
Seleccionar las opciones del menú en la consola que son:

1. **Obtener códigos de las estaciones**
  --> Hace un fetch a la API para obtener todos los códigos de las estaciones de la AEMET

2. **Obtener los datos históricos**
  --> Debes ingresar una fecha en formato 'YYY-MM-DD' y realizará la consulta desde el 2025-01-01 hasta la fecha introducida (toma tiempo)

3. **Crear temperatura.csv**
  --> Con los datos históricos obtenidos, crea un csv con los datos de *date, province, town, avg_t, max_t, min_t, ts_insert, ts_update*

4. **Crear precipitaciones.csv**
  --> Con los datos históricos obtenidos, crea un csv con los datos de *date, province, town, precip, ts_insert, ts_update*

5. **Crear viento.csv**
  --> Con los datos históricos obtenidos, crea un csv con los datos de *date, province, town, avg_vel, max_vel, ts_insert, ts_update*

5. **Crear humedad_relativa.csv**
  --> Con los datos históricos obtenidos, crea un csv con los datos de *date, province, town, avg_rel_hum, max_rel_hum, min_rel_hum, ts_insert, ts_update*

6. **Terminar la ejecución**
  --> Finaliza la ejecución de la aplicación

# Estructura de la aplicación
````txt
\aemet_api
+--csv
+--error_journal
+--json
\--scripts
    +--__init__.py
    +--date_validate.py
    +--export_to_csv.py
    +--fetch_station_data.py
    +--make_error_journal.py
    +--obtain_ema_code.py
    +--scriptv2.py
```