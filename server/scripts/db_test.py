"""
Simple DB connectivity test script.

Run with the same environment as the app. It prints whether a simple SELECT 1 succeeds.
"""
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    try:
        result = db.session.execute('SELECT 1').scalar()
        print('DB connection OK, SELECT 1 =>', result)
    except Exception as e:
        print('DB connection failed:', e)
