# Historic and Forecast Weather Data from AEMET - Spain
---
A command-line tool built with Python that retrieves historical weather data from all weather stations in Spain from 01-01-2025 to the desired date. With this data, it generates ```'.csv'``` files to be used on platforms like Google Cloud Platform.
It also retrieves and generates ```'.csv'``` files containing Weather Forecast data for all Spanish municipalities (8132 in total).

The data is extracted using the [AEMET API](https://opendata.aemet.es/centrodedescargas/inicio).


## Requirements
---
1. Obtain an [AEMET API KEY](https://opendata.aemet.es/centrodedescargas/altaUsuario) to use the application and store it in a ```.env``` file with the name **AEMET_API_KEY=your_api_key_here**.

2. Create the virtual environment **.venv**
    ```python
    python -m venv .venv
    ```

3. Activate the newly created virtual environment:
	- Windows
	```
	.venv\Scripts\activate
	```
	- Linux/MacOS
	```
	source .venv/bin/activate
	```

4. Install the required packages listed in **requirements.txt**:
    ```python
    pip3 install -r requirements.txt
    ```

## Execution
---
Run the application using the command:

```python 
python -m main
```


# Console Menu Options

## Main Menu

Select options from the menu displayed in the console:

### 1️⃣ Get weather station codes
Fetches all AEMET station codes via the API and generates:
- `json/ema_codes.json`
- `json/codes_group.json`

### 2️⃣ Get historical weather data
This option opens a sub-menu:

#### 1️⃣ Generate file from scratch
Creates the file at `~/json/weather_data.json`

#### 2️⃣ Resume data collection
Creates:
- `~/json/pending_group_codes.json`
Resumes updating `~/json/weather_data.json`  
*(You must enter the same end date used when the file was first created)*

#### 3️⃣ Recover data from error log
Uses:
- `~/error_journal/errors.json` (log of previously failed stations)
To update:
- `~/json/weather_data.json`

#### 0️⃣ Back
Returns to the previous menu

### 3️⃣ Generate historical 'csv' files
This option opens a sub-menu:

#### 1️⃣ Create temperatura_historico.csv
Location: `~/csv/historical/temperatura_historico.csv`

#### 2️⃣ Create humedad_relativa_historico.csv
Location: `~/csv/historical/humedad_relativa_historico.csv`

#### 3️⃣ Create precipitaciones_historico.csv
Location: `~/csv/historical/precipitaciones_historico.csv`

#### 4️⃣ Create viento_historico.csv
Location: `~/csv/historical/viento_historico.csv`

#### 0️⃣ Back
Returns to the previous menu

### 4️⃣ 7-day forecast (all municipalities)
This option opens a sub-menu:

#### 1️⃣ Fetch 7-day forecast
Retrieves and stores at `~/json/prediction_data.json`  
*(Based on execution date)*

#### 2️⃣ Resume 7-day forecast retrieval
Creates `~/json/pending_towns_codes.json`  
Resumes forecast collection from this file

#### 0️⃣ Back
Returns to the previous menu

### 5️⃣ Generate forecast 'csv' files
This option opens a sub-menu:

#### 1️⃣ Create prediccion_precipitaciones.csv
Location: `~/csv/prediction/prediccion_precipitaciones.csv`

#### 2️⃣ Create prediccion_cota_nieve.csv
Location: `~/csv/prediction/prediccion_cota_nieve.csv`

#### 3️⃣ Create prediccion_estado_cielo.csv
Location: `~/csv/prediction/prediccion_estado_cielo.csv`

#### 4️⃣ Create prediccion_viento.csv
Location: `~/csv/prediction/prediccion_viento.csv`

#### 5️⃣ Create prediccion_racha_max.csv
Location: `~/csv/prediction/prediccion_racha_max.csv`

#### 6️⃣ Create prediccion_temperatura.csv
Location: `~/csv/prediction/prediccion_temperatura.csv`

#### 7️⃣ Create prediccion_sens_termica.csv
Location: `~/csv/prediction/prediccion_sens_termica.csv`

#### 8️⃣ Create prediccion_humedad_relativa.csv
Location: `~/csv/prediction/prediccion_humedad_relativa.csv`

#### 0️⃣ Back
Returns to the previous menu

### 0️⃣ Exit
Ends the application

# Application Structure
---
```txt
\aemet_api
│
├───csv
│   ├───historical
│   │       humedad_relativa_historico.csv
│   │       precipitaciones_historico.csv
│   │       temperatura_historico.csv
│   │       viento_historico.csv
│   │
│   └───prediction
│           prediccion_cota_nieve.csv
│           prediccion_estado_cielo.csv
│           prediccion_humedad_relativa.csv
│           prediccion_precipitaciones.csv
│           prediccion_racha_max.csv
│           prediccion_sens_termica.csv
│           prediccion_temperatura.csv
│           prediccion_viento.csv
│
├───error_journal
│       errors.json
│       error_prediction.json
│
├───json
│       codes_group.json
│       ema_codes.json
│       pending_group_codes.json
│       pending_towns_codes.json
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
│   │
│   └───__pycache__
```

# End
