import json
import os
from datetime import datetime, timezone
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

def build_journal(station_code, server_response, fetched_url, fetched_date):

    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    error_journal_dir = os.path.join(api_dir, 'error_journal', 'errors.json')

    os.makedirs(os.path.dirname(error_journal_dir), exist_ok=True)

    json_format = {
        "station_code": station_code,
        "url": fetched_url,
        "server_response": str(server_response),
        "fetched_date": fetched_date
    }

    if os.path.exists(error_journal_dir):
        with open(error_journal_dir, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)

                if not isinstance(existing_data, list):
                    existing_data = []

                existing_data.append(json_format)
                
            except json.JSONDecodeError:
                existing_data = [json_format]
    else:
        existing_data = [json_format]
    
    with open(error_journal_dir, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"No se recibieron datos válidos. Ver -->  {error_journal_dir}")
    return None