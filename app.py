import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session

# Get the base directory (where app.py is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = 'bdf872a9d3ef5c7a8b9e1d2f3a4c5b6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2'
ADMIN_PASSWORD = 'admin123'

# Database path
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/database.db'
else:
    DB_PATH = os.path.join(BASE_DIR, 'database.db')

def get_db_path():
    return DB_PATH

INITIAL_FINES = [
    ('А777АА77', 'Превышение скорости', 500.0, '2026-02-13 12:00', 'ул. Ленина, д. 1'),
    ('В888ВВ88', 'Проезд на красный', 1000.0, '2026-03-15 18:30', 'пр. Мира, д. 5'),
]

def ensure_db():
    """Гарантируем что база существует с правильной структурой и начальными данными"""
    needs_seed = False

    if not os.path.exists(DB_PATH):
        needs_seed = True

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Создаём таблицу если нет
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Fines'")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE Fines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                CarNumber TEXT NOT NULL,
                Violation TEXT,
                Amount REAL,
                VioTime TEXT,
                Location TEXT,
                status TEXT DEFAULT 'unpaid'
            )
        ''')
        conn.commit()
        needs_seed = True

    # Миграция: добавляем колонку status если нет
    cursor.execute("PRAGMA table_info(Fines)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute('''
            CREATE TABLE Fines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                CarNumber TEXT NOT NULL,
                Violation TEXT,
                Amount REAL,
                VioTime TEXT,
                Location TEXT,
                status TEXT DEFAULT 'unpaid'
            )
        ''')
        cursor.execute('''
            INSERT INTO Fines_new (id, CarNumber, Violation, Amount, VioTime, Location, status)
            SELECT id, CarNumber, Violation, Amount, VioTime, Location, 'unpaid' FROM Fines
        ''')
        cursor.execute("DROP TABLE Fines")
        cursor.execute("ALTER TABLE Fines_new RENAME TO Fines")
        conn.commit()

    # Сеем начальные данные если база пустая (холодный старт на Vercel)
    if needs_seed:
        cursor.execute("SELECT COUNT(*) FROM Fines")
        if cursor.fetchone()[0] == 0:
            for car, viol, amt, vtime, loc in INITIAL_FINES:
                cursor.execute(
                    "INSERT INTO Fines (CarNumber, Violation, Amount, VioTime, Location, status) VALUES (?, ?, ?, ?, ?, 'unpaid')",
                    (car, viol, amt, vtime, loc)
                )
            conn.commit()

    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    ensure_db()
    fines = None
    search_query = ""
    error = None
    success = None

    if request.method == 'POST':
        search_query = request.form.get('car_number', '').strip().upper()

        if not search_query:
            error = "⚠️ Введите номер автомобиля"
        else:
            try:
                conn = sqlite3.connect(get_db_path())
                cursor = conn.cursor()
                cursor.execute("SELECT id, Violation, Amount, VioTime, Location FROM Fines WHERE UPPER(CarNumber) = UPPER(?) AND status = 'unpaid'", (search_query,))
                fines = cursor.fetchall()
                conn.close()
                success = f"✅ Поиск выполнен для номера: {search_query}"
            except Exception as e:
                error = f"❌ Ошибка соединения с базой данных"
    # GET запрос - оставляем fines=None, search_query="" чтобы страница была чистой

    return render_template('index.html', fines=fines, query=search_query, error=error, success=success)


@app.route('/pay', methods=['POST'])
def pay():
    ensure_db()
    fine_id = request.form.get('fine_id')
    car_number = request.form.get('car_number', '').strip().upper()
    success = None

    if fine_id:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        # Помечаем штраф как оплаченный вместо удаления
        cursor.execute("UPDATE Fines SET status = 'paid' WHERE id = ?", (fine_id,))
        conn.commit()

        # После оплаты перезагружаем список неоплаченных штрафов для этого автомобиля
        cursor.execute(
            "SELECT id, Violation, Amount, VioTime, Location FROM Fines WHERE UPPER(CarNumber) = UPPER(?) AND status = 'unpaid'",
            (car_number,)
        )
        fines = cursor.fetchall()
        conn.close()
        success = "✅ Штраф успешно оплачен"
    else:
        fines = None

    return render_template('index.html', fines=fines, query=car_number, success=success)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged'] = True
            return redirect(url_for('admin'))
        else:
            error = "❌ Неверный пароль"
    return render_template('login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    ensure_db()
    
    error = None
    debug_info = []
    
    # Отладочная информация только для админа
    debug_info.append(f"✅ Режим: {'VERCEL' if os.environ.get('VERCEL') else 'LOCAL'}")
    debug_info.append(f"📁 Путь к базе: {get_db_path()}")
    debug_info.append(f"📁 База существует: {'✅ ДА' if os.path.exists(get_db_path()) else '❌ НЕТ'}")
    
    if os.environ.get('VERCEL'):
        debug_info.append(f"📁 Исходная база: данные сеются из кода")
    
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Fines")
        total = cursor.fetchone()[0]
        debug_info.append(f"📊 Всего записей в базе: {total}")
        conn.close()
    except Exception as e:
        debug_info.append(f"💥 Ошибка: {str(e)}")
    
    success = None
    if request.method == 'POST':
        car_number = request.form.get('car_number', '').strip().upper()
        violation = request.form.get('violation', '').strip()
        amount = request.form.get('amount', '').strip()
        vio_time = request.form.get('vio_time', '').strip()
        location = request.form.get('location', '').strip()

        if not car_number:
            error = "Введите номер автомобиля"
        else:
            try:
                amount = float(amount) if amount else 0.0
                conn = sqlite3.connect(get_db_path())
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Fines (CarNumber, Violation, Amount, VioTime, Location, status) VALUES (?, ?, ?, ?, ?, 'unpaid')",
                               (car_number, violation, amount, vio_time, location))
                conn.commit()
                conn.close()
                success = f"✅ Нарушение для {car_number} успешно добавлено"
            except ValueError:
                error = "Сумма штрафа должна быть числом"
            except Exception as e:
                error = f"Ошибка базы данных: {str(e)}"

    return render_template('admin.html', error=error, success=success, debug_info=debug_info)

if __name__ == '__main__':
    debug_mode = not os.environ.get('VERCEL')
    app.run(debug=debug_mode, host='0.0.0.0')
