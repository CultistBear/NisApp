from datetime import datetime
from decimal import Decimal, InvalidOperation
from util import sanitise_input

class ValidationError(Exception):
    pass


def validate_table_data(table_data, allowed_columns):

    if not isinstance(table_data, dict):
        raise ValidationError("Invalid table format")

    if "headings" not in table_data or "data" not in table_data:
        raise ValidationError("Missing table fields")

    headings = table_data["headings"]
    rows = table_data["data"]

    if not isinstance(rows, list) or len(rows) == 0:
        raise ValidationError("At least one row is required")

    received_cols = [h["name"].lower() for h in headings]
    allowed_cols = [c["name"].lower() for c in allowed_columns]

    if received_cols != allowed_cols:
        raise ValidationError("Column mismatch detected")

    col_index = {sanitise_input(name): idx for idx, name in enumerate(received_cols)}

    for row_num, row in enumerate(rows, start=1):
        if not isinstance(row, list):
            raise ValidationError(f"Row {row_num} is invalid")

        if len(row) != len(received_cols):
            raise ValidationError(f"Row {row_num} has invalid column count")

        try:
            amount = Decimal(row[col_index["amount"]])
            if amount <= 0:
                raise ValidationError
        except (InvalidOperation, ValidationError):
            raise ValidationError(f"Row {row_num}: Amount must be > 0")

        try:
            datetime.strptime(row[col_index["date"]], "%Y-%m-%d")
        except Exception:
            raise ValidationError(f"Row {row_num}: Invalid date")

        receipt = row[col_index["receipts"]]
        if not isinstance(receipt, str):
            raise ValidationError(f"Row {row_num}: Receipts must be text")

        if len(receipt) > 100:
            raise ValidationError(f"Row {row_num}: Receipts too long")

    return True
