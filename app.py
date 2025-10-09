# app.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
from models import db, User, PuttSession, Drive
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import random
import math
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discgolf.db'
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///discgolf.db')
# PostgreSQL vyžaduje malou úpravu URL z 'postgres://' na 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

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

# app.py

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'] # <-- Načteme email
        password = request.form['password']

        # Kontrola, jestli uživatel nebo email existuje
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            error = "Toto uživatelské jméno je již obsazeno."
            return render_template('register.html', error=error)
        
        # NOVINKA: Kontrola, jestli email již existuje
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            error = "Tato emailová adresa je již registrována."
            return render_template('register.html', error=error)
        
        # Pokud neexistuje, vytvoříme nového uživatele i s emailem
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrace proběhla úspěšně! Nyní se můžete přihlásit.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']): 
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

@app.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    # === NOVÁ ČÁST PRO FILTROVÁNÍ ===
    # 1. Načtení filtrů z URL, pokud existují
    mode_filter = request.args.get('mode_filter', '')
    period_filter = request.args.get('period_filter', 'all')
    
    # 2. Vytvoření základního dotazu na sessions daného uživatele
    query = PuttSession.query.filter_by(user_id=user.id)
    
    # 3. Aplikace filtru podle herního režimu
    if mode_filter:
        query = query.filter(PuttSession.mode == mode_filter)
        
    # 4. Aplikace filtru podle časového období
    start_date = None
    if period_filter == '7':
        start_date = datetime.now() - timedelta(days=7)
    elif period_filter == '30':
        start_date = datetime.now() - timedelta(days=30)
        
    if start_date:
        query = query.filter(PuttSession.date >= start_date)
    # === KONEC NOVÉ ČÁSTI PRO FILTROVÁNÍ ===

    # Získání dat pro Tabulku Historie (seřazeno od nejnovějšího)
    # Použijeme náš finální, vyfiltrovaný dotaz 'query'
    putt_sessions = query.order_by(desc(PuttSession.date)).all()

    # Příprava dat pro Graf (seřazeno od nejstaršího)
    sessions_for_chart = sorted(putt_sessions, key=lambda x: x.date)
    
    chart_labels = [session.date.strftime('%d.%m.') for session in sessions_for_chart]
    chart_scores = [session.score for session in sessions_for_chart]
        
    chart_data = {
        'labels': chart_labels,
        'scores': chart_scores
    }

    return render_template(
        'user_profile.html', 
        user=user, 
        putt_sessions=putt_sessions,
        chart_data=chart_data,
        # DŮLEŽITÉ: Předáme vybrané hodnoty, aby zůstaly v menu zaškrtnuté
        selected_mode=mode_filter,
        selected_period=period_filter
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


            ###################################tady od semmmmmm
            # # zpracování tlačítka
            # if '0' in request.form:
            #     distance = 5
            #     # session['jyly_throw_count'] += 5
            # elif '1' in request.form:
            #     score += 1 * distance
            #     distance = 6
            #     # session['jyly_throw_count'] += 5
            # elif '2' in request.form:
            #     score += 2 * distance
            #     distance = 7
            #     # session['jyly_throw_count'] += 5
            # elif '3' in request.form:
            #     score += 3 * distance
            #     distance = 8
            #     # session['jyly_throw_count'] += 5
            # elif '4' in request.form:
            #     score += 4 * distance
            #     distance = 9
            #     # session['jyly_throw_count'] += 5
            # elif '5' in request.form:
            #     score += 5 * distance
            #     distance = 10

            # if any(key in request.form for key in ['0', '1', '2', '3', '4', '5']):
            #     round_ += 1
            #     session['jyly_throw_count'] += 5

            ###################################tady az semmmmmm

            rules = {
                '0': (0, 5), '1': (1, 6), '2': (2, 7),
                '3': (3, 8), '4': (4, 9), '5': (5, 10)
            }

            # Najdeme, které tlačítko bylo stisknuto
            pressed_button = next((key for key in rules if key in request.form), None)

            if pressed_button:
                multiplier, next_distance = rules[pressed_button]
                
                score += multiplier * distance
                distance = next_distance
                
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
        
        #*********** ZDE ZAČÍNÁ SPRÁVNÝ VÝPOČET PROCENT PRO JYLY ***********
        
        # 1. Načtení aktuálního stavu
        score = session.get('score', 0)
        round_ = session.get('round', 1) # Kolo, které se HÁZÍ
        
        # Počet dokončených kol (použijeme pro výpočet maxima)
        completed_rounds = round_ - 1
        
        # 2. VÝPOČET MAXIMA DLE PRAVIDEL (50 bodů za každé dokončené kolo)
        max_possible_score = completed_rounds * 50
        
        # 3. Výpočet procenta (Aktuální skóre / Max. možné skóre)
        if max_possible_score > 0:
            current_percentage = (score / max_possible_score) * 100
        else:
            current_percentage = 0.0 # Když hra začíná (Round 1)
        #*********** ZDE KONČÍ SPRÁVNÝ VÝPOČET PROCENT PRO JYLY ***********



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

            # 💡 NOVÉ PROMĚNNÉ PRO PROCENTO
            max_possible_score=max_possible_score,
            current_percentage=current_percentage,
            
            # PROMĚNNÉ PRO PROGRESS BAR
            current_throw_count=current_throw_count, 
            progress_percentage=progress_percentage,
            progress_style_attr=progress_style_attr
        )
    # ***************************** Daily putt zde
