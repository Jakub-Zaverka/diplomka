def get_proficiency_bonus(level: int) -> int:
    '''Vrátí proficiency bonus, Bere parametr level, vrací chybu pokud je level větší něž 20'''
    if level < 1:
        raise ValueError("Level must be at least 1.")
    if level <= 4:
        return 2
    elif level <= 8:
        return 3
    elif level <= 12:
        return 4
    elif level <= 16:
        return 5
    elif level <= 20:
        return 6
    else:
        raise ValueError("Level must not exceed 20.")
    
def calc_mod(value: int) ->int:
    '''Vrátí modifier z vložené hodnoty'''
    result = (value-10)/2
    if value < 10:
        return result
    return result

# def set_features(features, char):
#     print(">>> set_features called")
#     for item in features:
#         # Jestli max charges feature je podle atributu, tak ho nastav dle atributu characteru
#         if item["max_charges"] in ["strength","dexterity","constitution","intelligence","wisdom","charisma"]:
#             mod = calc_mod(char[item["max_charges"]])
#             #Vetšina features je nastavena takže minimum je jedna, nehledě na atribut
#             if mod < 1:
#                 mod = 1
#             item["max_charges"] = int(mod)
#             print(item["name"])
#             print(item["max_charges"])
#         # Jinak převeď původní hodnotu na int
#         else:
#             item["max_charges"] = int(item["max_charges"])
#     print(">>> set_features ended")


