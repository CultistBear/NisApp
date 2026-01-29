from flask import Flask, request, render_template, redirect, url_for, session, send_file
import logging
import os
from itsdangerous import URLSafeSerializer
from forms import SignUp, Login, DataEntryForm, UserEdit, FetchExcel, FetchTableData, SubmitData, DeleteRow
from flask_wtf.csrf import CSRFProtect
from db import get_db, close_db
from constants import FLASK_SECRET_KEY, CURRENT_WORKING_DIRECTORY, COLUMN_MAP, SAFE_HEADERS, ADMIN_ENDPOINTS, DISPLAY_COLUMNS, ID_FERNET_KEY, IS_PRODUCTION
from datetime import datetime, timedelta
from excelOrchestration import generate_excel
import bcrypt
import json
from io import BytesIO
from cryptography.fernet import Fernet
from validators import validate_table_data, ValidationError
from util import sanitise_input, is_valid_date, group_by_type_subtype, trim_column_map, build_db_data
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re

app = Flask(__name__)

app.config.update(
    SECRET_KEY = FLASK_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(days=15),
    WTF_CSRF_SSL_STRICT=IS_PRODUCTION,
    WTF_CSRF_TIME_LIMIT=None
    )

serializer = URLSafeSerializer(FLASK_SECRET_KEY)
csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

app.teardown_appcontext(close_db)

log_directory = os.path.join(CURRENT_WORKING_DIRECTORY, 'logs')
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file_path = os.path.join(log_directory, datetime.today().strftime('%d-%m-%Y')+'-logs.log')

logger = logging.getLogger()
file_handler = logging.FileHandler(log_file_path)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)

logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.disabled = True 
    
@app.before_request
def pre_request():
    if request.endpoint is None:
        return
    
    headers = ", ".join(f"{k}: {v}" for k, v in request.headers.items() if k in SAFE_HEADERS)
    logger.info(f"New request from IP: {request.remote_addr}, Headers: {headers}, Method: {request.method}, Path: {request.path}\n")
    
    if session.get("username", None) is None and request.endpoint not in ["login", "static", 'logout']:
        logger.info(f"Redirecting to login from IP: {request.remote_addr}")
        return redirect(url_for("login"))
    if session.get("username", None) is not None and request.endpoint in ["login"]:
        logger.info(f"User {session.get('username')} already logged in, redirecting to dataentry from IP: {request.remote_addr}")
        return redirect(url_for("dataentry"))
    if session.get("admin", None) != 1 and request.endpoint in ADMIN_ENDPOINTS:
        logger.warning(f"User {session.get('username', None)} Tried to log into admin endpoint {request.endpoint}, redirecting to dataentry from IP: {request.remote_addr}")
        return redirect(url_for("dataentry"))

for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler):
        print(f"Logs are being saved to: {handler.baseFilename}")

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    form = Login()
    db = get_db()
    logger.info(f"Login form requested from IP: {request.remote_addr}")
    if form.validate_on_submit():
        username = form.Username.data
        password = form.Password.data
        logger.info(f"Attempting login for {username} from IP: {request.remote_addr}")
        
        query = db.select(
    "SELECT * FROM NisUsers WHERE Username = %s AND is_active = TRUE LIMIT 1",
    (username,)
)
        
        if len(query) != 0:
            
            if bcrypt.checkpw(password.encode(), query[0]['password'].encode()):
                session.clear()
                session.permanent = True
                session["username"] = query[0]["username"]
                if query[0]["role"] == "admin":
                    session["admin"] = 1
                else:
                    session["admin"] = 0
                logger.info(f"User {session['username']} logged in successfully from IP: {request.remote_addr}")
                return redirect(url_for('dataentry'))
            
            else:
                session["error"] = 'Invalid Username/Password'
                logging.warning(f"Invalid password attempt for {username} from IP: {request.remote_addr}")
                return redirect(url_for("login"))
            
        session["error"] = 'Invalid Username/Password'
        
        logging.warning(f"Invalid username attempt for {username} from IP: {request.remote_addr}")
        return redirect(url_for('login'))

    error = session.pop("error", None)
    message = session.pop("message", None)
    logger.info(f"Rendering login page with error: {error}, message: {message}")
    return render_template('login.html', form=form, error=error, message=message)

@app.route("/logout")
def logout():
    logger.info(f"User {session.get('username')} logged out from IP: {request.remote_addr}")
    session.clear()
    session["message"] = "Successfully Logged Out"
    return redirect(url_for("login"))