# app.py (nahraďte CELOU existující sekci 'elif mode == 'daily_putt':' touto verzí)

    elif mode == 'daily_putt':
        session['current_putt_mode'] = mode
        
        SETUP_TEMPLATE = 'putt/daily_putt_setup.html'
        GAME_TEMPLATE = 'putt/daily_putt_game.html'

        # --- FÁZE 1: Nastavení (Zobrazení formuláře NEBO zpracování POST) ---
        # Kontrolujeme, zda už máme všechna data pro hru
        if 'total_putts' not in session:
            
            if request.method == "POST":
                try:
                    # Načtení nastavení z formuláře
                    total_putts = int(request.form.get('total_putts', 0))
                    distance = int(request.form.get('distance', 0))
                    discs = int(request.form.get('discs', 0))
                    
                    # 1. Validace rozsahů
                    if not (50 <= total_putts <= 300 and 5 <= distance <= 10 and 1 <= discs <= 10):
                        flash('Neplatné nastavení. Zkontrolujte rozsahy (Putts: 50-300, Vzdálenost: 5-10m, Disků: 1-10).', 'danger')
                        return render_template(SETUP_TEMPLATE)
                    
                    total_rounds = int(math.ceil(total_putts / discs))
                    session['total_rounds'] = total_rounds 

                    # Uložení nastavení do session a inicializace hry
                    session['total_putts'] = total_putts
                    session['distance'] = distance
                    session['discs'] = discs
                    # session['total_rounds'] = total_putts // discs
                    session['score'] = 0
                    session['round'] = 1
                    session['prev_score'] = 0
                    session['prev_round'] = 1
                    session['prev_discs'] = 0 
                    
                    # Přesměrování na TUTO SAMOU ROUTU (nyní se spustí Fáze 2)
                    return redirect(url_for('training_putt', mode='daily_putt'))

                except (ValueError, KeyError, ZeroDivisionError):
                    flash('Chyba při zpracování formuláře. Zkuste to znovu.', 'danger')
                    # Při chybě se vrátíme na setup, bez proměnných z herní fáze
                    return render_template(SETUP_TEMPLATE)
            
            # GET: Zobrazení formuláře pro nastavení (při prvním vstupu)
            return render_template(SETUP_TEMPLATE)


        # --- FÁZE 2: Samotná hra (Probíhá, když je 'total_putts' v session) ---
        
        # Načtení aktuálního stavu
        score = session.get('score', 0)
        round_ = session.get('round', 1)
        distance = session.get('distance', 5)
        discs = session.get('discs', 5)
        total_rounds = session.get('total_rounds', 20)
        
        if request.method == "POST":
            
            # 1. Zpracování speciálních tlačítek
            if 'back' in request.form:
                # Logika ZPĚT (návrat do PŘEDCHOZÍHO kola)
                session['score'] = session.get('prev_score', 0)
                session['round'] = session.get('prev_round', 1)
                session.pop('prev_discs', None) # Zrušíme uložené data kola
                return redirect(url_for('training_putt', mode='daily_putt'))

            elif 'resBtn' in request.form:
                # Reset celé hry (návrat na setup)
                session.pop('total_putts', None)
                return redirect(url_for('training_putt', mode='daily_putt'))

            # 2. Uložení aktuálního stavu jako "Předchozí" pro případný 'back'
            session['prev_score'] = score
            session['prev_round'] = round_
            
            # 3. Zpracování skóre pro aktuální kolo
            hits = int(request.form.get('hits', 0))

            score += hits
            round_ += 1 

            # Uložení nového stavu
            session['score'] = score
            session['round'] = round_
            
            # 4. Kontrola konce hry
            if round_ > total_rounds:
                session['final_score'] = score
                session['total_throws'] = session['total_putts']
                # Vymazání herních proměnných pro nové kolo
                session['score'] = 0
                session['round'] = 1
                session.pop('total_rounds', None) # Udržujeme jen 'total_putts'
                return redirect(url_for('game_over_daily'))

            # redirect po POSTu
            return redirect(url_for('training_putt', mode='daily_putt'))

        # --- FÁZE 3: Zobrazení herní obrazovky (GET po nastavení nebo po kole) ---

        # Musíme zkontrolovat, zda už nějaké hody proběhly, abychom se vyhnuli dělení nulou
        current_putt_count = (round_ - 1) * discs
        current_percentage = (score / current_putt_count) * 100 if current_putt_count > 0 else 0
        
        # Progres bar (Celkový počet)
        total_throws = session['total_putts']
        progress_percentage = (current_putt_count / total_throws) * 100
        progress_style_attr = f"width: {int(progress_percentage)}%;"

        discs_to_throw = discs 
        remaining_putts = session['total_putts'] - current_putt_count
        if round_ == total_rounds and remaining_putts > 0:
            # Pokud je aktuální kolo poslední A zbývají nějaké hody (např. 2), použijeme je
            # Vypočítáme zbývající hody
            discs_to_throw = remaining_putts

        return render_template(
            GAME_TEMPLATE,
            mode=mode,
            Hscore=score,
            Hround=round_,
            Hdistance=distance,
            Hdiscs=discs,
            Htotal_rounds=total_rounds,
            current_percentage=current_percentage,
            current_putt_count=current_putt_count,
            progress_style_attr=progress_style_attr,
            progress_percentage=progress_percentage # <-- KLÍČOVÁ PROMĚNNÁ pro Jinja
        )
