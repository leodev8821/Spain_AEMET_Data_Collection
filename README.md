# Aplicación de Datos Históricos de la AEMET - España

# Requisitos

1. Obtener la API Key la [AEMET](https://opendata.aemet.es/centrodedescargas/altaUsuario) para poder usar la aplicación y almacenarla en el archivo ```.env``` con el nombre **AEMET_API_KEY**

2. Crear el entorno virutal **.venv**
```python
python -m venv .venv
```

3. Activar el entorno virtual recién creado
- Windows
```
.venv\Scripts\activate
```

- Linux/MacOS
```
source .venv/bin/activate
```

3. Instalar los paquetes necesarios incluidos en el **requirements.txt**:

```python
pip3 install -r requirements.txt
```

# Ejecución
Ejecutar la aplicación mediante el comando

```python 
python -m main
```

# Menú de la aplicación

Seleccionar las opciones del menú en la consola que son:

1️⃣ **Opción 1 ➡️ Obtener códigos de las estaciones**

  Hace un fetch a la API para obtener todos los códigos de las estaciones de la AEMET y crear los archivos ***json/ema_codes.json*** y ***json/codes_group.json***.

2️⃣ **Opción 2 ➡️ Obtener los datos históricoss**

  Esta opción abre otro prompt para ingresar otras opciones:

  1️⃣ **1. Generar archivo desde cero**.

      Crea el archivo en ***~/csv/historical/temperatura_historico.csv***.

    2️⃣ **2. Crear humedad_relativa_historico.csv**

      Crea el archivo en ***~/csv/historical/humedad_relativa_historico.csv***.

  🔸 **3. Crear precipitaciones_historico.csv**

    Crea el archivo en ***~/csv/historical/precipitaciones_historico.csv***.

  🔸 **4. Crear viento_historico.csv**

    Crea el archivo en ***~/csv/historical/viento_historico.csv***.

  🔸 **0. Volver**

    Retorna al menú anterior.

🔵 **Opción 3 --> Crear archivos 'csv' históricos**

  * Esta opción abre otro prompt para ingresar otras opciones:

    🔸 **1. Crear temperatura_historico.csv**.

     Crea el archivo en ***~/csv/historical/temperatura_historico.csv***.

    🔸 **2. Crear humedad_relativa_historico.csv**

     Crea el archivo en ***~/csv/historical/humedad_relativa_historico.csv***.

    🔸 **3. Crear precipitaciones_historico.csv**

     Crea el archivo en ***~/csv/historical/precipitaciones_historico.csv***.

    🔸 **4. Crear viento_historico.csv**

     Crea el archivo en ***~/csv/historical/viento_historico.csv***.

    🔸 **0. Volver**

     Retorna al menú anterior.

🔵 **Opción 4 --> Recuperar información histórica de los errores**

  Actualiza la información de ***weather_data.json*** desde ***errors.json*** que son las estaciones que produjeron errores.

🔵 **5. Obtener previsión de los próximos 7 dias de todos los municipios**

  Crea un archivo con la previsión de los próximos 7 días en ***~/json/prediction_progress.json***

🔵 **6. Reanudar obtención de previsión de los próximos 7 dias**

  Reanuda y actualiza el archivo ***~/json/prediction_progress.json*** con la previsión de los próximos 7 días de los municipios restantes en ***~/json/pending_town_codes.json***

🔵 **7. Crear archivos 'csv' de previsión**

  * Esta opción abre otro prompt para ingresar otras opciones:

    🔸 **1. Crear prediccion_precipitaciones.csv**.

      Crea el archivo en ***~/csv/prediction/prediccion_precipitaciones.csv***.

    🔸 **2. Crear prediccion_cota_nieve.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_cota_nieve.csv***.

    🔸 **3. Crear prediccion_estado_cielo.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_estado_cielo.csv***.

    🔸 **4. Crear prediccion_viento.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_viento.csv***.
    
    🔸 **5. Crear prediccion_racha_max.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_racha_max.csv***.

    🔸 **6. Crear prediccion_temperatura.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_temperatura.csv***.

    🔸 **7. Crear prediccion_sens_termica.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_sens_termica.csv***.

    🔸 **8. Crear prediccion_humedad_relativa.csv**

      Crea el archivo en ***~/csv/prediction/prediccion_humedad_relativa.csv***.

    🔸 **0. Volver**

      Retorna al menú anterior.

🔵 **0. Terminar la ejecución**

  Finaliza la ejecución de la aplicación

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