# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
from models import db, User, PuttSession, DriveSession
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import random

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
    # 1. Čtení parametrů z URL (filtru)
    # Získáváme hodnoty filtrů z URL (request.args). 
    # Pokud nejsou nastaveny, použijeme výchozí hodnoty.
    mode_filter = request.args.get('mode_filter', '')  # '' = Všechny režimy
    period_filter = request.args.get('period_filter', 'all') # 'all' = Celá historie
    
    # Začneme s dotazem na sessions aktuálního uživatele
    query = PuttSession.query.filter_by(user_id=current_user.id)
    
    # 2. Aplikace filtru podle Režimu Hry (mode)
    if mode_filter:
        query = query.filter(PuttSession.mode == mode_filter)
        
    # 3. Aplikace filtru podle Časového Období (period)
    start_date = None
    if period_filter == '7':
        # Filtrace za posledních 7 dní
        start_date = datetime.now() - timedelta(days=7)
    elif period_filter == '30':
        # Filtrace za posledních 30 dní
        start_date = datetime.now() - timedelta(days=30)
        
    if start_date:
        # Filtrujeme sessions, které jsou novější než start_date
        query = query.filter(PuttSession.date >= start_date) 
        
    # 4. Získání dat pro Tabulku Historie
    # Pro tabulku chceme data seřazená od nejnovějšího
    putt_sessions = query.order_by(desc(PuttSession.date)).all()

    # 5. Příprava dat pro Graf (Trend skóre)
    
    # Pro graf musíme data seřadit chronologicky (od nejstaršího)
    sessions_for_chart = query.order_by(PuttSession.date).all()
    
    chart_labels = [] # Datumy pro osu X
    chart_scores = [] # Skóre pro osu Y
    
    for session in sessions_for_chart:
        # Zkrácený formát data pro graf
        chart_labels.append(session.date.strftime('%d.%m.')) 
        chart_scores.append(session.score)
        
    chart_data = {
        'labels': chart_labels,
        'scores': chart_scores
    }

    # 6. Renderování šablony
    return render_template(
        'profile.html', 
        putt_sessions=putt_sessions,
        chart_data=chart_data,
        
        # Tyto parametry jsou klíčové, aby po odeslání formuláře
        # zůstaly vybrané správné hodnoty ve filtrech v HTML.
        selected_mode=mode_filter, 
        selected_period=period_filter
    )

# Seznamy dostupných ID (seeds) pro stabilní avatary
# Používáme čísla z vaší struktury: static/images/avatar/male/ID.png
MALE_AVATAR_IDS = [12, 15, 17, 19, 32, 40, 41, 42, 45, 46]
# static/images/avatar/female/ID.png
FEMALE_AVATAR_IDS = [63, 64, 73, 76, 82, 83, 85, 86, 94, 95]

