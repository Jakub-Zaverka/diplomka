from flask import Flask, render_template, request, redirect, g, session, flash
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
            CREATE TABLE spells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id INTEGER NOT NULL,
                spell_id INTEGER NOT NULL,
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
        email = request.form['email']

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", (username, pw_hash, email))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
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

        # místo return textu → flash message
        flash("Neplatné přihlašovací údaje!", "danger")
        return redirect('/login')

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

    #Spells
    row_character_spells = db.execute("SELECT spell_id FROM spells WHERE char_id = ?",(char_id,)).fetchall()

    # vyrobíme list samotných spell_id hodnot
    character_spells = [row["spell_id"] for row in row_character_spells]

    for spell_id, spell_data in page_template.get("spells", {}).items():
        if spell_id in character_spells:
            spell_data["checked"] = True
        else:
            spell_data["checked"] = False
    pass

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

# ---------- API Spells ----------

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

# ---------- Vytvoření dynamické stránky ----------
#Atributes and skills
with open("data/stats.json","r") as f:
    data_json = f.read()
    data_page_template = json.loads(data_json)

#Items
with open("data/items/gear.json","r") as f:
    data_json = f.read()
    gear_items = json.loads(data_json)
    # print(gear_items)
    data_page_template["items"] = gear_items


#Lepší podoba gear pro inventory
#TODO: Implementovat tento přístup v jiných místech
gear_list = data_page_template["items"]
gear_dict = {item["UUID"]: item for item in gear_list}

#Spells
with open("data/items/spells.json","r") as f:
    data_json = f.read()
    spells = json.loads(data_json)
    # print(gear_items)
    spells_dict = {item["UUID"]: item for item in spells}
    data_page_template["spells"] = spells_dict
    pass
# print(data_page_template["spells"]["3119226a-b092-4d83-9f8d-ef00a11ba471"])
# print(data_page_template["spells"]["6bc1291e-5fd8-44ba-a8e8-43eee559b101"])

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



