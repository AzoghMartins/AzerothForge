# 3.3.5a Game Constants

RACE_MAP = {
    1: 'Human', 
    2: 'Orc', 
    3: 'Dwarf', 
    4: 'Night Elf', 
    5: 'Undead', 
    6: 'Tauren', 
    7: 'Gnome', 
    8: 'Troll', 
    10: 'Blood Elf', 
    11: 'Draenei'
}

CLASS_MAP = {
    1: 'Warrior', 
    2: 'Paladin', 
    3: 'Hunter', 
    4: 'Rogue', 
    5: 'Priest', 
    6: 'Death Knight', 
    7: 'Shaman', 
    8: 'Mage', 
    9: 'Warlock', 
    26: 'Druid'
}

TELEPORT_LOCATIONS = {
    'Alliance': {
        'Stormwind': (0, -8833.38, 628.628, 94.0066),
        'Ironforge': (0, -4918.88, -940.406, 501.564),
        'Darnassus': (1, 9946.39, 2484.29, 1316.21),
        'Exodar': (530, -3987.29, -11846.6, -2.01903)
    },
    'Horde': {
        'Orgrimmar': (1, 1637.81, -4439.19, 15.7814),
        'Undercity': (0, 1586.48, 239.562, -52.149),
        'Thunder Bluff': (1, -1277.37, 113.12, 129.17),
        'Silvermoon': (530, 9473.03, -7279.67, 14.2285)
    },
    'Neutral': {
        'Dalaran': (571, 5804.15, 624.77, 647.77),
        'Shattrath': (530, -1838.16, 5301.79, 12.428)
    }
}

ALLIANCE_RACES = [1, 3, 4, 7, 11]
HORDE_RACES = [2, 5, 6, 8, 10]

PROGRESSION_TIERS = {
    0: "Reach level 60",
    1: "Defeat Ragnaros and Onyxia",
    2: "Defeat Nefarian",
    3: "Complete 'Might of Kalimdor' or 'Bang a Gong!'",
    4: "Complete 'Chaos and Destruction'",
    5: "Defeat C'thun",
    6: "Defeat Kel'thuzad (Naxx 40)",
    7: "Complete 'Into the Breach'",
    8: "Defeat Prince Malchezaar",
    9: "Defeat Kael'thas",
    10: "Defeat Illidan",
    11: "Defeat Zul'jin",
    12: "Defeat Kil'jaeden",
    13: "Defeat Kel'thuzad (Naxx 80)",
    14: "Defeat Yogg-Saron",
    15: "Defeat Anub'arak",
    16: "Defeat the Lich King",
    17: "Defeat Halion"
}
