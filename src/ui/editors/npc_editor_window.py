from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QFormLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QListWidget,
    QListWidgetItem, QGroupBox, QCheckBox, QFileDialog, QCompleter
)
from PySide6.QtCore import Qt, Signal

from src.core.data_manager import DataManager
from src.core.config_manager import ConfigManager
from src.database.db_manager import DbManager
from src.ui.components.selectors import SmartSelector, BitmaskSelector, SearchDialog
# Fallback flag dictionaries for bitmask selectors
# These can be expanded later; using common core bits.
NPC_FLAG_DICT = {
    0x00000001: "Gossip",
    0x00000002: "Quest Giver",
    0x00000004: "Unknown 1",
    0x00000008: "Unknown 2",
    0x00000010: "Trainer",
    0x00000020: "Trainer (Class)",
    0x00000040: "Trainer (Profession)",
    0x00000080: "Vendor",
    0x00000100: "Vendor (Ammo)",
    0x00000200: "Vendor (Food)",
    0x00000400: "Vendor (Poison)",
    0x00000800: "Vendor (Reagent)",
    0x00001000: "Repair",
    0x00002000: "Flight Master",
    0x00004000: "Spirit Healer",
    0x00008000: "Spirit Guide",
    0x00010000: "Innkeeper",
    0x00020000: "Banker",
    0x00040000: "Petitioner",
    0x00080000: "Tabard Designer",
    0x00100000: "Battlemaster",
    0x00200000: "Auctioneer",
    0x00400000: "Stable Master",
    0x00800000: "Guild Banker",
    0x01000000: "Spell Click",
    0x02000000: "Player Vehicle",
    0x04000000: "Mailbox"
}

UNIT_FLAG_DICT = {
    0x00000001: "Server Controlled",
    0x00000002: "Non-Attackable",
    0x00000004: "Disable Move",
    0x00000008: "Player Controlled",
    0x00000010: "Rename",
    0x00000020: "Preparation",
    0x00000040: "Unknown 6",
    0x00000080: "Not Attackable 1",
    0x00000100: "Immune to PC",
    0x00000200: "Immune to NPC",
    0x00000400: "Looting",
    0x00000800: "Pet In Combat",
    0x00001000: "PvP",
    0x00002000: "Silenced",
    0x00004000: "Cannot Swim",
    0x00008000: "Swimming",
    0x00010000: "Non-Attackable 2",
    0x00020000: "Pacified",
    0x00040000: "Stunned",
    0x00080000: "In Combat",
    0x00100000: "Taxi Flight",
    0x00200000: "Disarmed",
    0x00400000: "Confused",
    0x00800000: "Fleeing",
    0x01000000: "Possessed",
    0x02000000: "Not Selectable",
    0x04000000: "Skinnable",
    0x08000000: "Mount",
    0x10000000: "Unknown 28",
    0x20000000: "Prevent Emotes from Chat Text",
    0x40000000: "Sheathe",
    0x80000000: "Immune"
}

UNIT_FLAG2_DICT = {
    0x00000001: "Feign Death",
    0x00000002: "Hide Body",
    0x00000004: "Ignore Reputation",
    0x00000008: "Comprehend Lang",
    0x00000010: "Mirror Image",
    0x00000020: "Do Not Fade In",
    0x00000040: "Force Movement",
    0x00000080: "Disarm Offhand",
    0x00000100: "Disable Pred Stats",
    0x00000400: "Disarm Ranged",
    0x00000800: "Regenerate Power",
    0x00001000: "Restrict Party Interaction",
    0x00002000: "Prevent Spell Click",
    0x00004000: "Allow Enemy Interact",
    0x00008000: "Cannot Turn",
    0x00010000: "Unknown 2",
    0x00020000: "Play Death Anim",
    0x00040000: "Allow Cheat Spells",
    0x01000000: "Unused 6"
}

CREATURE_FAMILY = {
    0: "None",
    1: "Wolf",
    2: "Cat",
    3: "Spider",
    4: "Bear",
    5: "Boar",
    6: "Crocolisk",
    7: "Carrion Bird",
    8: "Crab",
    9: "Gorilla",
    10: "Raptor",
    11: "Tallstrider",
    12: "Felhunter",
    13: "Voidwalker",
    14: "Succubus",
    15: "Doomguard",
    16: "Scorpid",
    17: "Turtle",
    18: "Imp",
    19: "Bat",
    20: "Hyena",
    21: "Bird of Prey",
    22: "Wind Serpent",
    23: "Remote Control",
    24: "Felguard",
    25: "Dragonhawk",
    26: "Ravager",
    27: "Warp Stalker",
    28: "Sporebat",
    29: "Nether Ray",
    30: "Serpent",
    31: "Moth",
    32: "Chimaera",
    33: "Devilsaur",
    34: "Ghoul",
    35: "Silithid",
    36: "Worm",
    37: "Rhino",
    38: "Wasp",
    39: "Core Hound",
    40: "Spirit Beast"
}

CREATURE_TYPE = {
    0: "None",
    1: "Beast",
    2: "Dragonkin",
    3: "Demon",
    4: "Elemental",
    5: "Giant",
    6: "Undead",
    7: "Humanoid",
    8: "Critter",
    9: "Mechanical",
    10: "Totem",
    11: "Non-Combat Pet",
    12: "Gas Cloud"
}

INHABIT_TYPE = {
    1: "Ground",
    2: "Water",
    3: "Ground + Water",
    4: "Flying",
    5: "Ground + Flying",
    6: "Water + Flying",
    7: "All (Ground/Water/Flying)"
}

MOVEMENT_TYPE = {
    0: "Idle",
    1: "Random",
    2: "Waypoint"
}

UNIT_CLASS = {
    1: "Warrior",
    2: "Paladin",
    4: "Rogue",
    8: "Mage"
}

SHEATH_STATE = {
    0: "None",
    1: "Melee",
    2: "Ranged",
    3: "Shield"
}

ITEM_CLASS = {
    0: "Consumable",
    1: "Container",
    2: "Weapon",
    3: "Gem",
    4: "Armor",
    5: "Reagent",
    6: "Projectile",
    7: "Trade Goods",
    9: "Recipe",
    11: "Quiver",
    12: "Quest",
    13: "Key",
    15: "Misc",
    16: "Glyph"
}

INVENTORY_TYPE = {
    0: "Non-equip",
    1: "Head",
    2: "Neck",
    3: "Shoulder",
    4: "Body",
    5: "Chest",
    6: "Waist",
    7: "Legs",
    8: "Feet",
    9: "Wrist",
    10: "Hands",
    11: "Finger",
    12: "Trinket",
    13: "One-Hand",
    14: "Off-Hand",
    15: "Ranged",
    16: "Back",
    17: "Two-Hand",
    18: "Bag",
    19: "Tabard",
    20: "Robe",
    21: "Main Hand",
    22: "Off Hand",
    23: "Holdable",
    24: "Ammo",
    25: "Thrown",
    26: "Ranged (Right)",
    27: "Quiver",
    28: "Relic"
}

import datetime
import os


