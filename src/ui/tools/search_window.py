from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QAbstractItemView, QLabel, QSpinBox)
from PySide6.QtCore import Qt, Signal

try:
    import mysql.connector
except ImportError:
    mysql = None

class SearchWindow(QDialog):
    selection_confirmed = Signal(dict)

    def __init__(self, config_manager, table_name, is_picker=True, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.table_name = table_name
        self.is_picker = is_picker
        
        self.setWindowTitle(f"Search: {table_name}")
        self.resize(600, 500)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"Search {self.table_name} by name...")
        self.search_input.returnPressed.connect(self.on_search)
        
        # Level Filters (Visible only for creatures)
        self.lvl_layout = QHBoxLayout()
        self.min_lvl = QSpinBox()
        self.min_lvl.setRange(0, 100) # 0 means ignore? Or just use value
        self.min_lvl.setValue(0)
        self.min_lvl.setSpecialValueText("Min")
        
        self.max_lvl = QSpinBox()
        self.max_lvl.setRange(0, 100)
        self.max_lvl.setValue(100)
        self.max_lvl.setSpecialValueText("Max") # Maybe not needed if 100
        
        # Only add if creature_template
        if self.table_name == "creature_template":
            self.lvl_layout.addWidget(QLabel("Lvl:"))
            self.lvl_layout.addWidget(self.min_lvl)
            self.lvl_layout.addWidget(QLabel("-"))
            self.lvl_layout.addWidget(self.max_lvl)
            search_layout.addLayout(self.lvl_layout)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.on_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Results Table
        self.table = QTableWidget()
        cols = ["ID", "Name"]
        if self.table_name == "creature_template":
            cols.append("Level")
            
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        
        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if self.is_picker:
            self.select_btn = QPushButton("Select")
            self.select_btn.clicked.connect(self.on_select)
            self.select_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            btn_layout.addWidget(self.select_btn)
            
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)

    def on_search(self):
        term = self.search_input.text().strip()
        if not term:
            return
            
        auth_config = self.config_manager.config.get("auth_database", {})
        # We need world db name
        realm = self.config_manager.get_active_realm()
        world_db = realm.get("db_world_name", "acore_world")
        
        if not mysql:
            return
            
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=world_db # Connect directly to world DB if possible, or use world_db.table syntax
            )
            cursor = conn.cursor()
            
            # Simple query - adjust limit as needed
            # Query Generation
            where_clause = "WHERE name LIKE %s"
            params = [f"%{term}%"]
            
            select_cols = "entry, name"
            
            if self.table_name == "creature_template":
                select_cols += ", minlevel, maxlevel"
                
                # Min Level
                if self.min_lvl.value() > 0:
                    where_clause += " AND minlevel >= %s"
                    params.append(self.min_lvl.value())
                    
                # Max Level (if not default max)
                if self.max_lvl.value() < 100:
                    where_clause += " AND maxlevel <= %s"
                    params.append(self.max_lvl.value())

            query = f"SELECT {select_cols} FROM {self.table_name} {where_clause} LIMIT 50"
            cursor.execute(query, tuple(params))
            
            rows = cursor.fetchall()
            conn.close()
            
            self.populate_table(rows)
            
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def populate_table(self, rows):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            id_item = QTableWidgetItem(str(row[0]))
            id_item.setData(Qt.UserRole, row[0])
            self.table.setItem(r, 0, id_item)
            
            name_item = QTableWidgetItem(str(row[1]))
            self.table.setItem(r, 1, name_item)
            
            # Level Column (Creatures Only)
            if self.table_name == "creature_template" and len(row) >= 4:
                min_l = row[2]
                max_l = row[3]
                lvl_str = f"{min_l}" if min_l == max_l else f"{min_l}-{max_l}"
                self.table.setItem(r, 2, QTableWidgetItem(lvl_str))

    def on_select(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        entry = self.table.item(row, 0).data(Qt.UserRole)
        name = self.table.item(row, 1).text()
        
        data = {"entry": entry, "name": name}
        self.selection_confirmed.emit(data)
        
        if self.is_picker:
            self.accept()
