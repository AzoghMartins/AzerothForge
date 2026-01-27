from src.ui.components.base_manager import BaseManagerTab
from src.database.db_manager import DbManager
from src.ui.components.worker import SearchWorker
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt

class QuestTab(BaseManagerTab):
    def __init__(self, campaign_manager, parent=None):
        self.campaign_manager = campaign_manager
        super().__init__("Quests", parent)
        self.search_worker = None
        
        # Customize Table
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Level", "Rew Money", "Starters", "Enders"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        # Keep only Edit for now
        self.new_btn.setVisible(False)
        self.delete_btn.setVisible(False)
        
        # Initial Load: Removed.

    def on_search(self):
        # Override Base
        search_text = self.search_input.text().strip()
        
        db = DbManager.get_instance()
        active_campaign = self.campaign_manager.get_active_campaign()
        realm_id = active_campaign.get("dev_realm_id") if active_campaign else None
        
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            
        self.search_worker = SearchWorker(db.search_quests, search_text, realm_id=realm_id)
        self.search_worker.results_ready.connect(self.populate_table)
        self.search_worker.start()

    def populate_table(self, quests):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        # Global Search = White Text
        text_color = QBrush(QColor("white"))

        for row_data in quests:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            q_id = row_data['ID']
            title = row_data.get('LogTitle', 'Unknown')
            level = row_data.get('QuestLevel', 0)
            money = row_data.get('RewardMoney', 0)
            
            # Prefer Names if available, fallback to IDs - (search_quests might not return names if minimal query used, but DbManager.search_quests selects specific fields. Starters/Enders names aren't in search_quests result set to keep it fast, so we might miss them here unless we join.
            # DbManager.search_quests returns ID, LogTitle, QuestLevel, MinLevel, Money, XP.
            # It does NOT return Starters/Enders. 
            # I must fix that if I want to show them, OR just show empty/basic info.
            # To keep it fast, maybe omit Starter/Ender columns or fetch on separate details?
            # Or update search_quests to join? Joining might be slow.
            # Let's keep starter/ender empty or remove columns? 
            # The original `get_all_quests` did NOT join either usually unless specified.
            # Checked `get_all_quests`: It did `SELECT *` from `quest_template`, and `Starters` comes from lookup?
            # Actually `get_all_quests` in original code (viewed earlier) used `quest_template` but did it have starters?
            # The viewer saw `get_all_quests` doing `SELECT *`. `quest_template` does NOT have Starter/Ender columns (they are in `creature_queststarter`).
            # So the original `populate_table` trying to get `Starters` / `StarterNames` relied on `get_all_quests` doing a JOIN or post-process?
            # Looking at previous logs/code: `get_campaign_dependencies` did joins. `get_all_quests` just `SELECT *`.
            # So `Starters`/`Enders` in `populate_table` might have been from a joined query I replaced?
            # Wait, `get_all_quests` in `db_manager.py` (before refactor) was `SELECT *`.
            # Unless `quest_template` has a VIEW or customized core? Standard AC `quest_template` no longer has Start/End script columns sometimes?
            # actually `StartScript` / `CompleteScript` exist but those are scripts.
            # `creature_queststarter` is the table.
            # So `Starters` in `populate_table` probably wasn't working or relied on a custom query I didn't see fully.
            # Regardless, for FAST search, I will omit Starters/Enders or just show simple data.
            # Users want fast lookup.
            
            starters_display = "" 
            enders_display = ""
            
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setForeground(text_color)
                if text == str(q_id):
                    item.setData(Qt.UserRole, q_id)
                    item.setData(Qt.UserRole + 1, True) # Valid
                return item

            self.table.setItem(row, 0, create_item(q_id))
            self.table.setItem(row, 1, create_item(title))
            self.table.setItem(row, 2, create_item(level))
            self.table.setItem(row, 3, create_item(money))
            self.table.setItem(row, 4, create_item(starters_display))
            self.table.setItem(row, 5, create_item(enders_display))
            
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

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection", "Please select a quest first.")
            return
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        quest_id = int(id_item.text())
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
        from src.ui.editors.quest_editor import QuestEditor
        editor = QuestEditor(quest_id, dev_realm_config, self)
        if editor.exec():
            self.on_search()

    def on_realm_changed(self):
        self.on_search()