class NpcEditorWindow(QDialog):
    """
    Full-featured NPC editor used by campaign workstation.
    Supports dual output: SQL file generation or direct DB writes.
    """

    saved = Signal(int)  # emits entry id on successful save

    def __init__(self, entry_id: int, campaign_data: dict, dev_realm_config: dict,
                 config_manager: ConfigManager, mode: str = "update", parent=None,
                 allowed_id_range=None):
        super().__init__(parent)
        self.entry_id = entry_id
        self.campaign_data = campaign_data or {}
        self.dev_realm_config = dev_realm_config or config_manager.get_active_realm()
        self.config_manager = config_manager or ConfigManager()
        self.mode = mode  # "insert" or "update"
        self.allowed_id_range = allowed_id_range

        self.db = DbManager.get_instance(self.config_manager)
        self.data = DataManager()
        self._schema = {}
        self._classlevel_cache = {}
        self._armor_modifier = 1.0
        self._exp = 0
        self._addon_row = None

        self.setWindowTitle(f"NPC Editor - {entry_id}")
        self.resize(1000, 750)

        self.init_ui()
        self.load_from_db()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        main = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel(f"Editing Entry: {self.entry_id}"))
        header.addStretch()
        db_name = self.dev_realm_config.get("db_world_name", "?")
        header.addWidget(QLabel(f"Target DB: {db_name}"))
        main.addLayout(header)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs, 1)

        self.build_general_tab()
        self.build_appearance_tab()
        self.build_stats_tab()
        self.build_flags_tab()
        self.build_equipment_tab()
        self.build_vendor_trainer_tab()
        self.build_scripts_tab()
        self.build_gossip_tab()
        self.build_preview_tab()

        # Footer buttons
        footer = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_npc)
        self.delete_btn.setVisible(self.mode == "update")
        footer.addWidget(self.delete_btn)

        footer.addStretch()

        self.gen_btn = QPushButton("Generate SQL")
        self.gen_btn.clicked.connect(self.generate_sql_file)
        footer.addWidget(self.gen_btn)

        self.save_btn = QPushButton("Save to Database")
        self.save_btn.clicked.connect(self.save_to_db)
        footer.addWidget(self.save_btn)

        cancel = QPushButton("Close")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)

        main.addLayout(footer)

    # ---------------------------- Tab builders ----------------------------
    def build_general_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.name_edit = QLineEdit()
        self.subname_edit = QLineEdit()

        self.faction_combo = QComboBox()
        self.faction_combo.setEditable(True)
        if self.data.factions:
            items = [f"[{fid}] {name}" for fid, name in self.data.factions.items()]
            items.sort()
            self.faction_combo.addItems(items)
        completer = QCompleter(self.faction_combo.model(), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.faction_combo.setCompleter(completer)

        self.min_level = QSpinBox(); self.min_level.setRange(1, 83)
        self.max_level = QSpinBox(); self.max_level.setRange(1, 83)
        self.rank_combo = QComboBox(); self.rank_combo.addItems([
            "Normal", "Elite", "Rare Elite", "World Boss", "Rare"])
        self.family_combo = QComboBox()
        for k, v in CREATURE_FAMILY.items():
            self.family_combo.addItem(f"{v} ({k})", k)

        self.type_combo = QComboBox()
        for k, v in CREATURE_TYPE.items():
            self.type_combo.addItem(f"{v} ({k})", k)

        self.inhabit_combo = QComboBox()
        for k, v in INHABIT_TYPE.items():
            self.inhabit_combo.addItem(f"{v} ({k})", k)

        self.move_type_combo = QComboBox()
        for k, v in MOVEMENT_TYPE.items():
            self.move_type_combo.addItem(f"{v} ({k})", k)
        self.speed_walk = QDoubleSpinBox(); self.speed_walk.setRange(0.1, 10); self.speed_walk.setValue(1.0)
        self.speed_run = QDoubleSpinBox(); self.speed_run.setRange(0.1, 20); self.speed_run.setValue(1.14)
        self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(0.01, 10.0); self.scale_spin.setValue(1.0)

        layout.addRow("Name", self.name_edit)
        layout.addRow("Subname", self.subname_edit)
        layout.addRow("Faction", self.faction_combo)
        layout.addRow("Level Min", self.min_level)
        layout.addRow("Level Max", self.max_level)
        layout.addRow("Rank", self.rank_combo)
        layout.addRow("Family", self.family_combo)
        layout.addRow("Type", self.type_combo)
        layout.addRow("InhabitType", self.inhabit_combo)
        layout.addRow("MovementType", self.move_type_combo)
        layout.addRow("Speed Walk", self.speed_walk)
        layout.addRow("Speed Run", self.speed_run)
        layout.addRow("Scale", self.scale_spin)

        self.tabs.addTab(w, "General")

    def build_appearance_tab(self):
        w = QWidget(); outer = QHBoxLayout(w)

        left = QVBoxLayout()
        self.display_list = QListWidget()
        self.display_list.setSelectionMode(QListWidget.SingleSelection)
        left.addWidget(QLabel("Display IDs (primary first)"))
        left.addWidget(self.display_list, 1)

        add_btn = QPushButton("Add Display")
        add_btn.clicked.connect(self.add_display_id)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_display_id)
        btn_row = QHBoxLayout(); btn_row.addWidget(add_btn); btn_row.addWidget(remove_btn); btn_row.addStretch()
        left.addLayout(btn_row)

        self.model_search = QLineEdit(); self.model_search.setPlaceholderText("Search models (name or displayId)")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_models)
        srow = QHBoxLayout(); srow.addWidget(self.model_search); srow.addWidget(search_btn)
        left.addLayout(srow)

        self.model_results = QListWidget(); self.model_results.itemDoubleClicked.connect(self.apply_search_result)
        left.addWidget(self.model_results, 1)

        # Viewer side
        viewer_box = QVBoxLayout()
        # Disable embedded Panda3D to avoid GLX BadMatch on systems without a stable context.
        self.viewer = None
        viewer_box.addWidget(QLabel("Embedded preview disabled to avoid GLX issues.\nUse Full Viewer instead."), 1)
        open_full = QPushButton("Open Full Viewer")
        open_full.clicked.connect(self.open_full_viewer)
        viewer_box.addWidget(open_full)

        outer.addLayout(left, 2)
        outer.addLayout(viewer_box, 3)
        self.tabs.addTab(w, "Appearance")

    def build_stats_tab(self):
        w = QWidget(); layout = QFormLayout(w)
        self.unit_class = QComboBox()
        for k, v in UNIT_CLASS.items():
            self.unit_class.addItem(f"{v} ({k})", k)
        self.base_attack = QSpinBox(); self.base_attack.setRange(100, 5000); self.base_attack.setValue(2000)
        self.ranged_attack = QSpinBox(); self.ranged_attack.setRange(100, 5000); self.ranged_attack.setValue(2000)
        self.dmg_multi = QDoubleSpinBox(); self.dmg_multi.setRange(0.01, 50); self.dmg_multi.setValue(1.0)
        self.ap_base = QSpinBox(); self.ap_base.setRange(0, 10000)
        self.rap_base = QSpinBox(); self.rap_base.setRange(0, 10000)
        self.armor = QSpinBox(); self.armor.setRange(0, 50000)
        self.res_arcane = QSpinBox(); self.res_arcane.setRange(0, 500)
        self.res_fire = QSpinBox(); self.res_fire.setRange(0, 500)
        self.res_frost = QSpinBox(); self.res_frost.setRange(0, 500)
        self.res_nature = QSpinBox(); self.res_nature.setRange(0, 500)
        self.res_shadow = QSpinBox(); self.res_shadow.setRange(0, 500)
        self.hp_mod = QDoubleSpinBox(); self.hp_mod.setRange(0.01, 1000); self.hp_mod.setValue(1.0)
        self.mana_mod = QDoubleSpinBox(); self.mana_mod.setRange(0.01, 1000); self.mana_mod.setValue(1.0)
        self.regen_health = QCheckBox("Regenerate Health")

        self.ap_base.setToolTip("Optional override. If 0, core computes from level/class defaults.")
        self.rap_base.setToolTip("Optional override. If 0, core computes from level/class defaults.")
        self.armor.setToolTip("Optional override. If 0, core computes from level/class defaults.")
        self.dmg_multi.setToolTip("Damage multiplier applied to base damage from level/class.")
        self.hp_mod.setToolTip("Health multiplier applied to base health from level/class.")
        self.mana_mod.setToolTip("Mana multiplier applied to base mana from level/class.")

        layout.addRow("Unit Class", self.unit_class)
        layout.addRow("Base Attack Time (ms)", self.base_attack)
        layout.addRow("Ranged Attack Time (ms)", self.ranged_attack)
        layout.addRow("Damage Mult", self.dmg_multi)
        layout.addRow("AP Base", self.ap_base)
        layout.addRow("RAP Base", self.rap_base)
        layout.addRow("Armor", self.armor)
        layout.addRow("Res Arcane", self.res_arcane)
        layout.addRow("Res Fire", self.res_fire)
        layout.addRow("Res Frost", self.res_frost)
        layout.addRow("Res Nature", self.res_nature)
        layout.addRow("Res Shadow", self.res_shadow)
        layout.addRow("HP Modifier", self.hp_mod)
        layout.addRow("Mana Modifier", self.mana_mod)
        layout.addRow(self.regen_health)

        # Derived stats preview
        self.derived_label = QLabel()
        self.derived_label.setStyleSheet("color: #aaa; font-style: italic;")
        self.derived_label.setWordWrap(True)
        layout.addRow("Derived Preview", self.derived_label)
        self._wire_derived_preview()
        self.update_derived_preview()

        self.tabs.addTab(w, "Stats")

    def build_flags_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.npcflag_selector = BitmaskSelector(self._filter_flags(NPC_FLAG_DICT))
        self.unitflag_selector = BitmaskSelector(self._filter_flags(UNIT_FLAG_DICT))
        self.unitflag2_selector = BitmaskSelector(self._filter_flags(UNIT_FLAG2_DICT))
        layout.addWidget(QLabel("NPC Flags")); layout.addWidget(self.npcflag_selector)
        layout.addWidget(QLabel("Unit Flags")); layout.addWidget(self.unitflag_selector)
        layout.addWidget(QLabel("Unit Flags 2")); layout.addWidget(self.unitflag2_selector)
        self.tabs.addTab(w, "Flags")

    def build_equipment_tab(self):
        w = QWidget()
        outer = QVBoxLayout(w)

        top = QFormLayout()
        self.sheath_state = QComboBox()
        for k, v in SHEATH_STATE.items():
            self.sheath_state.addItem(f"{v} ({k})", k)
        top.addRow("Sheath State", self.sheath_state)
        outer.addLayout(top)

        cols = QHBoxLayout()
        self.equip_slot1 = SmartSelector("item")
        self.equip_slot2 = SmartSelector("item")
        self.equip_slot3 = SmartSelector("item")

        self.slot_widgets = {}
        cols.addWidget(self._build_slot_group(1))
        cols.addWidget(self._build_slot_group(2))
        cols.addWidget(self._build_slot_group(3))
        outer.addLayout(cols)

        self.tabs.addTab(w, "Equipment")

        self.equip_slot1.valueChanged.connect(lambda _v: self._update_item_info(1))
        self.equip_slot2.valueChanged.connect(lambda _v: self._update_item_info(2))
        self.equip_slot3.valueChanged.connect(lambda _v: self._update_item_info(3))

    def build_vendor_trainer_tab(self):
        w = QWidget(); outer = QVBoxLayout(w)
        # Loot table
        loot_group = QGroupBox("Loot")
        loot_layout = QVBoxLayout(loot_group)
        self.loot_table = self._make_table(["Item", "Chance", "Min", "Max", "Group"])
        self._set_header_tooltips(self.loot_table, {
            0: "Item entry ID.",
            1: "Chance percent (0-100).",
            2: "Minimum count.",
            3: "Maximum count.",
            4: "0 = independent roll, >0 = group roll (one item per group)."
        })
        loot_layout.addWidget(self.loot_table)
        loot_btns = QHBoxLayout()
        btn_add_loot = QPushButton("Add Loot")
        btn_del_loot = QPushButton("Remove Selected")
        btn_add_loot.clicked.connect(self._add_loot_dialog)
        btn_del_loot.clicked.connect(lambda: self._remove_selected_rows(self.loot_table))
        loot_btns.addWidget(btn_add_loot)
        loot_btns.addWidget(btn_del_loot)
        loot_btns.addStretch()
        loot_layout.addLayout(loot_btns)
        outer.addWidget(loot_group)

        vendor_group = QGroupBox("Vendor")
        vendor_layout = QVBoxLayout(vendor_group)
        self.vendor_table = self._make_table(["Item", "Slot", "ExtendedCost", "MaxCount", "IncrTime"])
        self._set_header_tooltips(self.vendor_table, {
            0: "Item entry ID.",
            1: "Vendor slot/order (0 = auto).",
            2: "Extended cost ID (item_extended_cost). 0 = none.",
            3: "Limited stock amount. 0 = unlimited.",
            4: "Restock time in seconds. 0 = no restock."
        })
        vendor_layout.addWidget(self.vendor_table)
        vendor_btns = QHBoxLayout()
        btn_add_vendor = QPushButton("Add Item")
        btn_del_vendor = QPushButton("Remove Selected")
        btn_add_vendor.clicked.connect(self._add_vendor_dialog)
        btn_del_vendor.clicked.connect(lambda: self._remove_selected_rows(self.vendor_table))
        vendor_btns.addWidget(btn_add_vendor)
        vendor_btns.addWidget(btn_del_vendor)
        vendor_btns.addStretch()
        vendor_layout.addLayout(vendor_btns)
        outer.addWidget(vendor_group)

        trainer_group = QGroupBox("Trainer")
        trainer_layout = QVBoxLayout(trainer_group)
        self.trainer_table = self._make_table(["SpellId", "ReqSkill", "ReqSkillVal", "ReqLevel"])
        self._set_header_tooltips(self.trainer_table, {
            0: "Spell ID.",
            1: "Required skill line (skillline_dbc ID).",
            2: "Required skill rank.",
            3: "Required player level."
        })
        trainer_layout.addWidget(self.trainer_table)
        trainer_btns = QHBoxLayout()
        btn_add_trainer = QPushButton("Add Spell")
        btn_del_trainer = QPushButton("Remove Selected")
        btn_add_trainer.clicked.connect(self._add_trainer_dialog)
        btn_del_trainer.clicked.connect(lambda: self._remove_selected_rows(self.trainer_table))
        trainer_btns.addWidget(btn_add_trainer)
        trainer_btns.addWidget(btn_del_trainer)
        trainer_btns.addStretch()
        trainer_layout.addLayout(trainer_btns)
        outer.addWidget(trainer_group)

        self.tabs.addTab(w, "Loot/Vendor/Trainer")

    def build_scripts_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        ai_row = QHBoxLayout()
        self.ai_name = QComboBox(); self.ai_name.addItems(["SmartAI", "EventAI", "ScriptedAI", "None"])
        self.script_name = QLineEdit(); self.script_name.setPlaceholderText("ScriptName (optional if SmartAI)")
        ai_row.addWidget(QLabel("AIName")); ai_row.addWidget(self.ai_name)
        ai_row.addWidget(QLabel("ScriptName")); ai_row.addWidget(self.script_name)
        layout.addLayout(ai_row)

        self.smart_table = self._make_table([
            "Event", "E1", "E2", "E3", "E4",
            "Action", "A1", "A2", "A3", "A4", "A5", "A6",
            "Target", "T1", "T2", "T3", "Chance", "Comment"
        ])
        layout.addWidget(self.smart_table)
        self.tabs.addTab(w, "Smart Scripts")

    def build_gossip_tab(self):
        w = QWidget(); layout = QFormLayout(w)
        self.gossip_menu_id = QSpinBox(); self.gossip_menu_id.setRange(0, 1000000)
        self.npc_text_id = QSpinBox(); self.npc_text_id.setRange(0, 1000000)

        btn_row = QHBoxLayout()
        btn_load = QPushButton("Load TextID from MenuID")
        btn_search = QPushButton("Search NPC Text")
        btn_load.clicked.connect(self._load_textid_from_menu)
        btn_search.clicked.connect(self._search_npc_text)
        btn_row.addWidget(btn_load)
        btn_row.addWidget(btn_search)
        btn_row.addStretch()

        self.greeting = QTextEdit()
        self.greeting.setReadOnly(True)
        self.greeting.setMaximumHeight(120)
        self.greeting.setPlaceholderText("Greeting text will appear here...")

        self.gossip_options = self._make_table(["OptionID", "Text", "Type", "NPC Flag", "ActionMenuID", "ActionPOI"])

        layout.addRow("GossipMenuId", self.gossip_menu_id)
        layout.addRow("NpcTextId", self.npc_text_id)
        layout.addRow("", btn_row)
        layout.addRow("Greeting Text", self.greeting)
        layout.addRow("Gossip Options", self.gossip_options)

        self.npc_text_id.valueChanged.connect(lambda _v: self._load_npc_text_preview())
        self.gossip_menu_id.valueChanged.connect(lambda _v: self._load_gossip_options())
        self.tabs.addTab(w, "Gossip")

    def build_preview_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        layout.addWidget(self.preview)
        self.tabs.addTab(w, "Preview")

    # ------------------------------------------------------------------ helpers
    def _make_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.AllEditTriggers)
        return table

    def _ensure_schema(self, cur=None):
        if self._schema:
            return
        close_conn = False
        if cur is None:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            close_conn = True
        self._tables = self._get_tables(cur)
        for table in [
            "creature_template",
            "creature_template_model",
            "creature_equip_template",
            "creature_template_addon",
            "creature_loot_template",
            "npc_vendor",
            "creature_default_trainer",
            "trainer",
            "trainer_spell",
            "gossip_menu",
            "npc_text",
            "smart_scripts"
        ]:
            self._schema[table] = self._get_columns(cur, table)
        if close_conn:
            cur.close()
            conn.close()

    def _get_tables(self, cur):
        tables = set()
        try:
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
            for r in rows:
                # value is in the first column, key varies by DB name
                val = next(iter(r.values()))
                if val:
                    tables.add(str(val).lower())
        except Exception as err:
            print(f"NPC editor schema table list failed: {err}")
        return tables

    def _get_columns(self, cur, table):
        if hasattr(self, "_tables") and table.lower() not in self._tables:
            return {}
        try:
            cur.execute(f"SHOW COLUMNS FROM {table}")
            rows = cur.fetchall()
            cols = {}
            for r in rows:
                col = r.get("Field")
                if col:
                    cols[col.lower()] = col
            return cols
        except Exception as err:
            return {}

    def _col(self, table, *candidates):
        cols = self._schema.get(table, {})
        for c in candidates:
            if c.lower() in cols:
                return cols[c.lower()]
        return None

    # ------------------------------------------------------------------ data load
    def load_from_db(self):
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            self._ensure_schema(cur)

            def safe_exec(query, params=None):
                try:
                    cur.execute(query, params or ())
                    return cur.fetchall()
                except Exception as err:
                    # Ignore missing/legacy columns to keep editor usable across DB variants.
                    print(f"NPC editor query skipped: {err}")
                    return []

            # creature_template
            rows = safe_exec("SELECT * FROM creature_template WHERE entry=%s", (self.entry_id,))
            tpl = rows[0] if rows else None
            if tpl:
                self.name_edit.setText(tpl.get('name', ''))
                self.subname_edit.setText(tpl.get('subname', ''))
                self._select_combo_by_prefix(self.faction_combo, tpl.get('faction', 35))
                self.min_level.setValue(tpl.get('minlevel', 1))
                self.max_level.setValue(tpl.get('maxlevel', 1))
                self.rank_combo.setCurrentIndex(min(tpl.get('rank', 0), self.rank_combo.count()-1))
                self._select_combo_by_data(self.family_combo, tpl.get('family', 0))
                self._select_combo_by_data(self.type_combo, tpl.get('type', 0))
                self._select_combo_by_data(self.inhabit_combo, tpl.get('InhabitType', 0))
                self._select_combo_by_data(self.move_type_combo, tpl.get('MovementType', 0))
                self.speed_walk.setValue(float(tpl.get('speed_walk', 1)))
                self.speed_run.setValue(float(tpl.get('speed_run', 1.14)))
                self.scale_spin.setValue(float(tpl.get('scale', 1.0)))
                self._select_combo_by_data(self.unit_class, tpl.get('unit_class', 1))
                self.base_attack.setValue(tpl.get('BaseAttackTime', 2000))
                self.ranged_attack.setValue(tpl.get('RangeAttackTime', 2000))
                self.dmg_multi.setValue(float(tpl.get('DamageModifier', 1)))
                self.ap_base.setValue(tpl.get('AttackPower', 0))
                self.rap_base.setValue(tpl.get('RangedAttackPower', 0))
                self.armor.setValue(tpl.get('armor', 0))
                self.res_arcane.setValue(tpl.get('resistance1', 0))
                self.res_fire.setValue(tpl.get('resistance2', 0))
                self.res_frost.setValue(tpl.get('resistance3', 0))
                self.res_nature.setValue(tpl.get('resistance4', 0))
                self.res_shadow.setValue(tpl.get('resistance5', 0))
                self.hp_mod.setValue(float(tpl.get('HealthModifier', 1)))
                self.mana_mod.setValue(float(tpl.get('ManaModifier', 1)))
                self._armor_modifier = float(tpl.get('ArmorModifier', 1))
                self._exp = tpl.get('exp', 0)
                self.regen_health.setChecked(tpl.get('RegenHealth', 1) == 1)
                self.npcflag_selector.set_value(tpl.get('npcflag', 0))
                self.unitflag_selector.set_value(tpl.get('unit_flags', 0))
                self.unitflag2_selector.set_value(tpl.get('unit_flags2', 0))

            # Models
            for row in safe_exec("SELECT * FROM creature_template_model WHERE CreatureID=%s ORDER BY Idx", (self.entry_id,)):
                self.display_list.addItem(f"{row['CreatureDisplayID']}|{row.get('DisplayScale',1.0)}|{row.get('Probability',1.0)}")

            # Equip
            equip_entry_col = self._col("creature_equip_template", "CreatureID", "entry")
            rows = safe_exec(
                f"SELECT * FROM creature_equip_template WHERE {equip_entry_col}=%s" if equip_entry_col else "SELECT * FROM creature_equip_template WHERE CreatureID=%s",
                (self.entry_id,)
            )
            eq = rows[0] if rows else None
            if eq:
                self.equip_slot1.set_value(eq.get('ItemID1', 0))
                self.equip_slot2.set_value(eq.get('ItemID2', 0))
                self.equip_slot3.set_value(eq.get('ItemID3', 0))
                self._update_item_info(1)
                self._update_item_info(2)
                self._update_item_info(3)

            # Addon (sheath state from bytes2)
            rows = safe_exec("SELECT * FROM creature_template_addon WHERE entry=%s", (self.entry_id,))
            if rows:
                self._addon_row = rows[0]
                bytes2 = self._addon_row.get("bytes2", 0)
                sheath = bytes2 & 0xFF
                self._select_combo_by_data(self.sheath_state, sheath)
            else:
                self._addon_row = None
                self._select_combo_by_data(self.sheath_state, 0)

            # Loot
            loot_entry_col = self._col("creature_loot_template", "Entry", "entry")
            loot_item_col = self._col("creature_loot_template", "Item", "item")
            loot_chance_col = self._col("creature_loot_template", "ChanceOrQuestChance", "Chance")
            loot_min_col = self._col("creature_loot_template", "MinCount")
            loot_max_col = self._col("creature_loot_template", "MaxCount")
            loot_group_col = self._col("creature_loot_template", "GroupId", "groupid")
            if all([loot_entry_col, loot_item_col, loot_chance_col, loot_min_col, loot_max_col, loot_group_col]):
                q = f"SELECT {loot_item_col} as Item, {loot_chance_col} as ChanceOrQuestChance, {loot_min_col} as MinCount, {loot_max_col} as MaxCount, {loot_group_col} as GroupId FROM creature_loot_template WHERE {loot_entry_col}=%s"
                self._fill_table(self.loot_table, safe_exec(q, (self.entry_id,)))

            # Vendor
            vendor_entry_col = self._col("npc_vendor", "entry", "Entry")
            vendor_item_col = self._col("npc_vendor", "item", "Item")
            vendor_slot_col = self._col("npc_vendor", "slot", "Slot")
            vendor_ext_col = self._col("npc_vendor", "ExtendedCost", "extendedcost")
            vendor_max_col = self._col("npc_vendor", "maxcount", "MaxCount")
            vendor_incr_col = self._col("npc_vendor", "incrtime", "IncrTime")
            if all([vendor_entry_col, vendor_item_col, vendor_slot_col, vendor_ext_col, vendor_max_col, vendor_incr_col]):
                q = f"SELECT {vendor_item_col} as item, {vendor_slot_col} as slot, {vendor_ext_col} as ExtendedCost, {vendor_max_col} as maxcount, {vendor_incr_col} as incrtime FROM npc_vendor WHERE {vendor_entry_col}=%s"
                self._fill_table(self.vendor_table, safe_exec(q, (self.entry_id,)))

            # Trainer
            if self._schema.get("creature_default_trainer") and self._schema.get("trainer_spell"):
                trainer_rows = safe_exec(
                    "SELECT TrainerId FROM creature_default_trainer WHERE CreatureId=%s",
                    (self.entry_id,)
                )
                if trainer_rows:
                    trainer_id = trainer_rows[0].get("TrainerId", 0)
                    if trainer_id:
                        spell_col = self._col("trainer_spell", "SpellId", "SpellID")
                        req_skill_col = self._col("trainer_spell", "ReqSkillLine")
                        req_skill_val_col = self._col("trainer_spell", "ReqSkillRank")
                        req_level_col = self._col("trainer_spell", "ReqLevel")
                        if all([spell_col, req_skill_col, req_skill_val_col, req_level_col]):
                            q = (
                                f"SELECT {spell_col} as SpellID, {req_skill_col} as ReqSkill, "
                                f"{req_skill_val_col} as ReqSkillValue, {req_level_col} as ReqLevel "
                                f"FROM trainer_spell WHERE TrainerId=%s"
                            )
                            self._fill_table(self.trainer_table, safe_exec(q, (trainer_id,)))

            # Smart scripts
            scripts = safe_exec(
                "SELECT * FROM smart_scripts WHERE entryorguid=%s AND source_type=0 ORDER BY id",
                (self.entry_id,)
            )
            self._fill_table(self.smart_table, [
                [r['event_type'], r['event_param1'], r['event_param2'], r['event_param3'], r['event_param4'],
                 r['action_type'], r['action_param1'], r['action_param2'], r['action_param3'], r['action_param4'], r['action_param5'], r['action_param6'],
                 r['target_type'], r['target_param1'], r['target_param2'], r['target_param3'], r['event_chance'], r['comment']]
                for r in scripts
            ])

            # Gossip (schema differs across cores; make it best-effort)
            gossip_menu_col = self._col("creature_template", "gossip_menu_id")
            if gossip_menu_col and tpl and tpl.get(gossip_menu_col):
                self.gossip_menu_id.setValue(tpl.get(gossip_menu_col, 0))
                gm_cols = self._schema.get("gossip_menu", {})
                menu_id_col = gm_cols.get("menuid")
                text_id_col = gm_cols.get("textid")
                if menu_id_col and text_id_col:
                    q = f"SELECT {text_id_col} as npc_text_id FROM gossip_menu WHERE {menu_id_col}=%s"
                    rows = safe_exec(q, (tpl.get(gossip_menu_col),))
                    if rows:
                        self.npc_text_id.setValue(rows[0].get("npc_text_id", 0))
                        self._load_npc_text_preview()
                        self._load_gossip_options()

            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", str(e))

    # ------------------------------------------------------------------ actions
    def add_display_id(self):
        text = self.model_search.text().strip()
        if not text:
            return
        self.display_list.addItem(f"{text}|1.0|1.0")
        self.display_list.setCurrentRow(self.display_list.count()-1)
        self.load_current_display_into_viewer()

    def remove_display_id(self):
        row = self.display_list.currentRow()
        if row >= 0:
            self.display_list.takeItem(row)

    def search_models(self):
        term = self.model_search.text().strip()
        self.model_results.clear()
        if not term:
            return
        results = self.data.search_models(term, limit=100)
        for did, path, tex in results:
            item = QListWidgetItem(f"[{did}] {path}")
            item.setData(Qt.UserRole, (did, path, tex))
            self.model_results.addItem(item)

    def apply_search_result(self, item):
        did, path, tex = item.data(Qt.UserRole)
        self.display_list.addItem(f"{did}|1.0|1.0")
        self.display_list.setCurrentRow(self.display_list.count()-1)
        self.load_model(path, tex)

    def load_current_display_into_viewer(self):
        if not self.viewer:
            return
        item = self.display_list.currentItem()
        if not item:
            return
        text = item.text()
        did = text.split('|')[0]
        try:
            did_int = int(did.strip())
        except ValueError:
            return
        info = self.data.display_infos.get(did_int)
        if info:
            self.load_model(info.get('model', ''), info.get('texture', ''))

    def open_full_viewer(self):
        from src.ui.tools.model_viewer_window import ModelViewerWindow
        win = ModelViewerWindow(self)
        win.show()

    def load_model(self, path, tex):
        if self.viewer:
            self.viewer.load_model(path, texture_path=tex)

    # ------------------------------------------------------------------ SQL helpers
    def collect_tables(self):
        """Gather current UI state into dict of table rows."""
        tpl = {
            'entry': self.entry_id,
            'name': self.name_edit.text(),
            'subname': self.subname_edit.text(),
            'faction': self._parse_bracket_value(self.faction_combo.currentText(), default=35),
            'minlevel': self.min_level.value(), 'maxlevel': self.max_level.value(),
            'rank': self.rank_combo.currentIndex(),
            'family': self.family_combo.currentData(),
            'type': self.type_combo.currentData(),
            'InhabitType': self.inhabit_combo.currentData(),
            'MovementType': self.move_type_combo.currentData(),
            'speed_walk': self.speed_walk.value(), 'speed_run': self.speed_run.value(), 'scale': self.scale_spin.value(),
            'unit_class': self.unit_class.currentData(), 'BaseAttackTime': self.base_attack.value(), 'RangeAttackTime': self.ranged_attack.value(),
            'DamageModifier': self.dmg_multi.value(), 'AttackPower': self.ap_base.value(), 'RangedAttackPower': self.rap_base.value(),
            'armor': self.armor.value(),
            'resistance1': self.res_arcane.value(), 'resistance2': self.res_fire.value(), 'resistance3': self.res_frost.value(),
            'resistance4': self.res_nature.value(), 'resistance5': self.res_shadow.value(),
            'HealthModifier': self.hp_mod.value(), 'ManaModifier': self.mana_mod.value(),
            'RegenHealth': 1 if self.regen_health.isChecked() else 0,
            'npcflag': self.npcflag_selector.get_value(),
            'unit_flags': self.unitflag_selector.get_value(),
            'unit_flags2': self.unitflag2_selector.get_value(),
            'AIName': self.ai_name.currentText(),
            'ScriptName': self.script_name.text(),
            'gossip_menu_id': self.gossip_menu_id.value()
        }

        models = []
        for idx in range(self.display_list.count()):
            text = self.display_list.item(idx).text()
            parts = text.split('|')
            did = int(parts[0]) if parts else 0
            scale = float(parts[1]) if len(parts) > 1 else 1.0
            prob = float(parts[2]) if len(parts) > 2 else 1.0
            models.append({'CreatureID': self.entry_id, 'Idx': idx, 'CreatureDisplayID': did, 'DisplayScale': scale, 'Probability': prob})

        equip = {
            'CreatureID': self.entry_id,
            'ID': 1,
            'ItemID1': self.equip_slot1.value(),
            'ItemID2': self.equip_slot2.value(),
            'ItemID3': self.equip_slot3.value()
        }

        addon = None
        if self._schema.get("creature_template_addon") is not None:
            # Preserve existing addon row when possible
            base = self._addon_row or {
                "entry": self.entry_id,
                "path_id": 0,
                "mount": 0,
                "bytes1": 0,
                "bytes2": 0,
                "emote": 0,
                "visibilityDistanceType": 0,
                "auras": ""
            }
            bytes2 = int(base.get("bytes2", 0))
            sheath = int(self.sheath_state.currentData() or 0)
            bytes2 = (bytes2 & 0xFFFFFF00) | (sheath & 0xFF)
            addon = {
                "entry": self.entry_id,
                "path_id": base.get("path_id", 0),
                "mount": base.get("mount", 0),
                "bytes1": base.get("bytes1", 0),
                "bytes2": bytes2,
                "emote": base.get("emote", 0),
                "visibilityDistanceType": base.get("visibilityDistanceType", 0),
                "auras": base.get("auras", "")
            }

        loot = self._table_rows(self.loot_table, ['Item', 'ChanceOrQuestChance', 'MinCount', 'MaxCount', 'GroupId'])
        vendor = self._table_rows(self.vendor_table, ['item', 'slot', 'ExtendedCost', 'maxcount', 'incrtime'])
        trainer = self._table_rows(self.trainer_table, ['SpellID', 'ReqSkill', 'ReqSkillValue', 'ReqLevel'])

        smart = []
        for r in range(self.smart_table.rowCount()):
            def cell(i):
                item = self.smart_table.item(r, i)
                return item.text() if item else ''
            smart.append({
                'event_type': self._safe_int(cell(0)), 'event_param1': self._safe_int(cell(1)), 'event_param2': self._safe_int(cell(2)),
                'event_param3': self._safe_int(cell(3)), 'event_param4': self._safe_int(cell(4)),
                'action_type': self._safe_int(cell(5)), 'action_param1': self._safe_int(cell(6)), 'action_param2': self._safe_int(cell(7)),
                'action_param3': self._safe_int(cell(8)), 'action_param4': self._safe_int(cell(9)), 'action_param5': self._safe_int(cell(10)), 'action_param6': self._safe_int(cell(11)),
                'target_type': self._safe_int(cell(12)), 'target_param1': self._safe_int(cell(13)), 'target_param2': self._safe_int(cell(14)), 'target_param3': self._safe_int(cell(15)),
                'event_chance': self._safe_int(cell(16), 100), 'comment': cell(17)
            })

        gossip = {
            'gossip_menu_id': self.gossip_menu_id.value(),
            'npc_text_id': self.npc_text_id.value(),
            'greeting': self.greeting.toPlainText()
        }

        return {
            'template': tpl,
            'models': models,
            'equip': equip,
            'addon': addon,
            'loot': loot,
            'vendor': vendor,
            'trainer': trainer,
            'smart': smart,
            'gossip': gossip
        }

    def generate_sql_strings(self, package):
        # Ensure schema if available (best-effort)
        if not self._schema:
            try:
                self._ensure_schema()
            except Exception:
                pass

        def map_cols(table, row):
            cols = self._schema.get(table, {})
            if not cols:
                return row
            mapped = {}
            for k, v in row.items():
                actual = cols.get(k.lower())
                if actual:
                    mapped[actual] = v
            return mapped

        sql = []
        e = package['template']['entry']
        # creature_template
        sql.append(f"DELETE FROM creature_template WHERE entry={e};")
        tpl_row = map_cols("creature_template", package['template'])
        cols = ','.join(tpl_row.keys())
        vals = ','.join(self._sql_val(v) for v in tpl_row.values())
        sql.append(f"INSERT INTO creature_template ({cols}) VALUES ({vals});")

        # models
        sql.append(f"DELETE FROM creature_template_model WHERE CreatureID={e};")
        for m in package['models']:
            mrow = map_cols("creature_template_model", m)
            cols = ','.join(mrow.keys()); vals = ','.join(self._sql_val(v) for v in mrow.values())
            sql.append(f"INSERT INTO creature_template_model ({cols}) VALUES ({vals});")

        # equip
        equip_entry_col = self._col("creature_equip_template", "CreatureID", "entry") or "CreatureID"
        sql.append(f"DELETE FROM creature_equip_template WHERE {equip_entry_col}={e};")
        erow = map_cols("creature_equip_template", package['equip'])
        cols = ','.join(erow.keys()); vals = ','.join(self._sql_val(v) for v in erow.values())
        sql.append(f"INSERT INTO creature_equip_template ({cols}) VALUES ({vals});")

        # addon (sheath state)
        if package.get('addon'):
            sql.append(f"DELETE FROM creature_template_addon WHERE entry={e};")
            arow = map_cols("creature_template_addon", package['addon'])
            cols = ','.join(arow.keys()); vals = ','.join(self._sql_val(v) for v in arow.values())
            sql.append(f"INSERT INTO creature_template_addon ({cols}) VALUES ({vals});")

        # loot
        loot_entry_col = self._col("creature_loot_template", "Entry", "entry") or "Entry"
        sql.append(f"DELETE FROM creature_loot_template WHERE {loot_entry_col}={e};")
        for row in package['loot']:
            lcols = self._schema.get("creature_loot_template", {})
            chance_col = lcols.get("chanceorquestchance") or lcols.get("chance") or "Chance"
            group_col = lcols.get("groupid") or "GroupId"
            mapped = {
                (lcols.get("item") or "Item"): row.get("Item", 0),
                chance_col: row.get("ChanceOrQuestChance", 0),
                (lcols.get("mincount") or "MinCount"): row.get("MinCount", 0),
                (lcols.get("maxcount") or "MaxCount"): row.get("MaxCount", 0),
                group_col: row.get("GroupId", 0)
            }
            cols = f"{loot_entry_col}," + ','.join(mapped.keys())
            vals = self._sql_val(e) + ',' + ','.join(self._sql_val(v) for v in mapped.values())
            sql.append(f"INSERT INTO creature_loot_template ({cols}) VALUES ({vals});")

        # vendor
        vend_entry_col = self._col("npc_vendor", "entry", "Entry") or "entry"
        sql.append(f"DELETE FROM npc_vendor WHERE {vend_entry_col}={e};")
        for row in package['vendor']:
            vcols = self._schema.get("npc_vendor", {})
            mapped = {
                (vcols.get("item") or "item"): row.get("item", 0),
                (vcols.get("slot") or "slot"): row.get("slot", 0),
                (vcols.get("extendedcost") or "ExtendedCost"): row.get("ExtendedCost", 0),
                (vcols.get("maxcount") or "maxcount"): row.get("maxcount", 0),
                (vcols.get("incrtime") or "incrtime"): row.get("incrtime", 0)
            }
            cols = f"{vend_entry_col}," + ','.join(mapped.keys())
            vals = self._sql_val(e) + ',' + ','.join(self._sql_val(v) for v in mapped.values())
            sql.append(f"INSERT INTO npc_vendor ({cols}) VALUES ({vals});")

        # trainer (AC: creature_default_trainer + trainer + trainer_spell)
        if self._schema.get("creature_default_trainer") and self._schema.get("trainer") and self._schema.get("trainer_spell"):
            sql.append(f"DELETE FROM creature_default_trainer WHERE CreatureId={e};")
            sql.append(f"DELETE FROM trainer WHERE Id={e};")
            sql.append(f"DELETE FROM trainer_spell WHERE TrainerId={e};")
            sql.append(f"INSERT INTO trainer (Id, Type, Requirement, Greeting) VALUES ({e}, 2, 0, '');")
            sql.append(f"INSERT INTO creature_default_trainer (CreatureId, TrainerId) VALUES ({e}, {e});")
            for row in package['trainer']:
                tcols = self._schema.get("trainer_spell", {})
                mapped = {
                    (tcols.get("spellid") or "SpellId"): row.get("SpellID", 0),
                    (tcols.get("reqskillline") or "ReqSkillLine"): row.get("ReqSkill", 0),
                    (tcols.get("reqskillrank") or "ReqSkillRank"): row.get("ReqSkillValue", 0),
                    (tcols.get("reqlevel") or "ReqLevel"): row.get("ReqLevel", 0),
                }
                if "moneycost" in tcols:
                    mapped[tcols.get("moneycost")] = 0
                cols = "TrainerId," + ','.join(mapped.keys())
                vals = self._sql_val(e) + ',' + ','.join(self._sql_val(v) for v in mapped.values())
                sql.append(f"INSERT INTO trainer_spell ({cols}) VALUES ({vals});")

        # smart_scripts
        sql.append(f"DELETE FROM smart_scripts WHERE entryorguid={e} AND source_type=0;")
        for idx, row in enumerate(package['smart']):
            cols = [
                'entryorguid','source_type','id','link','event_type','event_phase_mask','event_chance','event_flags',
                'event_param1','event_param2','event_param3','event_param4',
                'action_type','action_param1','action_param2','action_param3','action_param4','action_param5','action_param6',
                'target_type','target_param1','target_param2','target_param3','target_x','target_y','target_z','target_o',
                'comment'
            ]
            vals = [e,0,idx,0,row['event_type'],0,row.get('event_chance',100),0,
                    row['event_param1'],row['event_param2'],row['event_param3'],row['event_param4'],
                    row['action_type'],row['action_param1'],row['action_param2'],row['action_param3'],row['action_param4'],row['action_param5'],row['action_param6'],
                    row['target_type'],row['target_param1'],row['target_param2'],row['target_param3'],0,0,0,0,
                    row.get('comment','')]
            sql.append(f"INSERT INTO smart_scripts ({','.join(cols)}) VALUES ({','.join(self._sql_val(v) for v in vals)});")

        # gossip (AC: gossip_menu table uses MenuID/TextID; creature_template links by gossip_menu_id)
        if package['gossip']['gossip_menu_id']:
            gm_cols = self._schema.get("gossip_menu", {})
            menu_id_col = gm_cols.get("menuid") or "MenuID"
            text_id_col = gm_cols.get("textid") or "TextID"
            sql.append(f"DELETE FROM gossip_menu WHERE {menu_id_col}={package['gossip']['gossip_menu_id']};")
            sql.append(
                f"INSERT INTO gossip_menu ({menu_id_col}, {text_id_col}) "
                f"VALUES ({package['gossip']['gossip_menu_id']}, {package['gossip']['npc_text_id']});"
            )

        return '\n'.join(sql)

    # ------------------------------------------------------------------ file/db actions
    def generate_sql_file(self):
        pkg = self.collect_tables()
        sql = self.generate_sql_strings(pkg)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = f"output/npc_{self.entry_id}_{ts}.sql"
        path, _ = QFileDialog.getSaveFileName(self, "Save SQL", default_path, "SQL Files (*.sql)")
        if not path:
            return
        with open(path, 'w') as f:
            f.write(sql)
        self.preview.setText(sql)
        QMessageBox.information(self, "SQL Generated", f"Saved to {path}")

    def save_to_db(self):
        # range guard
        if self.allowed_id_range:
            start, end = self.allowed_id_range
            if not (start <= self.entry_id <= end):
                QMessageBox.critical(self, "Range Lock", f"Entry {self.entry_id} outside campaign range {start}-{end}")
                return

        pkg = self.collect_tables()
        sql_text = self.generate_sql_strings(pkg)
        self.preview.setText(sql_text)

        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get('id'))
            cur = conn.cursor()
            for stmt in sql_text.split(';'):
                if stmt.strip():
                    cur.execute(stmt)
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Saved", f"NPC {self.entry_id} written to database.")
            self.saved.emit(self.entry_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))

    def delete_npc(self):
        if self.allowed_id_range:
            s, e = self.allowed_id_range
            if not (s <= self.entry_id <= e):
                QMessageBox.critical(self, "Range Lock", "Cannot delete outside campaign range.")
                return
        if QMessageBox.question(self, "Confirm", f"Delete NPC {self.entry_id}?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get('id'))
            cur = conn.cursor()
            for table, key in [
                ('smart_scripts','entryorguid'),
                ('npc_vendor','entry'),
                ('trainer_spell','TrainerId'),
                ('trainer','Id'),
                ('creature_default_trainer','CreatureId'),
                ('creature_template_addon','entry'),
                ('creature_loot_template','Entry'),
                ('creature_equip_template','CreatureID'),
                ('creature_template_model','CreatureID'),
                ('creature_template','entry')
            ]:
                if self._schema.get(table):
                    cur.execute(f"DELETE FROM {table} WHERE {key}=%s", (self.entry_id,))
            conn.commit(); conn.close()
            QMessageBox.information(self, "Deleted", f"Entry {self.entry_id} removed.")
            self.saved.emit(self.entry_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))

    # ------------------------------------------------------------------ helpers
    def _fill_table(self, table, rows):
        table.setRowCount(0)
        for r in rows:
            row_idx = table.rowCount(); table.insertRow(row_idx)
            values = r.values() if hasattr(r, "values") else r
            for c, val in enumerate(values):
                table.setItem(row_idx, c, QTableWidgetItem(str(val)))

    def _table_rows(self, table, keys):
        rows = []
        for r in range(table.rowCount()):
            row = {}
            for c, k in enumerate(keys):
                item = table.item(r, c)
                row[k] = self._safe_int(item.text()) if item else 0
            rows.append(row)
        return rows

    def _sql_val(self, v):
        if v is None:
            return 'NULL'
        if isinstance(v, (int, float)):
            return str(v)
        # escape quotes
        return "'" + str(v).replace("'", "''") + "'"

    def _select_combo_by_prefix(self, combo, value):
        prefix = f"[{value}]"
        for i in range(combo.count()):
            if combo.itemText(i).startswith(prefix):
                combo.setCurrentIndex(i)
                return

    def _select_combo_by_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _filter_flags(self, flag_dict):
        return {k: v for k, v in flag_dict.items() if "Unknown" not in v and "Unused" not in v}

    def _load_textid_from_menu(self):
        menu_id = self.gossip_menu_id.value()
        if not menu_id:
            return
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT TextID FROM gossip_menu WHERE MenuID=%s", (menu_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                self.npc_text_id.setValue(row.get("TextID", 0))
                self._load_gossip_options()
        except Exception:
            pass

    def _load_npc_text_preview(self):
        text_id = self.npc_text_id.value()
        if not text_id:
            self.greeting.clear()
            return
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM npc_text WHERE ID=%s", (text_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                self.greeting.setText("NPC text not found.")
                return
            # Use first available line as greeting
            greeting_text = ""
            for i in range(0, 8):
                t0 = row.get(f"text{i}_0")
                t1 = row.get(f"text{i}_1")
                if t0 or t1:
                    greeting_text = t0 or t1
                    break
            self.greeting.setText(greeting_text or "NPC text is empty.")
        except Exception:
            self.greeting.setText("Failed to load NPC text.")

    def _search_npc_text(self):
        dlg = _NpcTextDialog(self)
        if dlg.exec():
            self.npc_text_id.setValue(dlg.text_id)

    def _load_gossip_options(self):
        menu_id = self.gossip_menu_id.value()
        if not menu_id:
            self.gossip_options.setRowCount(0)
            return
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT OptionID, OptionText, OptionType, OptionNpcFlag, ActionMenuID, ActionPoiID "
                "FROM gossip_menu_option WHERE MenuID=%s ORDER BY OptionID",
                (menu_id,)
            )
            rows = cur.fetchall()
            conn.close()
            self.gossip_options.setRowCount(0)
            for row in rows:
                r = self.gossip_options.rowCount()
                self.gossip_options.insertRow(r)
                self.gossip_options.setItem(r, 0, QTableWidgetItem(str(row.get("OptionID", 0))))
                self.gossip_options.setItem(r, 1, QTableWidgetItem(row.get("OptionText", "") or ""))
                self.gossip_options.setItem(r, 2, QTableWidgetItem(str(row.get("OptionType", 0))))
                self.gossip_options.setItem(r, 3, QTableWidgetItem(str(row.get("OptionNpcFlag", 0))))
                self.gossip_options.setItem(r, 4, QTableWidgetItem(str(row.get("ActionMenuID", 0))))
                self.gossip_options.setItem(r, 5, QTableWidgetItem(str(row.get("ActionPoiID", 0))))
        except Exception:
            self.gossip_options.setRowCount(0)

    def _update_item_info(self, slot_num):
        selector = {1: self.equip_slot1, 2: self.equip_slot2, 3: self.equip_slot3}.get(slot_num)
        widgets = self.slot_widgets.get(slot_num)
        if not selector or not widgets:
            return
        item_id = selector.value()
        if not item_id:
            widgets["name"].setText("Empty")
            widgets["type"].setText("-")
            widgets["damage"].setText("-")
            widgets["armor"].setText("-")
            widgets["speed"].setText("-")
            widgets["stats"].setText("-")
            return
        info = self._fetch_item_info(item_id)
        if not info:
            widgets["name"].setText("Item not found")
            widgets["type"].setText("-")
            widgets["damage"].setText("-")
            widgets["armor"].setText("-")
            widgets["speed"].setText("-")
            widgets["stats"].setText("-")
            return
        dmg_min = info.get("dmg_min1", 0)
        dmg_max = info.get("dmg_max1", 0)
        delay = info.get("delay", 0)
        armor = info.get("armor", 0)
        item_class = ITEM_CLASS.get(info.get("class", 0), str(info.get("class", 0)))
        subclass = self._item_subclass_name(info.get("class", 0), info.get("subclass", 0))
        inv = INVENTORY_TYPE.get(info.get("InventoryType", 0), str(info.get("InventoryType", 0)))
        name = info.get("name", "Unknown")

        widgets["name"].setText(f"{name} (ID: {item_id})")
        widgets["type"].setText(f"{item_class} / {subclass} | {inv}")
        if dmg_min or dmg_max:
            widgets["damage"].setText(f"{dmg_min:.1f} - {dmg_max:.1f}")
        else:
            widgets["damage"].setText("-")
        widgets["speed"].setText(f"{delay} ms" if delay else "-")
        widgets["armor"].setText(str(armor) if armor else "-")
        widgets["stats"].setText(self._format_item_stats(info))

    def _fetch_item_info(self, item_id):
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT entry, name, class, subclass, InventoryType, dmg_min1, dmg_max1, delay, armor, "
                "stat_type1, stat_value1, stat_type2, stat_value2, stat_type3, stat_value3, "
                "stat_type4, stat_value4, stat_type5, stat_value5, stat_type6, stat_value6, "
                "stat_type7, stat_value7, stat_type8, stat_value8, stat_type9, stat_value9, "
                "stat_type10, stat_value10 "
                "FROM item_template WHERE entry=%s",
                (item_id,)
            )
            row = cur.fetchone()
            conn.close()
            return row
        except Exception:
            return None

    def _build_slot_group(self, slot_num):
        box = QGroupBox(f"Slot {slot_num}")
        form = QFormLayout(box)
        selector = {1: self.equip_slot1, 2: self.equip_slot2, 3: self.equip_slot3}[slot_num]
        name = QLabel("-"); name.setWordWrap(True)
        type_lbl = QLabel("-"); type_lbl.setWordWrap(True)
        dmg = QLabel("-")
        armor = QLabel("-")
        speed = QLabel("-")
        stats = QLabel("-"); stats.setWordWrap(True)
        form.addRow("ID", selector)
        form.addRow("Name", name)
        form.addRow("Type", type_lbl)
        form.addRow("Damage", dmg)
        form.addRow("Speed", speed)
        form.addRow("Armor", armor)
        form.addRow("Stats", stats)
        self.slot_widgets[slot_num] = {
            "name": name, "type": type_lbl, "damage": dmg, "armor": armor, "speed": speed, "stats": stats
        }
        return box

    def _item_subclass_name(self, item_class, subclass):
        weapon = {
            0: "One-Hand Axe", 1: "Two-Hand Axe", 2: "Bow", 3: "Gun", 4: "One-Hand Mace",
            5: "Two-Hand Mace", 6: "Polearm", 7: "One-Hand Sword", 8: "Two-Hand Sword",
            9: "Obsolete", 10: "Staff", 11: "One-Hand Exotic", 12: "Two-Hand Exotic",
            13: "Fist Weapon", 14: "Miscellaneous", 15: "Dagger", 16: "Thrown",
            17: "Spear", 18: "Crossbow", 19: "Wand", 20: "Fishing Pole"
        }
        armor = {
            0: "Misc", 1: "Cloth", 2: "Leather", 3: "Mail", 4: "Plate",
            5: "Buckler", 6: "Shield", 7: "Libram", 8: "Idol", 9: "Totem", 10: "Sigil"
        }
        if item_class == 2:
            return weapon.get(subclass, f"Subclass {subclass}")
        if item_class == 4:
            return armor.get(subclass, f"Subclass {subclass}")
        return f"Subclass {subclass}"

    def _format_item_stats(self, info):
        stat_map = {
            0: "Mana", 1: "Health", 3: "Agility", 4: "Strength",
            5: "Intellect", 6: "Spirit", 7: "Stamina",
            38: "Attack Power", 39: "Ranged AP", 45: "Spell Power",
            32: "Crit Rating", 33: "Haste Rating", 31: "Hit Rating",
            15: "Block Rating", 13: "Dodge Rating", 14: "Parry Rating"
        }
        parts = []
        for i in range(1, 11):
            st = info.get(f"stat_type{i}", 0)
            sv = info.get(f"stat_value{i}", 0)
            if sv:
                parts.append(f"+{sv} {stat_map.get(st, f'Stat {st}')}")
        return ", ".join(parts) if parts else "-"

    def _add_table_row(self, table, defaults):
        row = table.rowCount()
        table.insertRow(row)
        for i, val in enumerate(defaults):
            table.setItem(row, i, QTableWidgetItem(str(val)))

    def _remove_selected_rows(self, table):
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for r in rows:
            table.removeRow(r)

    def _set_header_tooltips(self, table, mapping):
        header = table.horizontalHeader()
        for col, tip in mapping.items():
            item = table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tip)

    def _add_loot_dialog(self):
        dlg = _AddLootDialog(self)
        if dlg.exec():
            row = [dlg.item_id, dlg.chance, dlg.min_count, dlg.max_count, dlg.group_id]
            self._add_table_row(self.loot_table, row)

    def _add_vendor_dialog(self):
        dlg = _AddVendorDialog(self)
        if dlg.exec():
            row = [dlg.item_id, dlg.slot, dlg.extended_cost, dlg.max_count, dlg.incr_time]
            self._add_table_row(self.vendor_table, row)

    def _add_trainer_dialog(self):
        dlg = _AddTrainerDialog(self)
        if dlg.exec():
            row = [dlg.spell_id, dlg.req_skill, dlg.req_skill_val, dlg.req_level]
            self._add_table_row(self.trainer_table, row)

    def _wire_derived_preview(self):
        for w in [
            self.min_level, self.max_level, self.rank_combo, self.unit_class,
            self.hp_mod, self.mana_mod, self.dmg_multi, self.armor,
            self.ap_base, self.rap_base, self.base_attack, self.ranged_attack,
            self.res_arcane, self.res_fire, self.res_frost, self.res_nature, self.res_shadow
        ]:
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self.update_derived_preview)
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self.update_derived_preview)

    def update_derived_preview(self):
        lvl = max(self.min_level.value(), self.max_level.value())
        rank = self.rank_combo.currentIndex()
        cls = self.unit_class.currentData()

        stats = self._get_classlevelstats(lvl, cls)
        if stats:
            if rank == 0:
                base_hp = stats.get("basehp0", 0)
            elif rank in (1, 4):
                base_hp = stats.get("basehp1", 0)
            else:
                base_hp = stats.get("basehp2", 0)

            base_mana = stats.get("basemana", 0)
            base_armor = stats.get("basearmor", 0)
            base_ap = stats.get("attackpower", 0)
            base_rap = stats.get("rangedattackpower", 0)

            base_dmg = stats.get("damage_base", 0)
            if self._exp == 1 and "damage_exp1" in stats:
                base_dmg = stats.get("damage_exp1", base_dmg)
            if self._exp == 2 and "damage_exp2" in stats:
                base_dmg = stats.get("damage_exp2", base_dmg)

            eff_hp = int(base_hp * self.hp_mod.value())
            eff_mana = int(base_mana * self.mana_mod.value())
            eff_armor = self.armor.value() if self.armor.value() > 0 else int(base_armor * self._armor_modifier)
            eff_ap = self.ap_base.value() if self.ap_base.value() > 0 else base_ap
            eff_rap = self.rap_base.value() if self.rap_base.value() > 0 else base_rap
            ap_bonus = eff_ap / 14.0
            rap_bonus = eff_rap / 14.0
            melee_dmg = round((base_dmg + ap_bonus) * self.dmg_multi.value(), 1)
            ranged_dmg = round((base_dmg + rap_bonus) * self.dmg_multi.value(), 1)
            atk_ms = max(self.base_attack.value(), 1)
            ratk_ms = max(self.ranged_attack.value(), 1)
            melee_dps = round((melee_dmg / (atk_ms / 1000.0)), 1)
            ranged_dps = round((ranged_dmg / (ratk_ms / 1000.0)), 1)

            res_lines = self._format_resistance_lines(lvl)
            self.derived_label.setText(
                f"HP: {base_hp} → {eff_hp}\n"
                f"Mana: {base_mana} → {eff_mana}\n"
                f"Armor: {eff_armor}\n"
                f"AP/RAP: {eff_ap} / {eff_rap}\n"
                f"Base Damage: {base_dmg}\n"
                f"Melee: {melee_dmg} dmg / {melee_dps} DPS\n"
                f"Ranged: {ranged_dmg} dmg / {ranged_dps} DPS\n"
                f"{res_lines}"
            )
        else:
            base_hp = 100 + (lvl * 20)
            base_dmg = 5 + (lvl * 1.5)
            hp = int(base_hp * self.hp_mod.value())
            dmg = round(base_dmg * self.dmg_multi.value(), 1)
            res_lines = self._format_resistance_lines(lvl)
            self.derived_label.setText(
                f"Approx HP: {hp}\nApprox Damage: {dmg}\n{res_lines}\n(no classlevelstats found)"
            )

    def _format_resistance_lines(self, level):
        def pct(res):
            return self._resist_pct(res, level)
        return (
            f"Res Arcane: {self.res_arcane.value()} → {pct(self.res_arcane.value())}%\n"
            f"Res Fire: {self.res_fire.value()} → {pct(self.res_fire.value())}%\n"
            f"Res Frost: {self.res_frost.value()} → {pct(self.res_frost.value())}%\n"
            f"Res Nature: {self.res_nature.value()} → {pct(self.res_nature.value())}%\n"
            f"Res Shadow: {self.res_shadow.value()} → {pct(self.res_shadow.value())}%"
        )

    def _resist_pct(self, resistance, level):
        if resistance <= 0 or level <= 0:
            return 0
        denom = resistance + (level * 5)
        if denom <= 0:
            return 0
        avg = 0.75 * (resistance / denom) * 100
        return round(min(avg, 75.0), 1)

    def _get_classlevelstats(self, level, cls):
        key = (level, cls)
        if key in self._classlevel_cache:
            return self._classlevel_cache[key]
        try:
            conn = self.db.get_connection(realm_id=self.dev_realm_config.get("id"))
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT basehp0, basehp1, basehp2, basemana, basearmor, attackpower, rangedattackpower, "
                "damage_base, damage_exp1, damage_exp2 "
                "FROM creature_classlevelstats WHERE level=%s AND class=%s",
                (level, cls)
            )
            row = cur.fetchone()
            conn.close()
            self._classlevel_cache[key] = row
            return row
        except Exception:
            self._classlevel_cache[key] = None
            return None

    def _parse_bracket_value(self, text, default=0):
        if text.startswith('['):
            try:
                return int(text.split(']')[0].strip('['))
            except ValueError:
                return default
        return default

    def _safe_int(self, s, default=0):
        try:
            return int(str(s))
        except Exception:
            return default



