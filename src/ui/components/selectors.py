from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, 
                               QLineEdit, QPushButton, QLabel, QCheckBox, QDialog, 
                               QListWidget, QListWidgetItem, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt, Signal
from src.database.db_manager import DbManager
from src.core.data_manager import DataManager

class BitmaskSelector(QWidget):
    """
    A widget to select multiple flags from a bitmask using checkboxes.
    """
    valueChanged = Signal(int)

    def __init__(self, flags_dict, current_value=0, parent=None):
        super().__init__(parent)
        self.flags_dict = flags_dict # {1: "Name", 2: "Name"}
        self.current_value = current_value
        self.checkboxes = {}
        
        self.init_ui()

    def init_ui(self):
        # Use a grid layout in a scroll area if many flags
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Flags")
        grid = QGridLayout(group)
        
        row, col = 0, 0
        sorted_keys = sorted(self.flags_dict.keys())
        
        for flag in sorted_keys:
            name = self.flags_dict[flag]
            cb = QCheckBox(f"{name} ({flag})")
            cb.setChecked(bool(self.current_value & flag))
            cb.stateChanged.connect(self._update_value)
            
            grid.addWidget(cb, row, col)
            self.checkboxes[flag] = cb
            
            col += 1
            if col > 2: # 3 columns
                col = 0
                row += 1
                
        layout.addWidget(group)

    def _update_value(self):
        val = 0
        for flag, cb in self.checkboxes.items():
            if cb.isChecked():
                val |= flag
        self.current_value = val
        self.valueChanged.emit(val)

    def set_value(self, value):
        self.current_value = value
        for flag, cb in self.checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(bool(value & flag))
            cb.blockSignals(False)

    def value(self):
        return self.current_value


class SearchDialog(QDialog):
    """
    Generic Search Dialog for Creatures, Items, Spells.
    """
    def __init__(self, search_type="creature", parent=None):
        super().__init__(parent)
        self.search_type = search_type # creature, item, spell
        self.selected_id = None
        self.selected_name = None
        self.db = DbManager.get_instance()
        
        self.setWindowTitle(f"Search {search_type.capitalize()}")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search Bar
        h = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Name or ID...")
        self.inp_search.returnPressed.connect(self.perform_search)
        
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self.perform_search)
        
        h.addWidget(self.inp_search)
        h.addWidget(btn_search)
        layout.addLayout(h)
        
        # Results List
        self.list_results = QListWidget()
        self.list_results.itemDoubleClicked.connect(self.select_item)
        layout.addWidget(self.list_results)
        
        # Actions
        h2 = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Select")
        btn_ok.clicked.connect(self.accept_selection)
        
        h2.addStretch()
        h2.addWidget(btn_cancel)
        h2.addWidget(btn_ok)
        layout.addLayout(h2)

    def perform_search(self):
        term = self.inp_search.text().strip()
        if not term: return
        
        self.list_results.clear()
        
        # Determine Query based on type
        # Basic LIKE queries with strict limit
        results = []
        limit = 50
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if self.search_type == "creature":
                q = f"SELECT entry as id, name FROM creature_template WHERE name LIKE %s OR entry = %s LIMIT {limit}"
            elif self.search_type == "item":
                q = f"SELECT entry as id, name FROM item_template WHERE name LIKE %s OR entry = %s LIMIT {limit}"
            elif self.search_type == "spell":
                 # spell is often in `spell_template` or `spell` depending on core (AzerothCore uses DBC usually, but `spell` table might exist for custom or strict lookup?)
                 # Actually AC has `spell_dbc` or we rely on DBC files. DbManager doesn't usually load DBCs directly here purely via SQL unless imported.
                 # Let's check if `spell_template` exists (often custom) or if we just query `spell_dbc` table if it exists?
                 # Standard AC stores spells in DBCs. We might not have a SQL table for Spells unless `spell_dbc` was imported to DB.
                 # Fallback: Assume `spell_dbc` table exists or skip spell search for now?
                 # Let's try `spell_dbc` (often used in world db for servers).
                 q = f"SELECT Id as id, SpellName as name FROM spell_dbc WHERE SpellName LIKE %s OR Id = %s LIMIT {limit}"
                 pass 
            
            # Param handling
            # If term is int, use it for ID check, otherwise 0
            id_val = int(term) if term.isdigit() else 0
            name_val = f"%{term}%"
            
            # Need to handle Spell table name carefully.
            # If spell, let's try safely.
            if self.search_type == "spell":
                 # Check if spell_dbc table exists first? Or just try.
                 # Safe bet: Try checking `spell_dbc` first
                 # Update: Found Name_Lang_enUS column
                 q = f"SELECT Id as id, Name_Lang_enUS as name FROM spell_dbc WHERE Name_Lang_enUS LIKE %s OR Id = %s LIMIT {limit}"
                 try:
                     cursor.execute(q, (name_val, id_val))
                     results = cursor.fetchall()
                 except Exception as e:
                     # Fallback or empty
                     print(f"Searching spells via SQL failed: {e}")
                     results = []
            elif self.search_type == "quest":
                q = f"SELECT ID as id, LogTitle as name FROM quest_template WHERE LogTitle LIKE %s OR ID = %s LIMIT {limit}"
                cursor.execute(q, (name_val, id_val))
                results = cursor.fetchall()
            else:
                 cursor.execute(q, (name_val, id_val))
                 results = cursor.fetchall()
            
            conn.close()
            
            for r in results:
                name = r.get('name') or r.get('SpellName') or "Unknown"
                i = QListWidgetItem(f"[{r['id']}] {name}")
                i.setData(Qt.UserRole, r['id'])
                i.setData(Qt.UserRole+1, name)
                self.list_results.addItem(i)
                
        except Exception as e:
            print(f"Search Error: {e}")

    def select_item(self, item):
        self.selected_id = item.data(Qt.UserRole)
        self.selected_name = item.data(Qt.UserRole+1)
        self.accept()

    def accept_selection(self):
        item = self.list_results.currentItem()
        if item:
            self.select_item(item)


