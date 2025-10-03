# app.py
from flask import Flask, render_template, redirect, url_for, request, session
from models import db, User, PuttSession, DriveSession
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discgolf.db'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Kontrola, jestli uživatel existuje
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            error = "Toto uživatelské jméno je již obsazeno."
            return render_template('register.html', error=error)
        
        # Pokud neexistuje, vytvoříme nového uživatele
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            return render_template('training.html')
        else:
            error = "Špatné uživatelské jméno nebo heslo."
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))




@app.route('/training/putt/<mode>')
@login_required
def training_putt(mode):
    # zde podle mode vykreslíš různé typy tréninku
    return render_template('putt_training.html', mode=mode)

@app.route('/training/drive')
@login_required
def training_drive():
    return render_template('drive_training.html')





if __name__ == '__main__':
    app.run(debug=True)

