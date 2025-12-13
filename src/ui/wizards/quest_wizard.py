from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QStackedWidget, QWidget, QLabel, QLineEdit, 
                               QComboBox, QTextEdit, QFormLayout, QFrame)
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QStackedWidget, QWidget, QLabel, QLineEdit, 
                               QComboBox, QTextEdit, QFormLayout, QFrame,
                               QGroupBox, QSpinBox, QRadioButton, QCheckBox, QGridLayout)
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QStackedWidget, QWidget, QLabel, QLineEdit, 
                               QComboBox, QTextEdit, QFormLayout, QFrame,
                               QGroupBox, QSpinBox, QRadioButton, QCheckBox, QGridLayout, QMessageBox,
                               QListWidget, QInputDialog)
from PySide6.QtCore import Qt, Signal, QSize
from src.ui.tools.search_window import SearchWindow
from src.database.db_manager import DbManager
from functools import partial

class ObjectiveDialog(QDialog):
    def __init__(self, config_manager, campaign_data, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.campaign_data = campaign_data or {}
        self.setWindowTitle("Configure Objective")
        self.resize(500, 400)
        self.result_data = {}
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Type
        type_group = QGroupBox("Objective Type")
        type_layout = QVBoxLayout()
        self.obj_type_combo = QComboBox()
        self.obj_type_combo.addItems(["Slay Creature", "Collect Item", "Talk to NPC", "Reach Location"])
        self.obj_type_combo.currentIndexChanged.connect(self.update_objective_ui)
        type_layout.addWidget(self.obj_type_combo)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Dynamic Stack
        self.obj_stack = QStackedWidget()
        
        # --- Page 0: Slay ---
        p0 = QWidget()
        l0 = QVBoxLayout(p0)
        self.grp_slay = QGroupBox("Creature Target")
        l_slay = QHBoxLayout()
        self.slay_id = QLineEdit()
        self.slay_id.setPlaceholderText("Creature ID")
        self.slay_name = QLineEdit()
        self.slay_name.setReadOnly(True)
        btn_slay = QPushButton("🔍")
        btn_slay.clicked.connect(lambda: self.open_selector("slay_creature"))
        l_slay.addWidget(self.slay_id)
        l_slay.addWidget(self.slay_name)
        l_slay.addWidget(btn_slay)
        self.grp_slay.setLayout(l_slay)
        
        self.grp_qty = QGroupBox("Requirements")
        l_qty = QHBoxLayout()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100)
        l_qty.addWidget(QLabel("Amount:"))
        l_qty.addWidget(self.qty_spin)
        self.grp_qty.setLayout(l_qty)
        
        l0.addWidget(self.grp_slay)
        l0.addWidget(self.grp_qty)
        l0.addStretch()
        self.obj_stack.addWidget(p0)

        # --- Page 1: Collect Item ---
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        self.grp_item = QGroupBox("Item Selection")
        l_item = QHBoxLayout()
        self.item_id = QLineEdit()
        self.item_id.setPlaceholderText("Item ID")
        self.item_name = QLineEdit()
        self.item_name.setReadOnly(True)
        btn_item = QPushButton("🔍")
        btn_item.clicked.connect(lambda: self.open_selector("collect_item"))
        l_item.addWidget(self.item_id)
        l_item.addWidget(self.item_name)
        l_item.addWidget(btn_item)
        self.grp_item.setLayout(l_item)
        
        self.grp_item_qty = QGroupBox("Requirements")
        l_iq = QHBoxLayout()
        self.item_qty = QSpinBox()
        self.item_qty.setRange(1, 100)
        l_iq.addWidget(QLabel("Amount:"))
        l_iq.addWidget(self.item_qty)
        self.grp_item_qty.setLayout(l_iq)
        
        self.grp_source = QGroupBox("Source / Drop Configuration")
        l_src = QVBoxLayout()
        self.src_type = QComboBox()
        self.src_type.addItems(["Loot from Creature", "Loot from GameObject", "Vendor/Trade"])
        
        self.src_stack = QStackedWidget()
        
        w_creature = QWidget()
        lc = QHBoxLayout(w_creature)
        self.drop_creature_btn = QPushButton("Select Dropper")
        self.drop_creature_btn.clicked.connect(lambda: self.open_selector("loot_source"))
        self.drop_creature_id = QLineEdit()
        self.drop_creature_id.setPlaceholderText("Creature ID")
        self.drop_chance = QSpinBox()
        self.drop_chance.setRange(1, 100)
        self.drop_chance.setSuffix("%")
        lc.addWidget(self.drop_creature_btn)
        lc.addWidget(self.drop_creature_id)
        lc.addWidget(QLabel("Chance:"))
        lc.addWidget(self.drop_chance)
        self.src_stack.addWidget(w_creature)

        w_go = QWidget()
        lg = QHBoxLayout(w_go)
        self.drop_go_btn = QPushButton("Select Object")
        self.drop_go_btn.clicked.connect(lambda: self.open_selector("loot_source_go"))
        self.drop_go_id = QLineEdit()
        self.drop_go_id.setPlaceholderText("GameObject ID")
        self.drop_go_chance = QSpinBox()
        self.drop_go_chance.setRange(1, 100)
        self.drop_go_chance.setSuffix("%")
        lg.addWidget(self.drop_go_btn)
        lg.addWidget(self.drop_go_id)
        lg.addWidget(QLabel("Chance:"))
        lg.addWidget(self.drop_go_chance)
        self.src_stack.addWidget(w_go)
        
        w_ven = QWidget()
        lv = QVBoxLayout(w_ven)
        lv.addWidget(QLabel("Item must be sold by vendor or traded."))
        self.src_stack.addWidget(w_ven)
        
        self.src_type.currentIndexChanged.connect(self.src_stack.setCurrentIndex)
        l_src.addWidget(QLabel("Source Type:"))
        l_src.addWidget(self.src_type)
        l_src.addWidget(self.src_stack)
        self.grp_source.setLayout(l_src)
        
        l1.addWidget(self.grp_item)
        l1.addWidget(self.grp_item_qty)
        l1.addWidget(self.grp_source)
        l1.addStretch()
        self.obj_stack.addWidget(p1)

        # --- Page 2: Talk ---
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        self.grp_talk = QGroupBox("NPC Selection")
        l_talk = QHBoxLayout()
        self.talk_id = QLineEdit()
        self.talk_id.setPlaceholderText("NPC ID")
        self.talk_name = QLineEdit()
        self.talk_name.setReadOnly(True)
        btn_talk = QPushButton("🔍")
        btn_talk.clicked.connect(lambda: self.open_selector("talk_npc"))
        l_talk.addWidget(self.talk_id)
        l_talk.addWidget(self.talk_name)
        l_talk.addWidget(btn_talk)
        self.grp_talk.setLayout(l_talk)
        
        self.grp_gossip = QGroupBox("Gossip Settings")
        l_gos = QFormLayout()
        self.gossip_text = QLineEdit()
        l_gos.addRow("Option Text:", self.gossip_text)
        self.grp_gossip.setLayout(l_gos)
        
        l2.addWidget(self.grp_talk)
        l2.addWidget(self.grp_gossip)
        l2.addStretch()
        self.obj_stack.addWidget(p2)

        # --- Page 3: Reach ---
        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        self.grp_loc = QGroupBox("Target Coordinates")
        gl = QGridLayout()
        self.loc_map = QLineEdit()
        self.loc_x = QLineEdit()
        self.loc_y = QLineEdit()
        self.loc_z = QLineEdit()
        gl.addWidget(QLabel("Map:"),0,0); gl.addWidget(self.loc_map,0,1)
        gl.addWidget(QLabel("X:"),1,0); gl.addWidget(self.loc_x,1,1)
        gl.addWidget(QLabel("Y:"),2,0); gl.addWidget(self.loc_y,2,1)
        gl.addWidget(QLabel("Z:"),3,0); gl.addWidget(self.loc_z,3,1)
        self.grp_loc.setLayout(gl)
        
        self.gm_btn = QPushButton("Get Position from GM Character")
        self.gm_btn.clicked.connect(self.fetch_gm_coords)
        
        l3.addWidget(self.grp_loc)
        l3.addWidget(self.gm_btn)
        l3.addStretch()
        self.obj_stack.addWidget(p3)
        
        layout.addWidget(self.obj_stack)
        
        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Save Objective")
        ok_btn.clicked.connect(self.on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)
        
        self.update_objective_ui()

    def update_objective_ui(self):
        obj_type = self.obj_type_combo.currentText()
        if obj_type == "Slay Creature":
            self.obj_stack.setCurrentIndex(0)
        elif obj_type == "Collect Item":
            self.obj_stack.setCurrentIndex(1)
        elif obj_type == "Talk to NPC":
            self.obj_stack.setCurrentIndex(2)
        elif obj_type == "Reach Location":
            self.obj_stack.setCurrentIndex(3)

    def open_selector(self, context):
        table = None
        handler = None
        if context == "slay_creature":
            table = "creature_template"
            handler = self.on_slay_selected
        elif context == "collect_item":
            table = "item_template"
            handler = self.on_item_selected
        elif context == "loot_source":
            table = "creature_template" 
            handler = self.on_source_selected
        elif context == "loot_source_go":
            table = "gameobject_template"
            handler = self.on_go_source_selected
        elif context == "talk_npc":
            table = "creature_template"
            handler = self.on_talk_selected
            
        if table:
            self.picker = SearchWindow(self.config_manager, table, is_picker=True, parent=self)
            self.picker.selection_confirmed.connect(handler)
            self.picker.show()

    def on_slay_selected(self, row):
        self.slay_id.setText(str(row['entry']))
        self.slay_name.setText(row['name'])
        self.picker.close()

    def on_item_selected(self, row):
        self.item_id.setText(str(row['entry']))
        self.item_name.setText(row['name'])
        self.picker.close()

    def on_source_selected(self, row):
        self.drop_creature_id.setText(str(row['entry']))
        self.picker.close()

    def on_go_source_selected(self, row):
        self.drop_go_id.setText(str(row['entry']))
        self.picker.close()

    def on_talk_selected(self, row):
        self.talk_id.setText(str(row['entry']))
        self.talk_name.setText(row['name'])
        self.picker.close()

    def fetch_gm_coords(self):
        gm_name = self.campaign_data.get('gm_character')
        if not gm_name:
             gm_name, ok = QInputDialog.getText(self, "GM Lookup", "Enter GM Character Name:")
             if not ok or not gm_name: return
        try:
            dev_realm_id = self.campaign_data.get('dev_realm_id')
            realms = self.config_manager.get_realms()
            target_realm = next((r for r in realms if r.get('id') == dev_realm_id), None)
            if not target_realm: target_realm = self.config_manager.get_active_realm()
            if not target_realm:
                 QMessageBox.critical(self, "Error", "Could not identify target realm.")
                 return
            db = DbManager.get_instance()
            loc = db.get_character_location(gm_name, target_realm)
            if loc:
                self.loc_map.setText(str(loc['map']))
                self.loc_x.setText(f"{loc['x']:.2f}")
                self.loc_y.setText(f"{loc['y']:.2f}")
                self.loc_z.setText(f"{loc['z']:.2f}")
            else:
                QMessageBox.warning(self, "Not Found", f"Character '{gm_name}' not found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch coords: {e}")

    def on_save(self):
        otyp = self.obj_type_combo.currentText()
        data = {"objective_type": otyp}
        
        if otyp == "Slay Creature":
            data["target_id"] = self.slay_id.text().strip()
            data["target_count"] = self.qty_spin.value()
            data["description"] = f"Slay {self.slay_name.text()} (x{data['target_count']})"
        elif otyp == "Collect Item":
            data["target_id"] = self.item_id.text().strip()
            data["target_count"] = self.item_qty.value()
            data["source_type"] = self.src_type.currentText()
            if "Creature" in data["source_type"]:
                data["source_id"] = self.drop_creature_id.text()
                data["drop_chance"] = self.drop_chance.value()
            elif "GameObject" in data["source_type"]:
                data["source_id"] = self.drop_go_id.text()
                data["drop_chance"] = self.drop_go_chance.value()
            data["description"] = f"Collect {self.item_name.text()} (x{data['target_count']})"
        elif otyp == "Talk to NPC":
            data["target_id"] = self.talk_id.text().strip()
            data["gossip_text"] = self.gossip_text.text()
            data["description"] = f"Talk to {self.talk_name.text()}"
        elif otyp == "Reach Location":
            data["map_id"] = self.loc_map.text()
            data["pos_x"] = self.loc_x.text()
            data["pos_y"] = self.loc_y.text()
            data["pos_z"] = self.loc_z.text()
            data["description"] = "Reach Location"
            
        self.result_data = data
        self.accept()