class SmartSelector(QWidget):
    """
    Widget: [ID Input] [Search Button] -> Displays Name
    """
    valueChanged = Signal(int)

    def __init__(self, selector_type="creature", parent=None):
        super().__init__(parent)
        self.selector_type = selector_type
        self.db = DbManager.get_instance()
        self.init_ui()

    def set_selector_type(self, new_type):
        self.selector_type = new_type
        self.inp_id.clear()
        self.lbl_name.setText("None")

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.inp_id = QLineEdit()
        self.inp_id.setPlaceholderText("ID")
        self.inp_id.setMaximumWidth(80)
        self.inp_id.editingFinished.connect(self.on_id_changed)
        
        self.btn_search = QPushButton("?")
        self.btn_search.setMaximumWidth(30)
        self.btn_search.clicked.connect(self.open_search)
        
        self.lbl_name = QLabel("None")
        self.lbl_name.setStyleSheet("color: gray; font-style: italic;")
        
        layout.addWidget(self.inp_id)
        layout.addWidget(self.btn_search)
        layout.addWidget(self.lbl_name)
        layout.addStretch()

    def set_value(self, val):
        self.inp_id.setText(str(val))
        self.on_id_changed() # Trigger lookup

    def value(self):
        try:
            return int(self.inp_id.text())
        except:
            return 0

    def on_id_changed(self):
        val_str = self.inp_id.text().strip()
        if not val_str or not val_str.isdigit():
            self.lbl_name.setText("None")
            return
            
        val = int(val_str)
        self.resolve_name(val)
        self.valueChanged.emit(val)

    def clear(self):
        self.inp_id.clear()
        self.lbl_name.setText("None")
        self.valueChanged.emit(0)

    def resolve_name(self, val):
        # Fetch name from DB based on type
        # We can do a quick check via DbManager or direct query?
        # Let's add simple helper or do direct query here (simple enough)
        
        name = "Unknown"
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if self.selector_type == "creature":
                cursor.execute("SELECT name FROM creature_template WHERE entry = %s", (val,))
            elif self.selector_type == "item":
                cursor.execute("SELECT name FROM item_template WHERE entry = %s", (val,))
            elif self.selector_type == "spell":
                 # Try spell_dbc
                 try:
                     cursor.execute("SELECT Name_Lang_enUS FROM spell_dbc WHERE Id = %s", (val,))
                 except:
                     name = "Spell (DB lookup failed)"
                     conn.close()
                     self.lbl_name.setText(name)
                     return
            elif self.selector_type == "quest":
                cursor.execute("SELECT LogTitle FROM quest_template WHERE ID = %s", (val,))
            
            res = cursor.fetchone()
            conn.close()
            
            if res:
                name = res[0]
                
        except Exception:
            pass
            
        self.lbl_name.setText(name)

    def open_search(self):
        dlg = SearchDialog(self.selector_type, self)
        if dlg.exec():
            if dlg.selected_id is not None:
                self.inp_id.setText(str(dlg.selected_id))
                self.lbl_name.setText(dlg.selected_name)
                self.valueChanged.emit(dlg.selected_id)


