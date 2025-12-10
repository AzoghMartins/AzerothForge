from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QPushButton, QGroupBox, QGridLayout, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from src.core.server_controller import ServerController
from src.utils.game_constants import RACE_MAP, CLASS_MAP, TELEPORT_LOCATIONS, ALLIANCE_RACES, HORDE_RACES, PROGRESSION_TIERS
from src.core.data_manager import DataManager
from datetime import datetime, timedelta

try:
    import mysql.connector
except ImportError:
    mysql = None

class CharacterEditorDialog(QDialog):
    def __init__(self, guid, name, config_manager, parent=None):
        super().__init__(parent)
        self.guid = guid
        self.char_name = name
        self.config_manager = config_manager
        self.controller = ServerController()
        self.data_manager = DataManager()
        self.race_id = 0
        
        self.setWindowTitle(f"Character Editor: {self.char_name}")
        self.resize(600, 500)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Section A: Identity ---
        identity_group = QGroupBox("Identity")
        id_layout = QGridLayout()
        
        id_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit(self.char_name)
        self.name_edit.setReadOnly(True) # Rename uses special Logic
        id_layout.addWidget(self.name_edit, 0, 1)
        
        id_layout.addWidget(QLabel("Account:"), 0, 2)
        self.account_edit = QLineEdit()
        self.account_edit.setReadOnly(True)
        id_layout.addWidget(self.account_edit, 0, 3)
        
        id_layout.addWidget(QLabel("Level:"), 1, 0)
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 255)
        id_layout.addWidget(self.level_spin, 1, 1)
        
        self.save_lvl_btn = QPushButton("Set Level")
        self.save_lvl_btn.clicked.connect(self.set_level)
        id_layout.addWidget(self.save_lvl_btn, 1, 2)

        id_layout.addWidget(QLabel("Race:"), 2, 0)
        self.race_lbl = QLabel("Unknown")
        id_layout.addWidget(self.race_lbl, 2, 1)
        
        id_layout.addWidget(QLabel("Class:"), 2, 2)
        self.class_lbl = QLabel("Unknown")
        id_layout.addWidget(self.class_lbl, 2, 3)

        id_layout.addWidget(QLabel("Progression:"), 3, 0)
        self.tier_label = QLabel("Tier: Loading...")
        id_layout.addWidget(self.tier_label, 3, 1, 1, 3)
        
        identity_group.setLayout(id_layout)
        layout.addWidget(identity_group)
        
        # --- Section B: Metrics & Location ---
        metrics_group = QGroupBox("Status & Location")
        met_layout = QGridLayout()
        
        met_layout.addWidget(QLabel("Total Time:"), 0, 0)
        self.time_lbl = QLabel("0h 0m")
        met_layout.addWidget(self.time_lbl, 0, 1)
        
        met_layout.addWidget(QLabel("Status:"), 0, 2)
        self.online_lbl = QLabel("Offline")
        met_layout.addWidget(self.online_lbl, 0, 3)
        
        met_layout.addWidget(QLabel("Map:"), 1, 0)
        self.map_lbl = QLabel("Unknown")
        met_layout.addWidget(self.map_lbl, 1, 1, 1, 3)
        
        met_layout.addWidget(QLabel("Coords:"), 2, 0)
        self.coords_lbl = QLabel("X: 0 Y: 0 Z: 0")
        met_layout.addWidget(self.coords_lbl, 2, 1, 1, 3)
        
        metrics_group.setLayout(met_layout)
        layout.addWidget(metrics_group)
        
        # --- Section C: Commands ---
        cmd_group = QGroupBox("Command Center")
        cmd_layout = QGridLayout()
        
        # Row 0
        self.send_gold_btn = QPushButton("Send Gold")
        self.send_gold_btn.clicked.connect(self.send_gold)
        cmd_layout.addWidget(self.send_gold_btn, 0, 0)

        self.rename_btn = QPushButton("Force Rename")
        self.rename_btn.clicked.connect(self.force_rename)
        cmd_layout.addWidget(self.rename_btn, 0, 1)
        
        self.rename_btn = QPushButton("Force Rename")
        self.rename_btn.clicked.connect(self.force_rename)
        cmd_layout.addWidget(self.rename_btn, 0, 1)
        
        # Row 1
        self.revive_btn = QPushButton("Revive")
        self.revive_btn.clicked.connect(self.revive)
        cmd_layout.addWidget(self.revive_btn, 1, 0)
        
        self.kick_btn = QPushButton("Kick")
        self.kick_btn.clicked.connect(self.kick)
        self.kick_btn.setStyleSheet("background-color: #ff9800; color: white;")
        cmd_layout.addWidget(self.kick_btn, 1, 1)
        
        self.tele_btn = QPushButton("Kick & Teleport")
        self.tele_btn.clicked.connect(self.teleport)
        self.tele_btn.setStyleSheet("background-color: #2196f3; color: white;")
        cmd_layout.addWidget(self.tele_btn, 1, 2)

        cmd_group.setLayout(cmd_layout)
        layout.addWidget(cmd_group)

    def load_data(self):
        if not mysql: return
        
        realm = self.config_manager.get_active_realm()
        char_db = realm.get("db_chars_name", "acore_characters")
        auth_config = self.config_manager.config.get("auth_database", {})
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor(dictionary=True)
            
            # Query Character + Account Name
            query = f"""
                SELECT c.*, a.username 
                FROM {char_db}.characters c
                JOIN account a ON c.account = a.id
                WHERE c.guid = %s
            """
            cursor.execute(query, (self.guid,))
            row = cursor.fetchone()
            
            if not row:
                QMessageBox.critical(self, "Error", "Character not found!")
                self.close()
                return

            # Identity
            self.account_edit.setText(row['username'])
            self.level_spin.setValue(int(row['level']))
            
            self.race_id = row['race']
            r_id = row['race']
            c_id = row['class']
            self.race_lbl.setText(RACE_MAP.get(r_id, str(r_id)))
            self.class_lbl.setText(CLASS_MAP.get(c_id, str(c_id)))
            
            # Metrics
            total_time = row.get('totaltime', 0)
            self.time_lbl.setText(self.format_seconds(total_time))
            
            is_online = row.get('online', 0)
            self.online_lbl.setText("Online" if is_online else "Offline")
            self.online_lbl.setStyleSheet(f"color: {'#4caf50' if is_online else '#9e9e9e'}; font-weight: bold;")
            
            # Location
            map_id = row['map']
            x, y, z = row['position_x'], row['position_y'], row['position_z']
            map_name = self.data_manager.get_map_name(map_id)
            self.map_lbl.setText(f"{map_name} (ID: {map_id})")
            self.coords_lbl.setText(f"X: {x:.1f}  Y: {y:.1f}  Z: {z:.1f}")
            # DEBUG Query
            try:
                debug_query = f"SELECT source, data FROM {char_db}.character_settings WHERE guid = %s"
                cursor.execute(debug_query, (self.guid,))
                settings = cursor.fetchall()
                print(f"DEBUG SETTINGS for GUID {self.guid}: {settings}")
            except Exception as e:
                print(f"Debug Query Error: {e}")

            # Individual Progression Tier
            try:
                # Query character_settings for the module data
                tier_query = f"""
                    SELECT data FROM {char_db}.character_settings 
                    WHERE guid = %s AND (source = 'mod-individual-progression' OR source = 'individual-progression')
                """
                cursor.execute(tier_query, (self.guid,))
                tier_row = cursor.fetchone()
                
                if tier_row:
                    raw_data = tier_row['data'].strip()
                    try:
                        tier_level = int(raw_data.split()[0]) # distinct because "0 0 0..." like output possible 
                        # Actually data seems like "0 " based on debug output.
                        # safer: int(raw_data.split(' ')[0]) if space exists
                        # simpliest: int(raw_data) if it's just a number string?
                        # Debug output showed: '0 ' -> strip() gives '0' -> int('0') works.
                        
                        tier_level = int(raw_data)
                        objective = PROGRESSION_TIERS.get(tier_level, "Unknown Objective")
                        
                        if tier_level > 17:
                            self.tier_label.setText(f"Tier {tier_level}: Max Progression Reached")
                        else:
                            self.tier_label.setText(f"Tier {tier_level}: {objective}")
                    except ValueError:
                         self.tier_label.setText(f"Tier: {raw_data} (Parse Error)")

                else:
                    # Default is Tier 0
                    self.tier_label.setText(f"Tier 0: {PROGRESSION_TIERS.get(0, 'Default')}")
                    
            except Exception as e:
                # Table likely doesn't exist or other error
                self.tier_label.setText("Tier: N/A (Module Error)")
                print(f"Progression Tier Error: {e}")
            
            conn.close()

        except Exception as e:
            print(f"Error loading character: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")

    def format_seconds(self, seconds):
        if not seconds: return "0h 0m"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    # --- Actions ---
    
    def _send_soap(self, command):
        """Helper to send SOAP command to active realm"""
        realm = self.config_manager.get_active_realm()
        self.controller.set_connection_info(realm.get('soap_port'), realm.get('soap_user'), realm.get('soap_pass'))
        return self.controller.send_soap_command(command)

    def set_level(self):
        val = self.level_spin.value()
        resp = self._send_soap(f".character level {self.char_name} {val}")
        QMessageBox.information(self, "Result", resp)
        self.load_data()

    def send_gold(self):
        gold, ok = QInputDialog.getInt(self, "Send Gold", "Amount (Gold):", 100, 1, 999999)
        if ok:
            # Convert to copper? No, .send money usually takes gold or "100g" format depending on core.
            # AzerothCore .send money <name> "subject" "text" <amount>
            # Amount is usually in copper if just number, so multiply by 10000.
            copper = gold * 10000
            resp = self._send_soap(f'.send money {self.char_name} "GM Support" "Currency Adjustment" {copper}')
            QMessageBox.information(self, "Result", resp)
            
    def revive(self):
        resp = self._send_soap(f".revive {self.char_name}")
        QMessageBox.information(self, "Result", resp)
        
    def kick(self):
        if QMessageBox.question(self, "Confirm", f"Kick {self.char_name}?") == QMessageBox.Yes:
            resp = self._send_soap(f".kick {self.char_name}")
            QMessageBox.information(self, "Result", resp)
            self.load_data()
            
    def teleport(self):
        items = ["Hearthstone (Home)"]
        
        # Determine Faction logic
        is_alliance = self.race_id in ALLIANCE_RACES
        is_horde = self.race_id in HORDE_RACES
        
        # If unknown (0 or custom), show both
        show_all = not is_alliance and not is_horde
        
        if is_alliance or show_all:
            for city in TELEPORT_LOCATIONS['Alliance']:
                items.append(f"Alliance - {city}")
                
        if is_horde or show_all:
            for city in TELEPORT_LOCATIONS['Horde']:
                items.append(f"Horde - {city}")
                
        for city in TELEPORT_LOCATIONS['Neutral']:
            items.append(f"Neutral - {city}")
            
        dest, ok = QInputDialog.getItem(self, "Teleport", "Select Destination:", items, 0, False)
        if ok and dest:
            # 1. Kick
            self._send_soap(f".kick {self.char_name}")
            
            # 2. Wait and Finalize
            QTimer.singleShot(1000, lambda: self._finalize_teleport(dest))

    def _finalize_teleport(self, dest_str):
        try:
            realm = self.config_manager.get_active_realm()
            char_db = realm.get("db_chars_name", "acore_characters")
            auth_config = self.config_manager.config.get("auth_database", {})
            
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor()
            
            if "Hearthstone" in dest_str:
                # Update from character_homebind
                query = f"""
                    UPDATE {char_db}.characters c 
                    JOIN {char_db}.character_homebind h ON c.guid = h.guid 
                    SET c.position_x=h.position_x, c.position_y=h.position_y, c.position_z=h.position_z, c.map=h.map 
                    WHERE c.guid=%s
                """
                cursor.execute(query, (self.guid,))
            else:
                # Parse City
                # Format: "Faction - CityName"
                parts = dest_str.split(" - ")
                if len(parts) < 2: return
                city_name = parts[1]
                
                # Find coords
                coords = None
                for cat in TELEPORT_LOCATIONS:
                    if city_name in TELEPORT_LOCATIONS[cat]:
                        coords = TELEPORT_LOCATIONS[cat][city_name]
                        break
                
                if coords:
                    map_id, x, y, z = coords
                    query = f"UPDATE {char_db}.characters SET map=%s, position_x=%s, position_y=%s, position_z=%s WHERE guid=%s"
                    cursor.execute(query, (map_id, x, y, z, self.guid))
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Success", f"Character kicked and teleported to {dest_str}.")
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Teleport Error", str(e))

    def force_rename(self):
        if QMessageBox.question(self, "Confirm", "Force rename on next login?") == QMessageBox.Yes:
            try:
                # SQL Update
                realm = self.config_manager.get_active_realm()
                char_db = realm.get("db_chars_name", "acore_characters")
                auth_config = self.config_manager.config.get("auth_database", {})
                
                conn = mysql.connector.connect(
                    host=auth_config.get("host", "localhost"),
                    port=auth_config.get("port", 3306),
                    user=auth_config.get("user", "acore"),
                    password=auth_config.get("password", "acore"),
                    database=auth_config.get("db_name", "acore_auth")
                )
                cursor = conn.cursor()
                # at_login | 1 (AT_LOGIN_RENAME)
                cursor.execute(f"UPDATE {char_db}.characters SET at_login = at_login | 1 WHERE guid = %s", (self.guid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Flag set. User will be prompted to rename at next login.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Database Error: {e}")
