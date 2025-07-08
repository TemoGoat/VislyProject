from ext import app, db
from werkzeug.security import generate_password_hash, check_password_hash
from models import User


with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database created successfully.")
