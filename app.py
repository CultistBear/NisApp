from flask import Flask, request, render_template, redirect, url_for, session, send_file
import logging
import os
from itsdangerous import URLSafeSerializer
from forms import SignUp, Login, DataEntryForm, UserEdit, UserFullEdit, FetchExcel, FetchTableData, SubmitData, DeleteRow
from flask_wtf.csrf import CSRFProtect
from db import get_db, close_db
from constants import FLASK_SECRET_KEY, CURRENT_WORKING_DIRECTORY, COLUMN_MAP, SAFE_HEADERS, ADMIN_ENDPOINTS, DISPLAY_COLUMNS, ID_FERNET_KEY, IS_PRODUCTION, CLIENT_NAMES
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

# Set of usernames pending forced logout (cleared after logout) (kind of a bad idea)
pending_logout = set()

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

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
    
@app.before_request
def pre_request():
    if request.endpoint is None:
        return
    
    headers = ", ".join(f"{k}: {v}" for k, v in request.headers.items() if k in SAFE_HEADERS)
    logger.info(f"New request from IP: {get_client_ip()}, Headers: {headers}, Method: {request.method}, Path: {request.path}\n")
    
    if session.get("username", None) and session.get("username", None) in pending_logout:
        username_to_logout = session.get("username")
        pending_logout.discard(username_to_logout)
        session.clear()
        session["message"] = "Your account was updated by an administrator. Please log in again."
        logger.info(f"User {username_to_logout} force-logged out due to account changes from IP: {get_client_ip()}")
        return redirect(url_for("login"))
    if session.get("username", None) is None and request.endpoint not in ["login", "static", 'logout']:
        logger.info(f"Redirecting to login from IP: {get_client_ip()}")
        return redirect(url_for("login"))
    if session.get("username", None) is not None and request.endpoint in ["login"]:
        logger.info(f"User {session.get('username')} already logged in, redirecting to dataentry from IP: {get_client_ip()}")
        return redirect(url_for("dataentry"))
    if session.get("admin", None) != 1 and request.endpoint in ADMIN_ENDPOINTS:
        logger.warning(f"User {session.get('username', None)} Tried to log into admin endpoint {request.endpoint}, redirecting to dataentry from IP: {get_client_ip()}")
        return redirect(url_for("dataentry"))

for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler):
        print(f"Logs are being saved to: {handler.baseFilename}")

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    form = Login()
    db = get_db()
    logger.info(f"Login form requested from IP: {get_client_ip()}")
    if form.validate_on_submit():
        username = form.Username.data
        password = form.Password.data
        logger.info(f"Attempting login for {username} from IP: {get_client_ip()}")
        
        query = db.select(
    "SELECT * FROM NisUsers WHERE Username = %s AND is_active = TRUE LIMIT 1",
    (username,)
)
        
        if len(query) != 0:
            
            if bcrypt.checkpw(password.encode(), query[0]['password'].encode()):
                session.clear()
                session.permanent = True
                session["username"] = query[0]["username"]
                session["user_name"] = query[0]["name"]
                if query[0]["role"] == "admin":
                    session["admin"] = 1
                else:
                    session["admin"] = 0
                
                pending_logout.discard(query[0]["username"])
                
                logger.info(f"User {session['username']} logged in successfully from IP: {get_client_ip()}")
                return redirect(url_for('dataentry'))
            
            else:
                session["error"] = 'Invalid Username/Password'
                logging.warning(f"Invalid password attempt for {username} from IP: {get_client_ip()}")
                return redirect(url_for("login"))
            
        session["error"] = 'Invalid Username/Password'
        
        logging.warning(f"Invalid username attempt for {username} from IP: {get_client_ip()}")
        return redirect(url_for('login'))

    error = session.pop("error", None)
    message = session.pop("message", None)
    logger.info(f"Rendering login page with error: {error}, message: {message}")
    return render_template('login.html', form=form, error=error, message=message)

@app.route("/logout")
def logout():
    logger.info(f"User {session.get('username')} logged out from IP: {get_client_ip()}")
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
    return render_template("dataentry.html", form=form, columns=COLUMN_MAP, error=error, message=message, client_names=CLIENT_NAMES)
    
