import os
import json
import ttrpg

def load_category(source_type: str, category: str, source_name: str, char, page_template: dict, saved_data: dict = None):
    """
    Načte a zpracuje data kategorie (features, traits, spells...) z class/race složky.

    Args:
        source_type (str): "class" nebo "race"
        category (str): např. "features", "traits", "spells"
        source_name (str): jméno classy nebo rasy (wizard, dwarf...)
        char (dict): dict s postavou (sqlite3.Row)
        page_template (dict): dict do kterého se uloží výsledek
        saved_data (dict): uložené charges (např. {UUID: current_charges})
    """
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
