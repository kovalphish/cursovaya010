import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

# Get the base directory (where app.py is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

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
            Location TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    fines = None
    search_query = ""
    if request.method == 'POST':
        search_query = request.form.get('car_number', '').strip().upper()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, Violation, Amount, VioTime, Location FROM Fines WHERE UPPER(CarNumber) = UPPER(?)", (search_query,))
        fines = cursor.fetchall()
        conn.close()
    return render_template('index.html', fines=fines, query=search_query)


@app.route('/pay', methods=['POST'])
def pay():
    fine_id = request.form.get('fine_id')
    car_number = request.form.get('car_number', '').strip().upper()

    if fine_id:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Fines WHERE id = ?", (fine_id,))
        conn.commit()

        # После оплаты перезагружаем список штрафов для этого автомобиля
        cursor.execute(
            "SELECT id, Violation, Amount, VioTime, Location FROM Fines WHERE UPPER(CarNumber) = UPPER(?)",
            (car_number,)
        )
        fines = cursor.fetchall()
        conn.close()
    else:
        fines = None

    return render_template('index.html', fines=fines, query=car_number)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    error = None
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
                return redirect(url_for('admin'))
            except ValueError:
                error = "Сумма штрафа должна быть числом"
            except Exception as e:
                error = f"Ошибка базы данных: {str(e)}"
                
    return render_template('admin.html', error=error)

# Initialize database on module load
init_db()

if __name__ == '__main__':
    debug_mode = not os.environ.get('VERCEL')
    app.run(debug=debug_mode, host='0.0.0.0')