@app.route("/manageuser", methods = ["GET", "POST"])
def manageuser():
    form = SignUp()
    form1 = UserEdit()
    formEdit = UserFullEdit()
    db = get_db()
    
    userList = db.select(
    "SELECT username AS \"Username\", name AS \"Name\", role AS \"Role\" FROM NisUsers WHERE is_active = TRUE"
)

    filtered_users = [
            {k: v for k, v in user.items()}
            for user in userList
    ]
    
    if filtered_users:
        userList = {
            "columns": list(filtered_users[0].keys()),
            "data": filtered_users
        }
    else:
        userList = {
            "columns": ["Username", "Name", "Role"],
            "data": []
        }
    
    logger.info(f"Create User accessed by {session.get('username')} from IP: {get_client_ip()}")
    if form.is_submitted():
        if form.validate_on_submit():
            if len(db.select("SELECT * FROM NisUsers WHERE Username = %s LIMIT 1",(form.Username.data,)))!= 0:
                session["error"] = "Username already exists (or was previously used)"
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
    return render_template("manageuser.html", form=form, error=error, message=message, userList=userList, form1=form1, formEdit=formEdit, error1=error1, message1=message1)

@app.route("/delete_user", methods = ["POST"])
def delete_user():
    if session.get("admin") != 1:
        logger.warning(f"Unauthorized delete_user attempt by {session.get('username', 'unknown')} from IP: {get_client_ip()}")
        return redirect(url_for("dataentry"))
    
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
        
        pending_logout.add(form.Username.data)
        logger.info(f"User {form.Username.data} deactivated and added to pending logout list")
        
        session["message1"] = "User deactivated successfully."

    return redirect(url_for("manageuser"))

@app.route("/edit_user", methods = ["POST"])
def edit_user():
    if session.get("admin") != 1:
        logger.warning(f"Unauthorized edit_user attempt by {session.get('username', 'unknown')} from IP: {get_client_ip()}")
        return redirect(url_for("dataentry"))
    
    form = UserFullEdit()
    if form.validate_on_submit():
        db = get_db()
        original_username = form.OriginalUsername.data
        new_name = form.Name.data
        new_role = form.Role.data
        new_password = form.NewPassword.data
        
        if original_username == session.get("username") and new_role != "admin":
            session["error1"] = "You cannot demote yourself from admin."
            return redirect(url_for("manageuser"))
        
        if new_password and len(new_password) < 8:
            session["error1"] = "New password must be at least 8 characters."
            return redirect(url_for("manageuser"))
        
        try:
            if new_password and len(new_password) >= 8:
                hashed_pass = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                db.execute(
                    "UPDATE NisUsers SET name = %s, role = %s, password = %s WHERE Username = %s AND is_active = TRUE",
                    (new_name, new_role, hashed_pass, original_username)
                )
            else:
                db.execute(
                    "UPDATE NisUsers SET name = %s, role = %s WHERE Username = %s AND is_active = TRUE",
                    (new_name, new_role, original_username)
                )
            db.commit()
            logger.info(f"User {original_username} updated by {session.get('username')} from IP: {get_client_ip()}")
            session["message1"] = f"User {original_username} updated successfully."
            if original_username != session.get("username"):
                pending_logout.add(original_username)
                logger.info(f"User {original_username} added to pending logout list")
        except Exception as e:
            db.rollback()
            logger.exception("User update failed")
            session["error1"] = "User update failed."
    else:
        session["error1"] = [err for field_errors in form.errors.values() for err in field_errors]
    
    return redirect(url_for("manageuser"))