@app.route('/dataentry', methods=['GET', 'POST'])
def dataentry():
    form = DataEntryForm()
    db = get_db()

    if form.validate_on_submit():
        try:
            formType = form.type.data
            formSubtype = form.subtype.data
            tableData = json.loads(form.rowData.data)

            allowed_columns = COLUMN_MAP[formType][formSubtype]
            validate_table_data(tableData, allowed_columns)

            columns = [c["name"].lower() for c in allowed_columns]
            idx = {sanitise_input(name): i for i, name in enumerate(columns)}

            for row in tableData["data"]:
                db.execute("""INSERT INTO Input(type, subtype, amount, receipts, date_for, submitted_by) VALUES (%s, %s, %s, %s, %s, %s)""",(formType, formSubtype, row[idx["amount"]], row[idx["receipts"]], row[idx["date"]], session["username"]))

            db.commit() 
            session["message"] = "Data submitted successfully"

        except ValidationError as e:
            db.rollback()
            session["error"] = str(e)

        except ValueError:
            db.rollback()
            session["error"] = "Invalid numeric or date value."

        except Exception as e:
            db.rollback()
            err_msg = str(e).lower()
            if "integrity" in err_msg or "constraint" in err_msg or "foreign key" in err_msg:
                session["error"] = "Database constraint violation."
            else:
                logger.exception("Unexpected error")
                session["error"] = "Unexpected error occurred."

        return redirect(url_for("dataentry"))

    error = session.pop("error", None)
    message = session.pop("message", None)
    return render_template("dataentry.html", form=form, columns=COLUMN_MAP, error=error, message=message)
    
