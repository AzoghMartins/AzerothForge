from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QTableWidget, 
                               QTableWidgetItem, QDialogButtonBox, QHeaderView, 
                               QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from src.utils.game_constants import RACE_MAP, CLASS_MAP

try:
    import mysql.connector
except ImportError:
    mysql = None

class CharacterSelectorDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.selected_name = None
        
        self.setWindowTitle("Select Character")
        self.resize(500, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search character by name...")
        layout.addWidget(self.search_input)
        
        # Debounce Timer
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.debounce_timer.start)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Level", "Race", "Class"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.table)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept_selection)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Initial load (optional, maybe top 50?)
        self.perform_search()

    def perform_search(self):
        search_text = self.search_input.text().strip()
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        char_db = realm.get("db_chars_name", "acore_characters")
        
        
        bots_enabled = realm.get("playerbots_enabled", False)
        bot_prefix = realm.get("bot_prefix", "bot").strip()
        
        if not mysql:
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
            
            query = f"""
                SELECT c.name, c.level, c.race, c.class
                FROM {char_db}.characters c
                JOIN account a ON c.account = a.id
                WHERE UPPER(c.name) LIKE %s
            """
            
            params = [f"%{search_text.upper()}%"]
            
            if bots_enabled and bot_prefix:
                query += " AND a.username NOT LIKE %s"
                params.append(f"{bot_prefix}%")
                
            query += " ORDER BY c.name ASC LIMIT 50"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            
            self.update_table(rows)
            
        except mysql.connector.Error as e:
            print(f"Character Search Error: {e}")

    def update_table(self, rows):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            name, level, race, cls = row
            
            self.table.setItem(r, 0, QTableWidgetItem(str(name)))
            self.table.setItem(r, 1, QTableWidgetItem(str(level)))
            
            race_name = RACE_MAP.get(race, str(race))
            self.table.setItem(r, 2, QTableWidgetItem(race_name))
            
            class_name = CLASS_MAP.get(cls, str(cls))
            self.table.setItem(r, 3, QTableWidgetItem(class_name))

    def accept_selection(self):
        selected = self.table.selectedItems()
        if not selected:
            # If nothing selected, maybe check if there is only one row?
            # Or just warn
            if self.table.rowCount() == 1:
                self.table.selectRow(0)
                selected = self.table.selectedItems()
            else:
                QMessageBox.warning(self, "Selection", "Please select a character.")
                return
        
        # Column 0 is Name
        row = selected[0].row()
        self.selected_name = self.table.item(row, 0).text()
        self.accept()

    def get_selected_character(self):
        return self.selected_name
