from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                               QLineEdit, QComboBox, QPushButton, QTableWidget, QHeaderView, 
                               QMessageBox, QInputDialog, QGroupBox, QWidget, QAbstractItemView, QTableWidgetItem,
                               QSpinBox, QCheckBox)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt
from src.core.server_controller import ServerController
from src.utils.game_constants import RACE_MAP, CLASS_MAP
from datetime import datetime

try:
    import mysql.connector
except ImportError:
    mysql = None

class DurationDialog(QDialog):
    def __init__(self, mode="BAN", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(f"{mode.title()} Duration")
        self.resize(300, 200)
        self.result_duration = None
        self.result_reason = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Duration Section
        dur_group = QGroupBox("Duration")
        dur_layout = QGridLayout()
        
        self.perm_check = None
        
        if self.mode == "BAN":
            self.perm_check = QCheckBox("Permanent Ban")
            self.perm_check.toggled.connect(self.toggle_perm)
            dur_layout.addWidget(self.perm_check, 0, 0, 1, 2)
            
            dur_layout.addWidget(QLabel("Days:"), 1, 0)
            self.days_spin = QSpinBox()
            self.days_spin.setRange(0, 3650)
            dur_layout.addWidget(self.days_spin, 1, 1)
            
            dur_layout.addWidget(QLabel("Hours:"), 2, 0)
            self.hours_spin = QSpinBox()
            self.hours_spin.setRange(0, 23)
            dur_layout.addWidget(self.hours_spin, 2, 1)
            
            dur_layout.addWidget(QLabel("Minutes:"), 3, 0)
            self.mins_spin = QSpinBox()
            self.mins_spin.setRange(0, 59)
            dur_layout.addWidget(self.mins_spin, 3, 1)
            
        else: # MUTE
            dur_layout.addWidget(QLabel("Minutes:"), 0, 0)
            self.mins_spin = QSpinBox()
            self.mins_spin.setRange(1, 525600) # 1 year max
            self.mins_spin.setValue(60)
            dur_layout.addWidget(self.mins_spin, 0, 1)

        dur_group.setLayout(dur_layout)
        layout.addWidget(dur_group)
        
        # Reason Section
        layout.addWidget(QLabel("Reason:"))
        self.reason_edit = QLineEdit()
        layout.addWidget(self.reason_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Confirm")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def toggle_perm(self):
        enabled = not self.perm_check.isChecked()
        self.days_spin.setEnabled(enabled)
        self.hours_spin.setEnabled(enabled)
        self.mins_spin.setEnabled(enabled)

    def get_data(self):
        reason = self.reason_edit.text().strip()
        if not reason: reason = "No reason provided"
        
        if self.mode == "BAN":
            if self.perm_check.isChecked():
                return "-1", reason
            
            d = self.days_spin.value()
            h = self.hours_spin.value()
            m = self.mins_spin.value()
            
            if d == 0 and h == 0 and m == 0:
                # Default to something if user left all 0, maybe 1h? Or prevent?
                # For now let's default to perm if 0 to avoid syntax error, or just 10m
                return "-1", reason 
            
            timestring = ""
            if d > 0: timestring += f"{d}d"
            if h > 0: timestring += f"{h}h"
            if m > 0: timestring += f"{m}m"
            return timestring, reason
            
        else: # MUTE
            minutes = self.mins_spin.value()
            return str(minutes), reason

class AccountEditorDialog(QDialog):
    def __init__(self, account_id, account_name, config_manager, parent=None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.config_manager = config_manager
        self.controller = ServerController()
        
        self.setWindowTitle(f"Manage Account: {account_name} (ID: {account_id})")
        self.resize(900, 700)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Top: Identity & Metrics ---
        top_layout = QHBoxLayout()
        
        # Section A: Identity
        identity_group = QGroupBox("Identity")
        identity_layout = QGridLayout()
        
        identity_layout.addWidget(QLabel("Username:"), 0, 0)
        self.user_lbl = QLineEdit(self.account_name)
        self.user_lbl.setReadOnly(True)
        identity_layout.addWidget(self.user_lbl, 0, 1)
        
        identity_layout.addWidget(QLabel("Email:"), 1, 0)
        self.email_edit = QLineEdit()
        identity_layout.addWidget(self.email_edit, 1, 1)
        
        identity_layout.addWidget(QLabel("GM Level:"), 2, 0)
        self.gm_combo = QComboBox()
        self.gm_combo.addItems(["0 - Player", "1 - Moderator", "2 - Gamemaster", "3 - Admin"])
        identity_layout.addWidget(self.gm_combo, 2, 1)
        
        self.save_btn = QPushButton("Save Details")
        self.save_btn.clicked.connect(self.save_details)
        identity_layout.addWidget(self.save_btn, 3, 0, 1, 2)
        
        identity_group.setLayout(identity_layout)
        top_layout.addWidget(identity_group)
        
        # Section B: Metrics
        metrics_group = QGroupBox("Metrics")
        metrics_layout = QGridLayout()
        
        metrics_layout.addWidget(QLabel("Join Date:"), 0, 0)
        self.join_lbl = QLabel("-")
        metrics_layout.addWidget(self.join_lbl, 0, 1)
        
        metrics_layout.addWidget(QLabel("Last IP:"), 1, 0)
        self.ip_lbl = QLabel("-")
        metrics_layout.addWidget(self.ip_lbl, 1, 1)
        
        metrics_layout.addWidget(QLabel("OS / Locale:"), 2, 0)
        self.os_lbl = QLabel("-")
        metrics_layout.addWidget(self.os_lbl, 2, 1)
        
        metrics_layout.addWidget(QLabel("Total Play Time:"), 3, 0)
        self.time_lbl = QLabel("-")
        metrics_layout.addWidget(self.time_lbl, 3, 1)
        
        metrics_group.setLayout(metrics_layout)
        top_layout.addWidget(metrics_group)
        
        main_layout.addLayout(top_layout)
        
        # --- Middle: Status ---
        status_group = QGroupBox("Account Status")
        status_layout = QHBoxLayout()
        
        # Ban Status
        self.ban_lbl = QLabel("BANNED")
        self.ban_lbl.setAlignment(Qt.AlignCenter)
        self.ban_lbl.setFixedSize(100, 30)
        self.update_status_label(self.ban_lbl, False) # Default Green
        
        self.ban_btn = QPushButton("Ban Account")
        self.ban_btn.clicked.connect(self.toggle_ban)
        
        status_layout.addWidget(QLabel("Ban Status:"))
        status_layout.addWidget(self.ban_lbl)
        status_layout.addWidget(self.ban_btn)
        
        status_layout.addSpacing(40)
        
        # Mute Status
        self.mute_lbl = QLabel("MUTED")
        self.mute_lbl.setAlignment(Qt.AlignCenter)
        self.mute_lbl.setFixedSize(100, 30)
        self.update_status_label(self.mute_lbl, False)
        
        self.mute_btn = QPushButton("Mute Account")
        self.mute_btn.clicked.connect(self.toggle_mute)
        
        status_layout.addWidget(QLabel("Mute Status:"))
        status_layout.addWidget(self.mute_lbl)
        status_layout.addWidget(self.mute_btn)
        
        status_layout.addStretch()
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # --- Bottom: Characters ---
        char_group = QGroupBox("Characters")
        char_layout = QVBoxLayout()
        
        self.char_table = QTableWidget()
        self.char_table.setColumnCount(5)
        self.char_table.setHorizontalHeaderLabels(["Name", "Level", "Race", "Class", "Online"])
        self.char_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.char_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.char_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        char_layout.addWidget(self.char_table)
        
        char_group.setLayout(char_layout)
        main_layout.addWidget(char_group)
        
        # --- Footer: Danger Zone ---
        footer_layout = QHBoxLayout()
        self.delete_btn = QPushButton("DELETE USER PERMANENTLY")
        self.delete_btn.setStyleSheet("background-color: #b71c1c; color: white; font-weight: bold; padding: 10px;")
        self.delete_btn.clicked.connect(self.delete_account)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.delete_btn)
        main_layout.addLayout(footer_layout)

    def update_status_label(self, label, is_active):
        if is_active:
            label.setText("YES")
            label.setStyleSheet("background-color: #f44336; color: white; border-radius: 4px; font-weight: bold;")
        else:
            label.setText("NO")
            label.setStyleSheet("background-color: #4caf50; color: white; border-radius: 4px; font-weight: bold;")

    def load_data(self):
        if not mysql: return
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        char_db = realm.get("db_chars_name", "acore_characters")
        
        self.is_banned = False
        self.is_muted = False
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor(dictionary=True)
            
            # 1. Identity & Metrics
            # Trying to get 'os' column, might not exist in old cores. Fallback gracefully.
            try:
                cursor.execute("SELECT email, joindate, last_ip, locale, os FROM account WHERE id = %s", (self.account_id,))
            except mysql.connector.Error:
                # Fallback without 'os'
                cursor.execute("SELECT email, joindate, last_ip, locale FROM account WHERE id = %s", (self.account_id,))
                
            acc_data = cursor.fetchone()
            if acc_data:
                self.email_edit.setText(acc_data.get('email', ''))
                self.join_lbl.setText(str(acc_data.get('joindate', '-')))
                self.ip_lbl.setText(acc_data.get('last_ip', '-'))
                
                locale_id = acc_data.get('locale', 0)
                os_code = acc_data.get('os', '?')
                self.os_lbl.setText(f"{os_code} (Locale: {locale_id})")
                
            # 2. GM Level
            # access table usually: id, gmlevel, RealmID
            cursor.execute("SELECT gmlevel FROM account_access WHERE id = %s AND (RealmID = -1 OR RealmID = %s) ORDER BY gmlevel DESC LIMIT 1", (self.account_id, realm.get('id', 1)))
            access_row = cursor.fetchone()
            level = access_row['gmlevel'] if access_row else 0
            if level > 3: level = 3 # Clamp
            self.gm_combo.setCurrentIndex(level)
            
            # 3. Status (Banned/Muted)
            cursor.execute("SELECT COUNT(*) as cnt FROM account_banned WHERE id = %s AND active = 1", (self.account_id,))
            self.is_banned = cursor.fetchone()['cnt'] > 0
            
            cursor.execute("SELECT COUNT(*) as cnt FROM account_muted WHERE guid = %s AND (mutedate + mutetime * 60) > UNIX_TIMESTAMP()", (self.account_id,))
            self.is_muted = cursor.fetchone()['cnt'] > 0
            
            self.update_status_interface()
            
            # 4. Total Play Time (From Char DB)
            cursor.execute(f"SELECT SUM(totaltime) as total FROM {char_db}.characters WHERE account = %s", (self.account_id,))
            row = cursor.fetchone()
            total_time = row['total'] if row and row['total'] else 0
            self.time_lbl.setText(self.format_seconds(total_time))
            
            # 5. Characters List
            cursor.execute(f"SELECT name, race, class, level, online FROM {char_db}.characters WHERE account = %s", (self.account_id,))
            self.characters_data = cursor.fetchall()
            
            self.char_table.setRowCount(0)
            for char in self.characters_data:
                r = self.char_table.rowCount()
                self.char_table.insertRow(r)
                self.char_table.setItem(r, 0, QTableWidgetItem(char['name']))
                self.char_table.setItem(r, 1, QTableWidgetItem(str(char['level'])))
                
                race_name = RACE_MAP.get(char['race'], f"Unknown ({char['race']})")
                self.char_table.setItem(r, 2, QTableWidgetItem(race_name))
                
                class_name = CLASS_MAP.get(char['class'], f"Unknown ({char['class']})")
                self.char_table.setItem(r, 3, QTableWidgetItem(class_name))
                
                online = "Online" if char['online'] else "Offline"
                item_online = QTableWidgetItem(online)
                if char['online']:
                    item_online.setForeground(QBrush(QColor("#4caf50")))
                self.char_table.setItem(r, 4, item_online)

            conn.close()
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "DB Error", str(e))

    def update_status_interface(self):
        self.update_status_label(self.ban_lbl, self.is_banned)
        self.ban_btn.setText("Unban Account" if self.is_banned else "Ban Account")
        
        self.update_status_label(self.mute_lbl, self.is_muted)
        self.mute_btn.setText("Unmute Account" if self.is_muted else "Mute Account")

    def save_details(self):
        # Update Email and GM Level via SQL
        new_email = self.email_edit.text().strip()
        new_level = self.gm_combo.currentIndex()
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        
        try:
            conn = mysql.connector.connect(**{k:v for k,v in auth_config.items() if k != 'db_name'}, database=auth_config.get('db_name'))
            cursor = conn.cursor()
            
            # Update Email
            cursor.execute("UPDATE account SET email = %s WHERE id = %s", (new_email, self.account_id))
            
            # Update GM Level
            # Delete old entry first to ensure cleanliness
            cursor.execute("DELETE FROM account_access WHERE id = %s AND (RealmID = -1 OR RealmID = %s)", (self.account_id, realm.get('id', 1)))
            if new_level > 0:
                cursor.execute("INSERT INTO account_access (id, gmlevel, RealmID) VALUES (%s, %s, %s)", (self.account_id, new_level, realm.get('id', 1)))
                
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Saved", "Account details updated successfully.")
            
            # Reload to confirm
            self.load_data()
            
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def toggle_ban(self):
        realm = self.config_manager.get_active_realm()
        self.controller.set_connection_info(realm.get('soap_port'), realm.get('soap_user'), realm.get('soap_pass'))
        
        if self.is_banned:
            # Unban
            if QMessageBox.question(self, "Unban", f"Unban {self.account_name}?") == QMessageBox.Yes:
                resp = self.controller.send_soap_command(f".unban account {self.account_name}")
                QMessageBox.information(self, "Result", resp)
                self.load_data()
        else:
            # Ban with Custom Duration
            dlg = DurationDialog("BAN", self)
            if dlg.exec():
                duration, reason = dlg.get_data()
                cmd = f".ban account {self.account_name} {duration} {reason}"
                resp = self.controller.send_soap_command(cmd)
                QMessageBox.information(self, "Result", resp)
                self.load_data()

    def toggle_mute(self):
        realm = self.config_manager.get_active_realm()
        self.controller.set_connection_info(realm.get('soap_port'), realm.get('soap_user'), realm.get('soap_pass'))
        
        if not self.characters_data:
            QMessageBox.warning(self, "Warning", "This account has no characters. Mute command requires a character name.")
            return

        success_count = 0
        fail_count = 0
        last_msg = ""

        if self.is_muted:
            if QMessageBox.question(self, "Unmute", f"Unmute all characters on {self.account_name}?") == QMessageBox.Yes:
                for char in self.characters_data:
                    name = char['name']
                    resp = self.controller.send_soap_command(f".unmute {name}")
                    if "Player not found" not in resp and "Error" not in resp:
                        success_count += 1
                    else:
                        fail_count += 1
                        last_msg = resp
                
                # Manual DB Cleanup (Force remove from account_muted)
                try:
                    auth_config = self.config_manager.config.get("auth_database", {})
                    conn = mysql.connector.connect(**{k:v for k,v in auth_config.items() if k != 'db_name'}, database=auth_config.get('db_name'))
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM account_muted WHERE guid = %s", (self.account_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Error cleaning up account_muted: {e}")

                msg = f"Unmuted {success_count} characters.\nDatabase status stuck cleared."
                if fail_count > 0:
                    msg += f"\nFailed: {fail_count} (Last error: {last_msg})"
                QMessageBox.information(self, "Result", msg)
                self.load_data()
        else:
            # Mute with Custom Duration
            dlg = DurationDialog("MUTE", self)
            if dlg.exec():
                duration, reason = dlg.get_data() # duration is minutes string, reason is string
                
                for char in self.characters_data:
                    name = char['name']
                    # .mute <name> <minutes> <reason>
                    resp = self.controller.send_soap_command(f".mute {name} {duration} {reason}")
                    if "Player not found" not in resp and "Error" not in resp:
                        success_count += 1
                    else:
                        fail_count += 1
                        last_msg = resp
                
                msg = f"Muted {success_count} characters."
                if fail_count > 0:
                    msg += f"\nFailed: {fail_count} (Last error: {last_msg})"
                QMessageBox.information(self, "Result", msg)
                self.load_data()

    def delete_account(self):
        confirm = QMessageBox.warning(self, "DELETE ACCOUNT", 
                                      f"Are you sure you want to DELETE {self.account_name}?\n\nThis is PERMANENT and will delete all characters.",
                                      QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            realm = self.config_manager.get_active_realm()
            self.controller.set_connection_info(realm.get('soap_port'), realm.get('soap_user'), realm.get('soap_pass'))
            
            resp = self.controller.send_soap_command(f".account delete {self.account_name}")
            QMessageBox.information(self, "Result", resp)
            self.close()

    def format_seconds(self, seconds):
        if not seconds: return "0h 0m"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
