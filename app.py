from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
CORS(app)

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "autoservice.db")


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================
# HTML СТРАНИЦЫ
# =====================================

@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/applications")
def applications_page():
    return render_template("applications.html")


@app.route("/create_application")
def create_application_page():
    return render_template("create_application.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/reviews")
def reviews_page():
    return render_template("reviews.html")


# =====================================
# API РЕГИСТРАЦИЯ
# =====================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.json

    login = data.get("login")
    password = data.get("password")
    full_name = data.get("full_name")
    phone = data.get("phone")
    email = data.get("email")

    if not login or not password:
        return jsonify({
            "error": "Заполните обязательные поля"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE login = ?",
        (login,)
    )

    if cur.fetchone():
        conn.close()

        return jsonify({
            "error": "Логин уже существует"
        }), 400

    password_hash = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users
        (
            login,
            password_hash,
            full_name,
            phone,
            email,
            role_id
        )
        VALUES (?, ?, ?, ?, ?, 2)
    """,
    (
        login,
        password_hash,
        full_name,
        phone,
        email
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Пользователь зарегистрирован"
    })


# =====================================
# API АВТОРИЗАЦИЯ
# =====================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.json

    login = data.get("login")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE login = ?",
        (login,)
    )

    user = cur.fetchone()

    conn.close()

    if not user:
        return jsonify({
            "error": "Пользователь не найден"
        }), 401

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify({
            "error": "Неверный пароль"
        }), 401

    return jsonify({
        "message": "Успешный вход",
        "user_id": user["id"],
        "role_id": user["role_id"]
    })


# =====================================
# СОЗДАНИЕ ЗАЯВКИ
# =====================================

@app.route("/api/applications", methods=["POST"])
def create_application():

    data = request.json

    conn = get_db()
    cur = conn.cursor()

    try:

        cur.execute("""
            INSERT INTO applications
            (
                user_id,
                car_model,
                vin,
                service_type,
                description,
                start_date,
                status_id
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            data["user_id"],
            data["car_model"],
            data["vin"],
            data["service_type"],
            data["description"],
            data["start_date"]
        ))

        conn.commit()

        return jsonify({
            "message": "Заявка создана"
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "error": "Заявка с таким VIN на эту дату уже существует"
        }), 400

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400

    finally:
        conn.close()


# =====================================
# МОИ ЗАЯВКИ
# =====================================

@app.route("/api/applications/my/<int:user_id>")
def my_applications(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            a.id,
            a.car_model,
            a.vin,
            a.service_type,
            a.description,
            a.start_date,
            s.name AS status
        FROM applications a
        JOIN application_statuses s
            ON s.id = a.status_id
        WHERE a.user_id = ?
        ORDER BY a.id DESC
    """, (user_id,))

    rows = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify(rows)


# =====================================
# ВСЕ ЗАЯВКИ ДЛЯ АДМИНА
# =====================================

@app.route("/api/admin/applications")
def admin_applications():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            a.id,
            u.full_name,
            a.car_model,
            a.vin,
            a.service_type,
            a.start_date,
            s.name AS status
        FROM applications a
        JOIN users u
            ON u.id = a.user_id
        JOIN application_statuses s
            ON s.id = a.status_id
        ORDER BY a.id DESC
    """)

    rows = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify(rows)


# =====================================
# СМЕНА СТАТУСА
# =====================================

@app.route(
    "/api/admin/applications/<int:app_id>/status",
    methods=["PATCH"]
)
def change_status(app_id):

    data = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE applications
        SET status_id = ?
        WHERE id = ?
    """,
    (
        data["status_id"],
        app_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Статус обновлён"
    })

# =====================================
# удаление
# =====================================
@app.route(
    "/api/admin/applications/<int:app_id>",
    methods=["DELETE"]
)
def delete_application(app_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM applications WHERE id = ?",
        (app_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Заявка удалена"
    })
# =====================================
# ОТЗЫВЫ
# =====================================

@app.route("/api/reviews", methods=["POST"])
def create_review():

    data = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO reviews
        (
            user_id,
            text
        )
        VALUES (?, ?)
    """,
    (
        data["user_id"],
        data["text"]
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Отзыв сохранён"
    })


@app.route("/api/reviews")
def get_reviews():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.id,
            u.full_name,
            r.text,
            r.created_at
        FROM reviews r
        JOIN users u
            ON u.id = r.user_id
        ORDER BY r.id DESC
    """)

    rows = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify(rows)

# =====================================
# ЗАПУСК
# =====================================

if __name__ == "__main__":
    app.run(debug=True)