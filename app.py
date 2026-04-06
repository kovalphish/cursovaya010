import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Database path - works in both local and Vercel environments
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
    if request.method == 'POST':
        car_number = request.form.get('car_number').strip().upper()
        violation = request.form.get('violation')
        amount = request.form.get('amount')
        vio_time = request.form.get('vio_time')
        location = request.form.get('location')

        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Fines (CarNumber, Violation, Amount, VioTime, Location) VALUES (?, ?, ?, ?, ?)",
                       (car_number, violation, amount, vio_time, location))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)