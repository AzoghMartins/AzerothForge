from src.ui.components.base_manager import BaseManagerTab
from PySide6.QtWidgets import QPushButton

class CharacterTab(BaseManagerTab):
    def __init__(self, parent=None):
        super().__init__("Characters", parent)
        self.customize_ui()

    def customize_ui(self):
        self.new_btn.setVisible(False)
        self.table.setHorizontalHeaderLabels(["GUID", "Name", "Race", "Class", "Level"])
        
        self.kick_btn = QPushButton("Kick")
        self.tele_btn = QPushButton("Teleport")
        self.action_layout.insertWidget(2, self.kick_btn)
        self.action_layout.insertWidget(3, self.tele_btn)
