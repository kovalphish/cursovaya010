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

# Database path - use /tmp for serverless environments (Vercel) where filesystem is read-only
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/database.db'
    # Копируем исходную базу данных из репозитория в /tmp при первом запуске
    original_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    # Копируем только если база ещё не была скопирована
    if os.path.exists(original_db) and not os.path.exists(DB_PATH):
        import shutil
        shutil.copyfile(original_db, DB_PATH)
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_path():
    return DB_PATH

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            CarNumber TEXT NOT NULL,
            Violation TEXT,
            Amount REAL,
            VioTime TEXT,
            Location TEXT,
            status TEXT DEFAULT 'unpaid'
        )
    ''')
    # Миграция: проверяем и добавляем поле status если его нет (для старых баз)
    cursor.execute("PRAGMA table_info(Fines)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE Fines ADD COLUMN status TEXT DEFAULT 'unpaid'")
        conn.commit()
    # Устанавливаем status='unpaid' для всех записей где status IS NULL (старые записи)
    cursor.execute("UPDATE Fines SET status = 'unpaid' WHERE status IS NULL OR status = ''")
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
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

    return render_template('index.html', fines=fines, query=search_query, error=error, success=success)


@app.route('/pay', methods=['POST'])
def pay():
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
    
    error = None
    debug_info = []
    
    # Отладочная информация только для админа
    debug_info.append(f"✅ Режим: {'VERCEL' if os.environ.get('VERCEL') else 'LOCAL'}")
    debug_info.append(f"📁 Путь к базе: {get_db_path()}")
    debug_info.append(f"📁 База существует: {'✅ ДА' if os.path.exists(get_db_path()) else '❌ НЕТ'}")
    
    if os.environ.get('VERCEL'):
        debug_info.append(f"📁 Исходная база существует: {'✅ ДА' if os.path.exists(os.path.join(BASE_DIR, 'database.db')) else '❌ НЕТ'}")
    
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
                cursor.execute("INSERT INTO Fines (CarNumber, Violation, Amount, VioTime, Location) VALUES (?, ?, ?, ?, ?)",
                               (car_number, violation, amount, vio_time, location))
                conn.commit()
                conn.close()
                success = f"✅ Нарушение для {car_number} успешно добавлено"
            except ValueError:
                error = "Сумма штрафа должна быть числом"
            except Exception as e:
                error = f"Ошибка базы данных: {str(e)}"

    return render_template('admin.html', error=error, success=success, debug_info=debug_info)

# Initialize database on module load
init_db()

if __name__ == '__main__':
    debug_mode = not os.environ.get('VERCEL')
    app.run(debug=debug_mode, host='0.0.0.0')
