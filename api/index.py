import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Это ОБЯЗАТЕЛЬНО для работы Vercel Python Runtime!
# Vercel ожидает переменную `app` на экспорте как WSGI приложение
application = app