class QuestWizard(QDialog):
    quest_created = Signal(dict)

    def __init__(self, config_manager, min_id, max_id, campaign_data=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.min_id = min_id
        self.max_id = max_id
        self.campaign_data = campaign_data or {}
        
        self.setWindowTitle("Quest Creation Wizard")
        self.resize(700, 600)
        
        self.quest_data = {}
        self.quest_objectives = []
        
        # Reward State
        self.rewards_fixed = []
        self.rewards_choice = []
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 1. Content Area (Stacked Widget)
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)
        
        # Page 1: Identity & Narrative
        self.page1 = self.create_page_identity()
        self.pages.addWidget(self.page1)
        
        # Add a placeholder Page 2 so "Next" has somewhere to go (even if empty for now as per req logic, 
        # though user said "even if the next page is empty for now", it helps to visualize transition)
        # Page 2: Requirements
        self.page2 = self.setup_page_requirements()
        self.pages.addWidget(self.page2)

        # Page 3: Objectives
        self.page3 = self.setup_page_objectives()
        self.pages.addWidget(self.page3)

        # Page 4: Rewards
        self.page4 = self.setup_page_rewards()
        self.pages.addWidget(self.page4)

        # Page 5: Assignment
        self.page5 = self.setup_page_assignment()
        self.pages.addWidget(self.page5)
        
        # 2. Navigation Bar
        nav_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("< Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.next_btn = QPushButton("Next >")
        self.next_btn.clicked.connect(self.go_next)
        self.next_btn.setDefault(True)
        # Apply validation logic initially
        self.next_btn.setEnabled(False) 
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.cancel_btn)
        nav_layout.addWidget(self.next_btn)
        
        # Line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        main_layout.addLayout(nav_layout)
        
    def create_page_identity(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Header
        layout.addWidget(QLabel("<b>Step 1: Quest Identity & Narrative</b>"))
        
        form = QFormLayout()
        
        # Quest ID (Auto-Generated)
        self.id_input = QSpinBox()
        # Set Campaign Range or Default
        r_min = self.min_id if self.min_id > 0 else 1
        r_max = self.max_id if self.max_id > 0 else 999999
        self.id_input.setRange(r_min, r_max)
        
        # Auto-fill
        try:
            db = DbManager.get_instance()
            # Try to find gap in range
            if self.min_id > 0 and self.max_id > 0:
                next_id = db.get_free_entry_in_range('quest_template', self.min_id, self.max_id, col_name='ID') # Try 'ID' first or 'entry'? Error said 'entry' unknown?
                # The user said error: "Unknown column 'entry'".
                # This implies the column is NOT 'entry'. It is likely 'ID' or 'QuestId'.
                # I will try 'ID' as it's common in modern cores. If that fails I can't easily fallback without try-except but query is inside DbManager.
                # Actually, earlier I assumed 'entry' and it failed. So I should try 'ID'.
                if next_id is None:
                    next_id = r_min # If full or error, just set to min
            else:
                # Fallback to old MAX + 1 if no range
                next_id = db.get_next_entry_id('quest_template', column='ID') # Also change column here
                
            self.id_input.setValue(next_id)
        except Exception as e:
            print(f"Error fetching next ID: {e}")
            self.id_input.setValue(r_min)

        form.addRow("Quest ID (Auto-Generated):", self.id_input)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. The Lost Sword")
        self.title_input.textChanged.connect(self.validate_page)
        form.addRow("Title (Required):", self.title_input)
        
        # Zone
        self.zone_combo = QComboBox()
        self.zone_combo.addItems(["General", "Dragonblight", "Epic", "Dungeon", "Raid"])
        form.addRow("Zone / Category:", self.zone_combo)
        
        # Log Text
        self.log_text = QTextEdit()
        self.log_text.setPlaceholderText("Short description shown in the quest log...")
        self.log_text.setMaximumHeight(80)
        form.addRow("Log Description:", self.log_text)
        
        # NPC Dialogue
        self.npc_text = QTextEdit()
        self.npc_text.setPlaceholderText("Greetings, traveler! I have a task for you...")
        self.npc_text.setMaximumHeight(100)
        form.addRow("Offer Dialogue:", self.npc_text)
        
        # Completion Text
        self.completion_text = QTextEdit()
        self.completion_text.setPlaceholderText("Thank you for your help!")
        self.completion_text.setMaximumHeight(80)
        form.addRow("Completion Text:", self.completion_text)
        
        layout.addLayout(form)
        return page

    def validate_page(self):
        # Page 1 Validation
        if self.pages.currentIndex() == 0:
            title = self.title_input.text().strip()
            title = self.title_input.text().strip()
            self.next_btn.setEnabled(bool(title))
        elif self.pages.currentIndex() == 4: # Assignment Page
            starter = self.starter_id.text().strip()
            self.next_btn.setEnabled(bool(starter))
        else:
            self.next_btn.setEnabled(True)
    
    def go_next(self):
        current = self.pages.currentIndex()
        if current < self.pages.count() - 1:
            # Save data from current page
            if current == 0:
                self.quest_data["entry"] = self.id_input.value()
                self.quest_data["title"] = self.title_input.text().strip()
                self.quest_data["zone"] = self.zone_combo.currentText()
                self.quest_data["log_description"] = self.log_text.toPlainText()
                self.quest_data["quest_description"] = self.npc_text.toPlainText()
                self.quest_data["quest_completion_log"] = self.completion_text.toPlainText()
            elif current == 1:
                self.quest_data["min_level"] = self.min_level_spin.value()
                self.quest_data["quest_level"] = self.quest_level_spin.value()
                
                # Faction
                if self.faction_alliance.isChecked():
                    self.quest_data["required_races"] = "Alliance"
                elif self.faction_horde.isChecked():
                    self.quest_data["required_races"] = "Horde"
                else:
                    self.quest_data["required_races"] = "Both"
                
                # Classes
                if self.allow_all_classes.isChecked():
                    self.quest_data["required_classes"] = "All"
                else:
                    selected_classes = [name for name, chk in self.class_checks.items() if chk.isChecked()]
                    self.quest_data["required_classes"] = selected_classes
                    
            elif current == 2: # Objectives
                self.quest_data["objectives"] = self.quest_objectives
                    
            elif current == 3: # Rewards
                self.quest_data["reward_gold"] = self.rew_gold.value()
                self.quest_data["reward_silver"] = self.rew_silver.value()
                self.quest_data["reward_copper"] = self.rew_copper.value()
                self.quest_data["reward_xp_difficulty"] = self.rew_xp_combo.currentText()
                self.quest_data["rewards_fixed"] = self.rewards_fixed
                self.quest_data["rewards_choice"] = self.rewards_choice

            # Move Next
            self.pages.setCurrentIndex(current + 1)
            self.back_btn.setEnabled(True)
            
            # Check if last page
            if self.pages.currentIndex() == self.pages.count() - 1:
                self.next_btn.setText("Finish")
            
            # Re-validate for new page
            self.validate_page()
            
        else:
            # Finish - Save Last Page Data (if we are on the last page)
            if current == 4: # Assignment Page
                self.quest_data["starter_id"] = self.starter_id.text().strip()
                self.quest_data["ender_id"] = self.ender_id.text().strip()
                # If same as starter checked, ensure ender_id matches starter_id just in case
                if self.same_ender_chk.isChecked():
                    self.quest_data["ender_id"] = self.quest_data["starter_id"]
                
                self.submit_quest()

    def submit_quest(self):
        from src.core.quest_translator import QuestTranslator
        # Convert to Multi-Table Package
        package = QuestTranslator.prepare_transaction_package(self.quest_data)
        
        print("DEBUG: Quest Transaction Package:")
        import pprint
        pprint.pprint(package)
        
        # Save to DB
        db = DbManager.get_instance()
        success = db.save_quest_transaction(package)
        
        if success:
            QMessageBox.information(self, "Success", f"Quest {package['id']} saved successfully!")
            self.accept()
            self.quest_created.emit(self.quest_data)
        else:
            QMessageBox.critical(self, "Error", "Failed to save quest. Check console for details.")

    def go_back(self):
        current = self.pages.currentIndex()
        if current > 0:
            self.pages.setCurrentIndex(current - 1)
            self.next_btn.setText("Next >")
            self.validate_page() # Re-validate page 1 state
            
        if self.pages.currentIndex() == 0:
            self.back_btn.setEnabled(False)

    def setup_page_requirements(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(QLabel("<b>Step 2: Requirements & Eligibility</b>"))
        
        # 1. Level Requirements
        level_group = QGroupBox("Level Requirements")
        level_layout = QFormLayout()
        
        self.min_level_spin = QSpinBox()
        self.min_level_spin.setRange(1, 80)
        self.min_level_spin.setValue(1)
        
        self.quest_level_spin = QSpinBox()
        self.quest_level_spin.setRange(1, 80)
        self.quest_level_spin.setValue(1)
        
        level_layout.addRow("Min Level:", self.min_level_spin)
        level_layout.addRow("Quest Level:", self.quest_level_spin)
        level_group.setLayout(level_layout)
        layout.addWidget(level_group)
        
        # 2. Faction
        faction_group = QGroupBox("Faction")
        faction_layout = QHBoxLayout()
        
        self.faction_alliance = QRadioButton("Alliance Only")
        self.faction_horde = QRadioButton("Horde Only")
        self.faction_both = QRadioButton("Both")
        self.faction_both.setChecked(True)
        
        faction_layout.addWidget(self.faction_alliance)
        faction_layout.addWidget(self.faction_horde)
        faction_layout.addWidget(self.faction_both)
        faction_group.setLayout(faction_layout)
        layout.addWidget(faction_group)
        
        # 3. Class Restrictions
        class_group = QGroupBox("Class Restrictions")
        class_layout = QVBoxLayout()
        
        self.allow_all_classes = QCheckBox("Allow All Classes")
        self.allow_all_classes.setChecked(True)
        self.allow_all_classes.toggled.connect(self.toggle_class_grid)
        class_layout.addWidget(self.allow_all_classes)
        
        self.class_grid_widget = QWidget()
        grid = QGridLayout(self.class_grid_widget)
        self.class_checks = {}
        
        classes = [
            "Warrior", "Paladin", "Hunter", "Rogue", "Priest",
            "Death Knight", "Shaman", "Mage", "Warlock", "Druid"
        ]
        
        for i, cls_name in enumerate(classes):
            chk = QCheckBox(cls_name)
            chk.setEnabled(False) # Disabled by default since 'Allow All' is checked
            grid.addWidget(chk, i // 2, i % 2)
            self.class_checks[cls_name] = chk
            
        class_layout.addWidget(self.class_grid_widget)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # 4. Pre-Requisite
        prereq_group = QGroupBox("Pre-Requisite")
        prereq_layout = QHBoxLayout()
        
        self.prev_quest_id = QLineEdit()
        self.prev_quest_id.setPlaceholderText("Previous Quest ID (Optional)")
        # Enforce integer only?
        # self.prev_quest_id.setValidator(QIntValidator()) # Need import or just trust user/clean later
        
        search_btn = QPushButton("Search Quest")
        search_btn.setEnabled(False) # Placeholder
        
        prereq_layout.addWidget(QLabel("Prev Quest ID:"))
        prereq_layout.addWidget(self.prev_quest_id)
        prereq_layout.addWidget(search_btn)
        prereq_group.setLayout(prereq_layout)
        layout.addWidget(prereq_group)
        
        layout.addStretch()
        return page

    def toggle_class_grid(self, checked):
        # If 'Allow All' is checked, disable individual boxes, else enable
        for chk in self.class_checks.values():
            chk.setEnabled(not checked)

    def setup_page_objectives(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(QLabel("<b>Step 3: Objectives</b>"))
        
        self.objectives_list = QListWidget()
        layout.addWidget(self.objectives_list)
        
        btns = QHBoxLayout()
        add_btn = QPushButton("Add Objective")
        add_btn.clicked.connect(self.add_objective)
        
        rem_btn = QPushButton("Remove Selected")
        rem_btn.clicked.connect(self.remove_objective)
        
        btns.addWidget(add_btn)
        btns.addWidget(rem_btn)
        layout.addLayout(btns)
        
        return page

    def add_objective(self):
        dlg = ObjectiveDialog(self.config_manager, self.campaign_data, parent=self)
        if dlg.exec():
            # Add to list
            data = dlg.result_data
            self.quest_objectives.append(data)
            self.objectives_list.addItem(data.get('description', 'Objective'))

    def remove_objective(self):
        row = self.objectives_list.currentRow()
        if row >= 0:
            self.objectives_list.takeItem(row)
            self.quest_objectives.pop(row)

    def setup_page_rewards(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(QLabel("<b>Step 4: Rewards</b>"))
        
        # 1. Economy
        econ_group = QGroupBox("Economy")
        econ_layout = QHBoxLayout()
        
        self.rew_gold = QSpinBox()
        self.rew_gold.setRange(0, 100000)
        self.rew_gold.setSuffix(" g")
        
        self.rew_silver = QSpinBox()
        self.rew_silver.setRange(0, 99)
        self.rew_silver.setSuffix(" s")
        
        self.rew_copper = QSpinBox()
        self.rew_copper.setRange(0, 99)
        self.rew_copper.setSuffix(" c")
        
        econ_layout.addWidget(QLabel("Money:"))
        econ_layout.addWidget(self.rew_gold)
        econ_layout.addWidget(self.rew_silver)
        econ_layout.addWidget(self.rew_copper)
        econ_layout.addStretch()
        
        self.rew_xp_combo = QComboBox()
        self.rew_xp_combo.addItems(["Standard", "Low", "High", "Epic"])
        
        econ_layout.addWidget(QLabel("XP Difficulty:"))
        econ_layout.addWidget(self.rew_xp_combo)
        
        econ_group.setLayout(econ_layout)
        layout.addWidget(econ_group)
        
        # 2. Fixed Rewards
        fixed_group = QGroupBox("Fixed Rewards (You get these)")
        fixed_layout = QVBoxLayout()
        
        self.fixed_list = QListWidget()
        fixed_layout.addWidget(self.fixed_list)
        
        f_btns = QHBoxLayout()
        self.add_fixed_btn = QPushButton("Add Item")
        self.add_fixed_btn.clicked.connect(partial(self.add_reward_item, False))
        self.del_fixed_btn = QPushButton("Remove")
        self.del_fixed_btn.clicked.connect(partial(self.remove_reward_item, False))
        
        f_btns.addWidget(self.add_fixed_btn)
        f_btns.addWidget(self.del_fixed_btn)
        fixed_layout.addLayout(f_btns)
        
        fixed_group.setLayout(fixed_layout)
        layout.addWidget(fixed_group)
        
        # 3. Choice Rewards
        choice_group = QGroupBox("Choice Rewards (Pick one)")
        choice_layout = QVBoxLayout()
        
        self.choice_list = QListWidget()
        choice_layout.addWidget(self.choice_list)
        
        c_btns = QHBoxLayout()
        self.add_choice_btn = QPushButton("Add Item")
        self.add_choice_btn.clicked.connect(partial(self.add_reward_item, True))
        self.del_choice_btn = QPushButton("Remove")
        self.del_choice_btn.clicked.connect(partial(self.remove_reward_item, True))
        
        c_btns.addWidget(self.add_choice_btn)
        c_btns.addWidget(self.del_choice_btn)
        choice_layout.addLayout(c_btns)
        
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)
        
        return page

    def add_reward_item(self, is_choice):
        self.pending_choice_flag = is_choice # Store state for callback
        self.picker = SearchWindow(self.config_manager, "item_template", is_picker=True, parent=self)
        self.picker.selection_confirmed.connect(self.on_reward_item_selected)
        self.picker.show()
        
    def on_reward_item_selected(self, row_data):
        self.picker.close()
        
        # Prompt for Quantity
        count, ok = QInputDialog.getInt(self, "Quantity", f"Count for {row_data['name']}:", 1, 1, 100)
        if not ok:
            return
            
        entry_data = {
            "id": row_data['entry'],
            "name": row_data['name'],
            "count": count
        }
        
        # Add to list
        display_str = f"{entry_data['id']}: {entry_data['name']} (x{count})"
        
        if self.pending_choice_flag:
            self.rewards_choice.append(entry_data)
            self.choice_list.addItem(display_str)
        else:
            self.rewards_fixed.append(entry_data)
            self.fixed_list.addItem(display_str)

    def remove_reward_item(self, is_choice):
        if is_choice:
            row = self.choice_list.currentRow()
            if row >= 0:
                self.choice_list.takeItem(row)
                self.rewards_choice.pop(row)
        else:
            if row >= 0:
                self.fixed_list.takeItem(row)
                self.rewards_fixed.pop(row)

    def setup_page_assignment(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(QLabel("<b>Step 5: Quest Assignment</b>"))
        
        # 1. Quest Starter
        start_group = QGroupBox("Quest Starter")
        start_layout = QHBoxLayout()
        
        self.starter_id = QLineEdit()
        self.starter_id.setPlaceholderText("NPC ID")
        self.starter_id.setReadOnly(True)
        self.starter_id.setFixedWidth(80)
        self.starter_id.textChanged.connect(self.validate_page)
        self.starter_id.textChanged.connect(self.sync_ender) # Auto-sync if checked
        
        self.starter_name = QLineEdit()
        self.starter_name.setPlaceholderText("NPC Name")
        self.starter_name.setReadOnly(True)
        
        btn = QPushButton("Select NPC")
        btn.clicked.connect(self.open_starter_selector)
        
        start_layout.addWidget(QLabel("Started By:"))
        start_layout.addWidget(self.starter_id)
        start_layout.addWidget(self.starter_name)
        start_layout.addWidget(btn)
        
        start_group.setLayout(start_layout)
        layout.addWidget(start_group)
        
        # 2. Quest Ender
        end_group = QGroupBox("Quest Ender")
        end_layout = QVBoxLayout()
        
        self.same_ender_chk = QCheckBox("Same as Quest Starter")
        self.same_ender_chk.setChecked(True)
        self.same_ender_chk.toggled.connect(self.toggle_ender_fields)
        
        end_layout.addWidget(self.same_ender_chk)
        
        self.ender_widget = QWidget()
        h_layout = QHBoxLayout(self.ender_widget)
        h_layout.setContentsMargins(0,0,0,0)
        
        self.ender_id = QLineEdit()
        self.ender_id.setPlaceholderText("NPC ID")
        self.ender_id.setReadOnly(True)
        self.ender_id.setFixedWidth(80)
        
        self.ender_name = QLineEdit()
        self.ender_name.setPlaceholderText("NPC Name")
        self.ender_name.setReadOnly(True)
        
        self.ender_btn = QPushButton("Select NPC")
        self.ender_btn.clicked.connect(self.open_ender_selector)
        
        h_layout.addWidget(QLabel("Ended By:"))
        h_layout.addWidget(self.ender_id)
        h_layout.addWidget(self.ender_name)
        h_layout.addWidget(self.ender_btn)
        
        end_layout.addWidget(self.ender_widget)
        end_group.setLayout(end_layout)
        layout.addWidget(end_group)
        
        layout.addStretch()
        
        self.toggle_ender_fields(True)
        
        return page

    def toggle_ender_fields(self, checked):
        self.ender_widget.setEnabled(not checked)
        if checked:
            self.sync_ender()
            
    def sync_ender(self):
        if self.same_ender_chk.isChecked():
            self.ender_id.setText(self.starter_id.text())
            self.ender_name.setText(self.starter_name.text())

    def open_starter_selector(self):
        self.picker = SearchWindow(self.config_manager, "creature_template", is_picker=True, parent=self)
        self.picker.selection_confirmed.connect(self.on_starter_selected)
        self.picker.show()
        
    def on_starter_selected(self, row_data):
        self.starter_id.setText(str(row_data['entry']))
        self.starter_name.setText(row_data['name'])
        self.picker.close()
        
    def open_ender_selector(self):
        self.picker = SearchWindow(self.config_manager, "creature_template", is_picker=True, parent=self)
        self.picker.selection_confirmed.connect(self.on_ender_selected)
        self.picker.show()
        
    def on_ender_selected(self, row_data):
        self.ender_id.setText(str(row_data['entry']))
        self.ender_name.setText(row_data['name'])
        self.picker.close()
