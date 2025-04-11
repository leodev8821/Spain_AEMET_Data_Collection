# Aplicación de Datos Históricos de la AEMET - España

## Requisitos

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

4. Instalar los paquetes necesarios incluidos en el **requirements.txt**:

```python
pip3 install -r requirements.txt
```

## Ejecución
Ejecutar la aplicación mediante el comando

```python 
python -m main
```

## Menú de la aplicación
Seleccionar las opciones del menú en la consola que son:

####**1️⃣ Obtener códigos de las estaciones**

- Hace un fetch a la API para obtener todos los códigos de las estaciones de la AEMET y crear los archivos ***json/ema_codes.json*** y ***json/codes_group.json***.

####**2️⃣ Obtener los datos históricoss**
* Esta opción abre otro prompt para ingresar otras opciones:

 #####1️⃣ **Generar archivo desde cero**.
 - Crea el archivo en ***~/json/weather_data.json***.

 #####2️⃣ **Reanudar la obtención de la información**
 - Crea el archivo en ***~/json/pending_group_codes.json*** y a partir de éste, actualiza la informacion de ***~/json/weather_data.json*** (debe introducir la misma fecha final que se usó para generar el archivo desde cero).

 #####3️⃣ **Recuperar información histórica desde los errores**
 - A partir del archivo ***~/error_journal/errors.json*** (un log que guarda las estaciones que fallaron anteriormente) se actualiza la información en ***~/json/weather_data.json***.

 #####0️⃣ **Volver**
 - Retorna al menú anterior.

####**3️⃣ Crear archivos 'csv' históricos**

  * Esta opción abre otro prompt para ingresar otras opciones:

 #####1️⃣ **Crear temperatura_historico.csv**.
 - Crea el archivo en ***~/csv/historical/temperatura_historico.csv***.

 #####2️⃣ **Crear humedad_relativa_historico.csv**
 - Crea el archivo en ***~/csv/historical/humedad_relativa_historico.csv***.

 #####3️⃣ **Crear precipitaciones_historico.csv**
 - Crea el archivo en ***~/csv/historical/precipitaciones_historico.csv***.

 #####4️⃣ **Crear viento_historico.csv**
 - Crea el archivo en ***~/csv/historical/viento_historico.csv***.

 #####0️⃣ **Volver**
 - Retorna al menú anterior.

####**4️⃣ Previsión próximos 7 dias (todos los municipios)**

  * Esta opción abre otro prompt para ingresar otras opciones:

 #####1️⃣ **Obtener previsión de los próximos 7 dias**.
 - Obtiene y guarda en el archivo en ***~/json/prediction_data.json*** la la previsión meteorológica de los próximos 7 dias a la fecha de la consulta (cuando se ejecuta el script).

 #####2️⃣ **Reanudar obtención de previsión de los próximos 7 dias**
 - Crea el archivo  ***~/json/pending_towns_codes.json*** y a partir de éste, reanuda la obtención de la previsión meteorológica.

 #####0️⃣ **Volver**
 - Retorna al menú anterior.

####**5️⃣ Crear archivos 'csv' de predicción**

  * Esta opción abre otro prompt para ingresar otras opciones:

 #####1️⃣ **Crear prediccion_precipitaciones.csv**.
 - Crea el archivo en ***~/csv/prediction/prediccion_precipitaciones.csv***.

 #####2️⃣ **Crear prediccion_cota_nieve.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_cota_nieve.csv***.

 #####3️⃣ **Crear prediccion_estado_cielo.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_estado_cielo.csv***.

 #####4️⃣ **Crear prediccion_viento.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_viento.csv***.
 
 #####5️⃣ **Crear prediccion_racha_max.csv**.
 - Crea el archivo en ***~/csv/prediction/prediccion_racha_max.csv***.

 #####6️⃣ **Crear prediccion_temperatura.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_temperatura.csv***.

 #####7️⃣ **Crear prediccion_sens_termica.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_sens_termica.csv***.

 #####8️⃣ **Crear prediccion_humedad_relativa.csv**
 - Crea el archivo en ***~/csv/prediction/prediccion_humedad_relativa.csv***.

 #####0️⃣ **Volver**
 - Retorna al menú anterior.

 #####0️⃣ **Terminar la ejecución**
 - Finaliza la ejecución de la aplicación.


# Estructura de la aplicación
````txt
\aemet_api
│
├───csv                                       # Directorio donde se almacenan todos los 'csv' generados
│   ├───prediction
│   ├───historical
│                          
├───error_journal                             # Directorio donde se almacenan todos los 'json' con los errores generados
├───json
│       codes_group.json
│       ema_codes.json
│       prediction_data.json
│       towns_codes.json
│       weather_data.json
│
├───scripts
│   │   bk_historical_data.py
│   │   csv_convert.py
│   │   fetch_station_data.py
│   │   scriptv3.py
│   │   utils.py
│   │   verify_files.py
│   │   __init__.py
```

###End