@app.route('/profile_settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    
    # ------------------ LOGIKA POST (UKLÁDÁNÍ) ------------------
    if request.method == 'POST':
        # V POSTU se očekává URL ve tvaru: /static/images/avatar/gender/ID.png
        selected_avatar_url = request.form.get('avatar_url') 
        
        # Sestavíme platné prefixy pro robustní validaci
        male_prefix = url_for('static', filename='images/avatar/male/', _external=False)
        female_prefix = url_for('static', filename='images/avatar/female/', _external=False)
        
        # Validace: URL musí začínat jednou ze správných cest a končit .png
        if selected_avatar_url and selected_avatar_url.endswith('.png') and \
           (selected_avatar_url.startswith(male_prefix) or selected_avatar_url.startswith(female_prefix)):
            
            current_user.profile_image_url = selected_avatar_url 
            db.session.commit()
            flash('Avatar byl úspěšně uložen!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Neplatný výběr avatara. Zkuste to znovu.', 'danger')

    # ------------------ LOGIKA GET (ZOBRAZENÍ) ------------------
    
    num_avatars_to_show = 3
    
    # Náhodně vybereme ID
    selected_male_ids = random.sample(MALE_AVATAR_IDS, num_avatars_to_show)
    selected_female_ids = random.sample(FEMALE_AVATAR_IDS, num_avatars_to_show)

    # 1. Vytvoření seznamu pro muže
    male_avatars = []
    for avatar_id in selected_male_ids:
        # Vytvoření cesty: static/images/avatar/male/ID.png
        filename = f'images/avatar/male/{avatar_id}.png'
        url = url_for('static', filename=filename) # Flask převede na /static/images/avatar/male/ID.png
        male_avatars.append({'id': avatar_id, 'url': url})
        
    # 2. Vytvoření seznamu pro ženy
    female_avatars = []
    for avatar_id in selected_female_ids:
        # Vytvoření cesty: static/images/avatar/female/ID.png
        filename = f'images/avatar/female/{avatar_id}.png'
        url = url_for('static', filename=filename)
        female_avatars.append({'id': avatar_id, 'url': url})
        
    # Odešleme data do šablony
    return render_template(
        'profile_settings.html', 
        male_avatars=male_avatars, 
        female_avatars=female_avatars
    )



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
        if 'jyly_throw_count' not in session:
            session['jyly_throw_count'] = 0
        

        if request.method == "POST":
            score = session.get('score', 0)
            round_ = session.get('round', 1)
            distance = session.get('distance', 10)
            throw_count = session.get('jyly_throw_count', 0)

            # --- 1. Zpracování speciálních tlačítek (Back/Reset) ---
            
            if 'back' in request.form:
                # Jednoduché obnovení z předchozího stavu
                session['score'] = session.get('prev_score', 0)
                session['round'] = session.get('prev_round', 1)
                session['distance'] = session.get('prev_distance', 10)
                session['jyly_throw_count'] = session.get('prev_throw_count', 0)
                
                # Pro jistotu, aby se nešlo dvakrát zpět
                session['prev_score'] = 0 
                session['prev_round'] = 1
                session['prev_distance'] = 10
                session['prev_throw_count'] = 0
                
                return redirect(url_for('training_putt', mode='jyly'))
            
            elif 'resBtn' in request.form:
                # Reset celé hry
                session['score'] = 0
                session['round'] = 1
                session['distance'] = 10
                session['jyly_throw_count'] = 0
                session['prev_score'] = 0 
                session['prev_round'] = 1
                session['prev_distance'] = 10
                session['prev_throw_count'] = 0
                return redirect(url_for('training_putt', mode='jyly'))
                
            # --- 2. Uložení aktuálního stavu jako "Předchozí" pro další krok ---
            # Tyto hodnoty se použijí, pokud se v DALŠÍM KROKU stiskne 'back'
            session['prev_score'] = score
            session['prev_round'] = round_
            session['prev_distance'] = distance
            session['prev_throw_count'] = throw_count

            # --- 3. Zpracování skóre a výpočet nového stavu ---



            # zpracování tlačítka
            if '0' in request.form:
                distance = 5
                # session['jyly_throw_count'] += 5
            elif '1' in request.form:
                score += 1 * distance
                distance = 6
                # session['jyly_throw_count'] += 5
            elif '2' in request.form:
                score += 2 * distance
                distance = 7
                # session['jyly_throw_count'] += 5
            elif '3' in request.form:
                score += 3 * distance
                distance = 8
                # session['jyly_throw_count'] += 5
            elif '4' in request.form:
                score += 4 * distance
                distance = 9
                # session['jyly_throw_count'] += 5
            elif '5' in request.form:
                score += 5 * distance
                distance = 10
                # session['jyly_throw_count'] += 5                
            # elif 'resBtn' in request.form:
            #     score += 5 * distance
            #     distance = 10

            # round_ += 1
            if any(key in request.form for key in ['0', '1', '2', '3', '4', '5']):
                round_ += 1
                session['jyly_throw_count'] += 5

            # pokud je konec hry
            if round_ >= 11:
                session['final_score'] = score
                session['score'] = 0
                session['round'] = 1
                session['distance'] = 10
                session['jyly_throw_count'] = 0
                return redirect(url_for('game_over'))

            # uložení aktuálního stavu do session
            session['score'] = score
            session['round'] = round_
            session['distance'] = distance
            # session['jyly_throw_count'] = throw_count

            # redirect po POSTu → zabrání duplicitnímu přičtení skóre při refresh
            return redirect(url_for('training_putt', mode='jyly'))

        TOTAL_THROWS = 50

        current_throw_count = session.get('jyly_throw_count', 0)
        progress_percentage = (current_throw_count / TOTAL_THROWS) * 100 if TOTAL_THROWS > 0 else 0
        progress_style_attr = f"width: {int(progress_percentage)}%;"
        
        return render_template(
            f'putt/{template}', # <--- UŽIVATEL POUŽÍVAL f'putt/{template}', ZKONTROLUJTE CESTU!
            mode=mode,
            Hscore=session.get('score', 0),
            Hround=session.get('round', 1),
            Hdistance=session.get('distance', 10),
            
            # PROMĚNNÉ PRO PROGRESS BAR
            current_throw_count=current_throw_count, 
            progress_percentage=progress_percentage,
            progress_style_attr=progress_style_attr
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

@app.route('/leaderboard')
def leaderboard():
    # 1. Definice začátku a konce aktuálního měsíce
    today = datetime.now()
    # Začátek měsíce (první den v 00:00:00)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 2. Vytvoření poddotazu pro nalezení nejlepšího skóre pro každého uživatele
    # Filtr: pouze režim 'jyly' a pouze sessions v aktuálním měsíci
    subquery = (
        db.session.query(
            PuttSession.user_id,
            func.max(PuttSession.score).label('best_score') # Najdeme MAX skóre
        )
        .filter(PuttSession.mode == 'jyly')
        .filter(PuttSession.date >= start_of_month)
        # .filter(PuttSession.date < start_of_next_month) # Není nutné, stačí '>=' start_of_month
        .group_by(PuttSession.user_id) # Seskupíme podle uživatele
        .subquery()
    )
    
    # 3. Hlavní dotaz: Spojení (JOIN) s tabulkou User a seřazení
    # Získáme uživatelské jméno a nejlepší skóre
    leaderboard_data = (
        db.session.query(User.username, subquery.c.best_score)
        .join(subquery, User.id == subquery.c.user_id)
        .order_by(desc(subquery.c.best_score)) # Seřadíme od nejlepšího
        .all()
    )

    # Připravíme datum pro zobrazení v šabloně
    current_month_str = start_of_month.strftime('%B %Y')
    
    return render_template(
        'leaderboard.html', 
        leaderboard_data=leaderboard_data,
        current_month_str=current_month_str
    )


@app.route('/training/drive')
@login_required
def training_drive():
    # formulář pro drivy
    return render_template('drive_training.html')




if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

