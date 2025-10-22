from flask import Flask, render_template, request, redirect, g, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail
import pass_reset
import sqlite3
import os
import random
import json
import copy
#import uuid
import ttrpg
from data_loader import reload_base_data, load_category
import datetime
from dotenv import load_dotenv
from openai import OpenAI
from threading import Thread
import time
import jwt



global debug
debug = False

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# ---------- Inicializace ----------
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#načtení enviromental variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_CONFIG_SECRET")
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = os.getenv("MAIL_PORT")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")
#TODO:Zmenit!!! je nastaveno na localhost
app.config['SERVER_NAME'] = os.getenv("SERVER_NAME")
app.config['PREFERRED_URL_SCHEME'] = os.getenv("PREFERRED_URL_SCHEME")
mail = Mail(app)
DATABASE = 'main.db'

# Inicializace klienta OPENAI
client = OpenAI()


# ---------- Flask-Login Setup ----------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ---------- User class ----------
#Flask volá celý User objekt znovu mezi requests, takže všechno mezitím uložené se ztratí, asi spíše uložit do session?
class User(UserMixin):
    def __init__(self, id_, username, email=None):
        self.id = id_
        self.username = username
        self.email = email
        # self.character = Chararacter(user_id=id_)

    def get_reset_token(self, expires=600):
        """Vygeneruje JWT token platný po dobu 'expires' sekund"""
        payload = {
            'reset_password': self.username,
            'exp': time.time() + expires
        }
        token = jwt.encode(payload, key=os.getenv('FLASK_CONFIG_SECRET'), algorithm='HS256')
        return token
    
    @staticmethod
    def verify_reset_token(token):
        """Ověří JWT token, vrátí username pokud je platný"""
        try:
            payload = jwt.decode(token, key=os.getenv('SECRET_KEY_FLASK'), algorithms=['HS256'])
            return payload.get('reset_password')
        except jwt.ExpiredSignatureError:
            return None  # token expiroval
        except jwt.InvalidTokenError:
            return None  # token je neplatný


# ---------- Character class ----------
atributes = {
    "strength":0,
    "dexterity":0,
    "constitution":0,
    "intelligence":0,
    "wisdom":0,
    "charisma":0
}

class Chararacter():
    def __init__(self, user_id, id_ = "",  class_ = "", name = "None", notes = "", inventory = "", level = 1, hp = 1, atributes = atributes):
        self.id = id_
        self.user_id = user_id
        self.char_class = class_
        self.atributes = atributes
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.notes = notes
        self.inventory = inventory
        self.level = level


# ---------- Database connection ----------
# pro práci s db je potřeba app.context
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Přístup ke sloupcům podle názvu
    return g.db

# ---------- Co dělat když uživatel ukončí spojení ---------- 
@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db:
        db.close()

# ---------- Načtení uživatele pro Flask-Login ----------
@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        return User(id_=user['user_id'], username=user['username'])
    return None