@app.route("/manageuser", methods = ["GET", "POST"])
def manageuser():
    form = SignUp()
    form1 = UserEdit()
    db = get_db()
    
    userList = db.select(
    "SELECT username AS \"Username\", name AS \"Name\", role AS \"Role\" FROM NisUsers WHERE is_active = TRUE"
)

    filtered_users = [
            {k: v for k, v in user.items()}
            for user in userList
    ]
    userList = {
        "columns": list(filtered_users[0].keys()),
        "data": filtered_users
    }
    
    logger.info(f"Create User accessed by {session.get('username')} from IP: {request.remote_addr}")
    if form.is_submitted():
        if form.validate_on_submit():
            if len(db.select("SELECT * FROM NisUsers WHERE Username = %s LIMIT 1",(form.Username.data,)))!= 0:
                session["error"] = "User already exists"
                return redirect(url_for("manageuser"))
            hashed_pass = bcrypt.hashpw(form.Password.data.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            try:
                db.execute("""INSERT INTO nisusers(Username, Name, Password, role, is_active) VALUES (%s, %s, %s, %s, TRUE)""", (form.Username.data, form.Name.data, hashed_pass, form.Role.data))
                db.commit()
                session["message"] = "User Successfully Created"
                return redirect(url_for("manageuser"))
            except Exception as e:
                db.rollback()
                logger.exception("User creation failed")
                session["error"] = "User Creation Failed"
                return redirect(url_for("manageuser"))

        else:
            session['error'] = [err for field_errors in form.errors.values() for err in field_errors]
            return redirect(url_for("manageuser"))
        
    error = session.pop("error", None)
    message = session.pop("message", None)
    error1 = session.pop("error1", None)
    message1 = session.pop("message1", None)
    return render_template("manageuser.html", form=form, error=error, message=message, userList=userList, form1=form1, error1=error1, message1=message1)

@app.route("/delete_user", methods = ["POST"])
def delete_user():
    form = UserEdit()
    if form.validate_on_submit():
        db = get_db()

        if form.Username.data == session.get("username"):
            session["error1"] = "You cannot deactivate yourself."
            return redirect(url_for("manageuser"))

        db.execute(
            "UPDATE NisUsers SET is_active = FALSE WHERE Username = %s",
            (form.Username.data,)
        )
        db.commit()
        session["message1"] = "User deactivated successfully."

    return redirect(url_for("manageuser"))

@app.route("/manageexcel", methods = ["GET", "POST"])
def manageexcel():
    db = get_db()
    form = FetchExcel()
    formDate = FetchTableData()
    formSubmitTable = SubmitData()
    formDeleteRow = DeleteRow()
    tableData = session.pop("tableData", None)
    if tableData:
        tableData = group_by_type_subtype(tableData)
    storedDate = session.pop("fetchingDate", datetime.today().date().isoformat())
    if storedDate:
        formDate.FetchingDate.data = storedDate
        tableData = group_by_type_subtype(db.select("SELECT * FROM input WHERE date_for = %s", (formDate.FetchingDate.data,)))
        
    if form.validate_on_submit():
        try:
            formDate.FetchingDate.data = datetime.strptime(form.data["date"], "%Y-%m-%d").date().isoformat()
        except (ValueError, TypeError):
            session["error"] = "Invalid date format"
            return redirect(url_for("manageexcel"))
        
        tableData = db.select("SELECT * FROM input WHERE date_for = %s", (formDate.FetchingDate.data,))
        report_date = datetime.strptime(formDate.FetchingDate.data, "%Y-%m-%d").strftime("%d-%m-%Y")
        ws = generate_excel(trim_column_map(COLUMN_MAP, {"date"}), build_db_data(tableData), report_date)
        output = BytesIO()
        ws.save(output)
        output.seek(0)
        filename = f"expense_{formDate.FetchingDate.data}.xlsx"
        
        return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    error = session.pop("error", None)
    message = session.pop("message", None)
    return render_template("excel.html", form=form, formDate=formDate, tableData=tableData, error=error, message=message, columns = DISPLAY_COLUMNS, formSubmitTable=formSubmitTable, formDeleteRow = formDeleteRow)

@app.route("/fetchtable", methods = ["POST"])
def fetchtable():
    form = FetchTableData()
    if form.validate():
        if is_valid_date(str(form.FetchingDate.data)):
            db = get_db()
            tableData = db.select("SELECT * FROM input WHERE date_for = %s", (form.FetchingDate.data,))
            session["tableData"] = tableData
            session["fetchingDate"] = form.FetchingDate.data.isoformat()
        else:
            session["error"] = "Invalid Date"
    return redirect(url_for("manageexcel"))

@app.route("/deleterow", methods = ["POST"])
def deleterow():
    form = DeleteRow()
    if form.validate():
        cipher = Fernet(ID_FERNET_KEY)
        db = get_db()
        try:
            decrypted_id = cipher.decrypt(form.data["rowID"].encode()).decode()
            db.execute("delete from input where id=%s", (decrypted_id,))
            db.commit()
            session["message"] = "Record deleted successfully"
        except Exception as e:
            db.rollback()
            logger.exception("Row deletion failed")
            session["error"] = "Deletion unsuccessful"
    else:
        session["error"] = "Invalid request"
    
    try:
        session["fetchingDate"] = datetime.strptime(form.data["date"], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        session["fetchingDate"] = datetime.today().date().isoformat()
    return redirect(url_for("manageexcel"))

@app.route("/submittable", methods = ["POST"])
def submittable():
    form = SubmitData()
    if form.validate():
        cipher = Fernet(ID_FERNET_KEY)
        tableData = json.loads(form.data["rowData"])
        db = get_db()
        count_pass=0
        count_fail=0
        for i in tableData:
            if i:
                try:
                    amount = float(i.get('amount', 0))
                    if amount <= 0:
                        count_fail += 1
                        continue
                except (ValueError, TypeError):
                    count_fail += 1
                    continue
                
                receipts = str(i.get('receipts', ''))
                if not re.match(r'^[A-Za-z0-9\s\-\.]*$', receipts) or len(receipts) > 100:
                    count_fail += 1
                    continue
                
                try:
                    db.execute("update input set amount=%s, receipts=%s where id=%s", (amount, receipts, cipher.decrypt(i["id"]).decode()))
                    db.commit()
                    count_pass+=1
                except Exception as e:
                    logger.exception("Failed to update row")
                    db.rollback()
                    count_fail+=1
        if count_pass>0:
            session["message"] = str(count_pass) + " Record(s) Sucessfully Updated"
        if count_fail>0:
            session["error"] = str(count_fail) + " Record(s) Failed to Update"
        
        try:
            if tableData and tableData[0].get("date_for"):
                session["fetchingDate"] = datetime.strptime(tableData[0]["date_for"], "%Y-%m-%d").date().isoformat()
            else:
                session["fetchingDate"] = datetime.today().date().isoformat()
        except (ValueError, TypeError, IndexError):
            session["fetchingDate"] = datetime.today().date().isoformat()
        return redirect(url_for("manageexcel"))
    else:
        session['error'] = [err for field_errors in form.errors.values() for err in field_errors]
    return redirect(url_for("manageexcel"))

@app.errorhandler(404)
def not_found(e):
    user = session.get("username", "anonymous")
    logging.warning(f"404 error encountered by {user} at {request.url}")
    return render_template("404.html")

if __name__ == '__main__':
    logger.info("Starting the application")
    app.run(debug=not IS_PRODUCTION, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))