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
        entry['QuestLevel'] = user_data.get('quest_level', 1)
        entry['MinLevel'] = user_data.get('min_level', 1)
        
        zone_map = {
            "General": 0, "Dragonblight": 65, "Epic": -1, "Dungeon": -2, "Raid": -3
        }
        entry['QuestSortID'] = zone_map.get(user_data.get('zone'), 0)
        
        entry['LogTitle'] = user_data.get('title', 'Unknown Quest')
        entry['LogDescription'] = user_data.get('log_description', '')
        entry['QuestDescription'] = user_data.get('quest_description', '')
        entry['AreaDescription'] = ""
        entry['QuestCompletionLog'] = user_data.get('quest_completion_log', '')
        
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
        
        # Flags
        entry['Flags'] = 0
        
        for obj in objectives:
            otyp = obj.get('objective_type')
            tid = int(obj.get('target_id') or 0)
            count = int(obj.get('target_count') or 0)
            
            if otyp == "Slay Creature" or otyp == "Talk to NPC":
                if npc_go_idx <= 4:
                    entry[f'RequiredNpcOrGo{npc_go_idx}'] = tid
                    entry[f'RequiredNpcOrGoCount{npc_go_idx}'] = count if otyp == "Slay Creature" else 1
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
        addon['MaxLevel'] = 80
        addon['PrevQuestId'] = int(user_data.get('prev_quest_id') or 0)
        addon['NextQuestId'] = 0
        addon['ExclusiveGroup'] = 0
        addon['SpecialFlags'] = 0
        
        classes = user_data.get('required_classes')
        addon['AllowableClasses'] = 0 if classes == "All" else 0

        package['addon'] = addon                 
        # --- 5. Relations ---
        package['relations'] = {
            'starter_id': user_data.get('starter_id'),
            'ender_id': user_data.get('ender_id')
        }
        
        # --- 6. Text Tables ---
        package['text'] = {
            'RewardText': user_data.get('quest_completion_log', 'Thank you, $N.'),
            'CompletionText': user_data.get('log_description', '') # Using log_description as CompletionText for now based on mappings
        }
                 
        return package
