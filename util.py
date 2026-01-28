import re
from datetime import datetime
from constants import ID_FERNET_KEY
from cryptography.fernet import Fernet

def sanitise_input(strr):
    return "".join(re.findall("[A-Za-z1-9]*", strr))

def is_valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def group_by_type_subtype(rows):
    grouped = {}

    for r in rows:
        t = r["type"]
        st = r["subtype"]

        # --- normalize / format here ---
        row = dict(r)  # avoid mutating original row

        # Format date_for
        if isinstance(row.get("date_for"), str):
            try:
                row["date_for"] = datetime.strptime(
                    row["date_for"], "%a, %d %b %Y %H:%M:%S GMT"
                ).strftime("%d %b %Y")
            except ValueError:
                pass

        # Format created_at / updated_at
        for key in ("created_at", "updated_at"):
            if isinstance(row.get(key), datetime):
                row[key] = row[key].strftime("%d %b %Y %H:%M")
                
        cipher = Fernet(ID_FERNET_KEY)
        row["id"]=cipher.encrypt(str(row["id"]).encode()).decode()

        grouped.setdefault(t, {}).setdefault(st, []).append(row)

    return grouped

def build_db_data(rows):
    data = {}

    for r in rows:
        t = r["type"]
        st = r["subtype"]

        data.setdefault(t, {}).setdefault(st, []).append([
            r["amount"],
            r["receipts"],
        ])

    return data

def trim_column_map(column_map, excluded_columns):
    trimmed = {}

    for type_, subtypes in column_map.items():
        trimmed[type_] = {}

        for subtype, cols in subtypes.items():
            trimmed[type_][subtype] = [
                col for col in cols
                if col["name"].lower() not in excluded_columns
            ]

    return trimmed
