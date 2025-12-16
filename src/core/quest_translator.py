class QuestTranslator:
    @staticmethod
    def prepare_transaction_package(user_data):
        """
        Translates user-friendly wizard data into a multi-table transaction package.
        Returns a dictionary with keys: 'template', 'addon', 'poi', 'loot'.
        """
        package = {
            'template': {},
            'addon': {},
            'poi': None,
            'loot': None,
            'id': user_data.get('entry', 0)
        }
        
        # --- 1. Quest Template (The Main Table) ---
        entry = {}
        entry['ID'] = package['id']
        entry['QuestType'] = 2 
        
        # Gossip Defaults
        package['gossip'] = [] # Ensure it exists 
        entry['QuestLevel'] = user_data.get('quest_level', 1)
        entry['MinLevel'] = user_data.get('min_level', 1)
        
        zone_map = {
            "General": 0, "Dragonblight": 65, "Epic": -1, "Dungeon": -2, "Raid": -3
        }
        entry['QuestSortID'] = zone_map.get(user_data.get('zone'), 0)
        if 'zone' in user_data:
             # Legacy or string based default? 
             # Now using zone_or_sort for ID
             entry['QuestSortID'] = int(user_data.get('zone_or_sort', 0))
        else:
             entry['QuestSortID'] = 0
             
        entry['QuestInfoID'] = int(user_data.get('quest_info_id', 0))
        entry['SuggestedGroupNum'] = int(user_data.get('suggested_players', 0))
        entry['Flags'] = int(user_data.get('flags', 0))
        
        entry['LogTitle'] = user_data.get('title', 'Unknown Quest')
        entry['LogDescription'] = user_data.get('log_description', '')
        entry['QuestDescription'] = user_data.get('quest_description', '')
        entry['AreaDescription'] = user_data.get('area_description', '')
        entry['QuestCompletionLog'] = user_data.get('tracker_complete_text', '') # Decoupled!
        
        # Reward Spell (Cast on Complete)
        entry['RewardSpell'] = int(user_data.get('reward_spell', 0))
        
        # Races (Template)
        race_map = {"Alliance": 1101, "Horde": 690, "Both": 0}
        entry['AllowableRaces'] = race_map.get(user_data.get('required_races'), 0)
        
        # Objectives (Template)
        objectives = user_data.get('objectives', [])
        
        # Init Counters
        npc_go_idx = 1
        item_idx = 1
        
        # Clear/Init Default columns (Up to 4 NPC/GO, 6 Items)
        for i in range(1, 5):
            entry[f'RequiredNpcOrGo{i}'] = 0
            entry[f'RequiredNpcOrGoCount{i}'] = 0
            
        for i in range(1, 7):
            entry[f'RequiredItemId{i}'] = 0
            entry[f'RequiredItemCount{i}'] = 0
            
        entry['RewardItem1'] = 0
        entry['RewardAmount1'] = 0 
        
        entry['RewardAmount1'] = 0
        
        for obj in objectives:
            otyp = obj.get('objective_type')
            tid = int(obj.get('target_id') or 0)
            count = int(obj.get('target_count') or 0)
            
            if otyp == "Slay Creature" or otyp == "Talk to NPC" or otyp == "Interact with GameObject":
                if npc_go_idx <= 4:
                    # Interact = Negative ID
                    final_id = tid
                    if otyp == "Interact with GameObject":
                         final_id = -abs(tid)
                         
                    entry[f'RequiredNpcOrGo{npc_go_idx}'] = final_id
                    entry[f'RequiredNpcOrGoCount{npc_go_idx}'] = count if otyp == "Slay Creature" or otyp == "Interact with GameObject" else 1
                    
                    # Tracker Text
                    tracker_txt = obj.get('tracker_text', '')
                    entry[f'ObjectiveText{npc_go_idx}'] = tracker_txt
                    
                    # Gossip Packet (for DbManager)
                    # Gossip Packet (for DbManager)
                    if otyp == "Talk to NPC":
                        if not package.get('gossip'): package['gossip'] = []
                        
                        # Generate stable IDs
                        uid_base = package['id'] * 100 + npc_go_idx
                        
                        package['gossip'].append({
                            'npc_id': tid, # DbManager expects npc_id
                            'menu_id': uid_base,
                            'text_id': uid_base,
                            'npc_text_content': obj.get('gossip_text', 'Greetings'),
                            'option_text_content': obj.get('option_text', 'Continue'),
                            # SAI Defaults
                            'sai_source_type': 0, 'sai_event': 62, 'sai_action': 15, 'sai_target': 7
                        })
                    
                    npc_go_idx += 1
                    
            elif otyp == "Collect Item":
                if item_idx <= 6:
                    entry[f'RequiredItemId{item_idx}'] = tid
                    entry[f'RequiredItemCount{item_idx}'] = count
                    item_idx += 1
                    
                    # Loot Handlers (Side Effects) - Just grabbing the first valid one found for now
                    source_type = obj.get('source_type')
                    source_id = obj.get('source_id')
                    
                    if source_type == "Loot from Creature" and source_id:
                        # Only set if not already set, to avoid conflict or need logic to append
                        if not package['loot']: 
                            package['loot'] = {
                                'Entry': source_id,
                                'Item': tid,
                                'Chance': obj.get('drop_chance', 100),
                                'GroupId': 0
                            }
                    elif source_type == "Loot from GameObject" and source_id:
                        if not package.get('loot_go'):
                             package['loot_go'] = {
                                 'Entry': source_id,
                                 'Item': tid,
                                 'Chance': obj.get('drop_chance', 100),
                                 'GroupId': 0
                             }

            elif otyp == "Reach Location":
                # Exploration Flag
                entry['Flags'] |= 2 
                
                # POI Logic (Limit 1)
                if not package['poi']:
                    try:
                        map_id = int(str(obj.get('map_id', 0)))
                        x = float(str(obj.get('pos_x', 0)))
                        y = float(str(obj.get('pos_y', 0)))
                        package['poi'] = {
                            'QuestID': package['id'],
                            'MapID': map_id,
                            'X': int(x),
                            'Y': int(y)
                        }
                    except ValueError:
                        pass
                        
        # Restoring Rewards Logic
        gold = user_data.get('reward_gold', 0)
        silver = user_data.get('reward_silver', 0)
        copper = user_data.get('reward_copper', 0)
        entry['RewardMoney'] = (gold * 10000) + (silver * 100) + copper
        xp_val = user_data.get('reward_xp_difficulty', 0)
        try:
             entry['RewardXPDifficulty'] = int(xp_val)
        except (ValueError, TypeError):
             entry['RewardXPDifficulty'] = 0 

        # Rewards - Fixed
        fixed = user_data.get('rewards_fixed', [])
        for i in range(4):
            key_id = f"RewardItem{i+1}"
            key_count = f"RewardAmount{i+1}"
            if i < len(fixed):
                entry[key_id] = fixed[i]['id']
                entry[key_count] = fixed[i]['count']
            else:
                entry[key_id] = 0
                entry[key_count] = 0

        # Rewards - Choice
        choice = user_data.get('rewards_choice', [])
        for i in range(6):
            key_id = f"RewardChoiceItemID{i+1}"
            key_count = f"RewardChoiceItemQuantity{i+1}"
            if i < len(choice):
                entry[key_id] = choice[i]['id']
                entry[key_count] = choice[i]['count']
            else:
                entry[key_id] = 0
                entry[key_count] = 0

        package['template'] = entry

        # --- 2. Quest Template Addon ---
        addon = {}
        addon['ID'] = package['id']
        addon['MaxLevel'] = int(user_data.get('max_level') or 80)
        addon['AllowableClasses'] = QuestTranslator._map_classes(user_data.get('required_classes'))
        addon['AllowableClasses'] = QuestTranslator._map_classes(user_data.get('required_classes'))
        addon['SourceSpellID'] = int(user_data.get('source_spell', 0))
        addon['RewardMailTemplateID'] = int(user_data.get('reward_mail_template_id', 0))
        addon['RewardMailDelay'] = int(user_data.get('reward_mail_delay', 0))
        
        addon['ExclusiveGroup'] = 0
        addon['NextQuestId'] = 0
        addon['PrevQuestId'] = 0
        
        # Calculate SpecialFlags
        # 0 = None
        # 1 = Repeatable
        # 2 = External Event (Needed for Talk to NPC / SmartScript credit)
        special_flags = 0
        for obj in objectives:
             if obj.get('objective_type') == "Talk to NPC":
                 special_flags |= 2 
        
        addon['SpecialFlags'] = special_flags
        
        package['addon'] = addon                 
        # --- 5. Relations ---
        package['relations'] = {
            'starter_id': user_data.get('starter_id'),
            'ender_id': user_data.get('ender_id')
        }
        
        # --- 6. Text Tables ---
        # --- 6. Text Tables ---
        # --- 6. Text Tables (Advanced) ---
        package['text'] = {
            'RewardText': user_data.get('reward_text', 'Thank you, $N.'), # NPC Text
            'CompletionText': user_data.get('request_items_text', 'How goes the task?') 
        }
        
        # Offer Package (Emotes)
        package['offer'] = {
            'RewardText': package['text']['RewardText']
        }
        offer_emotes = user_data.get('offer_emotes', []) # List of (id, delay)
        for i, (eid, delay) in enumerate(offer_emotes):
            if i < 4:
                package['offer'][f"Emote{i+1}"] = eid
                package['offer'][f"EmoteDelay{i+1}"] = delay
                
        # Request Package (Emotes)
        package['request'] = {
            'CompletionText': package['text']['CompletionText'],
            'EmoteOnComplete': int(user_data.get('emote_on_complete', 0)),
            'EmoteOnIncomplete': int(user_data.get('emote_on_incomplete', 0))
        }

        # --- 7. Phasing (Spell Area & SmartAI) ---
        package['spell_area'] = user_data.get('spell_area', [])
        
        # Triggered Phasing
        p_acc = user_data.get('phase_accept', 0)
        p_com = user_data.get('phase_complete', 0)
        
        package['smart_phasing'] = {
            'accept': p_acc,
            'complete': p_com
        }

        # --- 8. Gossip & Scripts (Brain) ---
        package['gossip'] = []
        
        for idx, obj in enumerate(objectives):
            if obj.get('objective_type') == "Talk to NPC":
                npc_id = int(obj.get('target_id') or 0)
                if not npc_id: continue
                
                # Generate unique-ish IDs based on QuestID + Index
                # Schema assumption: IDs are usually ints in world DB
                # This logic is simple but effective for custom content
                menu_id = int(f"{package['id']}{idx}")
                text_id = int(f"{package['id']}{idx}")
                
                gossip_text = obj.get('gossip_text', 'Greetings.')
                option_text = obj.get('option_text', 'I am ready.')
                
                # 1. NPC Text
                # 2. Gossip Menu
                # 3. Gossip Option
                # 4. Smart Script (Action: Quest Credit)
                
                gossip_entry = {
                    'npc_id': npc_id,
                    'menu_id': menu_id,
                    'text_id': text_id,
                    'npc_text_content': gossip_text,
                    'option_text_content': option_text,
                    'sai_source_type': 0, # Creature
                    'sai_event': 62, # GOSSIP_SELECT
                    'sai_action': 15, # QUEST_ADD_KILL_CREDIT
                    'sai_target': 7 # INVOKER
                }
                package['gossip'].append(gossip_entry)
                 
        return package
    @staticmethod
    def _map_classes(classes_data):
        """
        Maps user selection to AllowableClasses bitmask.
        classes_data: "All" or ["Warrior", "Mage", ...]
        """
        if classes_data == "All" or not classes_data:
            return 0 # 0 usually means All Allowed in TC/AC
            
        mask_map = {
            "Warrior": 1,
            "Paladin": 2,
            "Hunter": 4,
            "Rogue": 8,
            "Priest": 16,
            "Death Knight": 32,
            "Shaman": 64,
            "Mage": 128,
            "Warlock": 256,
            "Druid": 1024
        }
        
        total_mask = 0
        for c in classes_data:
            total_mask |= mask_map.get(c, 0)
            
        return total_mask
