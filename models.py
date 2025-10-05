# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    putt_sessions = db.relationship('PuttSession', backref='user')
    drive_sessions = db.relationship('DriveSession', backref='user')

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
