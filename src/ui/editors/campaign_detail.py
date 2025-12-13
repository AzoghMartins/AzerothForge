from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTabWidget, QTableWidget, QTableWidgetItem, 
                               QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox)
from PySide6.QtCore import Qt
from src.core.campaign_manager import CampaignManager
from src.ui.editors.npc_editor import NpcEditorDialog

try:
    import mysql.connector
except ImportError:
    mysql = None

class CampaignDetailWindow(QMainWindow):
    def __init__(self, campaign_data, dev_realm_config, campaign_manager: CampaignManager, config_manager, parent=None):
        super().__init__(parent)
        self.campaign_data = campaign_data
        self.dev_realm_config = dev_realm_config
        self.campaign_manager = campaign_manager
        # We need full config manager for auth details to connect to DB
        self.config_manager = config_manager
        
        self.setWindowTitle(f"Campaign Workstation: {campaign_data['name']}")
        self.resize(900, 600)
        
        self.init_ui()
        self.load_npc_list()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"<b>{self.campaign_data['name']}</b>"))
        
        # Dev Realm Indicator
        realm_name = self.dev_realm_config.get('name', 'Unknown Realm')
        lbl_realm = QLabel(f"Dev Realm: {realm_name}")
        lbl_realm.setStyleSheet("color: #aaa; font-style: italic; margin-left: 15px;")
        header_layout.addWidget(lbl_realm)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Dashboard Content (3 Columns)
        dashboard_layout = QHBoxLayout()
        
        # Column 1: NPCs
        self.npc_group = QGroupBox("Campaign NPCs")
        self.init_npc_column()
        dashboard_layout.addWidget(self.npc_group)
        
        # Column 2: Items
        self.item_group = QGroupBox("Campaign Items")
        self.init_item_column()
        dashboard_layout.addWidget(self.item_group)
        
        # Column 3: Quests
        self.quest_group = QGroupBox("Campaign Quests")
        self.init_quest_column()
        dashboard_layout.addWidget(self.quest_group)
        
        layout.addLayout(dashboard_layout)

    def init_npc_column(self):
        layout = QVBoxLayout(self.npc_group)
        
        # List
        self.npc_table = QTableWidget()
        self.npc_table.setColumnCount(2) # ID, Name
        self.npc_table.setHorizontalHeaderLabels(["ID", "Name"])
        self.npc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.npc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(self.npc_table)
        
        # Actions
        actions = QHBoxLayout()
        
        self.new_npc_btn = QPushButton("Add NPC")
        self.new_npc_btn.clicked.connect(self.on_new_npc)
        self.new_npc_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.edit_npc_btn = QPushButton("Edit NPC")
        self.edit_npc_btn.clicked.connect(self.on_edit_npc)
        
        actions.addWidget(self.new_npc_btn)
        actions.addWidget(self.edit_npc_btn)
        layout.addLayout(actions)

    def init_item_column(self):
        layout = QVBoxLayout(self.item_group)
        self.item_list = QTableWidget()
        self.item_list.setColumnCount(2)
        self.item_list.setHorizontalHeaderLabels(["ID", "Name"])
        layout.addWidget(self.item_list)
        # Placeholder buttons
        btn = QPushButton("Add Item (TODO)")
        btn.setEnabled(False)
        layout.addWidget(btn)

    def init_quest_column(self):
        layout = QVBoxLayout(self.quest_group)
        self.quest_list = QTableWidget()
        self.quest_list.setColumnCount(2)
        self.quest_list.setHorizontalHeaderLabels(["ID", "Title"])
        self.quest_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.quest_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.quest_list.doubleClicked.connect(self.on_edit_quest)
        layout.addWidget(self.quest_list)
        
        # Actions
        actions = QHBoxLayout()
        
        self.new_quest_btn = QPushButton("Add Quest")
        self.new_quest_btn.clicked.connect(self.on_new_quest)
        self.new_quest_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.edit_quest_btn = QPushButton("Edit Quest")
        self.edit_quest_btn.clicked.connect(self.on_edit_quest)
        
        actions.addWidget(self.new_quest_btn)
        actions.addWidget(self.edit_quest_btn)
        layout.addLayout(actions)

    def on_new_quest(self):
        from src.ui.wizards.quest_wizard import QuestWizard
        
        # Get Range
        ranges = self.campaign_data.get("ranges", {}).get("quest", {})
        min_id = ranges.get("start", 0)
        max_id = ranges.get("end", 0)
        
        wizard = QuestWizard(self.config_manager, min_id, max_id, self.campaign_data, self)
        if wizard.exec():
            # TODO: Handle saving logic in next step
            print("Quest Wizard Finished:", wizard.quest_data)

    def on_edit_quest(self):
        print("Edit Quest Placeholder")

    def load_npc_list(self):
        self.npc_table.setRowCount(0)
        
        content = self.campaign_data.get("content", {})
        npc_ids = content.get("npcs", [])
        
        if not npc_ids:
            return

        if not mysql:
            return

        # Query DB
        try:
            auth = self.config_manager.config.get("auth_database", {})
            conn = mysql.connector.connect(
                host=auth.get("host", "localhost"),
                port=auth.get("port", 3306),
                user=auth.get("user", "acore"),
                password=auth.get("password", "acore"),
                database=self.dev_realm_config.get("db_world_name", "acore_world")
            )
            cursor = conn.cursor()
            
            # list to string
            ids_str = ",".join(map(str, npc_ids))
            query = f"SELECT entry, name, subname FROM creature_template WHERE entry IN ({ids_str})"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                r = self.npc_table.rowCount()
                self.npc_table.insertRow(r)
                self.npc_table.setItem(r, 0, QTableWidgetItem(str(row[0])))
                self.npc_table.setItem(r, 1, QTableWidgetItem(row[1]))
                # self.npc_table.setItem(r, 2, QTableWidgetItem(row[2]))
                
        except mysql.connector.Error as e:
            print(f"Error loading NPC list: {e}")

    def on_new_npc(self):
        # 1. Get Next ID (Smart Allocation)
        next_id = self.campaign_manager.get_first_available_id(self.campaign_data["id"], "creature")
        if not next_id:
            QMessageBox.warning(self, "Limit Reached", "No more IDs available in this campaign block!")
            return
            
        # 2. Open Editor (Insert Mode)
        # Pass Strict Realm Config & Range
        ranges = self.campaign_data.get("ranges", {}).get("creature", {})
        allowed_range = (ranges.get("start", 0), ranges.get("end", 0))
        
        editor = NpcEditorDialog(self, predefined_id=next_id, mode="insert", realm_config=self.dev_realm_config, allowed_id_range=allowed_range)
        if editor.exec():
            # 3. On Save (Accepted)
            self.campaign_manager.register_content(self.campaign_data["id"], "npcs", next_id)
            self.load_npc_list()

    def on_edit_npc(self):
        # 1. Get Selected Item
        row = self.npc_table.currentRow()
        if row < 0:
            return
            
        id_item = self.npc_table.item(row, 0)
        if not id_item:
            return
            
        try:
            npc_id = int(id_item.text())
        except ValueError:
            return
            
        # 2. Open Editor (Update Mode)
        ranges = self.campaign_data.get("ranges", {}).get("creature", {})
        allowed_range = (ranges.get("start", 0), ranges.get("end", 0))
        
        editor = NpcEditorDialog(self, predefined_id=npc_id, mode="update", realm_config=self.dev_realm_config, allowed_id_range=allowed_range)
        if editor.exec():
            # 3. On Save (Accepted)
            # Just refresh list as content is already registered
            self.load_npc_list()
