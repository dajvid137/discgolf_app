# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash # <-- IMPORT

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False) # <-- ZVĚTŠI DÉLKU PRO HASH
    putt_sessions = db.relationship('PuttSession', backref='user')
    drive_sessions = db.relationship('DriveSession', backref='user')
    profile_image_url = db.Column(db.String(255), nullable=True)

    # Přepíšeme, jak se nastavuje heslo
    def __init__(self, username, password, profile_image_url=None):
        self.username = username
        self.password = generate_password_hash(password, method='pbkdf2:sha256') # <-- HASHUJEME PŘI VYTVOŘENÍ
        self.profile_image_url = profile_image_url

    # Metoda pro ověření hesla
    def check_password(self, password):
        return check_password_hash(self.password, password) # <-- KONTROLUJEME HASH

class PuttSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    mode = db.Column(db.String(50), nullable=False) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class DriveSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