class _AddLootDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Loot Item")
        self.item_id = 0
        self.chance = 0
        self.min_count = 1
        self.max_count = 1
        self.group_id = 0
        self.item_name = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.item_label = QLabel("None")
        btn_search = QPushButton("Search Item")
        btn_search.clicked.connect(self._search_item)
        search_row = QHBoxLayout()
        search_row.addWidget(btn_search)
        search_row.addWidget(self.item_label)

        self.chance_inp = QDoubleSpinBox(); self.chance_inp.setRange(0, 100); self.chance_inp.setValue(0)
        self.min_inp = QSpinBox(); self.min_inp.setRange(1, 1000); self.min_inp.setValue(1)
        self.max_inp = QSpinBox(); self.max_inp.setRange(1, 1000); self.max_inp.setValue(1)
        self.group_combo = QComboBox()
        self.group_combo.addItem("Independent (0)", 0)
        for i in range(1, 6):
            self.group_combo.addItem(f"Group {i}", i)

        form.addRow("Item", search_row)
        form.addRow("Chance", self.chance_inp)
        form.addRow("Min Count", self.min_inp)
        form.addRow("Max Count", self.max_inp)
        self.group_combo.setToolTip("0 = independent roll, >0 = group roll (one item per group).")
        form.addRow("Group", self.group_combo)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("Add")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _search_item(self):
        dlg = SearchDialog("item", self)
        if dlg.exec():
            self.item_id = dlg.selected_id or 0
            self.item_name = dlg.selected_name or ""
            self.item_label.setText(f"[{self.item_id}] {self.item_name}")

    def _accept(self):
        if not self.item_id:
            QMessageBox.warning(self, "Validation", "Please select an item.")
            return
        self.chance = float(self.chance_inp.value())
        self.min_count = int(self.min_inp.value())
        self.max_count = int(self.max_inp.value())
        self.group_id = int(self.group_combo.currentData() or 0)
        self.accept()


