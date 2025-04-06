import json
import os

# Función para agrupar códigos EMA en grupos de 25
def group_codes():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    emca_codes_path = os.path.join(api_dir, 'json', 'ema_codes.json')
    ema_codes_grouped = os.path.join(api_dir, 'json', 'codes_group.json')
    
    if os.path.exists(emca_codes_path):
        with open(emca_codes_path, 'r', encoding='utf-8') as archive:
            ema_codes = json.load(archive)


    new_grouped_dict = {}
    group_size = 25
    ema_codes = list(ema_codes.values())

    for i in range(0, len(ema_codes), group_size):
        start = i
        end = min(i + group_size, len(ema_codes))
        values_group = ema_codes[start:end]
        key = f"group_{i // group_size + 1}"
        new_grouped_dict[key] = ",".join(values_group)

    with open(ema_codes_grouped, 'w', encoding='utf-8') as f:
                json.dump(new_grouped_dict, f, ensure_ascii=False, indent=4)