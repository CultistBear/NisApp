import logging
from flask import request
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, Length, EqualTo, AnyOf
from wtforms import StringField, PasswordField, HiddenField, SubmitField, SelectField, DateField


class SignUp(FlaskForm):
    Name = StringField('Name', validators=[InputRequired(), Length(min=3, max=100, message="Name cannot be less than 3 characters and more than 100 characters")])
    Username = StringField(
        "Username", validators=[InputRequired(), Length(min=5, max=16, message="Username cannot be less than 5 characters and more than 16 characters")], render_kw={"autocomplete": "new-password"}
    )
    Password = PasswordField(
        "Password", validators=[InputRequired(), EqualTo("Confirm_Password", message="Passwords Must Match"), Length(min=8, max=30, message="Password cannot be less than 8 characters and more than 30 characters")], render_kw={"autocomplete": "new-password"}
    )
    Confirm_Password = PasswordField(
        "Confirm Password", validators=[InputRequired(), Length(min=8, max=30, message="Confirm Password cannot be less than 8 characters and more than 30 characters")], render_kw={"autocomplete": "new-password"}
    )
    Role = SelectField(
        "Role",
        choices=[
            ("User", "User"),
            ("Admin", "Admin"),
        ],
        validators=[InputRequired(), AnyOf(["User", "Admin"], message="Role can only be User or Admin")]
    )
    Submit = SubmitField(label=('SignUp'))

    def __init__(self, *args, **kwargs):
        super(SignUp, self).__init__(*args, **kwargs)
        logging.info("SignUp form initialized")


class Login(FlaskForm):
    Username = StringField("Username", validators=[
                                  InputRequired(), Length(max=100)])
    Password = PasswordField("Password", validators=[
                             InputRequired(), Length(min=5, max=30)])
    Submit = SubmitField(label=('Login'))

    def __init__(self, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)
        logging.info("Login form initialized")

class DataEntryForm(FlaskForm):
    type = SelectField(
        "Type",
        choices=[
            ('', 'Select'),
            ("METRO", "METRO"),
            ("OFFICE", "OFFICE"),
            ("TOUR", "TOUR")
        ],
        validators=[InputRequired(), AnyOf(["METRO", "OFFICE", "TOUR"], message="Incorrect Type")]
    )

    subtype = SelectField(
        "Subtype",
        choices=[
            ('', 'Select'),
            ("CASH", "CASH"),
            ("PAYTM", "PAYTM"),
            ("HDFC BANK", "HDFC BANK"),
            ("OTHER BANK", "OTHER BANK")
        ],
        validators=[InputRequired(), AnyOf(["CASH", "PAYTM", "HDFC BANK", "OTHER BANK"], message="Incorrect Subtype")]
    )

    rowData = HiddenField("rowData", validators=[InputRequired()], id="rowData")
    
    submit = SubmitField("Save")
    
    def __init__(self, *args, **kwargs):
        super(DataEntryForm, self).__init__(*args, **kwargs)
        logging.info("Data Entry form initialized")


class UserEdit(FlaskForm):
    Username = HiddenField(validators=[InputRequired(), Length(min=5, max=16)])
    Delete = SubmitField("✕")

    def __init__(self, *args, **kwargs):
        super(UserEdit, self).__init__(*args, **kwargs)
        logging.info("UserEdit form initialized")
        
class FetchExcel(FlaskForm):
    date = HiddenField(id="downloadDate", validators=[InputRequired()])
    DownloadExcel = SubmitField("Download Excel")

    def __init__(self, *args, **kwargs):
        super(FetchExcel, self).__init__(*args, **kwargs)
        logging.info("FetchExcel form initialized")

class SubmitData(FlaskForm):
    rowData = HiddenField("rowData", validators=[InputRequired()], id="rowData")
    
    SubmitData = SubmitField("Submit Table")
    
    def __init__(self, *args, **kwargs):
        super(SubmitData, self).__init__(*args, **kwargs)
        logging.info("SubmitData form initialized")    

class FetchTableData(FlaskForm):
    FetchingDate = DateField("Date to Fetch", validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        super(FetchTableData, self).__init__(*args, **kwargs)
        logging.info("FetchTableData form initialized")

class DeleteRow(FlaskForm):
    rowID = HiddenField("rowID", validators=[InputRequired()], id="rowID")
    date = HiddenField(id="deleteDate", validators=[InputRequired()])
    DeleteRow = SubmitField("✕")
    
    def __init__(self, *args, **kwargs):
        super(DeleteRow, self).__init__(*args, **kwargs)
        logging.info("DeleteRow form initialized")
