# excelLayoutState.py

class LayoutState:
    def __init__(self, start_row=2, start_col=2):
        self.start_row = start_row
        self.start_col = start_col

        self.row = start_row
        self.col = start_col

    def move_down(self, n=1):
        self.row += n

    def move_right(self, n=1):
        self.col += n

    def reset_row(self):
        self.row = self.start_row

    def reset_to_type_start(self, type_start_row):
        self.row = type_start_row

    def snapshot(self):
        return {"row": self.row, "col": self.col}
