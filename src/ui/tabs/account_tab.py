from src.ui.components.base_manager import BaseManagerTab
from PySide6.QtWidgets import QPushButton, QTableWidgetItem, QAbstractItemView, QHeaderView, QMessageBox
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt, Signal
from datetime import datetime, timedelta
from src.ui.editors.account_editor import AccountEditorDialog

try:
    import mysql.connector
except ImportError:
    mysql = None

class AccountTab(BaseManagerTab):
    update_signal = Signal(list)

    def __init__(self, config_manager, parent=None):
        self.config_manager = config_manager
        super().__init__("Accounts", parent)
        self.customize_ui()
        
        self.update_signal.connect(self.update_table)
        self.db_manager = None 
        
        # Initial search to populate table
        self.on_search()

    def customize_ui(self):
        self.new_btn.setVisible(False) # Registration is usually external
        
        # Setup Table
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Access", "Joindate", "Total Time", "Email", "Banned", "Muted"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True) # Enable Sorting
        
        # Adjust specific column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Access
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents) # Banned
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents) # Muted
        
        # Connections
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

    def on_row_double_clicked(self, row, col):
        # Triggered by cellDoubleClicked(row, column)
        acc_id = self.table.item(row, 0).text()
        username = self.table.item(row, 1).text()
        
        editor = AccountEditorDialog(acc_id, username, self.config_manager, self)
        editor.exec()
        
        # Refresh after close
        self.on_search()

    def on_search(self):
        search_text = self.search_input.text().strip()
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        
        bots_enabled = realm.get("playerbots_enabled", False)
        bot_prefix = realm.get("bot_prefix", "bot").strip()
        
        char_db = realm.get("db_chars_name", "acore_characters")
        realm_id = realm.get("id", 1)

        if not mysql:
            print("MySQL not installed")
            return

        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor()
            
            # Construct Complex Query
            # Using f-string for char_db table name injection (safe since it comes from config)
            query = f"""
                SELECT
                  a.id, 
                  a.username, 
                  a.email, 
                  a.joindate,
                  MAX(COALESCE(aa.gmlevel, 0)) as access_level,
                  (SELECT COUNT(*) FROM account_banned ab WHERE ab.id = a.id AND ab.active = 1) as is_banned,
                  (SELECT COUNT(*) FROM account_muted am WHERE am.guid = a.id AND (am.mutedate + am.mutetime * 60) > UNIX_TIMESTAMP()) as is_muted,
                  (SELECT COALESCE(SUM(totaltime), 0) FROM {char_db}.characters c WHERE c.account = a.id) as total_played_time
                FROM account a
                LEFT JOIN account_access aa ON a.id = aa.id AND (aa.RealmID = -1 OR aa.RealmID = %s)
                WHERE a.username LIKE %s
            """
            
            params = [realm_id, f"%{search_text}%"]
            
            # Bot Exclusion
            if bots_enabled and bot_prefix:
                query += " AND a.username NOT LIKE %s"
                params.append(f"{bot_prefix}%")
                
            query += " GROUP BY a.id ORDER BY a.id ASC LIMIT 50"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            
            self.update_signal.emit(rows)
                
        except mysql.connector.Error as e:
            print(f"Account Search Error: {e}")

    def update_table(self, rows):
        self.table.setSortingEnabled(False) # Disable sorting during insert
        self.table.setRowCount(0)
        for row in rows:
            r_idx = self.table.rowCount()
            self.table.insertRow(r_idx)
            
            # Unpack Row
            # 0:id, 1:user, 2:email, 3:joined, 4:access, 5:banned, 6:muted, 7:totaltime
            acc_id, user, email, joined, access, banned, muted, total_time = row
            
            # 0. ID
            # Use setData for proper numerical sorting if desired, but string is default behavior here
            item_id = QTableWidgetItem(str(acc_id))
            item_id.setData(Qt.UserRole, acc_id) # Store value for potential custom sort
            self.table.setItem(r_idx, 0, item_id)
            
            # 1. Username
            self.table.setItem(r_idx, 1, QTableWidgetItem(str(user)))
            
            # 2. Access Level
            access_str = "Player"
            access_color = None
            if access > 0:
                access_str = f"GM (Lv{access})"
                if access >= 3:
                    access_color = QColor("#ff9800") # Admin Gold
                else:
                    access_color = QColor("#2196f3") # GM Blue
            
            item_access = QTableWidgetItem(access_str)
            if access_color:
                item_access.setForeground(QBrush(access_color))
            self.table.setItem(r_idx, 2, item_access)
            
            # 3. Joindate
            join_str = str(joined).split()[0] # Fallback
            if isinstance(joined, datetime):
                 join_str = joined.strftime("%Y-%m-%d")
            self.table.setItem(r_idx, 3, QTableWidgetItem(join_str))

            # 4. Total Time
            time_str = self.format_seconds(total_time)
            self.table.setItem(r_idx, 4, QTableWidgetItem(time_str))

            # 5. Email
            self.table.setItem(r_idx, 5, QTableWidgetItem(str(email)))
            
            # 6. Banned
            banned_str = "YES" if banned > 0 else "No"
            item_banned = QTableWidgetItem(banned_str)
            if banned > 0:
                item_banned.setForeground(QBrush(QColor("#f44336"))) # Red
            self.table.setItem(r_idx, 6, item_banned)
            
            # 7. Muted
            muted_str = "YES" if muted > 0 else "No"
            item_muted = QTableWidgetItem(muted_str)
            if muted > 0:
                item_muted.setForeground(QBrush(QColor("#f44336"))) # Red
            self.table.setItem(r_idx, 7, item_muted)
        
        self.table.setSortingEnabled(True) # Re-enable sorting
        self.table.sortItems(1, Qt.AscendingOrder) # Sort by Username

    def format_seconds(self, seconds):
        if not seconds: return "0h 0m"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"



    def get_expansion_name(self, exp_id):
        if exp_id == 0: return "Classic"
        if exp_id == 1: return "TBC"
        if exp_id == 2: return "WotLK"
        if exp_id == 3: return "Cata"
        return str(exp_id)
