from src.ui.components.base_manager import BaseManagerTab
from src.ui.editors.npc_editor import NpcEditorDialog
from src.database.db_manager import DbManager
from src.ui.components.worker import SearchWorker
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt

class NpcTab(BaseManagerTab):
    def __init__(self, campaign_manager, parent=None):
        self.campaign_manager = campaign_manager
        super().__init__("NPCs", parent)
        self.customize_ui()
        self.search_worker = None

    def customize_ui(self):
        # Keep only Edit for now
        self.new_btn.setVisible(False)
        self.delete_btn.setVisible(False)

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Entry", "Name", "Subname", "Level", "Flags"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def on_search(self):
        # Override Base Search
        search_text = self.search_input.text().strip()
        
        db = DbManager.get_instance()
        active_campaign = self.campaign_manager.get_active_campaign()
        realm_id = active_campaign.get("dev_realm_id") if active_campaign else None
        
        # Disable search btn or show loading?
        # BaseManagerTab doesn't expose button easily, but we can set cursor?
        # For now, just fire worker.
        
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate() # Cancel previous
            
        self.search_worker = SearchWorker(db.search_creatures, search_text, realm_id=realm_id)
        self.search_worker.results_ready.connect(self.populate_table)
        self.search_worker.start()

    def populate_table(self, npcs):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        # Color: White for all (Global Search)
        text_color = QBrush(QColor("white")) 
        
        for row_data in npcs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            entry = row_data['entry']
            name = row_data.get('name', 'Unknown')
            subname = row_data.get('subname', '') or ""
            min_lvl = row_data.get('minlevel', 0)
            max_lvl = row_data.get('maxlevel', 0)
            level_str = f"{min_lvl}" if min_lvl == max_lvl else f"{min_lvl}-{max_lvl}"
            flags = row_data.get('npcflag', 0)
            
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setForeground(text_color)
                if text == str(entry):
                    item.setData(Qt.UserRole, entry)
                    # Validity is always true in global search mode for purpose of editing?
                    # User said: "NOT show ... in red". "Lookup tables".
                    # However, can we Edit/Delete? 
                    # If we edit an NPC outside our range, we might violate campaign rules?
                    # User didn't specify editing constraints, just search/view.
                    # Let's assume valid = True for interaction.
                    item.setData(Qt.UserRole + 1, True)
                return item

            self.table.setItem(row, 0, create_item(entry))
            self.table.setItem(row, 1, create_item(name))
            self.table.setItem(row, 2, create_item(subname))
            self.table.setItem(row, 3, create_item(level_str))
            self.table.setItem(row, 4, create_item(flags))
            
        self.table.setSortingEnabled(True)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.edit_btn.setEnabled(False)
            return
            
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        is_valid = id_item.data(Qt.UserRole + 1)
        
        self.edit_btn.setEnabled(is_valid)

    def on_new(self):
        pass

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection", "Please select an NPC first.")
            return
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        npc_id = int(id_item.text())
        active_campaign = self.campaign_manager.get_active_campaign()
        if not active_campaign:
            QMessageBox.warning(self, "Campaign", "No active campaign loaded.")
            return
        from src.core.config_manager import ConfigManager
        cm = ConfigManager()
        dev_realm_id = active_campaign.get("dev_realm_id")
        dev_realm_config = cm.get_active_realm()
        if dev_realm_id:
            realms = cm.get_realms()
            found = next((r for r in realms if r["id"] == dev_realm_id), None)
            if found:
                dev_realm_config = found
        ranges = active_campaign.get("ranges", {}).get("creature", {})
        allowed_range = (ranges.get("start", 0), ranges.get("end", 0))
        from src.ui.editors.npc_editor_window import NpcEditorWindow
        editor = NpcEditorWindow(npc_id, active_campaign, dev_realm_config, cm,
                                 mode="update", allowed_id_range=allowed_range, parent=self)
        if editor.exec():
            self.on_search()
        
    def on_realm_changed(self):
        self.on_search()
