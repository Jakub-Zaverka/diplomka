import os
import json
import ttrpg
import math

def reload_base_data():
    """
    Načte veškerá statická data (atributy, předměty, kouzla, feats, class options atd.)
    Vrací tuple: (data_page_template, folders_class, folders_race, spells_dict)
    """
    data_page_template = {}

    # --- Načtení Atributů a Skills ---
    with open("data/stats.json", "r", encoding="utf-8") as f:
        data_json = f.read()
        data_page_template = json.loads(data_json)

    # --- Načtení Items ---
    with open("data/items/gear.json", "r", encoding="utf-8") as f:
        gear_items = json.load(f)
        data_page_template["items"] = gear_items

    gear_dict = {item["UUID"]: item for item in gear_items}

    # --- Načtení Spells ---
    with open("data/items/spells.json", "r", encoding="utf-8") as f:
        spells = json.load(f)
        spells_dict = {item["UUID"]: item for item in spells}
        data_page_template["spells"] = spells_dict

    # --- Načtení dostupných classes a races ---
    folders_class = os.listdir(path="data/class")
    folders_race = os.listdir(path="data/race")

    # --- Subclasses
    subclasses_dict = {}
    for cls in folders_class:
        subclass_dir = os.path.join("data", "class", cls, "subclasses")
        if os.path.exists(subclass_dir):
            subclasses = [
                folder for folder in os.listdir(subclass_dir)
                if os.path.isdir(os.path.join(subclass_dir, folder))
            ]
            subclasses_dict[cls] = subclasses
        else:
            subclasses_dict[cls] = []

    data_page_template["subclasses"] = subclasses_dict

    # --- Načtení Feats ---
    with open("data/feats/feats.json", "r", encoding="utf-8") as f:
        feats = json.load(f)
        feats_dict = {item["UUID"]: item for item in feats}
        data_page_template["feats"] = feats_dict

    # --- Načtení class options ---
    for player_class in folders_class:
        options_path = f"data/class/{player_class}/options.json"
        if os.path.exists(options_path):
            with open(options_path, "r", encoding="utf-8") as f:
                options = json.load(f)
                options_dict = {item["UUID"]: item for item in options}
                data_page_template[f"option_{player_class}"] = options_dict

        # načti subclass options
        subclass_dir = os.path.join("data", "class", player_class, "subclasses")
        if os.path.exists(subclass_dir):
            for subclass in os.listdir(subclass_dir):
                subclass_path = os.path.join(subclass_dir, subclass)
                subclass_options_path = os.path.join(subclass_path, "options.json")

                if os.path.exists(subclass_options_path):
                    with open(subclass_options_path, "r", encoding="utf-8") as f:
                        try:
                            subclass_options = json.load(f)
                            subclass_options_dict = {item["UUID"]: item for item in subclass_options}
                            # uložíme pod názvem option_class_subclass
                            data_page_template[f"option_{player_class}_{subclass}"] = subclass_options_dict
                        except Exception as e:
                            print(f"[reload_base_data] Chyba při načítání subclass options ({player_class}/{subclass}): {e}")



    return data_page_template, folders_class, folders_race, spells_dict, gear_dict


def load_category(source_type: str, category: str, source_name: str, char, page_template: dict, saved_data: dict = None, reload_data: bool = False):
    """
    Načte a zpracuje data kategorie (features, traits, spells...) z class/race složky.

    Args:
        source_type (str): "class" nebo "race"
        category (str): např. "features", "traits", "spells"
        source_name (str): jméno classy nebo rasy (wizard, dwarf...)
        char (dict): dict s postavou (sqlite3.Row)
        page_template (dict): dict do kterého se uloží výsledek
        saved_data (dict): uložené charges (např. {UUID: current_charges})
        reload_data (bool): pokud True, znovu načte všechny zdrojové JSON soubory (např. po editaci dat za běhu)
    """

    # Pokud je povoleno reload, načti znovu všechna data
    if reload_data:
        new_template, _, _, _ = reload_base_data()
        page_template.update(new_template)

    base_path = f"data/{source_type}/{source_name}"
    data_path = os.path.join(base_path, "features.json")
    levelmap_path = os.path.join(base_path, "levelmap.json")

    # --- 1) Načtení kategorie ---
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            try:
                items = json.load(f)
            except Exception:
                items = []
    else:
        items = []
    page_template[category] = items

    # --- 2) Levelmap ---
    if os.path.exists(levelmap_path):
        with open(levelmap_path, "r", encoding="utf-8") as f:
            try:
                known = json.load(f)
                known_dict = {}
                for i in known:
                    known_dict.update(i)
            except Exception:
                known_dict = {}
    else:
        known_dict = {}
    
    # --- SUBCLASS SUPPORT ---
    if source_type == "class" and char["char_subclass"]:
        subclass_name = char["char_subclass"].lower()
        subclass_path = f"data/class/{source_name}/subclasses/{subclass_name}"

        subclass_features_path = os.path.join(subclass_path, "features.json")
        subclass_levelmap_path = os.path.join(subclass_path, "levelmap.json")

        if os.path.exists(subclass_features_path):
            with open(subclass_features_path, "r", encoding="utf-8") as f:
                try:
                    subclass_items = json.load(f)
                    # přidáme subclass features do stejné kategorie
                    page_template[category].extend(subclass_items)
                except Exception as e:
                    print(f"[load_category] Chyba při načítání subclass features: {e}")

        if os.path.exists(subclass_levelmap_path):
            with open(subclass_levelmap_path, "r", encoding="utf-8") as f:
                try:
                    subclass_known = json.load(f)
                    for i in subclass_known:
                        known_dict.update(i)
                except Exception as e:
                    print(f"[load_category] Chyba při načítání subclass levelmap: {e}")


    # --- 3) Postprocessing (stejně jako u features) ---
    for item in page_template.get(category, []):
        uuid = item.get("UUID")
        if uuid in known_dict:
            required_level = known_dict.get(uuid)
            if char["level"] >= required_level:
                item["known"] = True

                max_charges = item.get("max_charges")
                if isinstance(max_charges, str):
                    # atributy
                    if max_charges.lower() in [
                        "strength", "dexterity", "constitution",
                        "intelligence", "wisdom", "charisma"
                    ]:
                        try:
                            mod = ttrpg.calc_mod(int(char[max_charges.lower()]))
                        except Exception:
                            mod = 1
                        item["max_charges"] = max(1, mod)

                    # proficiency
                    elif max_charges.lower() == "proficiency":
                        try:
                            item["max_charges"] = ttrpg.get_proficiency_bonus(char["level"])
                        except Exception:
                            item["max_charges"] = 1
                    # level
                    elif max_charges.lower() == "level":
                        try:
                            item["max_charges"] = char["level"]
                        except Exception:
                            item["max_charges"] = 1
                    # level/2        
                    elif max_charges.lower() == "level/2":
                        #zaokrouhlení nahoru
                        value = math.ceil(char["level"]/2)
                        print(f"Level {value}")
                        try:
                            item["max_charges"] = value
                        except Exception:
                            item["max_charges"] = 1
                    # fallback
                    else:
                        try:
                            item["max_charges"] = int(max_charges)
                        except Exception:
                            item["max_charges"] = 0
                else:
                    try:
                        item["max_charges"] = int(max_charges)
                    except Exception:
                        item["max_charges"] = 0

                # charges
                if saved_data and uuid:
                    item["charges"] = saved_data.get(uuid, item["max_charges"])
                else:
                    item["charges"] = item.get("max_charges", 0)

    return page_template
