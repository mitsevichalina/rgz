from flask import Flask, render_template, request, redirect, url_for, session, jsonify, current_app
import os
import psycopg2
import psycopg2.extras
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'секретно-секретный-секрет')

# Генерация хешированного пароля для тестирования
password = 'pharmacist'
hashed_password = generate_password_hash(password, method='scrypt')
print(f"Хешированный пароль для 'pharmacist': {hashed_password}")

# Главная страница
@app.route("/")
@app.route("/rest-api/index")
def index():
    return render_template("index.html")

def db_connect():
    conn = psycopg2.connect(
        host="127.0.0.1",
        database="alina_mitsevich",
        user="alina_mitsevich",
        password="123"
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn, cur

@app.route('/rest-api/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        # Проверяем, какая кнопка была нажата
        if 'login' in request.form:
            # Обработка входа
            username = request.form.get('username')  # Используем .get() для безопасного доступа
            password = request.form.get('password')

            # Проверяем, что поля заполнены
            if not username or not password:
                return render_template('auth.html', error='Заполните все поля')

            # Подключаемся к базе данных
            conn, cur = db_connect()
            if current_app.config['DB_TYPE'] == 'postgres':
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            else:
                cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            # Отладочное сообщение: выводим данные пользователя
            if user:
                print(f"Найден пользователь: {user['username']}, пароль: {user['password']}")
            else:
                print(f"Пользователь с логином '{username}' не найден")

            # Проверяем, что пользователь найден и пароль совпадает
            if user and check_password_hash(user["password"], password):
                session["username"] = user["username"]
                return redirect(url_for("index"))
            else:
                print(f"Неверный пароль для пользователя '{username}'")
                return render_template('auth.html', error='Неверные логин или пароль')

        elif 'register' in request.form:
            # Обработка регистрации
            username = request.form.get('username')  # Используем .get() для безопасного доступа
            password = request.form.get('password')

            # Проверяем, что поля заполнены
            if not username or not password:
                return render_template('auth.html', register_error='Заполните все поля')

            # Подключаемся к базе данных
            conn, cur = db_connect()

            if current_app.config['DB_TYPE'] == 'postgres':
                cur.execute("SELECT username FROM users WHERE username = %s", (username,))
            else:
                cur.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('auth.html', register_error='Такой пользователь уже существует')

            # Хешируем пароль
            hashed_password = generate_password_hash(password)
            if current_app.config['DB_TYPE'] == 'postgres':
                cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            else:
                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
 
            conn.commit()
            cur.close()
            conn.close()
            return render_template('success.html', username=username)

    return render_template('auth.html')

# Страница меню
@app.route("/rest-api/menu")
def menu():
    return '''
<!DOCTYPE html>
<html>
    <head>
        <title>Аптека "аптека"</title>
        <link rel="stylesheet" href="''' + url_for('static', filename='main.css') + '''">
    </head>
    <body>
        <header>
            Аптека "аптека" - Меню
        </header>
        <main>
            <h1>Меню</h1>
            <ul>
                <li><a href="/rest-api">Главная</a></li>
                <li><a href="/rest-api/medicines">Список лекарств</a></li>
                <li><a href="/rest-api/add_medicine">Добавить лекарство</a></li>
                <li><a href="/rest-api/auth">Войти</a></li>
                <li><a href="/rest-api/logout">Выйти</a></li>
            </ul>
        </main>
        <footer>
            &copy; Аптека "аптека", 2024
        </footer>
    </body>
</html>
'''

# Страница со списком лекарств
@app.route("/rest-api/medicines", methods=["GET"])
def medicines_list():
    page = int(request.args.get("page", 1))
    search = request.args.get("search", "").lower()
    prescription_required = request.args.get("prescription_required", "all")
    min_price = float(request.args.get("min_price", 0))
    max_price = float(request.args.get("max_price", 999999))

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        query = """
            SELECT * FROM medicines
            WHERE (LOWER(name) LIKE %s OR LOWER(generic_name) LIKE %s)
            AND price BETWEEN %s AND %s
        """
    else:
        query = """
            SELECT * FROM medicines
            WHERE (LOWER(name) LIKE ? OR LOWER(generic_name) LIKE ?)
            AND price BETWEEN ? AND ?
        """
    params = (f"%{search}%", f"%{search}%", min_price, max_price)

    if prescription_required != "all":
        prescription_required_bool = prescription_required == "true"
        if current_app.config['DB_TYPE'] == 'postgres':
            query += " AND prescription_required = %s"
        else:
            query += " AND prescription_required = ?"
        params += (prescription_required_bool,)

    cur.execute(query, params)
    medicines = cur.fetchall()

    # Отладочный вывод
    print("Medicines:", medicines)

    total_medicines = len(medicines)
    medicines_for_page = medicines[(page - 1) * 10:page * 10]
    next_page = page + 1 if (page * 10) < total_medicines else None

    cur.close()
    conn.close()

    return render_template("medicines.html", medicines=medicines_for_page, next_page=next_page, page=page, search=search, prescription_required=prescription_required, min_price=min_price, max_price=max_price)

# Выход
@app.route("/rest-api/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("index"))

# Добавление нового лекарства (только для pharmacist)
@app.route("/rest-api/add_medicine", methods=["GET", "POST"])
def add_medicine():
    if session.get("username") != "pharmacist":
        return redirect(url_for("medicines_list"))

    if request.method == "POST":
        name = request.form["name"]
        generic_name = request.form["generic_name"]
        prescription_required = request.form.get("prescription_required") == "true"  # Преобразуем строку в булево значение
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])

        conn, cur = db_connect()
        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                INSERT INTO medicines (name, generic_name, prescription_required, price, quantity)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, generic_name, prescription_required, price, quantity))
        else:
            cur.execute("""
                INSERT INTO medicines (name, generic_name, prescription_required, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (name, generic_name, prescription_required, price, quantity))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("medicines_list"))

    return render_template("add_medicine.html")

# Редактирование лекарства (только для pharmacist)
@app.route("/rest-api/edit_medicine/<string:name>", methods=["GET", "POST"])
def edit_medicine(name):
    if session.get("username") != "pharmacist":
        return redirect(url_for("medicines_list"))

    conn, cur = db_connect()

    if request.method == "POST":
        generic_name = request.form["generic_name"]
        prescription_required = request.form.get("prescription_required") == "true"  # Преобразуем строку в булево значение
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])
        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                UPDATE medicines
                SET generic_name = %s, prescription_required = %s, price = %s, quantity = %s
                WHERE name = %s
            """, (generic_name, prescription_required, price, quantity, name))
        else:
            cur.execute("""
                UPDATE medicines
                SET generic_name = ?, prescription_required = ?, price = ?, quantity = ?
                WHERE name = ?
            """, (generic_name, prescription_required, price, quantity, name))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("medicines_list"))

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM medicines WHERE name = %s", (name,))
    else:
        cur.execute("SELECT * FROM medicines WHERE name = ?", (name,))
    medicine = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("edit_medicine.html", medicine=medicine)

