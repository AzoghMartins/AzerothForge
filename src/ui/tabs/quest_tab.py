from src.ui.components.base_manager import BaseManagerTab

class QuestTab(BaseManagerTab):
    def __init__(self, parent=None):
        super().__init__("Quests", parent)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Level", "Rew Money"])
