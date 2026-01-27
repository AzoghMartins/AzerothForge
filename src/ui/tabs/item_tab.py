from src.ui.components.base_manager import BaseManagerTab
from src.database.db_manager import DbManager
from src.ui.components.worker import SearchWorker
from PySide6.QtWidgets import (QPushButton, QTableWidgetItem, QAbstractItemView, QHeaderView, 
                               QMessageBox, QInputDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from src.utils.game_constants import ITEM_QUALITY_COLORS

class ItemTab(BaseManagerTab):
    update_signal = Signal(list)

    def __init__(self, config_manager, parent=None):
        self.config_manager = config_manager
        super().__init__("Items", parent)
        self.customize_ui()
        self.search_worker = None
        
        # Initial search removed

    def on_realm_changed(self):
        super().on_realm_changed()
        self.on_search()

    def customize_ui(self):
        # Hide default buttons we don't use yet
        self.new_btn.setVisible(False)
        self.delete_btn.setVisible(False)
        self.edit_btn.setVisible(True)
        
        # Columns: Entry ID, Name, iLvl, Req Lvl, Class/SubClass
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Entry ID", "Name", "iLvl", "Req Lvl", "Class/SubClass"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Resize Entry ID column to contents
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def on_search(self):
        search_text = self.search_input.text().strip()
        db = DbManager.get_instance()
        
        # Resolve Active Realm ID
        from src.core.campaign_manager import CampaignManager
        cm = CampaignManager(self.config_manager)
        active_campaign = cm.get_active_campaign()
        realm_id = active_campaign.get("dev_realm_id") if active_campaign else None
        
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            
        self.search_worker = SearchWorker(db.search_items, search_text, realm_id=realm_id)
        self.search_worker.results_ready.connect(self.update_table)
        self.search_worker.start()

    def update_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            # entry, name, ItemLevel, RequiredLevel, Quality, class, subclass
            entry = row['entry']
            name = row.get('name', 'Unknown')
            ilvl = row.get('ItemLevel', 0)
            req_lvl = row.get('RequiredLevel', 0)
            quality = row.get('Quality', 1)
            cls = row.get('class', 0)
            subcls = row.get('subclass', 0)
            
            # Coloring by Quality only
            color_hex = ITEM_QUALITY_COLORS.get(quality, "#ffffff")
            text_color = QBrush(QColor(color_hex))
            
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setForeground(text_color)
                # Ensure data is set for ID column
                if str(text) == str(entry):
                    item.setData(Qt.UserRole, entry)
                    item.setData(Qt.UserRole + 1, True) # Valid
                return item

            self.table.setItem(r, 0, create_item(entry))
            self.table.setItem(r, 1, create_item(name))
            self.table.setItem(r, 2, create_item(ilvl))
            self.table.setItem(r, 3, create_item(req_lvl))
            self.table.setItem(r, 4, create_item(f"{cls} / {subcls}"))
 
        self.table.setSortingEnabled(True)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.edit_btn.setEnabled(False)
            return
            
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        is_valid = id_item.data(Qt.UserRole + 1)
        
        self.edit_btn.setEnabled(bool(is_valid))

    def on_edit(self):
        QMessageBox.information(self, "Coming Soon", "Item editor not implemented yet.")
