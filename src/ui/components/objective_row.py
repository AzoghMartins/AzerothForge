from PySide6.QtWidgets import (QWidget, QHBoxLayout, QComboBox, QSpinBox, 
                               QPushButton, QLabel, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QLineEdit)
from src.ui.components.selectors import SmartSelector
from src.database.db_manager import DbManager

class ObjectiveRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Kill (Creature)", "Interact (GameObject)", "Talk (Creature)"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        
        # Selector
        self.selector = SmartSelector("creature") # Default
        
        # Count
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 999)
        self.count_spin.setValue(0)
        
        # Fix Button (for Talk)
        self.fix_btn = QPushButton("Config Talk")
        self.fix_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 2px;")
        self.fix_btn.setVisible(False)
        self.fix_btn.clicked.connect(self.on_fix_talk)
        
        self.layout.addWidget(QLabel("Type:"))
        self.layout.addWidget(self.type_combo)
        self.layout.addWidget(QLabel("Target:"))
        self.layout.addWidget(self.selector, 1) # Stretch
        self.layout.addWidget(QLabel("Count:"))
        self.layout.addWidget(self.count_spin)
        self.layout.addWidget(self.fix_btn)
        
    def on_type_changed(self):
        idx = self.type_combo.currentIndex()
        if idx == 1: # Interact (GO)
            self.selector.set_selector_type("gameobject")
            self.fix_btn.setVisible(False)
        elif idx == 2: # Talk (Creature)
            current_id = self.selector.value()
            self.selector.set_selector_type("creature")
            self.selector.set_value(current_id)
            self.fix_btn.setVisible(True)
        else: # Kill (Creature)
            current_id = self.selector.value()
            self.selector.set_selector_type("creature")
            self.selector.set_value(current_id) # Restore ID if relevant
            self.fix_btn.setVisible(False)
            
    def set_data(self, obj_id, count):
        self.count_spin.setValue(count)
        
        if obj_id < 0:
            # Game Object
            self.type_combo.setCurrentIndex(1)
            self.selector.set_value(abs(obj_id))
        elif obj_id > 0:
            # Creature (Kill or Talk? We can't know for sure just by ID easily without checking flags/scripts, 
            # but usually default to Kill. User can switch to Talk if they know.)
            self.type_combo.setCurrentIndex(0) 
            self.selector.set_value(obj_id)
        else:
            # Empty
            self.selector.set_value(0)
            
    def clear(self):
        self.count_spin.setValue(0)
        self.selector.set_value(0)
        self.type_combo.setCurrentIndex(0)
        self.fix_btn.setVisible(False)
            
    def set_type_externally(self, type_str):
        """Sets the type combo without logic concerns (logic handled by signals)"""
        if type_str == "Interact with GameObject":
            self.type_combo.setCurrentIndex(1)
        elif type_str == "Talk to NPC":
            self.type_combo.setCurrentIndex(2)
        else:
            self.type_combo.setCurrentIndex(0)
            
    def get_data(self):
        """Returns (FinalID, Count)"""
        raw_id = self.selector.value()
        count = self.count_spin.value()
        idx = self.type_combo.currentIndex()
        
        if idx == 1: # Interact
            return -abs(raw_id), count
        else: # Kill or Talk
            return abs(raw_id), count
            
    def set_target(self, obj_id, count):
        self.count_spin.setValue(count)
        self.selector.set_value(obj_id)

    def set_quest_context(self, quest_id, realm_id=None):
        self.quest_id = quest_id
        self.realm_id = realm_id

    def set_gossip_data(self, npc_text, option_text):
        self.gossip_npc_text = npc_text
        self.gossip_option_text = option_text
        # Optional: Indicate data is loaded?
        
    def on_fix_talk(self):
        # Configure NPC for Talk
        npc_id = self.selector.value()
        if not npc_id:
            QMessageBox.warning(self, "Error", "Please select a creature first.")
            return
            
        # If we don't have cached text, try to fetch it if we are in an editor context
        # But we don't easily have quest/realm ID here.
        # Fallback: Just open dialog. If empty, user must enter it.
        # Wait, user said "saves properly from Wizard" but "doesn't load into Editor".
        # This implies QuestEditor.load_data -> set_gossip_data was called.
        # If it wasn't called (because check_talk fail), the memory is empty.
        # If memory is empty, the dialog opens empty.
        # We need to try to fetch it HERE if missing.
        # But we need quest_id and realm_id.
        # Maybe we can inspect the parent chain or rely on a "setup" method?
        # Or simplistic: If the row was initialized, it should have the data.
        # If not, it means DB check failed.
        # If DB check failed, maybe the data ISN'T in the DB?
        # The user said Wizard SAVED it.
        # Try to fetch from DB if missing and we have context
        if not getattr(self, 'gossip_npc_text', '') and hasattr(self, 'quest_id'):
            # Check script first to get menu_id
            db = DbManager.get_instance()
            is_talk, menu_id = db.check_talk_objective(npc_id, self.quest_id, getattr(self, 'realm_id', None))
            if is_talk:
                npc_text, option_text = db.get_gossip_data(menu_id, getattr(self, 'realm_id', None))
                self.gossip_npc_text = npc_text
                self.gossip_option_text = option_text
        
        # Dialog to edit text
        edit_dlg = QDialog(self)
        edit_dlg.setWindowTitle("Edit Gossip Text")
        edit_dlg.resize(400, 300)
        l = QVBoxLayout(edit_dlg)
        
        npc_edit = QTextEdit()
        npc_edit.setPlaceholderText("NPC says: Greetings...")
        npc_edit.setText(getattr(self, 'gossip_npc_text', ''))
        
        opt_edit = QLineEdit()
        opt_edit.setPlaceholderText("Player replies: I am ready.")
        opt_edit.setText(getattr(self, 'gossip_option_text', ''))
        
        l.addWidget(QLabel("NPC Text (What they say):"))
        l.addWidget(npc_edit)
        l.addWidget(QLabel("Option Text (Your reply):"))
        l.addWidget(opt_edit)
        
        btns = QHBoxLayout()
        save_btn = QPushButton("Save & Inject")
        save_btn.clicked.connect(edit_dlg.accept)
        btns.addWidget(save_btn)
        l.addLayout(btns)
        
        if edit_dlg.exec():
            # Store in memory for save
            self.gossip_npc_text = npc_edit.toPlainText()
            self.gossip_option_text = opt_edit.text()
            QMessageBox.information(self, "Info", "Texts stored in memory. Save the Quest to apply changes.")
