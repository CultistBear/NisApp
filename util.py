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
    cipher = Fernet(ID_FERNET_KEY)

    for r in rows:
        it = r.get("input_type", "UNKNOWN")
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

        row["id"] = cipher.encrypt(str(row["id"]).encode()).decode()

        grouped.setdefault(it, {}).setdefault(t, {}).setdefault(st, []).append(row)

    flat_rows = []
    for input_type, types in grouped.items():
        it_rowspan = sum(
            len(rows) for subtypes in types.values() for rows in subtypes.values()
        )
        first_it = True

        for type_name, subtypes in types.items():
            t_rowspan = sum(len(rows) for rows in subtypes.values())
            first_t = True

            for subtype_name, rows in subtypes.items():
                st_rowspan = len(rows)
                first_st = True

                for row in rows:
                    row["input_type"] = input_type
                    row["type"] = type_name
                    row["subtype"] = subtype_name
                    row["input_type_rowspan"] = it_rowspan if first_it else None
                    row["type_rowspan"] = t_rowspan if first_t else None
                    row["subtype_rowspan"] = st_rowspan if first_st else None
                    flat_rows.append(row)
                    first_it = False
                    first_t = False
                    first_st = False

    return flat_rows

def build_db_data(rows):
    data = {}

    for r in rows:
        t = r["type"]
        it = r.get("input_type", "UNKNOWN")
        st = r["subtype"]

        data.setdefault(t, {}).setdefault(it, {}).setdefault(st, []).append([
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
