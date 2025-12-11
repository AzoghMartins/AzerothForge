from src.ui.components.base_manager import BaseManagerTab
from PySide6.QtWidgets import (QPushButton, QTableWidgetItem, QAbstractItemView, QHeaderView, 
                               QMessageBox, QInputDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from src.utils.game_constants import ITEM_QUALITY_COLORS
from src.core.server_controller import ServerController
from src.ui.components.character_selector import CharacterSelectorDialog

try:
    import mysql.connector
except ImportError:
    mysql = None

class ItemTab(BaseManagerTab):
    update_signal = Signal(list)

    def __init__(self, config_manager, parent=None):
        self.config_manager = config_manager
        super().__init__("Items", parent)
        self.customize_ui()
        
        self.update_signal.connect(self.update_table)
        
        # Initial search
        self.on_search()

    def on_realm_changed(self):
        super().on_realm_changed()
        self.on_search()

    def customize_ui(self):
        # Hide default buttons we don't use yet
        self.new_btn.setVisible(False)
        self.edit_btn.setVisible(False)
        self.delete_btn.setVisible(False)
        
        # Columns: Entry ID, Name, iLvl, Req Lvl, Class/SubClass
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Entry ID", "Name", "iLvl", "Req Lvl", "Class/SubClass"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Resize Entry ID column to contents
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        # Actions
        self.send_btn = QPushButton("Send to Player...")
        self.send_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.send_btn.clicked.connect(self.on_send_item)
        self.action_layout.addWidget(self.send_btn)

    def on_search(self):
        search_text = self.search_input.text().strip()
        
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        world_db = realm.get("db_world_name", "acore_world")
        
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
            
            # Query item_template
            # Columns: entry, name, Quality, ItemLevel, RequiredLevel, class, subclass
            query = f"""
                SELECT entry, name, Quality, ItemLevel, RequiredLevel, class, subclass
                FROM {world_db}.item_template
                WHERE name LIKE %s
                LIMIT 100
            """
            
            params = [f"%{search_text}%"]
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            
            self.update_signal.emit(rows)
            
        except mysql.connector.Error as e:
            print(f"Item Search Error: {e}")

    def update_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            # entry, name, Quality, ItemLevel, RequiredLevel, class, subclass
            entry, name, quality, ilvl, req_lvl, cls, subcls = row
            
            # 0. Entry ID
            item_id = QTableWidgetItem(str(entry))
            item_id.setData(Qt.UserRole, entry)
            self.table.setItem(r, 0, item_id)
            
            # 1. Name (Colored by Quality)
            name_item = QTableWidgetItem(str(name))
            color_hex = ITEM_QUALITY_COLORS.get(quality, "#ffffff")
            name_item.setForeground(QBrush(QColor(color_hex)))
            self.table.setItem(r, 1, name_item)
            
            # 2. iLvl
            self.table.setItem(r, 2, QTableWidgetItem(str(ilvl)))
            
            # 3. Req Lvl
            self.table.setItem(r, 3, QTableWidgetItem(str(req_lvl)))
            
            # 4. Class/SubClass
            # Displaying as integers for now per requirements
            self.table.setItem(r, 4, QTableWidgetItem(f"{cls} / {subcls}"))

        self.table.setSortingEnabled(True)

    def on_send_item(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection", "Please select an item first.")
            return
            
        # Get Item ID (stored in column 0 via UserRole or text)
        row = selected[0].row()
        item_id_item = self.table.item(row, 0)
        item_id = item_id_item.data(Qt.UserRole) # Prefer data if set, otherwise text
        
        if not item_id:
             item_id = item_id_item.text()

        item_name = self.table.item(row, 1).text()

        item_name = self.table.item(row, 1).text()

        # Open Character Selector Dialog
        dialog = CharacterSelectorDialog(self.config_manager, self)
        if dialog.exec():
            char_name = dialog.get_selected_character()
            if char_name:
                self.send_soap_request(char_name, item_id)

    def send_soap_request(self, char_name, item_id):
        realm = self.config_manager.get_active_realm()
        
        sc = ServerController()
        sc.set_connection_info(
            realm.get("soap_port", 7878),
            realm.get("soap_user", "admin"),
            realm.get("soap_pass", "admin")
        )
        
        command = f'.send items {char_name} "GM Delivery" "Requested Item" {item_id}'
        response = sc.send_soap_command(command)
        
        QMessageBox.information(self, "Server Response", response)
