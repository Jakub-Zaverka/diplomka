import json
import uuid
import sys
import os

#https://gist.github.com/dmcb/4b67869f962e3adaa3d0f7e5ca8f4912

def convert_spell(old_spell):
    """Převede kouzlo ze starého formátu na nový."""
    new_spell = {
        "UUID": str(uuid.uuid4()),
        "name": old_spell.get("name", ""),
        "description": old_spell.get("description", "").replace("\n", " "),
        "level": old_spell.get("level", 0),
        "damage": "4d4",  # fallback – pokusíme se detekovat níže
        "damage_type": "acid",  # fallback
        "casting_time": old_spell.get("actionType", "action"),
        "range": old_spell.get("range", "").replace(" feet", "ft"),
        "components": [],
        "duration": 0 if str(old_spell.get("duration", "")).lower() == "instantaneous" else old_spell.get("duration", ""),
        "upcast": "",
        "school": old_spell.get("school", "").capitalize(),
        "classes": old_spell.get("classes", []),
        "ritual": 1 if old_spell.get("ritual") else 0
    }

    # --- Components ---
    comps = old_spell.get("components", [])
    if isinstance(comps, list):
        for c in comps:
            if c.lower() == "v":
                new_spell["components"].append("Verbal")
            elif c.lower() == "s":
                new_spell["components"].append("Somatic")
            elif c.lower() == "m":
                mat = old_spell.get("material", "")
                new_spell["components"].append(mat if mat else "Material")

    # --- Upcast ---
    higher = old_spell.get("higherLevelSlot", "")
    if "1d4" in higher:
        new_spell["upcast"] = "1d4"
    elif "2d4" in higher:
        new_spell["upcast"] = "2d4"
    elif "1d8" in higher:
        new_spell["upcast"] = "1d8"

    # --- Damage autodetekce z textu ---
    desc = old_spell.get("description", "").lower()
    if "acid" in desc:
        new_spell["damage_type"] = "acid"
    elif "fire" in desc:
        new_spell["damage_type"] = "fire"
    elif "cold" in desc:
        new_spell["damage_type"] = "cold"
    elif "necrotic" in desc:
        new_spell["damage_type"] = "necrotic"
    elif "radiant" in desc:
        new_spell["damage_type"] = "radiant"

    for dice in ["4d4", "2d8", "3d8", "2d6", "1d10", "1d8"]:
        if dice in desc:
            new_spell["damage"] = dice
            break

    return new_spell


def convert_all_spells(old_json_path, new_json_path):
    """Načte celý starý JSON a uloží ho ve formátu nového."""
    if not os.path.exists(old_json_path):
        print(f"❌ Soubor {old_json_path} neexistuje.")
        return

    with open(old_json_path, "r", encoding="utf-8") as f:
        try:
            old_spells = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Chyba při čtení JSON: {e}")
            return

    if not isinstance(old_spells, list):
        print("❌ Soubor musí obsahovat seznam kouzel (list objektů).")
        return

    new_spells = [convert_spell(spell) for spell in old_spells]

    with open(new_json_path, "w", encoding="utf-8") as f:
        json.dump(new_spells, f, indent=4, ensure_ascii=False)

    print(f"✅ Hotovo! Uloženo do {new_json_path}")
    print(f"🧙‍♂️ Převedeno {len(new_spells)} kouzel.")


def main():
    if len(sys.argv) != 3:
        print("Použití: python convert_spells.py <vstupní_soubor.json> <výstupní_soubor.json>")
        print("Příklad: python convert_spells.py old_spells.json new_spells.json")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    convert_all_spells(input_path, output_path)


if __name__ == "__main__":
    main()
