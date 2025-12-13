from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QLabel, QLineEdit, QPushButton, QGroupBox, QFormLayout, 
                               QMessageBox, QSplitter, QComboBox)
from PySide6.QtCore import Qt
from src.core.campaign_manager import CampaignManager
from src.ui.components.character_selector import CharacterSelectorDialog
from src.ui.editors.campaign_detail import CampaignDetailWindow

class CampaignTab(QWidget):
    def __init__(self, campaign_manager: CampaignManager, config_manager, parent=None):
        super().__init__(parent)
        self.campaign_manager = campaign_manager
        self.config_manager = config_manager
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Splitter for Left (List) and Right (Details)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # --- Left Panel: Campaign List ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("<b>Your Campaigns</b>"))
        self.campaign_list = QListWidget()
        self.campaign_list.currentItemChanged.connect(self.on_campaign_selected)
        left_layout.addWidget(self.campaign_list)
        
        splitter.addWidget(left_widget)
        
        # --- Right Panel: Details & Creation ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 1. Active Campaign Indicator
        self.active_label = QLabel("No Campaign Loaded")
        self.active_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff9800;")
        right_layout.addWidget(self.active_label)
        
        # 2. Campaign Details Group
        self.details_group = QGroupBox("Campaign Details")
        details_layout = QFormLayout()
        
        self.det_name = QLabel("-")
        self.det_gm = QLabel("-")
        self.det_range = QLabel("-")
        self.det_dev_realm = QLabel("-")
        self.det_target_realm = QLabel("-")
        self.det_counts = QLabel("-")
        
        details_layout.addRow("Name:", self.det_name)
        details_layout.addRow("GM Character:", self.det_gm)
        details_layout.addRow("ID Range:", self.det_range)
        details_layout.addRow("Dev Server:", self.det_dev_realm)
        details_layout.addRow("Target Server:", self.det_target_realm)
        details_layout.addRow("Content:", self.det_counts)
        
        self.open_btn = QPushButton("📂 Open Campaign")
        self.open_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.on_open_campaign)
        details_layout.addRow(self.open_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete Campaign")
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.on_delete_campaign)
        details_layout.addRow(self.delete_btn)
        
        self.details_group.setLayout(details_layout)
        right_layout.addWidget(self.details_group)
        
        # 3. Create New Campaign Group
        create_group = QGroupBox("Create New Campaign")
        create_layout = QFormLayout()
        
        self.new_name = QLineEdit()
        self.new_start_id = QLineEdit()
        self.new_start_id.setPlaceholderText("e.g. 60000")
        
        # Realm Selectors
        self.dev_realm_combo = QComboBox()
        self.target_realm_combo = QComboBox()
        self.target_realm_combo.addItem("None", -1)
        
        realms = self.config_manager.get_realms()
        active_realm = self.config_manager.get_active_realm()
        
        # Populate Dev Realm
        for r in realms:
            self.dev_realm_combo.addItem(r["name"], r["id"])
            if r["id"] == active_realm.get("id"):
                self.dev_realm_combo.setCurrentIndex(self.dev_realm_combo.count() - 1)

        # Populate Target Realm
        for r in realms:
            self.target_realm_combo.addItem(f"Safe Check: {r['name']}", r["id"])
                
        # Connect signals
        self.dev_realm_combo.currentIndexChanged.connect(self.update_suggestion)
        self.target_realm_combo.currentIndexChanged.connect(self.update_suggestion)
        
        # Suggestion
        self.suggest_label = QLabel("Calculating...")
        self.suggest_label.setStyleSheet("color: #66bb6a; font-style: italic; font-size: 11px;")
        
        # GM Selector
        gm_layout = QHBoxLayout()
        self.new_gm_name = QLineEdit()
        self.new_gm_name.setReadOnly(True)
        self.select_gm_btn = QPushButton("Select GM...")
        self.select_gm_btn.clicked.connect(self.on_select_gm)
        gm_layout.addWidget(self.new_gm_name)
        gm_layout.addWidget(self.select_gm_btn)
        
        self.create_btn = QPushButton("Create Campaign")
        self.create_btn.clicked.connect(self.on_create_campaign)
        
        create_layout.addRow("Name:", self.new_name)
        create_layout.addRow("Dev Realm (Save To):", self.dev_realm_combo)
        create_layout.addRow("Target Realm (Safe Check):", self.target_realm_combo)
        create_layout.addRow("Start ID:", self.new_start_id)
        create_layout.addRow("", self.suggest_label)
        create_layout.addRow("GM Char:", gm_layout)
        create_layout.addRow(self.create_btn)
        
        create_group.setLayout(create_layout)
        right_layout.addWidget(create_group)
        
        # Initial Suggestion
        self.update_suggestion()
        
        right_layout.addStretch()
        splitter.addWidget(right_widget)
        
        # Set proportion
        splitter.setSizes([300, 600])

    def refresh_list(self):
        self.campaign_list.clear()
        campaigns = self.campaign_manager.get_campaigns()
        for c in campaigns:
            self.campaign_list.addItem(c["name"])
            # Store ID in user role if needed, or look up by index/name
            # For simplicity assuming unique names or mapping by index
            item = self.campaign_list.item(self.campaign_list.count() - 1)
            item.setData(Qt.UserRole, c)

    def on_campaign_selected(self, current, previous):
        if not current:
            self.open_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
            
        campaign = current.data(Qt.UserRole)
        self.det_name.setText(campaign["name"])
        self.det_gm.setText(campaign["gm_character"])
        
        ranges = campaign["ranges"]["creature"]
        self.det_range.setText(f"{ranges['start']} - {ranges['end']}")
        
        # Realms
        realms = self.config_manager.get_realms()
        
        dev_id = campaign.get("dev_realm_id")
        dev_name = "Unknown"
        if dev_id:
            r = next((x for x in realms if x["id"] == dev_id), None)
            if r: dev_name = r["name"]
        self.det_dev_realm.setText(dev_name)
        
        target_id = campaign.get("target_realm_id")
        target_name = "None"
        if target_id and target_id != -1:
            r = next((x for x in realms if x["id"] == target_id), None)
            if r: target_name = r["name"]
        self.det_target_realm.setText(target_name)
        
        # Counts
        content = campaign.get("content", {})
        n_npcs = len(content.get("npcs", []))
        n_items = len(content.get("items", []))
        n_quests = len(content.get("quests", []))
        
        self.det_counts.setText(f"NPCs: {n_npcs} | Items: {n_items} | Quests: {n_quests}")
        
        self.open_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def on_select_gm(self):
        # Filter for GM Level >= 3
        # Use the specific Dev Realm selected
        dev_rid = self.dev_realm_combo.currentData()
        
        dialog = CharacterSelectorDialog(self.config_manager, self, min_gm_level=3, target_realm_id=dev_rid)
        if dialog.exec():
            char_name = dialog.get_selected_character()
            if char_name:
                self.new_gm_name.setText(char_name)

    def on_create_campaign(self):
        name = self.new_name.text().strip()
        start_id_str = self.new_start_id.text().strip()
        gm_char = self.new_gm_name.text().strip()
        
        if not name or not start_id_str or not gm_char:
            QMessageBox.warning(self, "Validation", "All fields are required.")
            return
            
        try:
            start_id = int(start_id_str)
        except ValueError:
            QMessageBox.warning(self, "Validation", "Start ID must be a number.")
            return

        # Explicit Realm Context
        dev_rid = self.dev_realm_combo.currentData()
        target_rid = self.target_realm_combo.currentData()
        
        check_ids = []
        if dev_rid:
            check_ids.append(dev_rid)
        if target_rid and target_rid != -1 and target_rid not in check_ids:
            check_ids.append(target_rid)

        # Security Check: Validate ID Block
        if not self.campaign_manager.validate_id_block(start_id, check_realm_ids=check_ids):
            msg = f"The Start ID {start_id} conflicts with existing data in Checked Realms!"
            msg += "\n\nThe range (up to +1000) contains used IDs or reserved ranges.\n"
            msg += "Please choose a different ID or use the suggested one."
            
            QMessageBox.critical(self, "ID Conflict", msg)
            return
            
        self.campaign_manager.create_campaign(name, start_id, gm_char, dev_realm_id=dev_rid, target_realm_id=target_rid)
        self.refresh_list()
        
        # Clear inputs
        self.new_name.clear()
        self.new_start_id.clear()
        self.new_gm_name.clear()
        
        QMessageBox.information(self, "Success", f"Campaign '{name}' created!")

    def on_open_campaign(self):
        item = self.campaign_list.currentItem()
        if not item:
            return
            
        campaign = item.data(Qt.UserRole)
        self.campaign_manager.set_active_campaign(campaign["id"])
        
        self.active_label.setText(f"Active Campaign: {campaign['name']}")
        
        # Get Dev Realm Config
        dev_realm_id = campaign.get("dev_realm_id")
        dev_realm_config = self.config_manager.get_active_realm() # Default
        
        if dev_realm_id:
            # Find specific realm
            realms = self.config_manager.get_realms()
            found = next((r for r in realms if r["id"] == dev_realm_id), None)
            if found:
                dev_realm_config = found
        
        # Launch Detail Window
        self.detail_window = CampaignDetailWindow(campaign, dev_realm_config, self.campaign_manager, self.config_manager, self)
        
        # Align with Main Window
        if self.window():
            self.detail_window.move(self.window().pos())
            
        self.detail_window.show()

    def update_suggestion(self):
        check_ids = []
        
        # Dev Realm (Always check)
        dev_rid = self.dev_realm_combo.currentData()
        if dev_rid:
            check_ids.append(dev_rid)
            
        # Target Realm (Optional)
        target_rid = self.target_realm_combo.currentData()
        if target_rid and target_rid != -1:
            if target_rid not in check_ids:
                check_ids.append(target_rid)
            
        suggested = self.campaign_manager.suggest_next_id_block(check_realm_ids=check_ids)
        self.new_start_id.setText(str(suggested))
        
        count = len(check_ids)
        msg = f"Suggested: {suggested} - {suggested + 1000} (Checked {count} Realm{'s' if count != 1 else ''})"
        self.suggest_label.setText(msg)

    def on_delete_campaign(self):
        item = self.campaign_list.currentItem()
        if not item:
            return
            
        campaign = item.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Confirm Deletion", 
                                     f"Are you sure you want to delete campaign '{campaign['name']}'?\n"
                                     "This action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            self.campaign_manager.delete_campaign(campaign["id"])
            
            # Check if active was deleted (handled in manager, but update UI)
            if self.campaign_manager.get_active_campaign() is None:
                self.active_label.setText("No Campaign Loaded")
                
            self.refresh_list()
            self.det_name.setText("-")
            self.det_gm.setText("-")
            self.det_range.setText("-")
            self.det_dev_realm.setText("-")
            self.det_target_realm.setText("-")
            self.det_counts.setText("-")
            self.open_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            
            QMessageBox.information(self, "Deleted", f"Campaign '{campaign['name']}' has been deleted.")
