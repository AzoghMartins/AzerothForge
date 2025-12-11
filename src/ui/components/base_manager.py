from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QTableWidget, QHeaderView, QSpacerItem, QSizePolicy)
from PySide6.QtCore import QTimer

class BaseManagerTab(QWidget):
    def __init__(self, title="Manager", parent=None):
        super().__init__(parent)
        self.init_ui(title)

    def init_ui(self, title):
        layout = QVBoxLayout(self)
        
        # --- Top: Search ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"Search {title} by username...")
        
        # Debounce Logic
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300) # 300ms delay
        self.debounce_timer.timeout.connect(self.on_search)
        
        self.search_input.textChanged.connect(self.debounce_timer.start)
        
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # --- Center: Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(4) # Default
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # --- Bottom: Actions ---
        self.action_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.setStyleSheet("background-color: #4caf50; color: white; font-weight: bold;")
        self.new_btn.clicked.connect(self.on_new)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.delete_btn.clicked.connect(self.on_delete)
        
        self.action_layout.addWidget(self.new_btn)
        self.action_layout.addWidget(self.edit_btn)
        self.action_layout.addWidget(self.delete_btn)
        self.action_layout.addStretch()
        
        layout.addLayout(self.action_layout)

    def on_search(self):
        print("Search triggered (Not implemented)")

    def on_new(self):
        print("New triggered (Not implemented)")

    def on_edit(self):
        print("Edit triggered (Not implemented)")

    def on_delete(self):
        print("Delete triggered (Not implemented)")

    def on_realm_changed(self):
        """Called when the active realm changes."""
        # Default behavior: Clear table to avoid displaying stale data
        self.table.setRowCount(0)
