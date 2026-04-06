import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize the database before importing the app
from app import init_db
init_db()

# Import the Flask app
from app import app as app