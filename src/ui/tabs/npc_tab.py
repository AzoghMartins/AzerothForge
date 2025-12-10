from src.ui.components.base_manager import BaseManagerTab
from src.ui.editors.npc_editor import NpcEditorDialog

class NpcTab(BaseManagerTab):
    def __init__(self, parent=None):
        super().__init__("NPCs", parent)
        self.customize_ui()

    def customize_ui(self):
        self.table.setHorizontalHeaderLabels(["Entry", "Name", "Subname", "Level"])

    def on_new(self):
        dialog = NpcEditorDialog(self)
        dialog.exec()
