from dotenv import load_dotenv
load_dotenv()

import logging
import pathlib
import os

logging.info("Initializing constants")

IS_PRODUCTION = os.environ.get('RENDER', False)

DATABASE_URL = os.environ.get('DATABASE_URL')
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DATABASE_NAME = os.environ.get('DATABASE_NAME')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 5432))

FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
ADMIN_DEFAULT_PASSWORD = os.environ.get('ADMIN_DEFAULT_PASSWORD')
ID_FERNET_KEY = os.environ.get('ID_FERNET_KEY')

_client_names_raw = os.environ.get('CLIENT_NAMES', '')
CLIENT_NAMES = [name.strip() for name in _client_names_raw.split(';;;') if name.strip()]

_required = ['DB_USERNAME', 'DB_PASSWORD', 'DATABASE_NAME', 'FLASK_SECRET_KEY', 'ID_FERNET_KEY']
_missing = [var for var in _required if not os.environ.get(var)]
if _missing and not DATABASE_URL:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(_missing)}")

if isinstance(ID_FERNET_KEY, str):
    ID_FERNET_KEY = ID_FERNET_KEY.encode()

CURRENT_WORKING_DIRECTORY = pathlib.Path(__file__).parent.resolve()
SAFE_HEADERS = ["User-Agent", "Accept", "Referer"]
ADMIN_ENDPOINTS = ["manageuser", "delete_user", "edit_user", "submittable", "deleterow"]

COLUMN_MAP = {
    "METRO": {
        "CASH": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "PAYTM": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "HDFC BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "OTHER BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ]
    },
    "OFFICE": {
        "CASH": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "PAYTM": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "HDFC BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "OTHER BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ]
    },
    "TOUR": {
        "CASH": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "PAYTM": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "HDFC BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ],
        "OTHER BANK": [
            {"name": "Amount(₹)",  "type": "number"},
            {"name": "Receipts",  "type": "text"},
            {"name": "Date",  "type": "date"}
        ]
    }
}

DISPLAY_COLUMNS = [
    ("amount", "Amount (₹)"),
    ("receipts", "Receipts"),
    ("date_for", "Date"),
    ("submitted_by", "Submitted By"),
    ("created_at", "Submittion Date"),
    ("updated_at", "Last Update Date")
]