class ZoneSearchDialog(QDialog):
    """
    Dialog to search Quest Sorts (Negative IDs) and Zones (Positive IDs) from DBC data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dm = DataManager() # Access loaded DBCs
        self.selected_id = None
        self.selected_name = None
        
        self.setWindowTitle("Select Quest Sort / Zone")
        self.resize(600, 500)
        self.init_ui()
        
        # Load initial data
        self.all_items = [] # (id, name, type_label)
        self.load_items()
        self.perform_search() # Show all

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search
        h = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Filter (e.g. 'Dragon', 'Epic')...")
        self.inp_search.textChanged.connect(self.perform_search)
        h.addWidget(self.inp_search)
        layout.addLayout(h)
        
        # List
        self.list_results = QListWidget()
        self.list_results.itemDoubleClicked.connect(self.select_item)
        layout.addWidget(self.list_results)
        
        # Actions
        h2 = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        layout.addLayout(h2)

    def load_items(self):
        self.all_items = []
        
        # 1. Quest Sorts (ID -> Negative)
        # DBC ID is positive, but in quest_template it's negative.
        # e.g. ID 1 (Epic) -> -1
        for qs_id, name in self.dm.quest_sorts.items():
            final_id = -int(qs_id)
            self.all_items.append((final_id, name, "[Category]"))
            
        # 2. Areas (ID -> Positive)
        for area_id, name in self.dm.areas.items():
            self.all_items.append((int(area_id), name, "[Zone]"))
            
        # Sort by Name
        self.all_items.sort(key=lambda x: x[1])

    def perform_search(self):
        term = self.inp_search.text().lower().strip()
        self.list_results.clear()
        
        count = 0
        limit = 200 # Don't flood
        
        for pid, name, lbl in self.all_items:
            # Filter
            if not term or term in name.lower() or term == str(pid):
                display = f"{lbl} {name} ({pid})"
                item = QListWidgetItem(display)
                item.setData(Qt.UserRole, pid)
                item.setData(Qt.UserRole+1, name)
                
                # Color code
                if lbl == "[Category]":
                    item.setForeground(Qt.blue)
                
                self.list_results.addItem(item)
                count += 1
                if count >= limit:
                    break

    def select_item(self, item):
        self.selected_id = item.data(Qt.UserRole)
        self.selected_name = item.data(Qt.UserRole+1)
        self.accept()


class ZoneSortSelector(QWidget):
    """
    Selector for Quest Sort/Zone ID.
    """
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dm = DataManager()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.inp_id = QLineEdit()
        self.inp_id.setPlaceholderText("ID")
        self.inp_id.setMaximumWidth(80)
        self.inp_id.editingFinished.connect(self.on_id_changed)
        
        self.btn_search = QPushButton("?")
        self.btn_search.setMaximumWidth(30)
        self.btn_search.clicked.connect(self.open_search)
        
        self.lbl_name = QLabel("None")
        self.lbl_name.setStyleSheet("color: gray; font-style: italic;")
        
        layout.addWidget(self.inp_id)
        layout.addWidget(self.btn_search)
        layout.addWidget(self.lbl_name)
        layout.addStretch()

    def set_value(self, val):
        self.inp_id.setText(str(val))
        self.resolve_name(val) # Update label
    
    def value(self):
        try:
            return int(self.inp_id.text())
        except:
            return 0

    def on_id_changed(self):
        try:
            val = int(self.inp_id.text())
        except:
            val = 0
        self.resolve_name(val)
        self.valueChanged.emit(val)

    def resolve_name(self, val):
        # Look up in DataManager
        name = "Unknown"
        if val == 0:
            name = "General (None)"
        elif val < 0:
            # QuestSort
            lookup_id = -val
            name = self.dm.quest_sorts.get(lookup_id, "Unknown Sort")
            name = f"[Category] {name}"
        else:
            # Area
            name = self.dm.areas.get(val, "Unknown Zone")
            name = f"[Zone] {name}"
            
        self.lbl_name.setText(name)

    def open_search(self):
        dlg = ZoneSearchDialog(self)
        if dlg.exec():
            if dlg.selected_id is not None:
                self.inp_id.setText(str(dlg.selected_id))
                self.resolve_name(dlg.selected_id)
                self.valueChanged.emit(dlg.selected_id)
