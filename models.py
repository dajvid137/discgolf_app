# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date, datetime # <-- Přidáme import 'date' pro jednodušší porovnání

db = SQLAlchemy()
# models.py

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    # NOVINKA: Přidáváme sloupec pro email
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    profile_image_url = db.Column(db.String(255), nullable=True)

    current_streak = db.Column(db.Integer, default=0)
    last_training_date = db.Column(db.Date, nullable=True)

    putt_sessions = db.relationship('PuttSession', backref='user')
    drives = db.relationship('Drive', backref='user')

    # Upravíme __init__ metodu, aby přijímala i email
    def __init__(self, username, email, password, profile_image_url=None):
        from werkzeug.security import generate_password_hash
        self.username = username
        self.email = email # <-- PŘIDÁNO
        self.password = generate_password_hash(password, method='pbkdf2:sha256')
        self.profile_image_url = profile_image_url
        self.current_streak = 0
        self.last_training_date = None

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)

# models.py

class PuttSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    mode = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    successful_putts = db.Column(db.Integer, nullable=True)
    total_putts = db.Column(db.Integer, nullable=True)
    
    # TENTO ŘÁDEK PRAVDĚPODOBNĚ CHYBÍ:
    distance = db.Column(db.Integer, nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Drive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    distance = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))