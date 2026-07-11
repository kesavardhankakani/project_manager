from flask import Flask,request,jsonify,render_template
import psycopg2
from flask_bcrypt import Bcrypt
import jwt
import datetime

app=Flask(__name__)
bcrypt=Bcrypt(app)

HOST="localhost"
NAME="project_management"
USER="postgres"
PASSWORD="kesava"
SECRET_KEY="this is my key"

def get_db_connection():
    return psycopg2.connect(
        host=HOST,
        database=NAME,
        user=USER,
        password=PASSWORD
    )

def create_users_table():
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
    userid SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(300) NOT NULL
    );
    """)
    connection.commit()
    cur.close()
    connection.close()

def create_projects_table():
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects(
    projectid SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(userid) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    connection.commit()
    cur.close()
    connection.close()

def create_project_tasks_table():
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects_tasks(
    taskid SERIAL PRIMARY KEY,
    projectid INTEGER REFERENCES projects(projectid) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending'
    CHECK(status IN ('Pending','In-Progress','Done'))
    );
    """)
    connection.commit()
    cur.close()
    connection.close()

create_users_table()
create_projects_table()
create_project_tasks_table()

@app.route("/")
def home():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/create_project")
def create_project_page():
    return render_template("create_project.html")

@app.route("/add_task")
def add_task_page():
    return render_template("add_task.html")

@app.route("/tasks")
def tasks_page():
    return render_template("tasks.html")

@app.route("/project_progress")
def progress_page():
    return render_template("project_progress.html")

def create_jwt(userid,username):
    payload={
        "userid":userid,
        "username":username,
        "exp":datetime.datetime.utcnow()+datetime.timedelta(hours=2)
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )
def verify_jwt(token):
    try:
        if token.startswith("Bearer "):
            token=token.split(" ")[1]
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )
    except Exception:
        return None
    
@app.route("/register",methods=["POST"])
def register():
    data=request.get_json()
    username=data.get("username","").strip()
    email=data.get("email","").strip()
    password=data.get("password","").strip()
    if not username or not email or not password:
        return jsonify({"message":"All fields are required"}),400
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("SELECT userid FROM users WHERE email=%s",(email,))
    if cur.fetchone():
        cur.close()
        connection.close()
        return jsonify({"message":"Email already exists"}),409
    hashed_password=bcrypt.generate_password_hash(password).decode("utf-8")
    cur.execute(
        "INSERT INTO users(username,email,password) VALUES(%s,%s,%s) RETURNING userid",
        (username,email,hashed_password)
    )
    userid=cur.fetchone()[0]
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Registration Successful",
        "userid":userid
    }),201

@app.route("/login",methods=["POST"])
def login():
    data=request.get_json()
    email=data.get("email","").strip()
    password=data.get("password","").strip()
    if not email or not password:
        return jsonify({"message":"Email and Password required"}),400
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute(
        "SELECT userid,username,password FROM users WHERE email=%s",
        (email,)
    )

    user=cur.fetchone()
    if user is None:
        cur.close()
        connection.close()
        return jsonify({"message":"User not found"}),404
    userid=user[0]
    username=user[1]
    hashed_password=user[2]
    if not bcrypt.check_password_hash(hashed_password,password):
        cur.close()
        connection.close()
        return jsonify({"message":"Invalid password"}),401
    token=create_jwt(userid,username)
    cur.close()
    connection.close()
    return jsonify({
        "message":"Login Successful",
        "token":token
    }),200
@app.route("/create_project",methods=["POST"])
def create_project():
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    data=request.get_json()
    title=data.get("title","").strip()
    description=data.get("description","").strip()
    if not title or not description:
        return jsonify({"message":"Title and Description required"}),400
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute(
        "INSERT INTO projects(userid,title,description) VALUES(%s,%s,%s) RETURNING projectid",
        (userid,title,description)
    )
    projectid=cur.fetchone()[0]
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Project Created Successfully",
        "projectid":projectid
    }),201