@app.route("/manageexcel", methods = ["GET", "POST"])
def manageexcel():
    db = get_db()
    form = FetchExcel()
    formDate = FetchTableData()
    formSubmitTable = SubmitData()
    formDeleteRow = DeleteRow()
    
    is_admin = session.get("admin") == 1
    user_type = session.get("user_name", "").upper() 
    
    tableData = session.pop("tableData", None)
    if tableData:
        if not is_admin and user_type:
            tableData = [row for row in tableData if row.get("type", "").upper() == user_type]
        tableData = group_by_type_subtype(tableData)
    storedDate = session.pop("fetchingDate", datetime.today().date().isoformat())
    if storedDate:
        formDate.FetchingDate.data = storedDate
        if is_admin:
            tableData = group_by_type_subtype(db.select("SELECT * FROM input WHERE date_for = %s", (formDate.FetchingDate.data,)))
        else:
            tableData = group_by_type_subtype(db.select("SELECT * FROM input WHERE date_for = %s AND UPPER(type) = %s", (formDate.FetchingDate.data, user_type)))
        
    if form.validate_on_submit():
        try:
            formDate.FetchingDate.data = datetime.strptime(form.data["date"], "%Y-%m-%d").date().isoformat()
        except (ValueError, TypeError):
            session["error"] = "Invalid date format"
            return redirect(url_for("manageexcel"))
        
        if is_admin:
            tableData = db.select("SELECT * FROM input WHERE date_for = %s", (formDate.FetchingDate.data,))
            column_map_for_excel = trim_column_map(COLUMN_MAP, {"date"})
        else:
            tableData = db.select("SELECT * FROM input WHERE date_for = %s AND UPPER(type) = %s", (formDate.FetchingDate.data, user_type))

            filtered_column_map = {k: v for k, v in COLUMN_MAP.items() if k.upper() == user_type}
            column_map_for_excel = trim_column_map(filtered_column_map, {"date"})
        
        report_date = datetime.strptime(formDate.FetchingDate.data, "%Y-%m-%d").strftime("%d-%m-%Y")
        ws = generate_excel(column_map_for_excel, build_db_data(tableData), report_date)
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
    return render_template("excel.html", form=form, formDate=formDate, tableData=tableData, error=error, message=message, columns = DISPLAY_COLUMNS, formSubmitTable=formSubmitTable, formDeleteRow = formDeleteRow, is_admin=is_admin)

@app.route("/fetchtable", methods = ["POST"])
def fetchtable():
    form = FetchTableData()
    if form.validate():
        if is_valid_date(str(form.FetchingDate.data)):
            db = get_db()
            is_admin = session.get("admin") == 1
            user_type = session.get("user_name", "").upper()
            
            if is_admin:
                tableData = db.select("SELECT * FROM input WHERE date_for = %s", (form.FetchingDate.data,))
            else:
                tableData = db.select("SELECT * FROM input WHERE date_for = %s AND UPPER(type) = %s", (form.FetchingDate.data, user_type))
            
            session["tableData"] = tableData
            session["fetchingDate"] = form.FetchingDate.data.isoformat()
        else:
            session["error"] = "Invalid Date"
    return redirect(url_for("manageexcel"))

@app.route("/deleterow", methods = ["POST"])
def deleterow():
    if session.get("admin") != 1:
        logger.warning(f"Unauthorized deleterow attempt by {session.get('username', 'unknown')} from IP: {get_client_ip()}")
        session["error"] = "Unauthorized action"
        return redirect(url_for("manageexcel"))
    
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
    if session.get("admin") != 1:
        logger.warning(f"Unauthorized submittable attempt by {session.get('username', 'unknown')} from IP: {get_client_ip()}")
        session["error"] = "Unauthorized action"
        return redirect(url_for("manageexcel"))
    
    form = SubmitData()
    if form.validate():
        cipher = Fernet(ID_FERNET_KEY)
        tableData = json.loads(form.data["rowData"])
        db = get_db()
        count_pass=0
        count_fail=0
        for i in tableData:
            if i:
                row_id = i.get('id', 'unknown')
                try:
                    amount = float(i.get('amount', 0))
                    if amount <= 0:
                        logger.warning(f"Record update failed - invalid amount ({amount}): row_id={row_id}")
                        count_fail += 1
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Record update failed - amount parse error ({i.get('amount')}): row_id={row_id}, error={e}")
                    count_fail += 1
                    continue
                
                receipts = str(i.get('receipts', ''))
                if len(receipts) > 200:
                    logger.warning(f"Record update failed - receipts too long ({len(receipts)} chars): row_id={row_id}")
                    count_fail += 1
                    continue
                
                try:
                    db.execute("update input set amount=%s, receipts=%s where id=%s", (amount, receipts, cipher.decrypt(i["id"]).decode()))
                    db.commit()
                    count_pass+=1
                except Exception as e:
                    logger.warning(f"Record update failed - DB error: row_id={row_id}, error={e}")
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