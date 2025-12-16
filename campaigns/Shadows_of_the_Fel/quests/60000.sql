DELETE FROM quest_template WHERE ID = 60000;
INSERT INTO quest_template (ID, QuestType, QuestLevel, MinLevel, QuestSortID, QuestInfoID, SuggestedGroupNum, RequiredFactionId1, RequiredFactionId2, RequiredFactionValue1, RequiredFactionValue2, RewardNextQuest, RewardXPDifficulty, RewardMoney, RewardMoneyDifficulty, RewardDisplaySpell, RewardSpell, RewardHonor, RewardKillHonor, StartItem, Flags, RequiredPlayerKills, RewardItem1, RewardAmount1, RewardItem2, RewardAmount2, RewardItem3, RewardAmount3, RewardItem4, RewardAmount4, ItemDrop1, ItemDropQuantity1, ItemDrop2, ItemDropQuantity2, ItemDrop3, ItemDropQuantity3, ItemDrop4, ItemDropQuantity4, RewardChoiceItemID1, RewardChoiceItemQuantity1, RewardChoiceItemID2, RewardChoiceItemQuantity2, RewardChoiceItemID3, RewardChoiceItemQuantity3, RewardChoiceItemID4, RewardChoiceItemQuantity4, RewardChoiceItemID5, RewardChoiceItemQuantity5, RewardChoiceItemID6, RewardChoiceItemQuantity6, POIContinent, POIx, POIy, POIPriority, RewardTitle, RewardTalents, RewardArenaPoints, RewardFactionID1, RewardFactionValue1, RewardFactionOverride1, RewardFactionID2, RewardFactionValue2, RewardFactionOverride2, RewardFactionID3, RewardFactionValue3, RewardFactionOverride3, RewardFactionID4, RewardFactionValue4, RewardFactionOverride4, RewardFactionID5, RewardFactionValue5, RewardFactionOverride5, TimeAllowed, AllowableRaces, LogTitle, LogDescription, QuestDescription, AreaDescription, QuestCompletionLog, RequiredNpcOrGo1, RequiredNpcOrGo2, RequiredNpcOrGo3, RequiredNpcOrGo4, RequiredNpcOrGoCount1, RequiredNpcOrGoCount2, RequiredNpcOrGoCount3, RequiredNpcOrGoCount4, RequiredItemId1, RequiredItemId2, RequiredItemId3, RequiredItemId4, RequiredItemId5, RequiredItemId6, RequiredItemCount1, RequiredItemCount2, RequiredItemCount3, RequiredItemCount4, RequiredItemCount5, RequiredItemCount6, Unknown0, ObjectiveText1, ObjectiveText2, ObjectiveText3, ObjectiveText4, VerifiedBuild) VALUES (60000, 2, 2, 1, 24, 0, 0, 0, 0, 0, 0, 0, 4, 10203, 0, 0, 0, 0, 0.0, 0, 0, 0, 2455, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2457, 1, 2458, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1101, 'Test Quest', 'Talk to Marshal McBride', 'Greetings, $N. Go talk to Marshal McBride.', '', 'Return to Deputy Willem.', 197, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 'Talk to Marshal McBride', NULL, NULL, NULL, NULL);
DELETE FROM quest_template_addon WHERE ID = 60000;
INSERT INTO quest_template_addon (ID, MaxLevel, AllowableClasses, SourceSpellID, PrevQuestID, NextQuestID, ExclusiveGroup, RewardMailTemplateID, RewardMailDelay, RequiredSkillID, RequiredSkillPoints, RequiredMinRepFaction, RequiredMaxRepFaction, RequiredMinRepValue, RequiredMaxRepValue, ProvidedItemCount, SpecialFlags) VALUES (60000, 80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2);
DELETE FROM creature_queststarter WHERE quest = 60000;
INSERT INTO creature_queststarter (id, quest) VALUES (823, 60000);
DELETE FROM creature_questender WHERE quest = 60000;
INSERT INTO creature_questender (id, quest) VALUES (823, 60000);
DELETE FROM quest_offer_reward WHERE ID = 60000;
INSERT INTO quest_offer_reward (ID, RewardText) VALUES (60000, 'Thank you for seeing the marshal.');
DELETE FROM quest_request_items WHERE ID = 60000;
INSERT INTO quest_request_items (ID, CompletionText) VALUES (60000, 'Hurry up!');
DELETE FROM npc_text WHERE ID = 6000001;
INSERT INTO npc_text (ID, text0_0, text0_1, Probability0) VALUES (6000001, 'Thank you for seeing me.', 'Thank you for seeing me.', 1);
DELETE FROM gossip_menu WHERE MenuID = 6000001 AND TextID = 6000001;
INSERT INTO gossip_menu (MenuID, TextID) VALUES (6000001, 6000001);
DELETE FROM gossip_menu_option WHERE MenuID = 6000001;
INSERT INTO gossip_menu_option 
                             (MenuID, OptionID, OptionIcon, OptionText, OptionType, OptionNpcFlag) 
                             VALUES (6000001, 0, 0, 'No problem.', 1, 1);
UPDATE creature_template SET gossip_menu_id = 6000001, npcflag = npcflag | 1 WHERE entry = 197;
DELETE FROM smart_scripts WHERE entryorguid = 197 AND source_type = 0 AND event_type = 62 AND event_param1 = 6000001;