class _AddVendorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Vendor Item")
        self.item_id = 0
        self.item_name = ""
        self.slot = 0
        self.extended_cost = 0
        self.max_count = 0
        self.incr_time = 0
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.item_label = QLabel("None")
        btn_search = QPushButton("Search Item")
        btn_search.clicked.connect(self._search_item)
        search_row = QHBoxLayout()
        search_row.addWidget(btn_search)
        search_row.addWidget(self.item_label)

        self.slot_inp = QSpinBox(); self.slot_inp.setRange(0, 1000); self.slot_inp.setValue(0)
        self.ext_inp = QSpinBox(); self.ext_inp.setRange(0, 1000000); self.ext_inp.setValue(0)
        self.max_inp = QSpinBox(); self.max_inp.setRange(0, 1000000); self.max_inp.setValue(0)
        self.incr_inp = QSpinBox(); self.incr_inp.setRange(0, 1000000); self.incr_inp.setValue(0)

        self.slot_inp.setToolTip("Vendor slot/order. 0 = auto.")
        self.ext_inp.setToolTip("Extended cost ID (item_extended_cost). 0 = none.")
        self.max_inp.setToolTip("Limited stock. 0 = unlimited.")
        self.incr_inp.setToolTip("Restock time in seconds. 0 = no restock.")

        form.addRow("Item", search_row)
        form.addRow("Slot", self.slot_inp)
        form.addRow("Extended Cost", self.ext_inp)
        form.addRow("Max Count", self.max_inp)
        form.addRow("Incr Time", self.incr_inp)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("Add")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _search_item(self):
        dlg = SearchDialog("item", self)
        if dlg.exec():
            self.item_id = dlg.selected_id or 0
            self.item_name = dlg.selected_name or ""
            self.item_label.setText(f"[{self.item_id}] {self.item_name}")

    def _accept(self):
        if not self.item_id:
            QMessageBox.warning(self, "Validation", "Please select an item.")
            return
        self.slot = int(self.slot_inp.value())
        self.extended_cost = int(self.ext_inp.value())
        self.max_count = int(self.max_inp.value())
        self.incr_time = int(self.incr_inp.value())
        self.accept()


