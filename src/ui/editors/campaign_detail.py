from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTabWidget, QTableWidget, QTableWidgetItem, 
                               QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from src.core.campaign_manager import CampaignManager
from src.database.db_manager import DbManager
from src.ui.editors.npc_editor_window import NpcEditorWindow

class CampaignDetailWindow(QMainWindow):
    def __init__(self, campaign_data, dev_realm_config, campaign_manager: CampaignManager, config_manager, parent=None):
        super().__init__(parent)
        self.campaign_data = campaign_data
        self.dev_realm_config = dev_realm_config
        self.campaign_manager = campaign_manager
        # We need full config manager for auth details to connect to DB
        self.config_manager = config_manager
        
        self.setWindowTitle(f"Campaign Workstation: {campaign_data['name']}")
        self.resize(1000, 600)
        
        self.init_ui()
        self.load_data()

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
        self.npc_group = QGroupBox(f"NPCs ({self.get_range_str('creature')})")
        self.init_npc_column()
        dashboard_layout.addWidget(self.npc_group)
        
        # Column 2: Items
        self.item_group = QGroupBox(f"Items ({self.get_range_str('item')})")
        self.init_item_column()
        dashboard_layout.addWidget(self.item_group)
        
        # Column 3: Quests
        self.quest_group = QGroupBox(f"Quests ({self.get_range_str('quest')})")
        self.init_quest_column()
        dashboard_layout.addWidget(self.quest_group)
        
        layout.addLayout(dashboard_layout)
        
        # Refresh Button
        btn_refresh = QPushButton("Refresh All")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh)

    def get_range_str(self, type_key):
        ranges = self.campaign_data.get("ranges", {}).get(type_key, {})
        return f"{ranges.get('start', '?')}-{ranges.get('end', '?')}"

    def init_npc_column(self):
        layout = QVBoxLayout(self.npc_group)
        
        # List
        self.npc_table = QTableWidget()
        self.npc_table.setColumnCount(3) # ID, Name, Level
        self.npc_table.setHorizontalHeaderLabels(["ID", "Name", "Lvl"])
        self.npc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.npc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.npc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
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
        self.item_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.item_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
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
        self.quest_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
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
            print("Quest Wizard Finished:", wizard.quest_data)
            self.load_data()

    def on_edit_quest(self):
        # 1. Get Selected Item
        row = self.quest_list.currentRow()
        if row < 0:
            return
            
        id_item = self.quest_list.item(row, 0)
        if not id_item:
            return
            
        try:
            quest_id = int(id_item.text())
        except ValueError:
            return
            
        # 2. Check Range (Optional warning)
        ranges = self.campaign_data.get("ranges", {}).get("quest", {})
        allowed_range = (ranges.get("start", 0), ranges.get("end", 0))
        
        # 3. Launch Editor
        from src.ui.editors.quest_editor import QuestEditor
        editor = QuestEditor(quest_id, self.dev_realm_config, self)
        if editor.exec():
            # Refresh if saved
            self.load_data()

    def load_data(self):
        print("DEBUG: CampaignDetailWindow.load_data calling...")
        
        db = DbManager.get_instance()
        realm_id = self.dev_realm_config.get("id")
        
        # 1. Quests (Range Based)
        q_range = self.campaign_data.get("ranges", {}).get("quest", {})
        q_min, q_max = q_range.get("start", 0), q_range.get("end", 0)
        
        quests = db.get_all_quests(realm_id=realm_id, min_id=q_min, max_id=q_max)
        self.populate_quest_list(quests)
        
        # 2. Linked Dependencies (NPCs & Items used by these Quests)
        deps = db.get_campaign_dependencies(realm_id, q_min, q_max)
        
        self.populate_npc_list(deps.get('npcs', []))
        self.populate_item_list(deps.get('items', []))

    def populate_quest_list(self, quests):
        self.quest_list.setRowCount(0)
        for row_data in quests:
            r = self.quest_list.rowCount()
            self.quest_list.insertRow(r)
            self.quest_list.setItem(r, 0, QTableWidgetItem(str(row_data['ID'])))
            self.quest_list.setItem(r, 1, QTableWidgetItem(row_data.get('LogTitle', 'Unknown')))

    def populate_npc_list(self, npcs):
        self.npc_table.setRowCount(0)
        
        # Range Check
        ranges = self.campaign_data.get("ranges", {}).get("creature", {})
        min_id, max_id = ranges.get("start", 0), ranges.get("end", 0)
        
        # Sort by ID
        npcs.sort(key=lambda x: x.get('entry', 0))
        
        for row_data in npcs:
            r = self.npc_table.rowCount()
            self.npc_table.insertRow(r)
            
            entry = row_data.get('entry', 0)
            name = row_data.get('name', 'Unknown')
            lvl = str(row_data.get('minlevel', '?'))
            
            # Validation
            is_valid = min_id <= entry <= max_id
            color = QBrush(QColor("white")) if is_valid else QBrush(QColor("#ff5252"))
            
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setForeground(color)
                return item
                
            self.npc_table.setItem(r, 0, create_item(entry))
            self.npc_table.setItem(r, 1, create_item(name))
            self.npc_table.setItem(r, 2, create_item(lvl))

    def populate_item_list(self, items):
        self.item_list.setRowCount(0)
        
        # Range Check
        ranges = self.campaign_data.get("ranges", {}).get("item", {})
        min_id, max_id = ranges.get("start", 0), ranges.get("end", 0)
        
        # Sort by ID
        items.sort(key=lambda x: x.get('entry', 0))
        
        for row_data in items:
            r = self.item_list.rowCount()
            self.item_list.insertRow(r)
            
            entry = row_data.get('entry', 0)
            name = row_data.get('name', 'Unknown')
            
            # Validation
            is_valid = min_id <= entry <= max_id
            color = QBrush(QColor("white")) if is_valid else QBrush(QColor("#ff5252"))
            
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setForeground(color)
                return item
                
            self.item_list.setItem(r, 0, create_item(entry))
            self.item_list.setItem(r, 1, create_item(name))

    def on_new_npc(self):
        # 1. Get Next ID (Smart Allocation)
        next_id = self.campaign_manager.get_first_available_id(self.campaign_data["id"], "creature")
        if not next_id:
            QMessageBox.warning(self, "Limit Reached", "No more IDs available in this campaign block!")
            return
            
        # 2. Open Editor (Insert Mode)
        ranges = self.campaign_data.get("ranges", {}).get("creature", {})
        allowed_range = (ranges.get("start", 0), ranges.get("end", 0))
        
        editor = NpcEditorWindow(next_id, self.campaign_data, self.dev_realm_config, self.config_manager,
                                 mode="insert", allowed_id_range=allowed_range, parent=self)
        if editor.exec():
            self.campaign_manager.register_content(self.campaign_data["id"], "npcs", next_id)
            self.load_data()

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
        
        # Check if out of range -> Warn user?
        min_v, max_v = allowed_range
        if not (min_v <= npc_id <= max_v):
             # You shouldn't leverage the editor for outside IDs generally, but let's allow "Viewing"?
             # Or maybe just block editing.
             pass
        
        editor = NpcEditorWindow(npc_id, self.campaign_data, self.dev_realm_config, self.config_manager,
                                 mode="update", allowed_id_range=allowed_range, parent=self)
        if editor.exec():
            self.load_data()
