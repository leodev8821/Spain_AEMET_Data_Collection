from datetime import datetime
import re

# Validación del formato de la fecha introducida por el usuario
def date_validation(date_str):
    try:
        # Verificar formato básico con regex
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False, "Formato inválido. Debe ser YYYY-MM-DD"
        
        # Validar que sea una fecha válida
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    
    except ValueError:
        return False, "Fecha inválida. Por favor, ingrese una fecha correcta."