class _AddTrainerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Trainer Spell")
        self.spell_id = 0
        self.spell_name = ""
        self.req_skill = 0
        self.req_skill_val = 0
        self.req_level = 0
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.spell_label = QLabel("None")
        btn_search = QPushButton("Search Spell")
        btn_search.clicked.connect(self._search_spell)
        search_row = QHBoxLayout()
        search_row.addWidget(btn_search)
        search_row.addWidget(self.spell_label)

        self.req_skill_inp = QSpinBox(); self.req_skill_inp.setRange(0, 10000); self.req_skill_inp.setValue(0)
        self.req_skill_label = QLabel("None")
        btn_skill = QPushButton("Search Skill Line")
        btn_skill.clicked.connect(self._search_skill_line)
        skill_row = QHBoxLayout()
        skill_row.addWidget(btn_skill)
        skill_row.addWidget(self.req_skill_label)
        self.req_skill_val_inp = QSpinBox(); self.req_skill_val_inp.setRange(0, 10000); self.req_skill_val_inp.setValue(0)
        self.req_level_inp = QSpinBox(); self.req_level_inp.setRange(0, 80); self.req_level_inp.setValue(0)

        self.req_skill_inp.setToolTip("Skill line required to learn the spell (e.g., Blacksmithing).")

        form.addRow("Spell", search_row)
        form.addRow("Req Skill Line", self.req_skill_inp)
        form.addRow("", skill_row)
        form.addRow("Req Skill Rank", self.req_skill_val_inp)
        form.addRow("Req Level", self.req_level_inp)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("Add")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _search_spell(self):
        dlg = SearchDialog("spell", self)
        if dlg.exec():
            self.spell_id = dlg.selected_id or 0
            self.spell_name = dlg.selected_name or ""
            self.spell_label.setText(f"[{self.spell_id}] {self.spell_name}")

    def _accept(self):
        if not self.spell_id:
            QMessageBox.warning(self, "Validation", "Please select a spell.")
            return
        self.req_skill = int(self.req_skill_inp.value())
        self.req_skill_val = int(self.req_skill_val_inp.value())
        self.req_level = int(self.req_level_inp.value())
        self.accept()

    def _search_skill_line(self):
        dlg = _SkillLineDialog(self)
        if dlg.exec():
            self.req_skill_inp.setValue(dlg.skill_id)
            self.req_skill_label.setText(f"[{dlg.skill_id}] {dlg.skill_name}")


