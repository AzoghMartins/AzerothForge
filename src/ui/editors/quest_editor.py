
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
                               QLabel, QLineEdit, QSpinBox, QCheckBox, QTextEdit, 
                               QPushButton, QFormLayout, QGroupBox, QGridLayout, QMessageBox, 
                               QScrollArea, QComboBox, QListWidget, QListWidgetItem,
                               QTableWidget, QHeaderView)
from PySide6.QtCore import Qt
from functools import partial
import copy
from src.database.db_manager import DbManager
from src.ui.components.selectors import SmartSelector, BitmaskSelector, ZoneSortSelector
from src.ui.components.objective_row import ObjectiveRow
from src.utils.game_constants import QUEST_TYPES, QUEST_FLAGS, XP_DIFFICULTY, SMART_EVENT, SMART_ACTION, SMART_TARGET

class QuestEditor(QDialog):
    def __init__(self, quest_id, realm_config, parent=None):
        super().__init__(parent)
        self.quest_id = quest_id
        self.realm_config = realm_config
        self.db = DbManager.get_instance()
        
        self.setWindowTitle(f"Quest Editor - ID {quest_id}")
        self.resize(900, 750)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Header
        self.lbl_title = QLabel(f"Editing Quest {self.quest_id}")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(self.lbl_title)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 1. General
        self.tab_general = QWidget()
        self.init_general_tab()
        self.tabs.addTab(self.tab_general, "General")
        
        # 2. Texts
        self.tab_texts = QWidget()
        self.init_texts_tab()
        self.tabs.addTab(self.tab_texts, "Texts")
        
        # 3. Objectives
        self.tab_objectives = QWidget()
        self.init_objectives_tab()
        self.tabs.addTab(self.tab_objectives, "Objectives")
        
        # 4. Rewards
        self.tab_rewards = QWidget()
        self.init_rewards_tab()
        self.tabs.addTab(self.tab_rewards, "Rewards")
        
        # 5. Connected NPCs
        self.tab_connected = QWidget()
        self.init_connected_tab()
        self.tabs.addTab(self.tab_connected, "Connected NPCs")
        
        # 6. Extras (Phasing, Emotes)
        self.tab_extras = QWidget()
        self.init_extras_tab()
        self.tabs.addTab(self.tab_extras, "Extras")
        
        # Footer
        footer = QHBoxLayout()
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_data)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_delete = QPushButton("Delete Quest")
        self.btn_delete.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.on_delete)
        
        footer.addWidget(self.btn_delete)
        footer.addStretch()
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        main_layout.addLayout(footer)

    def init_general_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)
        scroll.setWidget(content)
        
        self.inp_title = QLineEdit()
        self.inp_min_level = QSpinBox()
        self.inp_min_level.setRange(0, 80)
        self.inp_quest_level = QSpinBox()
        self.inp_quest_level.setRange(-1, 83)
        
        # Type Dropdown
        self.combo_type = QComboBox()
        for k, v in QUEST_TYPES.items():
            self.combo_type.addItem(f"{v} ({k})", k)
            
        # Suggested Group
        self.inp_suggested_groups = QSpinBox()
        self.inp_suggested_groups.setRange(0, 40)
        
        # Suggested Group
        self.inp_suggested_groups = QSpinBox()
        self.inp_suggested_groups.setRange(0, 40)
        
        # Zone / Sort ID
        self.inp_zone_sort = ZoneSortSelector()

        # Prerequisite Quest
        self.sel_prev_quest = SmartSelector("quest") # We need to handle 'quest' type in Selector or treat as basic ID
        # Since SmartSelector defaults to ID input, it works, but Name resolution needs 'quest_template' logic in Selector.
        # Let's assume standard ID for now, or update Selector later if needed.
        # Ideally we update Selector to support 'quest' type lookup.
        
        # Flags (Bitmask)
        self.flags_selector = BitmaskSelector(QUEST_FLAGS)
        
        layout.addRow("Log Title:", self.inp_title)
        layout.addRow("Min Level:", self.inp_min_level)
        layout.addRow("Quest Level:", self.inp_quest_level)
        layout.addRow("Type:", self.combo_type)
        layout.addRow("Suggested Players:", self.inp_suggested_groups)
        layout.addRow("Category / Sort ID:", self.inp_zone_sort)
        layout.addRow("Prerequisite Quest:", self.sel_prev_quest)
        layout.addRow("Flags:", self.flags_selector)
        
        l = QVBoxLayout(self.tab_general)
        l.addWidget(scroll)

    def init_texts_tab(self):
        layout = QFormLayout(self.tab_texts)
        
        self.inp_log_desc = QTextEdit()
        self.inp_log_desc.setMaximumHeight(80)
        
        self.inp_quest_desc = QTextEdit() # Offer text
        
        self.inp_area_desc = QTextEdit()
        self.inp_area_desc.setMaximumHeight(60)
        
        self.inp_completion_log = QTextEdit()
        self.inp_completion_log.setMaximumHeight(60)
        self.inp_completion_log.setPlaceholderText("Shown in Quest Log/Tracker when objective complete")
        
        self.inp_reward_text = QTextEdit()
        self.inp_reward_text.setMaximumHeight(80)
        self.inp_reward_text.setPlaceholderText("Spoken by NPC when turning in the quest")

        layout.addRow("Log Description:", self.inp_log_desc)
        layout.addRow("Offer Text (Gossip):", self.inp_quest_desc)
        layout.addRow("Area Description:", self.inp_area_desc)
        layout.addRow("Completion Log Text:", self.inp_completion_log)
        layout.addRow("Reward Text (NPC):", self.inp_reward_text)

    def init_objectives_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        
        # Text
        grp_texts = QGroupBox("Objective Texts")
        form = QFormLayout(grp_texts)
        self.obj_texts = []
        for i in range(4):
            le = QLineEdit()
            self.obj_texts.append(le)
            form.addRow(f"Obj Text {i+1}:", le)
        layout.addWidget(grp_texts)
        
        # NPCs/GOs
        grp_npcs = QGroupBox("Required NPCs / GameObjects / Talk")
        vbox_n = QVBoxLayout(grp_npcs)
        self.req_npcs = [] 
        for i in range(4):
            lbl = QLabel(f"Objective {i+1}:")
            row = ObjectiveRow()
            
            # Pass Context
            row.set_quest_context(self.quest_id, self.realm_config.get("id"))
            
            self.req_npcs.append(row)
            # Layout...
            h = QHBoxLayout()
            h.addWidget(lbl)
            h.addWidget(row)
            vbox_n.addLayout(h)
        layout.addWidget(grp_npcs)
        
        # Items
        grp_items = QGroupBox("Required Items")
        grid_i = QGridLayout(grp_items)
        self.req_items = []
        for i in range(6):
            row = i // 2
            col_base = (i % 2) * 3
            
            sel = SmartSelector("item")
            spin_count = QSpinBox()
            spin_count.setRange(0, 255)
            spin_count.setPrefix("x")
            
            self.req_items.append((sel, spin_count))
            
            grid_i.addWidget(sel, row, col_base)
            grid_i.addWidget(spin_count, row, col_base+1)
        layout.addWidget(grp_items)
        
        fl = QVBoxLayout(self.tab_objectives)
        fl.addWidget(scroll)

    def init_rewards_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        
        # Basic
        grp_basic = QGroupBox("Basic Rewards")
        form = QFormLayout(grp_basic)
        
        self.rew_money = QSpinBox()
        self.rew_money.setRange(0, 99999999) # Copper
        
        self.combo_xp = QComboBox()
        for k, v in XP_DIFFICULTY.items():
            self.combo_xp.addItem(f"{v} ({k})", k)
            
        self.rew_mail_tpl = QSpinBox() # Mail ID
        self.rew_mail_delay = QSpinBox() # Seconds
        
        form.addRow("Money (Copper):", self.rew_money)
        form.addRow("XP Difficulty:", self.combo_xp)
        form.addRow("Mail Template ID:", self.rew_mail_tpl)
        form.addRow("Mail Delay (Secs):", self.rew_mail_delay)
        layout.addWidget(grp_basic)
        
        # Fixed Items
        grp_fixed = QGroupBox("Fixed Item Rewards")
        grid_f = QGridLayout(grp_fixed)
        self.rew_fixed = []
        for i in range(4):
            sel = SmartSelector("item")
            cnt = QSpinBox()
            cnt.setRange(0, 255)
            cnt.setPrefix("x")
            self.rew_fixed.append((sel, cnt))
            grid_f.addWidget(QLabel(f"Slot {i+1}"), i, 0)
            grid_f.addWidget(sel, i, 1)
            grid_f.addWidget(cnt, i, 2)
        layout.addWidget(grp_fixed)
        
        # Choice Items
        grp_choice = QGroupBox("Choice Item Rewards")
        grid_c = QGridLayout(grp_choice)
        self.rew_choice = []
        for i in range(6):
            row = i // 2
            col = (i % 2) * 2
            sel = SmartSelector("item")
            cnt = QSpinBox()
            cnt.setRange(0, 255)
            cnt.setPrefix("x")
            self.rew_choice.append((sel, cnt))
            grid_c.addWidget(sel, row, col)
            grid_c.addWidget(cnt, row, col+1)
        layout.addWidget(grp_choice)
        
        fl = QVBoxLayout(self.tab_rewards)
        fl.addWidget(scroll)

    def init_connected_tab(self):
        layout = QVBoxLayout(self.tab_connected)
        
        # Starters
        grp_start = QGroupBox("Quest Givers (Starters)")
        self.list_starters = QListWidget()
        hbox_s = QHBoxLayout()
        self.sel_starter = SmartSelector("creature")
        btn_add_starter = QPushButton("Add")
        btn_add_starter.clicked.connect(self.add_starter)
        btn_del_starter = QPushButton("Remove")
        btn_del_starter.clicked.connect(lambda: self._remove_list_item(self.list_starters))
        hbox_s.addWidget(self.sel_starter)
        hbox_s.addWidget(btn_add_starter)
        vb_s = QVBoxLayout(grp_start)
        vb_s.addWidget(self.list_starters)
        vb_s.addLayout(hbox_s)
        vb_s.addWidget(btn_del_starter)
        layout.addWidget(grp_start)
        
        # Enders
        grp_end = QGroupBox("Quest Enders (Turn-In)")
        self.list_enders = QListWidget()
        hbox_e = QHBoxLayout()
        self.sel_ender = SmartSelector("creature")
        btn_add_ender = QPushButton("Add")
        btn_add_ender.clicked.connect(self.add_ender)
        btn_del_ender = QPushButton("Remove")
        btn_del_ender.clicked.connect(lambda: self._remove_list_item(self.list_enders))
        hbox_e.addWidget(self.sel_ender)
        hbox_e.addWidget(btn_add_ender)
        vb_e = QVBoxLayout(grp_end)
        vb_e.addWidget(self.list_enders)
        vb_e.addLayout(hbox_e)
        vb_e.addWidget(btn_del_ender)
        layout.addWidget(grp_end)

    def add_starter(self):
        val = self.sel_starter.value()
        if val:
            name = self.sel_starter.lbl_name.text()
            item = QListWidgetItem(f"{name} ({val})")
            item.setData(Qt.UserRole, val)
            self.list_starters.addItem(item)
            self.sel_starter.set_value(0) # Reset

    def add_ender(self):
        val = self.sel_ender.value()
        if val:
            name = self.sel_ender.lbl_name.text()
            item = QListWidgetItem(f"{name} ({val})")
            item.setData(Qt.UserRole, val)
            self.list_enders.addItem(item)
            self.sel_ender.set_value(0)

    def add_spell_area_row(self, spell_id=0, area_id=0, autocast=1):
        row = self.table_spell_area.rowCount()
        self.table_spell_area.insertRow(row)
        
        # Spell Selector? QTableWidget cell widget.
        sel_spell = SmartSelector("spell")
        if spell_id: sel_spell.set_value(spell_id)
        
        inp_area = QSpinBox()
        inp_area.setRange(0, 99999)
        inp_area.setValue(area_id)
        
        chk_auto = QCheckBox()
        chk_auto.setChecked(bool(autocast))
        
        self.table_spell_area.setCellWidget(row, 0, sel_spell)
        self.table_spell_area.setCellWidget(row, 1, inp_area)
        self.table_spell_area.setCellWidget(row, 2, chk_auto)

    def _del_spell_area_row(self):
        row = self.table_spell_area.currentRow()
        if row >= 0:
            self.table_spell_area.removeRow(row)

    def _remove_list_item(self, list_widget):
        row = list_widget.currentRow()
        if row >= 0:
            list_widget.takeItem(row)

    def init_extras_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        
        # Phasing (Spells)
        grp_phase = QGroupBox("Phasing Spells (Legacy / Simple)")
        form_p = QFormLayout(grp_phase)
        
        lbl_info_1 = QLabel("<b>Cast on Accept (SourceSpell):</b> Applies spell ID on quest accept.")
        self.spell_accept = SmartSelector("spell") # SourceSpellID
        
        lbl_info_2 = QLabel("<b>Cast on Complete (RewardSpell):</b> Casts on quest complete.")
        self.spell_complete = SmartSelector("spell") # RewardSpell
        
        form_p.addRow(lbl_info_1)
        form_p.addRow("Cast on Accept:", self.spell_accept)
        form_p.addRow(lbl_info_2)
        form_p.addRow("Cast on Complete:", self.spell_complete)
        layout.addWidget(grp_phase)

        # Permanent Zone State (spell_area)
        grp_area = QGroupBox("Permanent Zone State (spell_area)")
        vbox_area = QVBoxLayout(grp_area)
        self.table_spell_area = QTableWidget()
        self.table_spell_area.setColumnCount(3)
        self.table_spell_area.setHorizontalHeaderLabels(["Phase Spell (Aura)", "Area ID", "Autocast"])
        self.table_spell_area.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        vbox_area.addWidget(self.table_spell_area)
        
        hbox_area_btns = QHBoxLayout()
        btn_add_area = QPushButton("Add Zone Phase")
        btn_add_area.clicked.connect(self.add_spell_area_row)
        btn_del_area = QPushButton("Remove Selected")
        btn_del_area.clicked.connect(self._del_spell_area_row)
        hbox_area_btns.addWidget(btn_add_area)
        hbox_area_btns.addWidget(btn_del_area)
        vbox_area.addLayout(hbox_area_btns)
        layout.addWidget(grp_area)
        
        # Triggered Phasing (SmartAI)
        grp_smart = QGroupBox("Triggered Phasing (SmartAI)")
        form_smart = QFormLayout(grp_smart)
        self.inp_phase_accept = QSpinBox()
        self.inp_phase_accept.setRange(0, 65535)
        self.inp_phase_complete = QSpinBox()
        self.inp_phase_complete.setRange(0, 65535)
        
        lbl_s1 = QLabel("<b>Phase Mask on Accept:</b> Sets phase mask immediately on accept (SmartAI on Quest Givers). 0 = Disabled.")
        lbl_s2 = QLabel("<b>Phase Mask on Complete:</b> Sets phase mask immediately on complete (SmartAI on Quest Givers). 0 = Disabled (usually 1 uses default).")
        
        form_smart.addRow(lbl_s1)
        form_smart.addRow("Mask on Accept:", self.inp_phase_accept)
        form_smart.addRow(lbl_s2)
        form_smart.addRow("Mask on Complete:", self.inp_phase_complete)
        layout.addWidget(grp_smart)
        
        # Emotes (Offer - quest_offer_reward)
        grp_offer = QGroupBox("Offer Reward Emotes (On Talk)")
        grid_o = QGridLayout(grp_offer)
        self.emotes_offer = [] # (EmoteID, DelayMs)
        for i in range(4):
            spin_e = QSpinBox() # Emote ID
            spin_e.setRange(0, 9999)
            spin_e.setPrefix(f"Emote {i+1}: ")
            spin_d = QSpinBox()
            spin_d.setRange(0, 60000)
            spin_d.setPrefix("Delay: ")
            spin_d.setSuffix(" ms")
            self.emotes_offer.append((spin_e, spin_d))
            grid_o.addWidget(spin_e, i, 0)
            grid_o.addWidget(spin_d, i, 1)
        layout.addWidget(grp_offer)
        
        # Emotes (Request - quest_request_items)
        grp_req = QGroupBox("Request Items Emotes (On Complete/Incomplete)")
        form_r = QFormLayout(grp_req)
        self.emote_complete = QSpinBox()
        self.emote_incomplete = QSpinBox()
        form_r.addRow("On Complete:", self.emote_complete)
        form_r.addRow("On Incomplete:", self.emote_incomplete)
        layout.addWidget(grp_req)
        
        fl = QVBoxLayout(self.tab_extras)
        fl.addWidget(scroll)

    def load_data(self):
        realm_id = self.realm_config.get("id")
        # Use Extended Fetch
        data = self.db.get_quest_extended(self.quest_id, realm_id)
        
        if not data or not data.get('template'):
            QMessageBox.critical(self, "Error", f"Could not load quest {self.quest_id}")
            self.close()
            return
            
        self.loaded_data = data # Store for safe saving (Merge logic)
        
        tpl = data['template']
        addon = data.get('addon') or {}
        offer = data.get('offer_reward') or {}
        req = data.get('request_items') or {}
        starters = data.get('starters') or []
        enders = data.get('enders') or []
        
        # --- General ---
        self.inp_title.setText(tpl.get("LogTitle") or "")
        self.inp_min_level.setValue(tpl.get("MinLevel", 0))
        self.inp_quest_level.setValue(tpl.get("QuestLevel", 1))
        
        idx = self.combo_type.findData(tpl.get("QuestInfoID", 0))
        if idx >= 0: self.combo_type.setCurrentIndex(idx)
        
        self.inp_suggested_groups.setValue(tpl.get("SuggestedGroupNum", 0))
        self.inp_suggested_groups.setValue(tpl.get("SuggestedGroupNum", 0))
        # Handle both naming conventions if core varies, usually QuestSortID or ZoneOrSort
        self.inp_zone_sort.set_value(tpl.get("QuestSortID", tpl.get("ZoneOrSort", 0)))
        
        self.flags_selector.set_value(tpl.get("Flags", 0))
        
        # Prerequisite
        # Prerequisite
        prev_quest = addon.get("PrevQuestID", 0)
        if prev_quest > 0:
            self.sel_prev_quest.set_value(prev_quest)
        else:
            self.sel_prev_quest.set_value(0)
            self.sel_prev_quest.clear() # Explicitly clear text if 0
        
        # --- Texts ---
        self.inp_log_desc.setText(tpl.get("LogDescription") or "")
        self.inp_quest_desc.setText(tpl.get("QuestDescription") or "")
        self.inp_area_desc.setText(tpl.get("AreaDescription") or "")
        self.inp_completion_log.setText(tpl.get("QuestCompletionLog"))
        
        # Load Rich Texts (Reward/Completion) - Decoupled
        rich = self.db.get_quest_rich_texts(self.quest_id, self.realm_config.get("id"))
        self.inp_reward_text.setText(rich.get("RewardText", ""))
        # We could load CompletionText too if we had a field, for now we fix RewardText coupling or "")
        
        # --- Objectives ---
        for i, le in enumerate(self.obj_texts):
            le.setText(tpl.get(f"ObjectiveText{i+1}") or "")
            
        special_flags = addon.get("SpecialFlags", 0)
        
        for i, row_widget in enumerate(self.req_npcs):
            rid = tpl.get(f"RequiredNpcOrGo{i+1}", 0)
            rcount = tpl.get(f"RequiredNpcOrGoCount{i+1}", 0)
            
            # Heuristic for Type
            # 1. Negative ID = Interact with GameObject
            # 2. Positive ID + SpecialFlags & 2 = Talk to NPC
            # 3. Positive ID = Slay Creature (Default)
            
            if rid < 0:
                 row_widget.set_type_externally("Interact with GameObject")
                 rid = abs(rid)
                 row_widget.set_target(rid, rcount)
            elif rid > 0:
                # Positive ID, check for Talk vs Slay
                is_talk, menu_id = self.db.check_talk_objective(rid, self.quest_id, realm_id)
                
                if is_talk:
                    row_widget.set_type_externally("Talk to NPC")
                    # Fetch and set gossip data
                    npc_text, option_text = self.db.get_gossip_data(menu_id, realm_id)
                    row_widget.set_gossip_data(npc_text, option_text)
                else:
                    row_widget.set_type_externally("Slay Creature")
                    
                row_widget.set_target(rid, rcount)
            else: 
                 row_widget.clear()
            
        for i, (sel, spin_cnt) in enumerate(self.req_items):
            sel.set_value(tpl.get(f"RequiredItemId{i+1}", 0))
            spin_cnt.setValue(tpl.get(f"RequiredItemCount{i+1}", 0))
            
        # --- Rewards ---
        self.rew_money.setValue(tpl.get("RewardMoney", 0))
        
        idx_xp = self.combo_xp.findData(tpl.get("RewardXPDifficulty", 0))
        if idx_xp >= 0: self.combo_xp.setCurrentIndex(idx_xp)
        
        # RewardMail fields (in Addon usually, but sometimes Template? Check Addon first)
        self.rew_mail_tpl.setValue(addon.get("RewardMailTemplateID", 0)) 
        self.rew_mail_delay.setValue(addon.get("RewardMailDelay", 0))
        
        for i, (sel, cnt) in enumerate(self.rew_fixed):
             sel.set_value(tpl.get(f"RewardItem{i+1}", 0))
             cnt.setValue(tpl.get(f"RewardAmount{i+1}", 0))
             
        for i, (sel, cnt) in enumerate(self.rew_choice):
             sel.set_value(tpl.get(f"RewardChoiceItemID{i+1}", 0))
             cnt.setValue(tpl.get(f"RewardChoiceItemQuantity{i+1}", 0))
             
        # --- Phasing (SmartAI Triggers) ---
        # Check first starter to see if Phasing is configured
        starter_id = starters[0] if starters else 0
        scripts = self.db.get_quest_phase_scripts(starter_id, self.quest_id, realm_id)
        
        mask_accept = 0
        mask_complete = 0
        
        for s in scripts:
            if s['event_type'] == SMART_EVENT.ACCEPTED_QUEST:
                mask_accept = s['action_param1']
            elif s['event_type'] == SMART_EVENT.REWARD_QUEST:
                mask_complete = s['action_param1']
                
        self.inp_phase_accept.setValue(mask_accept)
        self.inp_phase_complete.setValue(mask_complete)
        
        # --- Phasing (Spell Area) ---
        sa_rows = self.db.get_quest_spell_area(self.quest_id, realm_id)
        self.table_spell_area.setRowCount(0) # Clear
        for r in sa_rows:
            self.add_spell_area_row(r['spell'], r['area'], r['autocast'])

        # --- Connected ---
        self.list_starters.clear()
        for nid in starters:
             self.sel_starter.set_value(nid) # To resolve name
             name = self.sel_starter.lbl_name.text()
             item = QListWidgetItem(f"{name} ({nid})")
             item.setData(Qt.UserRole, nid)
             self.list_starters.addItem(item)
        self.sel_starter.set_value(0)
             
        self.list_enders.clear()
        for nid in enders:
             self.sel_ender.set_value(nid) 
             name = self.sel_ender.lbl_name.text()
             item = QListWidgetItem(f"{name} ({nid})")
             item.setData(Qt.UserRole, nid)
             self.list_enders.addItem(item)
        self.sel_ender.set_value(0)
             
        # --- Extras ---
        self.spell_accept.set_value(addon.get("SourceSpellID", 0))
        self.spell_complete.set_value(tpl.get("RewardSpell", 0))
        
        # Emotes Offer
        for i, (spin_e, spin_d) in enumerate(self.emotes_offer):
            spin_e.setValue(offer.get(f"Emote{i+1}", 0))
            spin_d.setValue(offer.get(f"EmoteDelay{i+1}", 0))
            
        # Emotes Request
        self.emote_complete.setValue(req.get("EmoteOnComplete", 0))
        self.emote_incomplete.setValue(req.get("EmoteOnIncomplete", 0))

    def save_data(self):
        # Gather all data into full_data
        
        # 1. Base on Loaded Data to preserve non-UI fields
        if hasattr(self, 'loaded_data') and self.loaded_data:
             full = copy.deepcopy(self.loaded_data)
        else:
             full = {'ID': self.quest_id}
             
        # Initialize sub-dicts if missing (shouldn't happen if loaded, but safe checks)
        template = full.get('template') or {}
        addon = full.get('addon') or {'ID': self.quest_id}
        
        # Ensure Top-Level ID (Fix "Missing ID" error)
        full['ID'] = self.quest_id
        
        offer = full.get('offer_reward') or {'ID': self.quest_id}
        request = full.get('request_items') or {'ID': self.quest_id}
        
        # Enforce ID in template (Critical Fix for INSERT)
        template['ID'] = self.quest_id
        
        # 2. Update with UI Values (Template)
        template['LogTitle'] = self.inp_title.text()
        template['MinLevel'] = self.inp_min_level.value()
        template['QuestLevel'] = self.inp_quest_level.value()
        template['QuestInfoID'] = self.combo_type.currentData()
        template['QuestSortID'] = self.inp_zone_sort.value()
        template['Flags'] = self.flags_selector.value()
        template['SuggestedGroupNum'] = self.inp_suggested_groups.value()
        
        template['LogDescription'] = self.inp_log_desc.toPlainText()
        template['QuestDescription'] = self.inp_quest_desc.toPlainText()
        template['AreaDescription'] = self.inp_area_desc.toPlainText()
        template['QuestCompletionLog'] = self.inp_completion_log.toPlainText()
        
        for i, le in enumerate(self.obj_texts):
             val = le.text().strip()
             template[f"ObjectiveText{i+1}"] = val if val else None
             
        for i, row_widget in enumerate(self.req_npcs):
            rid, rcount = row_widget.get_data()
            template[f"RequiredNpcOrGo{i+1}"] = rid
            template[f"RequiredNpcOrGoCount{i+1}"] = rcount
             
        for i, (sel, cnt) in enumerate(self.req_items):
             template[f"RequiredItemId{i+1}"] = sel.value()
             template[f"RequiredItemCount{i+1}"] = cnt.value()
             
        template['RewardMoney'] = self.rew_money.value()
        template['RewardXPDifficulty'] = self.combo_xp.currentData()
        template['RewardSpell'] = self.spell_complete.value() # From Extras tab
        
        # To Addon, NOT Template!
        addon['RewardMailTemplateID'] = self.rew_mail_tpl.value()
        addon['RewardMailDelay'] = self.rew_mail_delay.value()
        addon['PrevQuestID'] = self.sel_prev_quest.value()
        addon['SourceSpellID'] = self.spell_accept.value()
        
        for i, (sel, cnt) in enumerate(self.rew_fixed):
             template[f"RewardItem{i+1}"] = sel.value()
             template[f"RewardAmount{i+1}"] = cnt.value()
             
        for i, (sel, cnt) in enumerate(self.rew_choice):
             template[f"RewardChoiceItemID{i+1}"] = sel.value()
             template[f"RewardChoiceItemQuantity{i+1}"] = cnt.value()
             
        full['template'] = template
        full['addon'] = addon
        
        # 3. Offer (Emotes)
        has_offer = False
        for i, (spin_e, spin_d) in enumerate(self.emotes_offer):
             offer[f"Emote{i+1}"] = spin_e.value()
             offer[f"EmoteDelay{i+1}"] = spin_d.value()
             if spin_e.value() > 0: has_offer = True
        
        if has_offer: full['offer_reward'] = offer
        
        # 4. Request (Emotes)
        request['EmoteOnComplete'] = self.emote_complete.value()
        request['EmoteOnIncomplete'] = self.emote_incomplete.value()
        if request['EmoteOnComplete'] > 0 or request['EmoteOnIncomplete'] > 0:
             full['request_items'] = request
             
        # 5. Connected
        starters = []
        for i in range(self.list_starters.count()):
            starters.append(self.list_starters.item(i).data(Qt.UserRole))
        full['starters'] = starters
            
        enders = []
        for i in range(self.list_enders.count()):
            enders.append(self.list_enders.item(i).data(Qt.UserRole))
        full['enders'] = enders
        
        # SAVE
        realm_id = self.realm_config.get("id")
        success, msg = self.db.save_quest_extended(full, realm_id)
        
        if not success:
             QMessageBox.critical(self, "Error", msg)
             return
             
        # --- Save Phasing (Spell Area) ---
        sa_entries = []
        for r in range(self.table_spell_area.rowCount()):
            w_spell = self.table_spell_area.cellWidget(r, 0) # SmartSelector
            w_area = self.table_spell_area.cellWidget(r, 1)  # SpinBox
            w_auto = self.table_spell_area.cellWidget(r, 2)  # CheckBox
            
            if w_spell and w_area:
                entry = {
                    'spell': w_spell.value(),
                    'area': w_area.value(),
                    'autocast': 1 if w_auto.isChecked() else 0
                }
                if entry['spell']: # Skip empty
                    sa_entries.append(entry)
        
        self.db.save_quest_spell_area(self.quest_id, sa_entries, realm_id)
        
        # --- Save Phasing (SmartAI) ---
        # Triggers
        m_acc = self.inp_phase_accept.value()
        m_com = self.inp_phase_complete.value()
        
        # Get Starters (We need to rely on what's in the list widget if accessible, or fetch fresh?)
        # List Widget has IDs in UserRole.
        valid_starters = []
        for i in range(self.list_starters.count()):
            item = self.list_starters.item(i)
            sid = item.data(Qt.UserRole)
            if sid: valid_starters.append(sid)
            
        # Apply to all starters
        for sid in valid_starters:
            # 1. Clear old
            self.db.clear_quest_phase_scripts(sid, self.quest_id, realm_id)
            
            # 2. Add Accept
            if m_acc > 0:
                self.db.add_smart_script(
                    entry=sid, source_type=0, 
                    event=SMART_EVENT.ACCEPTED_QUEST, 
                    action=SMART_ACTION.SET_INGAME_PHASE_MASK,
                    param1=m_acc, # Phase Mask
                    target=SMART_TARGET.INVOKER,
                    realm_id=realm_id
                )
            
            # 3. Add Complete
            if m_com > 0:
                 self.db.add_smart_script(
                    entry=sid, source_type=0, 
                    event=SMART_EVENT.REWARD_QUEST, 
                    action=SMART_ACTION.SET_INGAME_PHASE_MASK,
                    param1=m_com, 
                    target=SMART_TARGET.INVOKER,
                    realm_id=realm_id
                )


        
        # --- REGENERATE SQL FILE ---
        # Construct Package for save_quest_transaction to handle file generation
        # We reuse the data we just prepared.
        
        package = {
            'id': self.quest_id,
            'template': full['template'],
            'addon': full['addon'],
            'poi': None, # Extras tab doesn't edit POI yet, maybe later
            'loot': None, # Editor doesn't edit loot yet
            'spell_area': sa_entries,
            'smart_phasing': {
                'accept': m_acc,
                'complete': m_com
            },
            'relations': {
                'starter_id': starters[0] if starters else 0, # Primary starter
                'ender_id': enders[0] if enders else 0
            },
            'gossip': [] # Editor doesn't track these explicit "Talk" configs in a way we can easily dump yet, 
                         # usually they are permanent. But if we want to ensure Talk Objectives are in SQL, 
                         # we might need to scan objectives. 
                         # For now, let's skip re-generating Gossip/Talk SQL from Editor to avoid overwriting custom changes 
                         # unless we add explicit UI for it.
        }
        
        # Determine File Path
        # We need to find where the campaign is.
        # This Editor is usually launched from Campaign Detail, so we assume strictly active campaign if possible?
        # Or we just don't generate if we can't find path.
        # But user reported specific issue.
        
        # Strategy: Try to find campaign via CampaignManager or passed config?
        # self.realm_config is passed.
        # We can try to assume standard path structure if we knew the campaign name.
        
        # Better: We only generate SQL if we can resolve the file path.
        # Since QuestEditor is standalone-ish, it might not know the Campaign Name easily.
        # But wait, how does it know where to save? It usually saves to DB. 
        # The User said "generated sql file is not updated". This implies there IS a file.
        # If we can't easily find the file, we can't update it.
        # However, we can TRY to look up the campaign from the DB or config? 
        # Or pass campaign_path to QuestEditor?
        
        # Let's check if we can get the active campaign.
        # from src.ui.campaign_manager import CampaignManager?
        # No, circular import risk.
        
        # Simple fix: Check if we can find the file in known user directory structure?
        # /campaigns/<name>/quests/<id>.sql
        
        import os
        import glob
        
        # Search for ID.sql in campaigns folder
        # Assumption: User is running from root.
        
        found_file = None
        search_pattern = f"campaigns/*/quests/{self.quest_id}.sql"
        matches = glob.glob(search_pattern)
        if matches:
            found_file = matches[0] # Pick first
        else:
             # Try simpler pattern
             search_pattern_2 = f"campaigns/*/{self.quest_id}.sql"
             matches_2 = glob.glob(search_pattern_2)
             if matches_2: found_file = matches_2[0]
             
        if found_file:
            cleanup_file = found_file.replace(".sql", "_cleanup.sql")
            
            # Call Transaction (Dry Run = False, but we already saved to DB? 
            # If we call it with dry_run=False, it does DB + File. 
            # If we already did DB via save_quest_extended, doing it again is fine (idempotent-ish).
            # ACTUALLY, save_quest_transaction wipes and rewrites. 
            # It might be SAFER to just use save_quest_transaction INSTEAD of save_quest_extended?
            # But save_quest_extended handles Offer/Request text tables which transaction might not cover fully yet?
            # Transaction covers text tables! 
            # save_quest_transaction calls 'quest_offer_reward' and 'quest_request_items'.
            
            # Let's USE save_quest_transaction primarily if we can build the full package.
            # But we already wrote the code to gather `full` data.
            # Let's just run save_quest_transaction at the end to "Sync to File".
            # It will redundant-write to DB but that ensures DB ~ File.
            
            # Check Text Tables in Package
            # Check Text Tables in Package
            # Fix Mapping: Use explicitly edited fields
            package['text'] = {
                'RewardText': self.inp_reward_text.toPlainText(),
                'CompletionText': None # We don't edit "How goes the task" yet, preserve it by sending None?
                # Actually save_quest_transaction logic needs review:
                # If we send None/Empty, does it wipe? 
                # Logic: `completion_text = package.get('text', {}).get('CompletionText', '')`
                # If we send None, it gets ''. Then `if completion_text:` fails.
                # So if we send None, it effectively deletes text if specific detailed object not present.
                # To PRESERVE "RequestItemsText" (CompletionText), we should fetch it and send it back?
                # Or we leave 'CompletionText' key OUT of dict?
                # `package.get('text', {}).get('CompletionText', '')` -> returns '' if key missing.
                # So missing key = Wipe?
                # Yes, standard DbManager logic wipes if plain text supplied.
                # So we SHOULD fetch CompletionText (RequestItems) and include it to avoid wiping it.
            }
            # Fetch existing CompletionText (RequestItems) from DB to preserve it
            current_rich = self.db.get_quest_rich_texts(self.quest_id, self.realm_config.get("id"))
            package['text']['CompletionText'] = current_rich.get('CompletionText', '')
            
            # --- Generate Gossip Package (SQL) ---
            # We need to include the 'gossip' list so SQL file includes the SmartScripts and NPC Text.
            # Logic matches QuestTranslator: MenuID = QuestID * 10 + Index?
            # We need to replicate ID generation logic or fetch?
            # Fetching is safer if it exists.
            # We have the data in ObjectiveRows.
            
            gossip_list = []
            for i, row in enumerate(self.req_npcs):
                data = row.get_data() # (id, count)
                # Check Type
                idx = row.type_combo.currentIndex()
                if idx == 2: # Talk
                    npc_id = data[0]
                    # Get Texts from row memory
                    npc_text = getattr(row, 'gossip_npc_text', '')
                    option_text = getattr(row, 'gossip_option_text', '')
                    
                    if not npc_text: npc_text = "Greetings."
                    if not option_text: option_text = "I am ready."

                    # Generate IDs
                    # Heuristic: QuestID * 100 + (i+1) (1-based to match Translator)
                    uid_base = self.quest_id * 100 + (i + 1)
                    menu_id = uid_base
                    text_id = uid_base
                    
                    gossip_list.append({
                        'npc_id': npc_id,
                        'menu_id': menu_id,
                        'text_id': text_id,
                        'npc_text_content': npc_text,
                        'option_text_content': option_text,
                         # SAI fields for transaction
                        'sai_source_type': 0, 
                        'sai_event': 62,
                        'sai_action': 15,
                        'sai_target': 7
                    })
            package['gossip'] = gossip_list
            # save_quest_transaction maps 'RewardText' -> quest_offer_reward? 
            # No, 'RewardText' in package['text'] -> quest_completion_log?
            
            # Let's check QuestTranslator for mapping. 
            # package['text']['RewardText'] -> quest_offer_reward (RewardText)
            # package['text']['CompletionText'] -> quest_request_items (CompletionText)
            
            # In Editor:
            # self.inp_completion_log -> QuestCompletionLog (Template)
            # self.inp_log_desc -> LogDescription (Template)
            # self.inp_quest_desc -> QuestDescription (Template)
            # self.inp_area_desc -> AreaDescription (Template)
            
            # Where is Offer/Request text?
            # The Editor doesn't expose `quest_offer_reward.RewardText` or `quest_request_items.CompletionText` in the UI explicitly?
            # Wait, `QuestEditor.init_general_tab` has:
            # self.inp_npc_text (Offer Dialogue) ?
            # Let's check lines 410-415 of QuestEditor.
            
            # Line 411: self.inp_log_desc.setText(tpl.get("LogDescription"))
            # Line 414: self.inp_completion_log.setText(tpl.get("QuestCompletionLog"))
            
            # The Editor seems to edit `quest_template` fields primarily.
            # But `quest_offer_reward` and `quest_request_items` are separate tables.
            # If `save_quest_extended` handles them, does `save_quest_transaction`?
            # Yes, lines 300+ of DbManager.
            
            # We need to make sure we populate package['text'] correctly.
            # But wait, does the User edit them in the Editor?
            # The Editor shows "Log Description", "Quest Description", "Area Description", "Completion Log". These are ALL in `quest_template`.
            # Use `Offer Reward Emotes` group for Emotes, but maybe not text?
            
            # If the editor doesn't allow editing Offer/Request text, we shouldn't overwrite them with empty?
            # We should fetch them if missing.
            # But `save_quest_transaction` deletes them if present?
            
            # Safety: ONLY generate file if we are confident.
            # The user said "Changed the Offer Text of quest ID 60000". 
            # Where is "Offer Text"?
            # Maybe they mean `QuestDescription` (Offer Dialogue)? 
            # If so, that IS in `quest_template` and IS covered by `template` dict.
            
            # So `package['template']` having `QuestDescription` updated is enough.
            
            try:
                self.db.save_quest_transaction(package, dry_run=False, log_file=found_file, cleanup_file=cleanup_file, realm_id=realm_id)
            except Exception as e:
                print(f"Failed to sync SQL: {e}")
                # Don't block UI success on file error, but nice to warn?
        

        QMessageBox.information(self, "Success", "Quest Saved Successfully")
        self.close()

    def on_delete(self):
        confirm = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to DELETE quest {self.quest_id}?\n\n"
            "This will permanently remove:\n"
            "- Quest Template & Addon\n"
            "- Offer/Reward/Request Data\n"
            "- Quest Starters/Enders (NPCs/GOs)\n"
            "- Linked SmartAI Scripts (Phasing/Gossip)\n"
            "- Spell Area entries\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            realm_id = self.realm_config.get("id")
            success, msg = self.db.delete_quest_full(self.quest_id, realm_id)
            if success:
                QMessageBox.information(self, "Success", msg)
                self.accept() # Triggers refresh in parent
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete quest: {msg}")
