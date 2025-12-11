from src.ui.components.base_manager import BaseManagerTab
from src.ui.editors.npc_editor import NpcEditorDialog

class NpcTab(BaseManagerTab):
    def __init__(self, campaign_manager, parent=None):
        self.campaign_manager = campaign_manager
        super().__init__("NPCs", parent)
        self.customize_ui()

    def customize_ui(self):
        self.table.setHorizontalHeaderLabels(["Entry", "Name", "Subname", "Level"])

    def on_new(self):
        # Check for active campaign
        next_id = self.campaign_manager.get_next_id("creature")
        
        # Open Editor
        dialog = NpcEditorDialog(self, predefined_id=next_id)
        dialog.exec()
