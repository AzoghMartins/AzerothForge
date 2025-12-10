from src.ui.components.base_manager import BaseManagerTab

class ItemTab(BaseManagerTab):
    def __init__(self, parent=None):
        super().__init__("Items", parent)
        self.table.setHorizontalHeaderLabels(["Entry", "Name", "Quality", "Inventory Type"])