# ---------- Inicializace databáze ----------
def init_db():
    if not os.path.exists(DATABASE):
        db = sqlite3.connect(DATABASE)
        db.execute("PRAGMA foreign_keys = ON")

        db.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')

        db.execute('''
            CREATE TABLE characters (
                char_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                strength INTEGER DEFAULT 8,
                dexterity INTEGER DEFAULT 8,
                constitution INTEGER DEFAULT 8,
                intelligence INTEGER DEFAULT 8,
                wisdom INTEGER DEFAULT 8,
                charisma INTEGER DEFAULT 8,
                ac INTEGER DEFAULT 10,
                hp INTEGER DEFAULT 1,
                max_hp INTEGER DEFAULT 1,
                temp_hp INTEGER DEFAULT 0,
                hit_die INTEGER DEFAULT 1,
                initiative INTEGER DEFAULT 0, 
                level INTEGER DEFAULT 1,
                speed INTEGER DEFAULT 30,
                char_class TEXT DEFAULT None,
                char_subclass TEXT DEFAULT None,
                char_race TEXT DEFAULT None,
                notes TEXT DEFAULT None,
                status TEXT DEFAULT "Alive",
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        db.execute('''
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                item_id STRING NOT NULL,
                count FLOAT NOT NULL,
                equipped INTEGER DEFAULT 0,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.execute('''
            CREATE TABLE spells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id STRING NOT NULL,
                spell_id STRING NOT NULL,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.execute('''
            CREATE TABLE character_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 3),
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.execute('''
            CREATE TABLE features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                feature_id STRING NOT NULL,
                current_charges INTEGER NOT NULL,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.execute('''
            CREATE TABLE feats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                feat_id STRING NOT NULL,
                level INTEGER NOT NULL,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.execute('''
            CREATE TABLE character_choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                choice_id STRING NOT NULL,
                choice STRING NOT NULL,
                level INTEGER NOT NULL,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.commit()
        db.close()



#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# ---------- App Routes ----------
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# ---------- Registrace ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pw_hash = generate_password_hash(password)
        email = request.form['email']

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", (username, pw_hash, email))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            # Flask umožnuje použít lepší podobu Alertu v podobě FLash, který se následně dá v jinja2 vypsat při znovunačtení stránky, proto je uživatel redirected zpět na stránku register.html
            flash("Uživatelské jméno či email je již používáno", "danger")
    return render_template('register.html')

# ---------- Přihlášení ----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", 
            (request.form['username'],)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], request.form['password']):
            user_obj = User(id_=user['user_id'], username=user['username'])
            login_user(user_obj)
            return redirect('/dashboard')

        # flash message jako u registrace
        flash("Neplatné přihlašovací údaje!", "danger")
        return redirect('/login')
    return render_template('login.html')

# ---------- Password reset ----------
@app.route('/pass_reset', methods=['GET', 'POST'])
def password_reset():
    # Lognutý uživatel by neměl mít možnost resetovat heslo
    if current_user.is_authenticated:
        return redirect('/dashboard')

    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        # Flash zpráva se zobrazí vždy (z bezpečnostních důvodů)
        flash("Pokud existuje účet s tímto e-mailem, zkontrolujte schránku pro další kroky.", "info")

        if user:
            # vytvoříme User objekt
            user_obj = User(id_=user['user_id'], username=user['username'], email=user['email'])
            # pošli e-mail asynchronně - jinak to až na moc dlouho zamrzne aplikaci
            Thread(target=pass_reset.send_reset_email, args=(user_obj,)).start()

        return redirect('/login')

    return render_template('pass_reset.html')

# ---------- Password reset - Token stránka ----------
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    print("DEBUG token:", token, type(token))
    try:
        payload = jwt.decode(token, key=os.getenv('FLASK_CONFIG_SECRET'), algorithms=['HS256'])
        username = payload.get('reset_password')
    except jwt.ExpiredSignatureError:
        flash('Odkaz pro reset hesla vypršel.', 'danger')
        return redirect('/pass_reset')
    except jwt.InvalidTokenError:
        flash('Neplatný odkaz pro reset hesla.', 'danger')
        return redirect('/pass_reset')

    if request.method == 'POST':
        new_password = request.form['password']
        pw_hash = generate_password_hash(new_password)
        db = get_db()
        db.execute("UPDATE users SET password_hash = ? WHERE username = ?", (pw_hash, username))
        db.commit()
        flash('Heslo bylo úspěšně změněno. Můžeš se přihlásit.', 'success')
        return redirect('/login')

    return render_template('pass_reset_change.html', username=username)
    

# ---------- Odhlášení ----------
@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

# ---------- Dashboard ----------
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    rows = db.execute("SELECT * FROM characters WHERE user_id = ? AND status = 'Alive'", (current_user.id,)).fetchall()
    db.commit()
    return render_template('dashboard.html', data=rows, username=current_user.username)

# ---------- User Info ----------
@app.route('/user_info')
@login_required
def user_info():
    db = get_db()
    rows = db.execute("SELECT * FROM users WHERE user_id = ?", (current_user.id,)).fetchone()
    return render_template('user_info.html', data=rows, user=current_user)

# ---------- Sheet ----------
@app.route("/sheet/<int:char_id>")
@login_required
def sheet(char_id):
    db = get_db()

    # Načti postavu - pokud neexistuje nebo uživateli nepatří, vrať chybu
    char = db.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = ?",(char_id, current_user.id)).fetchone()
    
    if char is None:
        return "Postava nebyla nalezena nebo ti nepatří", 404

    # Uložíme do session aktuální char
    session["current_character_id"] = char_id

    # --- Načtení dat z DB a jejich párování s data_page_template-------------------------------------------------
    # ----Načtení dat z DB-----
    # inventář
    items = db.execute("SELECT item_id, count, equipped FROM inventory WHERE char_id = ?",(char_id,)).fetchall()

    # dovednosti
    prof = db.execute("SELECT skill_name, proficiency_level FROM character_skills WHERE char_id = ?",(char_id,)).fetchall()

    # features - aktuální stav (předpokládám, že feature_name odpovídá name v JSONu)
    features_db = db.execute("SELECT feature_id, current_charges FROM features WHERE char_id = ?",(char_id,)).fetchall()

    
    # --- Deep copy šablony (aby zůstala čistá pro ostatní requesty) -----
    page_template = copy.deepcopy(data_page_template)

    
    # --- Převod DB resultů na dicty pro rychlý lookup --------------------
    # vše se klíčuje podle UUID, pouze skills ho nemají, takže ty se klíčují podle jména
    # TODO: Přesunou tento krok do základního běhu programu, aby se to nemuselo dít při každém volání /sheet funkce
    
    proficiencies_dict = {
        row["skill_name"].lower(): row["proficiency_level"] for row in prof
    }

    item_data_dict = {
        row["item_id"]: {"count": row["count"], "equipped": row["equipped"]} for row in items
    }

    feature_data_dict = {
        row["feature_id"]: row["current_charges"] for row in features_db
    }

    # --- Aktualizace položek (items) -------------------------------------
    for item in page_template.get("items", []):
        item_uuid = item.get("UUID")
        data = item_data_dict.get(item_uuid)
        if data:
            item["checked"] = True
            item["count"] = data.get("count", 0)
            item["equipped"] = data.get("equipped", 0)
        else:
            item["checked"] = False
            item["count"] = 0
            item["equipped"] = 0

    
    #Features
    #page_template = load_category("class", "features", char["char_class"], char, page_template, feature_data_dict)
    page_template = load_category(
    source_type="class",
    category="features",
    source_name=char["char_class"],
    char=char,
    page_template=page_template,
    saved_data=feature_data_dict,
    #TODO: SET TO FALSE
    reload_data=False  # nastav True, pokud chceš při každém načtení znovu načíst JSONy
    )
    

    # Spells byly dělány pozdeji, takže jsou udělány jinak než zbytek
    # Spells
    row_character_spells = db.execute("SELECT spell_id FROM spells WHERE char_id = ?",(char_id,)).fetchall()

    # vyrobíme list samotných spell_id hodnot
    character_spells = [row["spell_id"] for row in row_character_spells]

    for spell_id, spell_data in page_template.get("spells", {}).items():
        if spell_id in character_spells:
            spell_data["checked"] = True
        else:
            spell_data["checked"] = False
    pass

    #Race - bylo přesunuto do vlastního modulu data_loader.py 
    #TODO: Upravit do podoby features 334
    page_template = load_category("race", "traits", char["char_race"], char, page_template)


    #Feats
    feats_db = db.execute("SELECT * FROM feats WHERE char_id = ?",(char_id,)).fetchall()
    character_feats = [row["feat_id"] for row in feats_db]
    for feat_id, feat_data in page_template.get("feats", {}).items():
        if feat_id in character_feats:
            feat_data["known"] = True
        else:
            feat_data["known"] = False


    # --- Výpočet ostatních hodnot ---
    bonus = ttrpg.get_proficiency_bonus(char["level"])

    # --- Render ---
    return render_template(
        "sheet.html",
        character=char,
        user=current_user,
        data_page_template=page_template,
        saved_items=items,
        proficiencies=proficiencies_dict,
        prof_bonus=bonus,
        features=page_template.get("features", []),
        traits=page_template.get("traits", [])
    )

# ---------- Sheet Edit Mode ----------

@app.route("/sheet_edit_mode/<int:char_id>")
@login_required
def sheet_edit_mode(char_id):
    db = get_db()
    char = db.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = ?",(char_id, current_user.id)).fetchone()
    prof = db.execute("SELECT skill_name, proficiency_level FROM character_skills WHERE char_id = ?",(char_id,)).fetchall()
    known_feats = db.execute("SELECT * FROM feats WHERE char_id = ?", (char_id,)).fetchall()
    known_choices = db.execute("SELECT * FROM character_choices WHERE char_id = ?", (char_id,)).fetchall()
    

    # Vytvoření slovníku pro hledání následně v šabloně
    #Potřeba převést na dict, jinja nerada pracuje s sqlite3.row object
    proficiencies_dict = {
    row["skill_name"].lower(): row["proficiency_level"]
    for row in prof
    }

    known_feats_by_level = {row["level"]: row["feat_id"] for row in known_feats}

    
    known_dict = {
        row["choice_id"].lower(): row["choice"]
        for row in known_choices
    }

    pass
    if char is None:
        return "Postava nebyla nalezena nebo ti nepatří"

    return render_template("sheet_edit_mode.html", character=char, data_page_template = data_page_template, proficiencies=proficiencies_dict, player_classes = folders_class, player_races = folders_race, known_feats = known_feats_by_level, known_dict =  known_dict)


# ---------- Create new Character ----------

@app.route("/create_new", methods=["POST"])
@login_required
def create_new():
    
    name = request.form.get("name")
    db = get_db()
    db.execute("INSERT INTO characters (user_id,name) VALUES (?,?)", (current_user.id, name))
    db.commit()

    #TODO:Změnit po přechodu na UUID
    # char = db.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = (SELECT max(char_id) FROM characters)",(current_user.id)).fetchone()
    #musí být předáno jako tuple                                                        ....
    char_id = db.execute("""SELECT MAX(char_id) FROM characters WHERE user_id = ?""",(current_user.id,)).fetchone()[0]
    session["current_character_id"] = char_id
    # print(f"Session: {session["current_character_id"]}")
    char = db.execute("""SELECT * FROM characters WHERE char_id = ? """, (char_id,)).fetchone()
    prof = db.execute("SELECT skill_name, proficiency_level FROM character_skills WHERE char_id = ?",(char_id,)).fetchall()
    known_feats = db.execute("SELECT * FROM feats WHERE char_id = ?", (char_id,)).fetchall()


    # Vytvoření slovníku pro hledání následně v šabloně
    proficiencies_dict = {
    row["skill_name"].lower(): row["proficiency_level"]
    for row in prof
    }

    known_feats_by_level = {row["level"]: row["feat_id"] for row in known_feats}

    
    return render_template("sheet_edit_mode.html", character=char, data_page_template = data_page_template, proficiencies=proficiencies_dict, player_classes = folders_class, player_races = folders_race, known_feats = known_feats_by_level)


@app.route('/chat')
@login_required
def chat_test():
    return render_template('chat.html')


#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# ---------- API Endpoints ----------
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


#--------------------------------------------
# ---------- API delete character ----------
#--------------------------------------------
@login_required
@app.route('/api/user_info', methods=['POST'])
def change_user_info():
    data = request.get_json()
    print(data)
    db = get_db()
    result = db.execute("SELECT password_hash from USERS where user_id = ?",(current_user.id,)).fetchone()["password_hash"]
    #Kontrola hesla
    if(check_password_hash(result,data["password"])):
        if data["type"] == "password":
            new_hash = generate_password_hash(data["data"])
            db.execute("UPDATE USERS SET password_hash = ? WHERE user_id = ?", (new_hash,current_user.id))
        if data["type"] == "email":
            # Kontrola zda již není email/username používán jiným uživatelem (pokud je používán jím samotným tak si ho může "změnit" na to stávající ale reálně žádná změna nepojde)
            result = db.execute("SELECT email, user_id from USERS where email = ?",(data["data"],)).fetchall()
            if len(result) > 0 and result[0]["user_id"] != current_user.id:
                return {"status": "Email in use", "received": data}
            # Input do db by měl být už ochráněn tímto způsobem
            # TODO: Projít zda je chráněn
            db.execute("UPDATE USERS SET email = ? WHERE user_id = ?", (data["data"],current_user.id))

        if data["type"] == "username":
            result = db.execute("SELECT username, user_id from USERS where username = ?",(data["data"],)).fetchall()
            if len(result) > 0 and result[0]["user_id"] != current_user.id:
                return {"status": "Username in use", "received": data}
            db.execute("UPDATE USERS SET username = ? WHERE user_id = ?", (data["data"],current_user.id))
        db.commit()

        return {"status": "OK", "received": data}
    else:
        return {"status": "Incorrect Password", "received": data}
    


@login_required
@app.route('/api/delete', methods=['POST'])
def delete_char():
    data = request.get_json()
    print(data)
    db = get_db()
    # if character gets deleted, nahraď alive status v db unix time stamp, takže se pak dá určit kdy byly postavy zmazány a dají se později natrvalo smazat z db
    db.execute('UPDATE characters SET status = ? WHERE char_id = ?',(datetime.datetime.now().timestamp() , data["char_id"]))
    db.commit()

    return {"status": "OK", "received": data}

#------------------------------------
# ---------- API Stats ----------
#------------------------------------
@login_required
@app.route('/api/stats', methods=['POST'])
def stats_api():
    data = request.get_json()
    print(data)   
    print(f"User: {current_user.id} Session: {session.get("current_character_id")}")

    # current_user.character.atributes[data["id"]] = data["value"]
    # print(current_user.character.atributes)

    db = get_db()
    db.execute(f'UPDATE characters SET {data["id"]} = ? WHERE char_id = ?',(data["value"] , session.get("current_character_id")))
    db.commit()

    # print("Updating features")
    # char = db.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = ?",(session.get("current_character_id"), current_user.id)).fetchone()
    # ttrpg.set_features(features,char)

    return {"status": "OK", "received": data}



#------------------------------------
# ---------- API Skills -------------
#------------------------------------
# ----- API Feats
@login_required
@app.route('/api/feats', methods=['POST'])
def feats_api():
    data = request.get_json()
    db = get_db()

    char_id = session.get("current_character_id")

    feat_id = data.get("id")
    level = int(data.get("level", 0))

    if feat_id is None:
        return {"status": "error", "message": "Chybí ID"}, 400

    # Pokud je hodnota 0 smaž záznam pro daný level
    if feat_id == "0" or feat_id == 0:
        db.execute(
            "DELETE FROM feats WHERE char_id = ? AND level = ?",
            (char_id, level)
        )
    else:
        # Nejprve update
        result = db.execute(
            "UPDATE feats SET feat_id = ? WHERE char_id = ? AND level = ?",
            (feat_id, char_id, level)
        )
        # Pokud žádný řádek neexistoval, vložit nový
        if result.rowcount == 0:
            db.execute(
                "INSERT INTO feats (char_id, feat_id, level) VALUES (?, ?, ?)",
                (char_id, feat_id, level)
            )

    db.commit()

    # vrať aktuální seznam featů
    # rows = db.execute(
    #     "SELECT feat_id, level FROM feats WHERE char_id = ?",
    #     (char_id,)
    # ).fetchall()

    # feats_list = [{"id": row["feat_id"], "level": row["level"]} for row in rows]

    # return {"status": "OK", "feats": feats_list}
    return {"status": "OK"}


#---API Class Choices
@login_required
@app.route('/api/character_choice', methods=['POST'])
def character_choice_api():
    data = request.get_json()
    db = get_db()
    print(data)
    char_id = session.get("current_character_id")

    choice_id = data.get("id")
    choice = data.get("choice")
    #TODO: vyřešit Level
    level = 0

    if choice_id is None:
        return {"status": "error", "message": "Chybí ID"}, 400

    # Pokud je hodnota 0 smaž záznam pro daný level
    if choice == "0" or choice == 0:
        db.execute(
            "DELETE FROM character_choices WHERE char_id = ? AND choice_id = ?",
            (char_id, choice_id)
        )
    else:
        # Nejprve update
        result = db.execute(
            "UPDATE character_choices SET choice = ? WHERE char_id = ? AND choice_id = ?",
            (choice, char_id, choice_id)
        )
        # Pokud žádný řádek neexistoval, vložit nový
        if result.rowcount == 0:
            db.execute(
                "INSERT INTO character_choices (choice_id, choice, level, char_id) VALUES (?, ?, ?, ?)",
                (choice_id, choice, level, char_id)
            )

    db.commit()

    return {"status": "OK"}

#---API Subclasses
@app.route("/api/get_subclasses", methods=["POST"])
def get_subclasses():
    data = request.get_json()
    char_class = data.get("char_class", "").lower()

    base_path = f"data/class/{char_class}/subclass"
    subclasses = []

    if os.path.exists(base_path):
        for folder in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, folder)):
                subclasses.append(folder)

    return jsonify({"subclasses": subclasses})



# ---------- API Skills ----------
VALID_SKILLS = {
    "athletics", "acrobatics", "sleight_of_hand", "stealth",
    "arcana", "history", "investigation", "nature", "religion",
    "animal_handling", "insight", "medicine", "perception",
    "survival", "deception", "intimidation", "performance", "persuasion","strength","constitution","dexterity","intelligence","wisdom","charisma"
}

@login_required
@app.route('/api/skills', methods=['POST'])
def skills_api():
    data = request.get_json()
    skill_id = data.get("id").lower()
    value = data.get("value")
    char_id = session.get("current_character_id")

    print(data)
    # print(f"User: {current_user.id} Session: {char_id}")

    if skill_id not in VALID_SKILLS:
        return {"status": "error", "message": "Invalid skill id"}, 400

    db = get_db()

    # zkontroluj, jestli už záznam existuje
    existing = db.execute(
        "SELECT 1 FROM character_skills WHERE char_id = ? AND skill_name = ?",
        (char_id, skill_id)
    ).fetchone()

    if existing:
        if value == 1:
            db.execute("DELETE FROM character_skills WHERE char_id = ? AND skill_name = ?", (char_id, skill_id))
        else:
            db.execute(
                "UPDATE character_skills SET proficiency_level = ? WHERE char_id = ? AND skill_name = ?",
                (value, char_id, skill_id)
            )
    else:
        # INSERT
        db.execute(
            "INSERT INTO character_skills (char_id, skill_name, proficiency_level) VALUES (?, ?, ?)",
            (char_id, skill_id, value)
        )

    db.commit()

    return {"status": "OK", "received": data}


#------------------------------------
# ---------- API Inventory ----------
#------------------------------------
@login_required
@app.route('/api/inventory', methods=['POST'])
def inventory_api():
    data = request.get_json()
    print(data)
    db = get_db()

    for item in data["changes"]["checked"]:
        db.execute("INSERT INTO inventory (char_id, item_id, count, equipped) VALUES (?, ?, ?, ?)", (session.get("current_character_id"), item["UUID"], item["amount"], 0))
        
    for item in data["changes"]["unchecked"]:
        db.execute("DELETE FROM inventory WHERE char_id = ? AND item_id = ?", (session.get("current_character_id"), item["UUID"]))

    for item in data["changes"]["changed"]:
        db.execute('UPDATE inventory SET count = ? WHERE char_id = ? AND item_id = ?',(item["amount"], session.get("current_character_id"),item["UUID"]))

    print(data["changes"]["checked"])

    db.commit()
    
    # načti nový inventář
    rows = db.execute(
        "SELECT item_id, count, equipped FROM inventory WHERE char_id = ?",
        (session.get("current_character_id"),)
    ).fetchall()

    # gear_dict = { item["UUID"]: item for item in data_page_template["items"] }
    gear_dict = {item["UUID"]: item for item in data_page_template["items"]}
    
    
    char_stats = db.execute("SELECT strength,dexterity,constitution,intelligence,wisdom,charisma FROM characters WHERE char_id = ? AND user_id = ?",(session.get("current_character_id"), current_user.id)).fetchone()

    inventory_list = []
    for row in rows:
        gear_item = gear_dict.get(row["item_id"], {})

        # výpočet bonusu pro vybavení
        bonus = None
        if gear_item.get("damage") and gear_item.get("damage_modifier"):
            damage_mods = [char_stats[mod] for mod in gear_item["damage_modifier"] if mod in char_stats.keys()]
            if damage_mods:  # aby nespadlo, když je prázdný list
                bonus = int((max(damage_mods) - 10) / 2)

    for row in rows:
        gear_item = gear_dict.get(row["item_id"], {})
        inventory_list.append({
            "UUID": row["item_id"],
            "count": row["count"],
            "equipped": row["equipped"],
            "name": gear_item.get("name", row["item_id"]),
            "description": gear_item.get("description", ""),
            "damage": gear_item.get("damage"),
            "damage_modifier":gear_item.get("damage_modifier"),
            "damage_type": gear_item.get("damage_type"),
            "bonus": bonus
        })

        #TODO: OPravit situaci, kdy nefunguje změna počtu, když uživatel má equiped item

    return {"status": "OK", "inventory": inventory_list}
    
#----------------------------------------------------
#---------- API Inventory Equipped Status ----------
#----------------------------------------------------
@login_required
@app.route('/api/inventory_equipped', methods=['POST'])
def inventory_equipped_api():
    data = request.get_json()
    print(data)
    db = get_db()
    if data["change"] == "equip":
        db.execute('UPDATE inventory SET equipped = ? WHERE char_id = ? AND item_id = ?',(1, session.get("current_character_id"),data["items"]["UUID"]))
    else:
        db.execute('UPDATE inventory SET equipped = ? WHERE char_id = ? AND item_id = ?',(0, session.get("current_character_id"),data["items"]["UUID"]))
    
    db.commit()
    return {"status": "OK", "received": data}

#---------------------------------------------------
# ---------- API Features Charges Tracking ----------
#----------------------------------------------------
@login_required
@app.route('/api/charges', methods=['POST'])
def charges():
    data = request.get_json()
    value = data["value"]
    print(data)
    db = get_db()
    

    # zkontroluj, jestli už záznam existuje
    existing = db.execute(
        "SELECT 1 FROM features WHERE char_id = ? AND feature_id = ?",(session.get("current_character_id"), data["id"])).fetchone()

    if existing:
        #TODO: Fix
        # ducktape fix pro mizející záznamy, když uživatel odebere všechny charges, systém mu pak dá po resetu stránky všechny zpět
        if value == "0" and (True == False):
            db.execute("DELETE FROM features WHERE char_id = ? AND feature_id = ?", (session.get("current_character_id"), data["id"]))
        else:
            db.execute("UPDATE features SET current_charges = ? WHERE char_id = ? AND feature_id = ?",
                (value,session.get("current_character_id"), data["id"]))
    else:
        # INSERT
        db.execute(
            "INSERT INTO features (char_id, current_charges, feature_id) VALUES (?, ?, ?)",
            (session.get("current_character_id"), value, data["id"])
        )

    db.commit()
    return {"status": "OK", "received": data}




#------------------------------------
#---------- API Spells ----------
#------------------------------------
@login_required
@app.route('/api/spells', methods=['POST'])
def spell_api():
    data = request.get_json()
    print(data)
    db = get_db()

    for item in data["changes"]["checked"]:
        db.execute("INSERT INTO spells (char_id, spell_id) VALUES (?, ?)", (session.get("current_character_id"), item["UUID"]))
        
    for item in data["changes"]["unchecked"]:
        db.execute("DELETE FROM spells WHERE char_id = ? AND spell_id = ?", (session.get("current_character_id"), item["UUID"]))

    # for item in data["changes"]["changed"]:
    #     db.execute('UPDATE spells SET count = ? WHERE char_id = ? AND item_id = ?',(item["amount"], session.get("current_character_id"),item["UUID"]))

    # print(data["changes"]["checked"])

    db.commit()
    
    # načteš kouzla hráče z DB
    rows = db.execute("SELECT spell_id FROM spells WHERE char_id = ?", (session.get("current_character_id"),)).fetchall()

    spells_list = []
    for row in rows:
        spell_item = spells_dict.get(row["spell_id"], {})
        if spell_item:  # pokud kouzlo existuje v json definici
            spells_list.append({
                "UUID": spell_item.get("UUID", row["spell_id"]),
                "name": spell_item.get("name", row["spell_id"]),
                "description": spell_item.get("description", ""),
                "level": spell_item.get("level"),
                "damage": spell_item.get("damage"),
                "damage_type": spell_item.get("damage_type"),
                "casting_time": spell_item.get("casting_time"),
                "range": spell_item.get("range"),
                "components": spell_item.get("components", []),
                "duration": spell_item.get("duration"),
                "upcast": spell_item.get("upcast"),
                "school": spell_item.get("school"),
                "classes": spell_item.get("classes", []),
                "ritual": spell_item.get("ritual", 0),
            })


    return {"status": "OK", "spells": spells_list}

#-----------------------------------
#--------------API Feats------------
#-----------------------------------
@app.route("/api/update_character_options", methods=["POST"])
@login_required
def update_character_options():
    data = request.get_json()
    race = data.get("char_race")
    char_class = data.get("char_class")
    char_subclass = data.get("char_subclass")  # 🧩 přidáno

    # --- feat levels ---
    feat_levels = [
        {"level": 0, "label": "Origin Feat", "filter": "origin"},
        {"level": 4, "label": "Level 4 Feat", "filter": "non-epic"},
        {"level": 8, "label": "Level 8 Feat", "filter": "non-epic"},
        {"level": 12, "label": "Level 12 Feat", "filter": "non-epic"},
        {"level": 16, "label": "Level 16 Feat", "filter": "non-epic"},
        {"level": 19, "label": "Level 19 Feat/Epic Boon", "filter": "all"},
    ]

    if race == "human":
        feat_levels.append({"level": 1, "label": "Origin Feat (Human Bonus)", "filter": "origin"})
    if char_class == "fighter":
        feat_levels.append({"level": 6, "label": "Fighter Feat level 6", "filter": "non-epic"})
        feat_levels.append({"level": 14, "label": "Fighter Feat level 14", "filter": "non-epic"})
    if char_class == "rogue":
        feat_levels.append({"level": 10, "label": "Rogue Feat level 10", "filter": "non-epic"})

    # --- načtení feats ---
    feats = [
        {
            "UUID": feat["UUID"],
            "name": feat["name"],
            "type": feat["type"],
            "description": feat.get("description", "")
        }
        for feat in data_page_template["feats"].values()
    ]

    # --- načtení class choices ---
    class_choices = list(data_page_template.get(f"option_{char_class}", {}).values())

    # --- subclass-specific options
    if char_subclass:
        subclass_key = f"option_{char_class}_{char_subclass}"
        subclass_choices = list(data_page_template.get(subclass_key, {}).values())
        class_choices.extend(subclass_choices)

    # --- načtení dostupných subclasses ---
    subclasses = []
    subclass_dir = f"data/class/{char_class}/subclasses"
    if os.path.exists(subclass_dir):
        for folder in os.listdir(subclass_dir):
            if os.path.isdir(os.path.join(subclass_dir, folder)):
                subclasses.append(folder)

    pass
    return jsonify({
        "feat_levels": feat_levels,
        "feats": feats,
        "class_choices": class_choices,
        "subclasses": subclasses
    })





#------------------------------------
# ---------- API chat s AI ----------
#------------------------------------
preprompt = "Jsi AI assistent pro DND 5e 2024. Vždy odpovídej čistým textem bez Markdown, bez tučného písma, kurzívy nebo seznamů. Používej pouze prostý text.. Odpovídej přehledně."

@login_required
@app.route("/send_message", methods=["POST"])
def send_message():
    user_message = request.json.get("message", "")

    # 1) Pošle dotaz uživatele do AI s definovanými tools
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": preprompt},
            {"role": "system", "content": f"Aktuálně je přihlášen uživatel s ID={current_user.id}."},
            {"role": "user", "content": user_message}
        ],
        tools=tools
    )

    tool_calls = response.choices[0].message.tool_calls

    # 2) Zkontroluje, jestli AI chce volat funkci
    if tool_calls:
        for call in tool_calls:
            if call.function.name == "get_characters":
                # args = json.loads(call.function.arguments)
                # user_id = args.get("user_id", 1)

                # Zavoláme  Python funkci
                with app.app_context():
                    characters = get_characters(current_user.id)

                # Připraví výsledek pro AI
                result_message = {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"characters": characters})
                }

                # 3) Druhé volání AI s výsledkem funkce pro human-like response
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": preprompt},
                        {"role": "system", "content": f"Aktuálně je přihlášen uživatel s ID={current_user.id}."},
                        {"role": "user", "content": user_message},
                        response.choices[0].message,
                        result_message
                    ],
                    tools=tools
                )

                ai_reply = final_response.choices[0].message.content
                return jsonify({"reply": ai_reply})
            if call.function.name == "roll_dice":
                args = json.loads(call.function.arguments)
                result = roll_dice(args["dice"])

                # Připravíme pro frontend → pošleme i reply i akci
                return jsonify({
                    "reply": f"Hodil jsem {args['dice']} a padlo {result['total']}.",
                    "frontend_action": {
                        "type": "show_toast",
                        "title": f"Hod {args['dice']}",
                        "dice": args["dice"],
                        "rolls": result["rolls"],
                        "modifier": result["modifier"],
                        "total": result["total"]
                    }
                })

    # Pokud AI žádnou funkci nevolá, vrátíme normální odpověď, jako kdyby uživatel prostě promptival AI
    ai_reply = response.choices[0].message.content
    return jsonify({"reply": ai_reply})





# -----------------------------
#  Načtení dat pro tvorbu dynamické stránky
#  Data se ukládají do Dict data_page_template
#  Při jednotlivých přístupů do ní se pak tvoří deep copy aby se data nepřepisovala pro jiné uživatele
#  Všechno se děje v data_loader.py
# -----------------------------

# # Načtení Atributes and skills
# with open("data/stats.json","r") as f:
#     data_json = f.read()
#     data_page_template = json.loads(data_json)

# #Načtení Items
# with open("data/items/gear.json","r") as f:
#     data_json = f.read()
#     gear_items = json.loads(data_json)
#     # print(gear_items)
#     data_page_template["items"] = gear_items


# #Lepší podoba gear pro inventory
# #TODO: Implementovat tento přístup v jiných místech
# gear_list = data_page_template["items"]
# gear_dict = {item["UUID"]: item for item in gear_list}

# #Načtení Spells
# with open("data/items/spells.json","r",encoding="utf-8") as f:
#     data_json = f.read()
#     spells = json.loads(data_json)
#     # print(gear_items)
#     spells_dict = {item["UUID"]: item for item in spells}
#     data_page_template["spells"] = spells_dict
#     pass


# # dostupné classes a races
# # Předpokládá se, že každá dostupná class/povolání a race bude mít vlastní složku, ve které bude levelmap, kdy postava dostane jednotlivé schopnosti a features, obsahující 
# # bližší info o jednotlivých možnostech
# folders_class = os.listdir(path="data/class")
# folders_race = os.listdir(path="data/race")


# #Feats
# with open("data/feats/feats.json","r") as f:
#     data_json = f.read()
#     feats = json.loads(data_json)
#     feats_dict = {item["UUID"]: item for item in feats}
#     data_page_template["feats"] = feats_dict

# #class and race choices (e.g warden or eldritch invocations)

# for player_class in folders_class:
#     with open(f"data/class/{player_class}/options.json","r") as f:
#         data_json = f.read()
#         options = json.loads(data_json)
#         options_dict = {item["UUID"]: item for item in options}
#         data_page_template[f"option_{player_class}"] = options_dict

# pass


data_page_template, folders_class, folders_race, spells_dict, gear_dict = reload_base_data()


# -----------------------------
#  Definice funkcí pro AI
# -----------------------------
def get_characters(user_id: int = 1):
    """
    Načte ze SQLite databáze všechny živé postavy konkrétního uživatele.
    Vrací seznam jmen postav.
    """
    db = get_db()  # získáme připojení k databázi (funkce get_db už máš hotovou)
    rows = db.execute(
        "SELECT * FROM characters WHERE user_id = ? AND status = 'Alive'",
        (user_id,)
    ).fetchall()
    
    # Vrátíme jen jména (AI nepotřebuje celou tabulku)
    return [row["name"] for row in rows]

# -----------------------------
# Dice funkce (backend helper)
# -----------------------------
def roll_dice(dice: str):
    # jednoduchý parser formátu "1d20+3"
    parts = dice.lower().split("d")
    num = int(parts[0]) if parts[0] else 1
    if "+" in parts[1]:
        sides, mod = parts[1].split("+")
        sides = int(sides)
        mod = int(mod)
    else:
        sides = int(parts[1])
        mod = 0
    
    rolls = [random.randint(1, sides) for _ in range(num)]
    total = sum(rolls) + mod
    print(total)
    return {"rolls": rolls, "modifier": mod, "total": total, "dice": dice}

# -----------------------------
#  Definice tools pro AI
# -----------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_characters",  # název musí sedět s Python funkcí
            "description": "Vrátí všechny živé postavy aktuálního uživatele (pokud user_id není uveden, použije se 0).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID uživatele (pokud není zadáno, použije se 0)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Hodí virtuální kostkou a vrátí výsledek. Formát např. '1d20+3'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dice": {
                        "type": "string",
                        "description": "Hod kostkou, např. '1d20+3', '2d6', atd."
                    }
                },
                "required": ["dice"]
            }
        }
    }
]


#------------------------------------
# ---------- Spuštění ----------
#------------------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
