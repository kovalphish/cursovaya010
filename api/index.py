import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Initialize database on first load
if not os.path.exists('database.db'):
    from app import init_db
    init_db()

if __name__ == "__main__":
    app.run(debug=True)