# Удаление лекарства (только для pharmacist)
@app.route("/rest-api/delete_medicine/<string:name>", methods=["POST"])
def delete_medicine(name):
    # Проверка роли пользователя
    if session.get("username") != "pharmacist":
        return redirect(url_for("medicines_list"))

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("DELETE FROM medicines WHERE name = %s", (name,))
    else:
        cur.execute("DELETE FROM medicines WHERE name = ?", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("medicines_list"))

# REST API для работы с лекарствами
@app.route("/rest-api/medicines", methods=["GET", "POST"])
def api_medicines():
    conn, cur = db_connect()

    if request.method == "GET":
        cur.execute("SELECT * FROM medicines")
        medicines = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(medicine) for medicine in medicines])

    elif request.method == "POST":
        data = request.json
        name = data["name"]
        generic_name = data["generic_name"]
        prescription_required = data["prescription_required"]
        price = data["price"]
        quantity = data["quantity"]

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                INSERT INTO medicines (name, generic_name, prescription_required, price, quantity)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, generic_name, prescription_required, price, quantity))
        else:
            cur.execute("""
                INSERT INTO medicines (name, generic_name, prescription_required, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (name, generic_name, prescription_required, price, quantity))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Medicine added successfully"}), 201

@app.route("/rest-api/medicines/<int:medicine_id>", methods=["GET", "PUT", "DELETE"])
def api_medicine(medicine_id):
    conn, cur = db_connect()

    if request.method == "GET":
        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("SELECT * FROM medicines WHERE medicine_id = %s", (medicine_id,))
        else:
            cur.execute("SELECT * FROM medicines WHERE medicine_id = ?", (medicine_id,))
        medicine = cur.fetchone()
        cur.close()
        conn.close()
        if medicine:
            return jsonify(dict(medicine))
        return jsonify({"message": "Medicine not found"}), 404

    elif request.method == "PUT":
        data = request.json
        name = data["name"]
        generic_name = data["generic_name"]
        prescription_required = data["prescription_required"]
        price = data["price"]
        quantity = data["quantity"]

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                UPDATE medicines
                SET name = %s, generic_name = %s, prescription_required = %s, price = %s, quantity = %s
                WHERE medicine_id = %s
            """, (name, generic_name, prescription_required, price, quantity, medicine_id))
        else:
            cur.execute("""
                UPDATE medicines
                SET name = ?, generic_name = ?, prescription_required = ?, price = ?, quantity = ?
                WHERE medicine_id = ?
            """, (name, generic_name, prescription_required, price, quantity, medicine_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Medicine updated successfully"})

    elif request.method == "DELETE":
        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("DELETE FROM medicines WHERE medicine_id = %s", (medicine_id,))
        else:
            cur.execute("DELETE FROM medicines WHERE medicine_id = ?", (medicine_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Medicine deleted successfully"})

if __name__ == "__main__":
    app.run(debug=True)