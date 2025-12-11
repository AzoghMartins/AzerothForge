from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, 
                               QTextEdit, QPushButton, QGroupBox, QLabel, QMessageBox)
from src.core.data_manager import DataManager
try:
    import mysql.connector
except ImportError:
    mysql = None

class NpcEditorDialog(QDialog):
    def __init__(self, parent=None, predefined_id=None, mode="insert", realm_config=None, allowed_id_range=None):
        super().__init__(parent)
        self.predefined_id = predefined_id
        self.mode = mode # 'insert' or 'update'
        self.realm_config = realm_config # Strict override
        self.allowed_id_range = allowed_id_range # (start, end) strict check for deletion
        self.data_manager = DataManager()
        self.init_ui()
        self.load_data() # Loads static data (factions etc)
        self.on_active_realm_changed()
        
        if self.mode == "update":
            self.setWindowTitle(f"Edit NPC: {predefined_id}")
            self.save_db_btn.setText("Update NPC")
            self.load_npc_data() # Load specific NPC data
        else:
            self.setWindowTitle("Create New NPC")
            self.save_db_btn.setText("Create NPC")

    def on_active_realm_changed(self):
        # Determine strict Realm
        if self.realm_config:
            realm = self.realm_config
        else:
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
        self.entry_spin.setValue(self.predefined_id if self.predefined_id else 50000)
        self.entry_spin.setPrefix("ID: ")
        if self.predefined_id:
            self.entry_spin.setReadOnly(True)
            self.entry_spin.setStyleSheet("background-color: #333; color: #888;")
        
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
        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        
        self.gen_btn = QPushButton("Generate SQL")
        self.gen_btn.clicked.connect(self.generate_sql)
        self.gen_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 12px;")
        
        self.delete_btn = QPushButton("Delete NPC")
        self.delete_btn.clicked.connect(self.delete_from_database)
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 12px;")
        if self.mode != "update":
            self.delete_btn.setVisible(False)
            
        self.save_db_btn = QPushButton("Save to Database")
        self.save_db_btn.clicked.connect(self.save_to_database)
        self.save_db_btn.setStyleSheet("background-color: #4caf50; color: white; font-weight: bold; padding: 12px;")
        # User requirement: "The NpcEditorDialog must be set to 'Insert Mode'... On Save: Insert into DB"
        # We'll make it visible always for now, or check connection.
        self.save_db_btn.setVisible(True)

        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.save_db_btn)
        main_layout.addLayout(btn_layout)
        
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

    def load_npc_data(self):
        if not self.predefined_id or not mysql:
            return

        from src.core.config_manager import ConfigManager
        cm = ConfigManager()
        # Strict override
        if self.realm_config:
            realm = self.realm_config
        else:
            realm = cm.get_active_realm()
            
        auth = cm.config.get("auth_database", {})

        try:
            conn = mysql.connector.connect(
                host=auth.get("host", "localhost"),
                port=auth.get("port", 3306),
                user=auth.get("user", "acore"),
                password=auth.get("password", "acore"),
                database=realm.get("db_world_name", "acore_world")
            )
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT * FROM creature_template WHERE entry = %s"
            cursor.execute(query, (self.predefined_id,))
            row = cursor.fetchone()
            
            # Fetch Model separately
            model_query = "SELECT CreatureDisplayID FROM creature_template_model WHERE CreatureID = %s LIMIT 1"
            cursor.execute(model_query, (self.predefined_id,))
            model_row = cursor.fetchone()
            
            conn.close()
            
            if row:
                self.name_edit.setText(row['name'])
                self.subname_edit.setText(row.get('subname', ''))
                self.level_spin.setValue(row['minlevel']) # Assuming min=max for now
                self.hp_mod_spin.setValue(row.get('HealthModifier', 1.0))
                
                # Faction
                fid = row.get('faction', 35)
                for i in range(self.faction_combo.count()):
                    if self.faction_combo.itemText(i).startswith(f"[{fid}]"):
                        self.faction_combo.setCurrentIndex(i)
                        break
                
                # Model
                mid = model_row['CreatureDisplayID'] if model_row else 0
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemText(i).startswith(f"[{mid}]"):
                        self.model_combo.setCurrentIndex(i)
                        break

                # Rank
                rank = row.get('rank', 0)
                if rank < self.rank_combo.count():
                    self.rank_combo.setCurrentIndex(rank)

        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Error Loading NPC", str(e))

    def get_generated_sql(self):
        # Refactored generation logic to return string
        entry = self.entry_spin.value()
        name = self.name_edit.text()
        subname = self.subname_edit.text()
        
        model_text = self.model_combo.currentText()
        model_id = 0
        if model_text.startswith("["):
            try:
                model_id = int(model_text.split("]")[0].strip("["))
            except ValueError:
                pass
        
        faction_text = self.faction_combo.currentText()
        faction_id = 35 
        if faction_text.startswith("["):
             try:
                faction_id = int(faction_text.split("]")[0].strip("["))
             except ValueError:
                pass
        
        level = self.level_spin.value()
        rank = self.rank_combo.currentIndex()
        if rank > 4: rank = 0
        
        hp_mod = self.hp_mod_spin.value()
        npc_flag = 1 
        unit_class = 1 
        
        # Escape strings
        name = name.replace("'", "''")
        subname = subname.replace("'", "''")

        if self.mode == "update":
            sql = f"""-- [NPC] {entry} - {name}
UPDATE `creature_template` SET
`name` = '{name}',
`subname` = '{subname}',
`minlevel` = {level},
`maxlevel` = {level},
`faction` = {faction_id},
`npcflag` = {npc_flag},
`unit_class` = {unit_class},
`rank` = {rank},
`HealthModifier` = {hp_mod}
WHERE `entry` = {entry};

-- Update Model (Delete & Insert safely)
DELETE FROM `creature_template_model` WHERE `CreatureID` = {entry};
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`) VALUES ({entry}, 0, {model_id}, 1.0, 1.0);"""
        else:
            sql = f"""DELETE FROM `creature_template` WHERE `entry` = {entry};
INSERT INTO `creature_template`
(`entry`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `npcflag`, `unit_class`, `rank`, `HealthModifier`)
VALUES
({entry}, '{name}', '{subname}', {level}, {level}, {faction_id}, {npc_flag}, {unit_class}, {rank}, {hp_mod});

-- Insert Model
DELETE FROM `creature_template_model` WHERE `CreatureID` = {entry};
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`) VALUES ({entry}, 0, {model_id}, 1.0, 1.0);"""
        return sql

    def generate_sql(self):
        sql = self.get_generated_sql()
        self.preview_text.setText(sql)

    def save_to_database(self):
        if not mysql:
            QMessageBox.critical(self, "Error", "MySQL connector not available.")
            return

        sql = self.get_generated_sql()
        
        # Get Config
        from src.core.config_manager import ConfigManager
        cm = ConfigManager()
        
        if self.realm_config:
            realm = self.realm_config
        else:
            realm = cm.get_active_realm()
            
        auth = cm.config.get("auth_database", {})
        
        # We need to connect to World DB, so we need config to allow that.
        # ConfigManager stores auth DB details. World DB host/user details are often same as Auth?
        # In this project structure, `auth_database` has host/user/pass, and `realms` has db names.
        # Assumption: World DB is on same host/user as Auth DB.
        
        try:
            conn = mysql.connector.connect(
                host=auth.get("host", "localhost"),
                port=auth.get("port", 3306),
                user=auth.get("user", "acore"),
                password=auth.get("password", "acore"),
                database=realm.get("db_world_name", "acore_world")
            )
            cursor = conn.cursor()
            
            # Executing multiple statements manually to avoid CMySQLCursor 'multi' argument issue
            # The generated SQL uses ';' as separator.
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for stmt in statements:
                cursor.execute(stmt)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", f"NPC {self.entry_spin.value()} saved to database!")
            self.accept()
            
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def delete_from_database(self):
        confirm = QMessageBox.question(self, "Confirm Deletion", 
                                     f"Are you sure you want to delete NPC {self.entry_spin.value()}?\nThis action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        if self.allowed_id_range:
             entry = self.entry_spin.value()
             start, end = self.allowed_id_range
             if not (start <= entry <= end):
                 QMessageBox.critical(self, "Safety Lock", f"Cannot delete NPC {entry}.\nIt is outside the campaign's allowed ID range ({start}-{end}).")
                 return

        if not mysql:
             QMessageBox.critical(self, "Error", "MySQL connector not available.")
             return

        # Get Config
        from src.core.config_manager import ConfigManager
        cm = ConfigManager()
        
        if self.realm_config:
            realm = self.realm_config
        else:
            realm = cm.get_active_realm()
            
        auth = cm.config.get("auth_database", {})
        
        try:
            conn = mysql.connector.connect(
                host=auth.get("host", "localhost"),
                port=auth.get("port", 3306),
                user=auth.get("user", "acore"),
                password=auth.get("password", "acore"),
                database=realm.get("db_world_name", "acore_world")
            )
            cursor = conn.cursor()
            
            entry = self.entry_spin.value()
            
            # Delete from both tables
            del_template = f"DELETE FROM creature_template WHERE entry = {entry}"
            del_model = f"DELETE FROM creature_template_model WHERE CreatureID = {entry}"
            
            cursor.execute(del_template)
            cursor.execute(del_model)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Deleted", f"NPC {entry} has been deleted.")
            self.accept() # Close and refresh
            
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", str(e))
