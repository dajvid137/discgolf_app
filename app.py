# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
from models import db, User, PuttSession, DriveSession
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from sqlalchemy import desc
# import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klic'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discgolf.db'
db.init_app(app)

# def md5_filter(s):
#     """Vrací MD5 hash řetězce, potřebný pro Gravatar."""
#     return hashlib.md5(s.encode('utf-8')).hexdigest()

# app.jinja_env.filters['md5'] = md5_filter # <-- REGISTRACE FILTRU

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

@app.route('/profile')
@login_required
def profile():
    # Načtení všech puttovacích sessions pro aktuálně přihlášeného uživatele.
    putt_sessions = PuttSession.query.filter_by(user_id=current_user.id).order_by(desc(PuttSession.date)).all()
    
    # KLÍČOVÁ OPRAVA: Jméno šablony musí být 'profile.html'
    return render_template('profile.html', putt_sessions=putt_sessions)

@app.route('/profile_settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    if request.method == 'POST':
        selected_avatar = request.form.get('avatar_id')

        # Vytvoříme si seznam všech platných avatarů pro validaci
        valid_avatars = [f'male_{i}' for i in range(1, 6)] + [f'female_{i}' for i in range(1, 6)]

        if selected_avatar and selected_avatar in valid_avatars:
            current_user.profile_image_url = selected_avatar # Uložíme identifikátor, např. "female_2"
            db.session.commit()
            flash('Avatar byl úspěšně uložen!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Neplatný výběr avatara.', 'danger')
            
    return render_template('profile_settings.html')


@app.route('/training')
@login_required
def training():
    return render_template('training.html')

@app.route('/training/putt/<mode>', methods=['GET','POST'])
@login_required
def training_putt(mode):
    if mode == 'jyly':
        template = 'jyly.html'

        session['current_putt_mode'] = mode 

        # inicializace session, pokud ještě není
        if 'score' not in session:
            session['score'] = 0
        if 'round' not in session:
            session['round'] = 1
        if 'distance' not in session:
            session['distance'] = 10
        # Nové klíče pro JEDNODUCHÝ KROK ZPĚT
        if 'prev_score' not in session:
            session['prev_score'] = 0
        if 'prev_round' not in session:
            session['prev_round'] = 1
        if 'prev_distance' not in session:
            session['prev_distance'] = 10
        

        if request.method == "POST":
            score = session.get('score', 0)
            round_ = session.get('round', 1)
            distance = session.get('distance', 10)

            # --- 1. Zpracování speciálních tlačítek (Back/Reset) ---
            
            if 'back' in request.form:
                # Jednoduché obnovení z předchozího stavu
                session['score'] = session.get('prev_score', 0)
                session['round'] = session.get('prev_round', 1)
                session['distance'] = session.get('prev_distance', 10)
                
                # Pro jistotu, aby se nešlo dvakrát zpět
                session['prev_score'] = 0 
                session['prev_round'] = 1
                session['prev_distance'] = 10
                
                return redirect(url_for('training_putt', mode='jyly'))
            
            elif 'resBtn' in request.form:
                # Reset celé hry
                session['score'] = 0
                session['round'] = 1
                session['distance'] = 10
                session['prev_score'] = 0 
                session['prev_round'] = 1
                session['prev_distance'] = 10
                return redirect(url_for('training_putt', mode='jyly'))
                
            # --- 2. Uložení aktuálního stavu jako "Předchozí" pro další krok ---
            # Tyto hodnoty se použijí, pokud se v DALŠÍM KROKU stiskne 'back'
            session['prev_score'] = score
            session['prev_round'] = round_
            session['prev_distance'] = distance

            # --- 3. Zpracování skóre a výpočet nového stavu ---



            # zpracování tlačítka
            if '0' in request.form:
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
            # elif 'resBtn' in request.form:
            #     score += 5 * distance
            #     distance = 10

            round_ += 1

            # pokud je konec hry
            if round_ >= 11:
                session['final_score'] = score
                session['score'] = 0
                session['round'] = 1
                session['distance'] = 10
                return redirect(url_for('game_over'))

            # uložení aktuálního stavu do session
            session['score'] = score
            session['round'] = round_
            session['distance'] = distance

            # redirect po POSTu → zabrání duplicitnímu přičtení skóre při refresh
            return redirect(url_for('training_putt', mode='jyly'))

        # GET – jen zobrazíme stav hry
        return render_template(
            f'putt/{template}',
            mode=mode,
            Hscore=session.get('score', 0),
            Hround=session.get('round', 1),
            Hdistance=session.get('distance', 10)
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


@app.route('/game_over', methods=['GET', 'POST'])
@login_required
def game_over():

    if request.method == "POST":

            # --- 1. Zpracování speciálních tlačítek (Back/Reset) ---
            
            if 'newGame' in request.form:
                session['score'] = 0
                session['round'] = 1
                session['distance'] = 10
                session['prev_score'] = 0 
                session['prev_round'] = 0
                session['prev_distance'] = 10
                session.pop('final_score', None)
                return redirect(url_for('training_putt', mode='jyly'))

    final_score = session.get('final_score', 0)

    # Ukládáme POUZE pokud je 'final_score' v session
    if 'final_score' in session: 
        training_mode = session.get('current_putt_mode', 'jyly')
        
        # 💡 Ukládání se provede jen tehdy, když je skóre v session
        new_session = PuttSession(
            date=datetime.utcnow(),
            score=final_score,
            mode=training_mode,
            user_id=current_user.id
        )

        db.session.add(new_session)
        db.session.commit()
        
        # DŮLEŽITÉ: Po uložení skóre smažeme, aby se při dalším refresh/POSTu neuložilo znovu.
        session.pop('final_score', None)
               
    # 3. Zobrazení stránky (použijeme dříve načtené final_score)
    return render_template("putt/game_over.html", final_score=final_score)

@app.route('/training/drive')
@login_required
def training_drive():
    # formulář pro drivy
    return render_template('drive_training.html')




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