class _SkillLineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Skill Line")
        self.resize(500, 400)
        self.skill_id = 0
        self.skill_name = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        search_row = QHBoxLayout()
        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Search skill name or ID...")
        self.search_inp.setToolTip("Skill line is the profession/skill required (e.g., Blacksmithing).")
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._search)
        search_row.addWidget(self.search_inp)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        self.list_results = QListWidget()
        self.list_results.itemDoubleClicked.connect(self._select_item)
        layout.addWidget(self.list_results)

        buttons = QHBoxLayout()
        ok = QPushButton("Select")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _search(self):
        term = self.search_inp.text().strip()
        if not term:
            return
        self.list_results.clear()
        try:
            db = DbManager.get_instance()
            conn = db.get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) as cnt FROM skillline_dbc")
            if cur.fetchone().get("cnt", 0) == 0:
                conn.close()
                # Fallback to DBC
                from src.core.data_manager import DataManager
                dm = DataManager()
                if not dm.skill_lines:
                    dm.load_data()
                results = dm.search_skill_lines(term, limit=50)
                if not results:
                    QMessageBox.information(
                        self, "No Data",
                        "skillline_dbc is empty in this DB and no SkillLine.dbc data was found."
                    )
                    return
                for sid, name in results:
                    item = QListWidgetItem(f"[{sid}] {name}")
                    item.setData(Qt.UserRole, (sid, name))
                    self.list_results.addItem(item)
                return
            name_expr = "COALESCE(DisplayName_Lang_enUS, DisplayName_Lang_enGB, DisplayName_Lang_frFR, DisplayName_Lang_deDE, DisplayName_Lang_esES, DisplayName_Lang_ruRU, DisplayName_Lang_zhCN, DisplayName_Lang_koKR)"
            if term.isdigit():
                cur.execute(
                    f"SELECT ID, {name_expr} as name FROM skillline_dbc WHERE ID=%s",
                    (int(term),)
                )
            else:
                cur.execute(
                    f"SELECT ID, {name_expr} as name FROM skillline_dbc WHERE {name_expr} LIKE %s LIMIT 50",
                    (f"%{term}%",)
                )
            for row in cur.fetchall():
                name = row.get("name") or "Unknown"
                item = QListWidgetItem(f"[{row['ID']}] {name}")
                item.setData(Qt.UserRole, (row['ID'], name))
                self.list_results.addItem(item)
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Search Error", str(e))

    def _select_item(self, item):
        self.skill_id, self.skill_name = item.data(Qt.UserRole)
        self.accept()

    def _accept(self):
        item = self.list_results.currentItem()
        if not item:
            return
        self._select_item(item)


