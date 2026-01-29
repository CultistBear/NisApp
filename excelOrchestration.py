from openpyxl import Workbook
from openpyxl.styles import Border
from openpyxl.utils import get_column_letter
from datetime import date

from excelHelpers import (
    write_cell,
    merge_and_style,
    draw_outer_border,
    BOLD,
    LEFT,
    RIGHT,
    THICK
)


def render_subtype_table(ws, start_row, start_col, type_name, subtype_name, columns, rows, fixed_height):
    current_row = start_row
    width = len(columns)

    merge_and_style(
        ws,
        current_row,
        start_col,
        current_row,
        start_col + width - 1,
        f"{type_name} - {subtype_name}",
        font=BOLD,
        align=LEFT,
        border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
    )
    current_row += 1

    for i, col in enumerate(columns):
        write_cell(
            ws,
            current_row,
            start_col + i,
            col["name"],
            font=BOLD,
            align=LEFT,
            border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
        )
    current_row += 1

    data_start_row = current_row
    for row in rows:
        for i, value in enumerate(row):
            write_cell(ws, current_row, start_col + i, value)
        current_row += 1
    
    rows_written = len(rows)
    for _ in range(fixed_height - rows_written):
        current_row += 1
    
    data_end_row = data_start_row + len(rows) - 1

    amount_col = start_col
    amount_letter = get_column_letter(amount_col)

    if len(rows) > 0:
        formula = f"=SUM({amount_letter}{data_start_row}:{amount_letter}{data_end_row})"
    else:
        formula = 0

    write_cell(
        ws,
        current_row,
        amount_col,
        formula,
        font=BOLD,
        align=RIGHT,
        border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
    )

    write_cell(
        ws,
        current_row,
        amount_col + 1,
        "SUBTOTAL",
        font=BOLD,
        align=LEFT
    )

    subtotal_cell_ref = f"{amount_letter}{current_row}"

    draw_outer_border(ws, start_row, start_col, current_row, start_col + width - 1)

    return subtotal_cell_ref


def render_empty_subtype_slot(ws, start_row, start_col, width, fixed_height):
    return start_row + 1 + 1 + fixed_height


def generate_excel(column_map, db_data, report_date=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Expense Register"

    for col in range(1, 50):
        ws.column_dimensions[get_column_letter(col)].width = 18

    ws.column_dimensions['A'].width = 3

    if report_date is None:
        report_date = date.today().strftime('%d-%m-%Y')

    merge_and_style(
        ws,
        1,
        2,
        1,
        15,
        f"Expense Register — {report_date}",
        font=BOLD,
        align=LEFT
    )

    START_ROW = 3
    START_COL = 2
    COL_GAP = 1
    GAP_WIDTH = 3

    all_subtypes = []
    seen_subtypes = set()
    for type_name, subtypes in column_map.items():
        for subtype_name in subtypes.keys():
            if subtype_name not in seen_subtypes:
                all_subtypes.append(subtype_name)
                seen_subtypes.add(subtype_name)

    subtype_max_rows = {}
    for subtype_name in all_subtypes:
        max_rows = 1
        for type_name in column_map.keys():
            rows = db_data.get(type_name, {}).get(subtype_name, [])
            max_rows = max(max_rows, len(rows))
        subtype_max_rows[subtype_name] = max_rows

    subtype_start_rows = {}
    current_row = START_ROW
    for subtype_name in all_subtypes:
        subtype_start_rows[subtype_name] = current_row
        table_height = 1 + 1 + subtype_max_rows[subtype_name] + 1
        current_row += table_height + 1

    totals_row = current_row

    type_columns = {}
    type_widths = {}
    gap_columns = []
    current_col = START_COL
    
    type_list = list(column_map.items())
    for idx, (type_name, subtypes) in enumerate(type_list):
        type_columns[type_name] = current_col
        
        max_width = 2
        for subtype_name, columns in subtypes.items():
            max_width = max(max_width, len(columns))
        type_widths[type_name] = max_width
        
        current_col += max_width
        
        if idx < len(type_list) - 1:
            gap_columns.append(current_col)
            current_col += COL_GAP

    for gap_col in gap_columns:
        ws.column_dimensions[get_column_letter(gap_col)].width = GAP_WIDTH

    type_subtotal_cells = {type_name: [] for type_name in column_map.keys()}
    subtype_subtotal_cells = {subtype_name: [] for subtype_name in all_subtypes}
    
    for type_name, subtypes in column_map.items():
        col = type_columns[type_name]
        width = type_widths[type_name]
        
        for subtype_name in all_subtypes:
            row = subtype_start_rows[subtype_name]
            fixed_height = subtype_max_rows[subtype_name]
            
            if subtype_name in subtypes:
                columns = subtypes[subtype_name]
                columns = sorted(columns, key=lambda c: c["name"] != "Amount(₹)")
                rows = db_data.get(type_name, {}).get(subtype_name, [])
                
                subtotal_ref = render_subtype_table(
                    ws,
                    row,
                    col,
                    type_name,
                    subtype_name,
                    columns,
                    rows,
                    fixed_height
                )
                type_subtotal_cells[type_name].append(subtotal_ref)
                subtype_subtotal_cells[subtype_name].append(subtotal_ref)

    type_total_refs = []
    
    for type_name in column_map.keys():
        col = type_columns[type_name]
        amount_letter = get_column_letter(col)
        
        subtotal_cells = type_subtotal_cells[type_name]
        if subtotal_cells:
            type_formula = f"=SUM({','.join(subtotal_cells)})"
        else:
            type_formula = 0

        write_cell(
            ws,
            totals_row,
            col,
            type_formula,
            font=BOLD,
            align=RIGHT,
            border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
        )

        write_cell(
            ws,
            totals_row,
            col + 1,
            f"{type_name} TOTAL",
            font=BOLD,
            align=LEFT
        )

        type_total_refs.append(f"{amount_letter}{totals_row}")

    subtype_totals_col = current_col + 1
    subtype_total_refs = []
    
    for subtype_name in all_subtypes:
        subtype_row = subtype_start_rows[subtype_name]
        subtotal_row = subtype_row + 1 + 1 + subtype_max_rows[subtype_name]
        
        amount_letter = get_column_letter(subtype_totals_col)
        
        subtotal_cells = subtype_subtotal_cells[subtype_name]
        if subtotal_cells:
            subtype_formula = f"=SUM({','.join(subtotal_cells)})"
        else:
            subtype_formula = 0

        write_cell(
            ws,
            subtotal_row,
            subtype_totals_col,
            subtype_formula,
            font=BOLD,
            align=RIGHT,
            border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
        )

        write_cell(
            ws,
            subtotal_row,
            subtype_totals_col + 1,
            f"{subtype_name} TOTAL",
            font=BOLD,
            align=LEFT
        )

        subtype_total_refs.append(f"{amount_letter}{subtotal_row}")

    if type_total_refs:
        grand_total_col = subtype_totals_col
        grand_total_letter = get_column_letter(grand_total_col)
        
        grand_total_formula = f"=SUM({','.join(type_total_refs)})"

        write_cell(
            ws,
            totals_row,
            grand_total_col,
            grand_total_formula,
            font=BOLD,
            align=RIGHT,
            border=Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
        )

        write_cell(
            ws,
            totals_row,
            grand_total_col + 1,
            "GRAND TOTAL",
            font=BOLD,
            align=LEFT
        )

    return wb
