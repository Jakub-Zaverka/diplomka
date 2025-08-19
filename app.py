from flask import Flask, render_template, request, redirect, g, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import random
import json
import copy
#import uuid
import ttrpg
import data_loader
import datetime

global debug
debug = False

#test

#https://chatgpt.com/share/687f540c-97a0-8000-854e-98c5d7e180ff

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny-klic'
DATABASE = 'main.db'

# ---------- Flask-Login Setup ----------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ---------- User class ----------
#Flask volá celý User objekt znovu mezi requests, takže všechno mezitím uložené se ztratí, asi spíše uložit do session?
class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username
        # self.character = Chararacter(user_id=id_)


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
                password_hash TEXT NOT NULL
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
                hp INTEGER DEFAULT 10,
                max_hp INTEGER DEFAULT 10,
                temp_hp INTEGER DEFAULT 0,
                hit_die INTEGER DEFAULT 10,
                initiative INTEGER DEFAULT 10, 
                level INTEGER DEFAULT 10,
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
                item_id INTEGER NOT NULL,
                count FLOAT NOT NULL,
                equipped INTEGER DEFAULT 0,
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
                feature_id INTEGER NOT NULL,
                current_charges INTEGER NOT NULL,
                FOREIGN KEY (char_id) REFERENCES characters(char_id)
            )
        ''')

        db.commit()
        db.close()



# ---------- Registrace ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pw_hash = generate_password_hash(password)

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Uživatel již existuje!"
    return render_template('register.html')

# ---------- Přihlášení ----------
@app.route('/',methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (request.form['username'],)).fetchone()
        if user and check_password_hash(user['password_hash'], request.form['password']):
            user_obj = User(id_=user['user_id'], username=user['username'])
            login_user(user_obj)
            return redirect('/dashboard')
        return "Neplatné přihlašovací údaje"
    return render_template('login.html')

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
    if debug:
        db.execute("INSERT INTO characters (user_id, name) VALUES (?, ?)", (current_user.id, f"testChar{random.randint(0,10)}"))
    rows = db.execute("SELECT * FROM characters WHERE user_id = ? AND status = 'Alive'", (current_user.id,)).fetchall()
    db.commit()
    return render_template('dashboard.html', data=rows, username=current_user.username)

# ---------- Dashboard ----------
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

    # Načti postavu - pokud neexistuje nebo jí nepatří, vrať chybu
    char = db.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = ?",(char_id, current_user.id)).fetchone()
    print(char["char_class"])
    if char is None:
        return "Postava nebyla nalezena nebo ti nepatří", 404

    # Uložíme do session aktuální char
    session["current_character_id"] = char_id

    # --- Načtení dat z DB -------------------------------------------------
    # inventář (item_id, count, equipped)
    items = db.execute("SELECT item_id, count, equipped FROM inventory WHERE char_id = ?",(char_id,)).fetchall()

    # dovednosti
    prof = db.execute("SELECT skill_name, proficiency_level FROM character_skills WHERE char_id = ?",(char_id,)).fetchall()


    # features - aktuální stav (předpokládám, že feature_name odpovídá name v JSONu)
    feat_db = db.execute("SELECT feature_id, current_charges FROM features WHERE char_id = ?",(char_id,)).fetchall()

    # --- Deep copy šablony (aby zůstala čistá pro ostatní requesty) -----
    page_template = copy.deepcopy(data_page_template)

    # --- Převod DB resultů na dicty pro rychlý lookup --------------------
    proficiencies_dict = {
        row["skill_name"].lower(): row["proficiency_level"] for row in prof
    }

    item_data_dict = {
        row["item_id"]: {"count": row["count"], "equipped": row["equipped"]} for row in items
    }

    # Klíčujeme feature podle feature uuid (feature_id) - musí odpovídat fieldu "uuid" v JSONu
    feature_data_dict = {
        row["feature_id"]: row["current_charges"] for row in feat_db
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
    page_template = data_loader.load_category("class", "features", char["char_class"], char, page_template, feature_data_dict)

    # player_class_name = char["char_class"]
    # features_path = f"data/class/{player_class_name}/features.json"
    # levelmap_path = f"data/class/{player_class_name}/levelmap.json"
    # if os.path.exists(features_path):
    #     with open(features_path,"r") as f:
    #         data_json = f.read()
    #         features = json.loads(data_json)
    #         # print(gear_items)
    #         page_template["features"] = features
    # else:
    #     page_template["features"] = []
    
    # # --- Aktualizace features --------------------------------------------
    # # předpoklad: každý feature v JSON má pole "name" a "max_charges" (string nebo attribute name)
    # #  Filtr zda postava danou feature má a zda má dostatečnou úroveň
    # if os.path.exists(levelmap_path):
    #     with open(levelmap_path,"r") as f:
    #         data_json = f.read()
    #         known_features = json.loads(data_json)
    #         # print(gear_items)
    #         known_features_dict = {}
    #         for i in known_features:
    #             known_features_dict.update(i)
    # else:
    #     known_features={}
    #     known_features_dict={}

    # pass    
    # for feature in page_template.get("features", []):
    #     #  Zda postava danou feature má 
    #     if feature.get("UUID") in known_features_dict.keys():
    #         # A zda má dostatečnou úroveň
    #         required_level = known_features_dict.get(feature.get("UUID"))
    #         if char["level"] >= required_level:
    #             # print(f"{feature['name']} - splňuje (lvl {char["level"]} / požadavek {required_level})")
    #             feature["known"] = True
    #             # 1) dopočti max_charges podle atributů
    #             max_charges = feature.get("max_charges")
    #             if isinstance(max_charges, str) and max_charges.lower() in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
    #                 # char je sqlite3.Row, přístup podle názvu sloupce funguje: char["intelligence"]
    #                 try:
    #                     mod = ttrpg.calc_mod(int(char[max_charges.lower()]))
    #                 except Exception:
    #                     # bezpečně fallbacknout pokud char[max_charges] není dostupné nebo neint
    #                     mod = 1

    #                 if mod < 1:
    #                     mod = 1
    #                 feature["max_charges"] = int(mod)
    #             #Pokud je feature proficiency krát
    #             elif isinstance(max_charges, str) and max_charges.lower() == "proficiency":
    #                 try:
    #                     mod = ttrpg.get_proficiency_bonus(char["level"])
    #                 except Exception:
    #                     mod = 1
    #                 feature["max_charges"] = int(mod)
    #             else:
    #                 # pokud je to číslo uložené jako string v JSONu
    #                 try:
    #                     feature["max_charges"] = int(max_charges)
    #                 except Exception:
    #                     # fallback na 0 pokud neparsovatelné
    #                     feature["max_charges"] = 0

    #             # 2) nastav aktuální charges z DB pokud existuje, jinak použij max_charges jako výchozí
    #             # mapujeme podle jména feature (JSON "name")
    #             feature_id = feature.get("UUID")
    #             if feature_id is not None:
    #                 feature["charges"] = feature_data_dict.get(feature_id)
    #             else:
    #                 feature["charges"] = feature["max_charges"]

    #Race
    page_template = data_loader.load_category("race", "traits", char["char_race"], char, page_template)

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

    # Vytvoření slovníku pro hledání následně v šabloně
    proficiencies_dict = {
    row["skill_name"].lower(): row["proficiency_level"]
    for row in prof
    }


    if char is None:
        return "Postava nebyla nalezena nebo ti nepatří"

    return render_template("sheet_edit_mode.html", character=char, data_page_template = data_page_template, proficiencies=proficiencies_dict, player_classes = folders_class, player_races = folders_race)


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

    # Vytvoření slovníku pro hledání následně v šabloně
    proficiencies_dict = {
    row["skill_name"].lower(): row["proficiency_level"]
    for row in prof
    }
    
    return render_template("sheet_edit_mode.html", character=char, data_page_template = data_page_template, proficiencies=proficiencies_dict, player_classes = folders_class, player_races = folders_race)




# ---------- API Endpoints ----------
# ---------- test ----------

# @app.route('/api/test', methods=['POST'])
# def test_api():
#     data = request.get_json()
#     print(data)
#     return {"status": "OK", "received": data}


# ---------- API delete character ----------
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

# ---------- API Stats ----------
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



# @login_required
# @app.route('/api/inventory', methods=['POST'])
# def inventory_api():
#     data = request.get_json()
#     # print(data)
#     db = get_db()
#     for item in data["items"]:
#         row = db.execute("SELECT * FROM inventory WHERE char_id = ? AND item_id = ?",(session.get("current_character_id"), item["UUID"])).fetchone()
        
        
#         #Jestli záznam existuje, tak ho pouze upravím
#         if row:
#             print(f"Nalezeno: {row}")
#             db.execute('UPDATE inventory SET count = ? WHERE char_id = ? AND item_id = ?',(item["amount"], session.get("current_character_id"),item["UUID"]))
#         #Jinak vytvořím nový
#         else:
#             db.execute("INSERT INTO inventory (char_id, item_id, count, equipped) VALUES (?, ?, ?, ?)", (session.get("current_character_id"), item["UUID"], item["amount"], 0))
#             print(f"Nenalezeno pro item: {item['UUID']}")
#         db.commit()
    
#     return {"status": "OK", "received": data}

# ---------- API Inventory ----------

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

    db.commit()
    return {"status": "OK", "received": data}

# ---------- API Inventory Equipped Status ----------

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

# ---------- API Features Charges Tracking ----------

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
        if value == "0":
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


# @app.route('/api/get_db', methods=['POST'])
# def get_db_items():
#     data = request.get_json()
#     print(data)
#     result = next((item for item in gear_items if item['UUID'] == uuid), None)
#     print(result)

#     return {"status": "OK", "received": result}


# ---------- Vytvoření dynamické stránky ----------
#Atributes and skills
with open("data/stats.json","r") as f:
    data_json = f.read()
    data_page_template = json.loads(data_json)

#Skills
with open("data/items/gear.json","r") as f:
    data_json = f.read()
    gear_items = json.loads(data_json)
    # print(gear_items)
    data_page_template["items"] = gear_items


# dostupné classes a races
# Předpokládá se, že každá dostupná class/povolání bude mít vlastní složku, ve které bude levelmap, kdy postava dostane jednotlivé schopnosti a features, obsahující 
# bližší info o jednotlivých možnostech
folders_class = os.listdir(path="data/class")
folders_race = os.listdir(path="data/race")






# print(data_page_template)


# ---------- Spuštění ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)