# ... (zbytek app.py) ...
        
    elif mode == 'puttovacka':
        template = 'puttovacka.html'
        # specifická logika pro Puttovačku
    # ...

    elif mode == 'random':
        template = 'random.html'

    elif mode == 'survival':
        template = 'survival.html'

    else:
        return "Neznámý režim", 404

    return render_template(f'putt/{template}', mode=mode)


@app.route('/game_over_daily', methods=['GET', 'POST'])
@login_required
def game_over_daily():
    # Odlišná routa pro Denní trénink pro čistší logiku ukládání
    
    if request.method == "POST":
        if 'newGame' in request.form:
            # Smažeme nastavení, aby se uživateli zobrazil setup formulář
            session.pop('total_putts', None) 
            session.pop('total_rounds', None)
            session.pop('discs', None)
            session.pop('distance', None)
            session.pop('final_score', None)
            session.pop('total_throws', None)
            return redirect(url_for('training_putt', mode='daily_putt'))

    final_score = session.get('final_score', 0)
    total_throws = session.get('total_throws', 1) # Mělo by být v session

    # Ukládáme POUZE pokud je 'final_score' v session
    if 'final_score' in session: 
        training_mode = session.get('current_putt_mode', 'daily_putt')
        
        # Ukládání se provede jen tehdy, když je skóre v session
        new_session = PuttSession(
            date=datetime.utcnow(),
            mode=training_mode,
            score=final_score,                  # Stále ukládáme celkové skóre
            successful_putts=final_score,       # Pro Daily Putt je počet trefených stejný jako skóre
            total_putts=total_throws,           # NOVINKA: Uložíme celkový počet hodů
            user_id=current_user.id
        )

        db.session.add(new_session)
        db.session.commit()
        
        # DŮLEŽITÉ: Po uložení skóre smažeme, aby se při dalším refresh/POSTu neuložilo znovu.
        session.pop('final_score', None)
               
    percentage = (final_score / total_throws) * 100 if total_throws > 0 else 0
    
    return render_template(
        "putt/game_over_daily.html", 
        final_score=final_score,
        total_throws=total_throws,
        percentage=percentage
    )


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
        db.session.query(User, subquery.c.best_score) # <-- ZMĚNA ZDE
        .join(subquery, User.id == subquery.c.user_id)
        .order_by(desc(subquery.c.best_score))
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
    # with app.app_context():
    #     db.create_all() # Vytvoří tabulky podle modelů, pokud neexistují
    app.run(host="0.0.0.0", port=5000, debug=True)

