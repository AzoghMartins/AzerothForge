from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, 
                               QTextEdit, QPushButton, QGroupBox, QLabel)
from src.core.data_manager import DataManager

class NpcEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = DataManager()
        self.init_ui()
        self.load_data()
        self.on_active_realm_changed()

    def on_active_realm_changed(self):
        # We need to access ConfigManager. Since we didn't inject it like Dashboard,
        # we can get it from DataManager which has self.config_manager, or instantiate new.
        # DataManager is a singleton, so self.data_manager.config_manager is shared?
        # DataManager creates its own ConfigManager instance.
        # Let's rely on self.data_manager.config_manager.config which should be reloaded or current.
        # Ideally we should grab the fresh config.
        
        # But wait, DataManager.config_manager might be stale if we don't reload it.
        # However, we just updated the file on disk in MainWindow. 
        # So let's reload it here to be safe.
        
        # Actually simplest is just:
        from src.core.config_manager import ConfigManager
        cm = ConfigManager() # Loads fresh
        realm = cm.get_active_realm()
        db_name = realm.get("db_world_name", "Unknown")
        self.db_label.setText(f"Target DB: {db_name}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Top Row: Basic Info ---
        top_group = QGroupBox("Basic Information")
        top_layout = QHBoxLayout()
        
        # Entry ID
        self.entry_spin = QSpinBox()
        self.entry_spin.setRange(1, 999999)
        self.entry_spin.setValue(50000)
        self.entry_spin.setPrefix("ID: ")
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("NPC Name")
        
        # Subname
        self.subname_edit = QLineEdit()
        self.subname_edit.setPlaceholderText("Subname (Title)")
        
        top_layout.addWidget(self.entry_spin)
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.subname_edit)
        
        # Target DB Label
        self.db_label = QLabel("Target DB: -")
        self.db_label.setStyleSheet("color: #aaa; font-style: italic; margin-left: 10px;")
        top_layout.addWidget(self.db_label)
        
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)
        
        # --- Middle Row: Identity & Stats ---
        mid_layout = QHBoxLayout()
        
        # Identity Group
        identity_group = QGroupBox("Identity")
        identity_form = QFormLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        
        self.faction_combo = QComboBox()
        self.faction_combo.setEditable(True)
        
        identity_form.addRow("Model:", self.model_combo)
        identity_form.addRow("Faction:", self.faction_combo)
        identity_group.setLayout(identity_form)
        
        # Stats Group
        stats_group = QGroupBox("Stats")
        stats_form = QFormLayout()
        
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 83)
        self.level_spin.setValue(80)
        
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(["Normal", "Elite", "Rare Elite", "World Boss", "Rare"])
        # Map rank names to IDs if needed (0, 1, 2, 3, 4)
        
        self.hp_mod_spin = QDoubleSpinBox()
        self.hp_mod_spin.setRange(0.1, 1000.0)
        self.hp_mod_spin.setValue(1.0)
        self.hp_mod_spin.setSingleStep(0.1)
        
        stats_form.addRow("Level:", self.level_spin)
        stats_form.addRow("Rank:", self.rank_combo)
        stats_form.addRow("Health Mod:", self.hp_mod_spin)
        stats_group.setLayout(stats_form)
        
        mid_layout.addWidget(identity_group)
        mid_layout.addWidget(stats_group)
        main_layout.addLayout(mid_layout)
        
        # --- Generate Button ---
        self.gen_btn = QPushButton("Generate SQL")
        self.gen_btn.clicked.connect(self.generate_sql)
        self.gen_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 12px;")
        main_layout.addWidget(self.gen_btn)
        
        # --- Preview Area ---
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Generated SQL will appear here...")
        main_layout.addWidget(self.preview_text)

    def load_data(self):
        # Populate Factions
        self.faction_combo.clear()
        if self.data_manager.factions:
            # Performance: Add all if possible, or limit
            # With 400 factions, adding all is fine.
            items = [f"[{fid}] {name}" for fid, name in self.data_manager.factions.items()]
            items.sort() # Sort by text or ID?
            self.faction_combo.addItems(items)
        else:
            self.faction_combo.addItem("No Factions Loaded")
            
        # Populate Models
        self.model_combo.clear()
        if self.data_manager.display_infos:
            # 24k items might be slow to render in a combo box at once.
            # Let's add top 500 for now as a safety optimization, or checking constraint.
            # User said "ensure the ComboBox adds items efficiently (or just add the first 100 as a test)"
            # Let's try 1000.
            limit = 0
            items = []
            for cid, model_id in self.data_manager.display_infos.items():
                items.append(f"[{cid}] Model {model_id}")
                limit += 1
                if limit > 1000:
                    items.append("... (Load more logic needed for full list)")
                    break
            self.model_combo.addItems(items)
        else:
            self.model_combo.addItem("No Models Loaded")

    def generate_sql(self):
        entry = self.entry_spin.value()
        name = self.name_edit.text()
        subname = self.subname_edit.text()
        
        # Parse Model ID from combo string "[ID] ..."
        model_text = self.model_combo.currentText()
        model_id = 0
        if model_text.startswith("["):
            try:
                # Assuming format "[DisplayID] Model ModelID" ?? 
                # Wait, DBCParser returns {id: model_id}. The Key is CreatureDisplayInfo ID (which goes into creature_template.modelid1/2/3/4)
                # The Value is ModelID (m2 file reference).
                # creature_template.modelid1 expects the Display ID.
                # So we just need the ID from the start of the string.
                model_id = int(model_text.split("]")[0].strip("["))
            except ValueError:
                pass
        
        # Parse Faction ID
        faction_text = self.faction_combo.currentText()
        faction_id = 35 # Default friendly
        if faction_text.startswith("["):
             try:
                faction_id = int(faction_text.split("]")[0].strip("["))
             except ValueError:
                pass
        
        level = self.level_spin.value()
        # Rank mapping: 0=Normal, 1=Elite, 2=Rare Elite, 3=World Boss, 4=Rare
        # We index directly from combo box index since we added them in order
        rank = self.rank_combo.currentIndex()
        if rank > 4: rank = 0 # Safety
        
        hp_mod = self.hp_mod_spin.value()
        
        # Default Flags (Hardcoded for now as per minimal UI)
        npc_flag = 1 # Gossip?
        unit_class = 1 # Warrior default
        
        sql = f"""-- [NPC] {entry} - {name}
DELETE FROM `creature_template` WHERE `entry` = {entry};
INSERT INTO `creature_template`
(`entry`, `modelid1`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `npcflag`, `unit_class`, `rank`, `HealthModifier`)
VALUES
({entry}, {model_id}, '{name}', '{subname}', {level}, {level}, {faction_id}, {npc_flag}, {unit_class}, {rank}, {hp_mod});"""

        self.preview_text.setText(sql)