@app.route("/get_projects",methods=["GET"])
def get_projects():
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    SELECT p.projectid,p.title,p.description,
    COUNT(t.taskid),
    COUNT(CASE WHEN t.status='Done' THEN 1 END)
    FROM projects p
    LEFT JOIN projects_tasks t
    ON p.projectid=t.projectid
    WHERE p.userid=%s
    GROUP BY p.projectid,p.title,p.description
    ORDER BY p.projectid DESC
    """,(userid,))
    rows=cur.fetchall()
    cur.close()
    connection.close()
    projects=[]
    for row in rows:
        total=row[3]
        done=row[4]
        progress=0
        if total>0:
            progress=round((done/total)*100)
        projects.append({
            "project_id":row[0],
            "title":row[1],
            "description":row[2],
            "total_tasks":total,
            "done_tasks":done,
            "progress":f"{progress}%"
        })

    return jsonify({"projects":projects}),200

@app.route("/add_task/<int:projectid>",methods=["POST"])
def add_task(projectid):
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    data=request.get_json()
    title=data.get("title","").strip()
    status=data.get("status","Pending").strip()
    if not title:
        return jsonify({"message":"Task title required"}),400
    if status not in ["Pending","In-Progress","Done"]:
        return jsonify({"message":"Invalid status"}),400
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute(
        "SELECT projectid FROM projects WHERE projectid=%s AND userid=%s",
        (projectid,userid)
    )
    if cur.fetchone() is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Project not found"}),404
    cur.execute(
        "INSERT INTO projects_tasks(projectid,title,status) VALUES(%s,%s,%s) RETURNING taskid",
        (projectid,title,status)
    )
    taskid=cur.fetchone()[0]
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Task Added Successfully",
        "taskid":taskid
    }),201

@app.route("/get_tasks/<int:projectid>",methods=["GET"])
def get_tasks(projectid):
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute(
        "SELECT projectid FROM projects WHERE projectid=%s AND userid=%s",
        (projectid,userid)
    )
    if cur.fetchone() is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Project not found"}),404
    cur.execute(
        "SELECT taskid,title,status FROM projects_tasks WHERE projectid=%s ORDER BY taskid",
        (projectid,)
    )
    rows=cur.fetchall()
    cur.close()
    connection.close()
    tasks=[]
    for row in rows:
        tasks.append({
            "taskid":row[0],
            "projectid":projectid,
            "title":row[1],
            "status":row[2]
        })
    return jsonify({"tasks":tasks}),200
@app.route("/update_task/<int:taskid>",methods=["PUT"])
def update_task(taskid):
    token=request.headers.get("Authorization")
    if not token:
      return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    data=request.get_json()
    title=data.get("title")
    status=data.get("status")
    if title is not None:
        title=title.strip()
    if title=="":
        return jsonify({"message":"Title cannot be empty"}),400
    if status is not None:
        if status not in ["Pending","In-Progress","Done"]:
            return jsonify({"message":"Invalid status"}),400
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    SELECT t.taskid
    FROM projects_tasks t
    JOIN projects p
    ON t.projectid=p.projectid
    WHERE t.taskid=%s AND p.userid=%s
    """,(taskid,userid))
    if cur.fetchone() is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Task not found"}),404
    if title is not None and status is not None:
        cur.execute(
        "UPDATE projects_tasks SET title=%s,status=%s WHERE taskid=%s",
        (title,status,taskid)
        )
    elif title is not None:
        cur.execute(
        "UPDATE projects_tasks SET title=%s WHERE taskid=%s",
        (title,taskid)
        )
    elif status is not None:
        cur.execute(
        "UPDATE projects_tasks SET status=%s WHERE taskid=%s",
        (status,taskid)
        )
    else:
        cur.close()
        connection.close()
        return jsonify({"message":"Nothing to update"}),400
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Task Updated Successfully"
    }),200

@app.route("/delete_task/<int:taskid>",methods=["DELETE"])
def delete_task(taskid):
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    SELECT t.taskid
    FROM projects_tasks t
    JOIN projects p
    ON t.projectid=p.projectid
    WHERE t.taskid=%s AND p.userid=%s
    """,(taskid,userid))
    if cur.fetchone() is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Task not found"}),404
    cur.execute(
        "DELETE FROM projects_tasks WHERE taskid=%s",
        (taskid,)
    )
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Task Deleted Successfully"
    }),200



@app.route("/delete_project/<int:projectid>",methods=["DELETE"])
def delete_project(projectid):
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute(
        "SELECT projectid FROM projects WHERE projectid=%s AND userid=%s",
        (projectid,userid)
    )
    if cur.fetchone() is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Project not found"}),404
    cur.execute(
        "DELETE FROM projects WHERE projectid=%s",
        (projectid,)
    )
    connection.commit()
    cur.close()
    connection.close()
    return jsonify({
        "message":"Project Deleted Successfully"
    }),200

@app.route("/project_progress/<int:projectid>",methods=["GET"])
def project_progress(projectid):
    token=request.headers.get("Authorization")
    if not token:
        return jsonify({"message":"Token required"}),401
    user=verify_jwt(token)
    if user is None:
        return jsonify({"message":"Invalid token"}),401
    userid=user["userid"]
    connection=get_db_connection()
    cur=connection.cursor()
    cur.execute("""
    SELECT
    p.projectid,
    p.title,
    COUNT(t.taskid),
    COUNT(CASE WHEN t.status='Pending' THEN 1 END),
    COUNT(CASE WHEN t.status='In-Progress' THEN 1 END),
    COUNT(CASE WHEN t.status='Done' THEN 1 END)
    FROM projects p
    LEFT JOIN projects_tasks t
    ON p.projectid=t.projectid
    WHERE p.projectid=%s AND p.userid=%s
    GROUP BY p.projectid,p.title
    """,(projectid,userid))
    project=cur.fetchone()
    if project is None:
        cur.close()
        connection.close()
        return jsonify({"message":"Project not found"}),404
    total=project[2]
    done=project[5]
    progress=0
    if total>0:
        progress=round((done/total)*100,2)
    cur.close()
    connection.close()
    return jsonify({
        "project_id":project[0],
        "title":project[1],
        "total_tasks":total,
        "pending":project[3],
        "in_progress":project[4],
        "done":project[5],
        "progress_pct":progress

    }),200

if __name__=="__main__":
    app.run(debug=True)