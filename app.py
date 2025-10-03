# app.py
from flask import Flask, render_template, redirect, url_for, request, session
from models import db, User, PuttSession, DriveSession
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discgolf.db'
db.init_app(app)

score = 0
round = 0
distance = 0


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




@app.route('/training')
@login_required
def training():
    return render_template('training.html')

@app.route('/training/putt/<mode>', methods=['GET','POST'])
@login_required
def training_putt(mode):
    if mode == 'jyly':
        template = 'jyly.html'

        # první načtení stránky → inicializace proměnných
        if request.method == "GET":
            session['score'] = 0
            session['round'] = 0
            session['distance'] = 10
            return render_template(
                f'putt/{template}', 
                mode=mode, 
                Hscore=session['score'], 
                Hround=session['round'], 
                Hdistance=session['distance']
            )

        # zpracování POST (klik na tlačítko)
        if request.method == "POST":
            score = session.get('score', 0)
            round_ = session.get('round', 0)
            distance = session.get('distance', 10)

            if '0' in request.form:
                score = score
                distance = 5
            elif '1' in request.form:
                score += 1 * distance
                distance = 6
            elif '2' in request.form:
                score += 2 * distance
                distance = 7
            elif '3' in request.form:
                score += 3 * distance
                distance = 8
            elif '4' in request.form:
                score += 4 * distance
                distance = 9
            elif '5' in request.form:
                score += 5 * distance
                distance = 10
            else:
                score = score

            round_ += 1

            # uložení zpět do session
            session['score'] = score
            session['round'] = round_
            session['distance'] = distance

            # pokud je konec hry (např. 10 kol)
            if round_ >= 10:
                return render_template("putt/game_over.html", final_score=score)

            return render_template(
                f'putt/{template}', 
                mode=mode, 
                Hscore=score, 
                Hround=round_, 
                Hdistance=distance
            )

    elif mode == 'puttovacka':
        template = 'puttovacka.html'
        # specifická logika pro Puttovačku

    elif mode == 'random':
        template = 'random.html'
        # specifická logika pro Random

    else:
        return "Neznámý režim", 404

    return render_template(f'putt/{template}', mode=mode)


@app.route('/training/drive')
@login_required
def training_drive():
    # formulář pro drivy
    return render_template('drive_training.html')




if __name__ == '__main__':
    app.run(debug=True)

