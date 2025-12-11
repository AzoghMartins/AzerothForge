from src.ui.components.base_manager import BaseManagerTab
from PySide6.QtWidgets import QPushButton, QTableWidgetItem, QAbstractItemView, QHeaderView, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from src.utils.game_constants import RACE_MAP, CLASS_MAP
from src.ui.editors.character_editor import CharacterEditorDialog
from datetime import datetime

try:
    import mysql.connector
except ImportError:
    mysql = None

class CharacterTab(BaseManagerTab):
    update_signal = Signal(list)

    def __init__(self, config_manager, parent=None):
        self.config_manager = config_manager
        super().__init__("Characters", parent)
        self.customize_ui()
        
        self.update_signal.connect(self.update_table)
        
        # Initial search
        self.on_search()

    def on_realm_changed(self):
        super().on_realm_changed()
        self.on_search()

    def customize_ui(self):
        self.new_btn.setVisible(False)
        
        # Columns: ID, Name, Account, Level, Race, Class
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Account", "Level", "Race", "Class"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Adjust some columns
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Level

        # Actions (Placeholder for now)
        self.kick_btn = QPushButton("Kick")
        self.tele_btn = QPushButton("Teleport")
        self.action_layout.insertWidget(2, self.kick_btn)
        self.action_layout.insertWidget(3, self.tele_btn)
        
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

    def on_row_double_clicked(self, row, col):
        self.open_editor(row)

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection", "Please select a character first.")
            return
        row = selected[0].row()
        self.open_editor(row)

    def open_editor(self, row):
        guid = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        
        editor = CharacterEditorDialog(guid, name, self.config_manager, self)
        editor.exec()
        self.on_search()

    def on_search(self):
        search_text = self.search_input.text().strip()
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        char_db = realm.get("db_chars_name", "acore_characters")
        
        bots_enabled = realm.get("playerbots_enabled", False)
        bot_prefix = realm.get("bot_prefix", "bot").strip()
        
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
            
            # Simple Join to get Account Name
            query = f"""
                SELECT c.guid, c.name, a.username, c.level, c.race, c.class
                FROM {char_db}.characters c
                JOIN account a ON c.account = a.id
                WHERE c.name LIKE %s
            """
            
            params = [f"%{search_text}%"]
            
            if bots_enabled and bot_prefix:
                query += " AND a.username NOT LIKE %s"
                params.append(f"{bot_prefix}%")
                
            query += " ORDER BY c.name ASC LIMIT 50"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            
            self.update_signal.emit(rows)
            
        except mysql.connector.Error as e:
            print(f"Character Search Error: {e}")

    def update_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            # guid, name, account, level, race, class
            guid, name, acc_name, level, race, cls = row
            
            # 0. ID
            item_id = QTableWidgetItem(str(guid))
            item_id.setData(Qt.UserRole, guid)
            self.table.setItem(r, 0, item_id)
            
            # 1. Name
            # Color by class? Maybe later.
            self.table.setItem(r, 1, QTableWidgetItem(str(name)))
            
            # 2. Account
            self.table.setItem(r, 2, QTableWidgetItem(str(acc_name)))
            
            # 3. Level
            item_lvl = QTableWidgetItem(str(level))
            item_lvl.setData(Qt.UserRole, level)
            self.table.setItem(r, 3, item_lvl)
            
            # 4. Race
            race_name = RACE_MAP.get(race, f"Unknown ({race})")
            self.table.setItem(r, 4, QTableWidgetItem(race_name))
            
            # 5. Class
            class_name = CLASS_MAP.get(cls, f"Unknown ({cls})")
            self.table.setItem(r, 5, QTableWidgetItem(class_name))

        self.table.setSortingEnabled(True)
        self.table.sortItems(1, Qt.AscendingOrder) # Sort by Name