class _NpcTextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select NPC Text")
        self.resize(600, 450)
        self.text_id = 0
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        search_row = QHBoxLayout()
        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Search NPC text...")
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._search)
        search_row.addWidget(self.search_inp)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        self.list_results = QListWidget()
        self.list_results.itemDoubleClicked.connect(self._select_item)
        layout.addWidget(self.list_results)

        buttons = QHBoxLayout()
        ok = QPushButton("Select")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(); buttons.addWidget(cancel); buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _search(self):
        term = self.search_inp.text().strip()
        if not term:
            return
        self.list_results.clear()
        try:
            db = DbManager.get_instance()
            conn = db.get_connection()
            cur = conn.cursor(dictionary=True)
            # Search in text columns
            like = f"%{term}%"
            cur.execute(
                "SELECT ID, text0_0, text0_1 FROM npc_text "
                "WHERE text0_0 LIKE %s OR text0_1 LIKE %s LIMIT 50",
                (like, like)
            )
            for row in cur.fetchall():
                preview = row.get("text0_0") or row.get("text0_1") or ""
                item = QListWidgetItem(f"[{row['ID']}] {preview[:80]}")
                item.setData(Qt.UserRole, row.get("ID"))
                self.list_results.addItem(item)
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Search Error", str(e))

    def _select_item(self, item):
        self.text_id = item.data(Qt.UserRole)
        self.accept()

    def _accept(self):
        item = self.list_results.currentItem()
        if not item:
            return
        self._select_item(item)
