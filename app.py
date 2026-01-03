from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

import sqlite3

app = Flask(__name__)
# app.secret_key = "secret_key_change_later"
app.secret_key = "dev_key_change_in_production"

def get_db():
    return sqlite3.connect("users.db")

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
       CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first", "error")
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user" not in session:
                flash("Please log in first", "error")
                return redirect("/login")

            if session.get("role") != role:
                flash("Access denied", "error")
                return redirect("/dashboard")

            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, "user")
            )
            db.commit()
            db.close()

            flash("Account created successfully", "success")
            return redirect("/login")

        except Exception as e:
            print("REGISTER ERROR:", e)
            flash("Username already exists", "error")
            return redirect("/register")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        db.close()

        if user and check_password_hash(user[2], password):
            session["user"] = user[1]
            session["role"] = user[3]
            print(session)  # TEMPORARY: for verification only
            flash("Login successful", "success")
            return redirect("/dashboard")

        # return "Invalid credentials"
        flash("Invalid username or password", "error")
        return redirect("/login")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=session["user"])

@app.route("/profile")
@login_required
def profile():
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT username, role FROM users WHERE username = ?",
        (session["user"],)
    )
    user = cur.fetchone()
    db.close()

    return render_template(
        "profile.html",
        username=user[0],
        role=user[1]
    )


@app.route("/admin")
@role_required("admin")
def admin():
    return "Admin panel"

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect("/login")

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    db.close()
    return render_template("admin_dashboard.html", users=users)

@app.route("/admin/update-role/<int:user_id>/<role>")
@role_required("admin")
def update_role(user_id, role):
    if role not in ["user", "admin"]:
        flash("Invalid role", "error")
        return redirect("/admin/dashboard")

    # Prevent admin from changing their own role
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username FROM users WHERE username = ?", (session["user"],))
    current_user = cur.fetchone()

    if current_user and current_user[0] == user_id:
        flash("You cannot change your own role", "error")
        db.close()
        return redirect("/admin/dashboard")

    cur.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id)
    )
    db.commit()
    db.close()

    flash("User role updated", "success")
    return redirect("/admin/dashboard")

if __name__ == "__main__":
    app.run(debug=True)