
import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.database.db_manager import DbManager
from src.core.config_manager import ConfigManager

def debug_quest(q_id=60000):
    cm = ConfigManager()
    db = DbManager.get_instance(cm)
    
    # Get active campaign to find dev realm?
    # We will just iterate realms or assume the user's setup. 
    # For now, let's try to find the dev realm ID from the user's config if possible, 
    # or just try to connect to the DB named 'acore_world_dev' or similar if we can guess.
    # Actually, DbManager.get_connection has logic. Let's try to ask it for the Dev Realm if we can find it.
    
    # We know the campaign is "Shadows of the Fel" (from previous logs) but we don't have the object here easily.
    # Let's peek at campaigns.json?
    # Or just try to connect to the active realm first, checking the DB name.
    
    print("--- Connecting to Database ---")
    conn = db.get_connection() # Will use default/active. Hopefully that's where they verified.
    # Wait, user said "acore_world_dev".
    # We should ensure we read from that.
    
    cursor = conn.cursor(dictionary=True)
    
    print(f"\n--- Quest Template ({q_id}) ---")
    try:
        cursor.execute(f"SELECT ID, QuestType, SpecialFlags, RequiredNpcOrGo1, RequiredNpcOrGoCount1, Objectives FROM quest_template WHERE ID = {q_id}")
        print(cursor.fetchone())
    except Exception as e: print(e)

    print(f"\n--- Quest Template Addon ({q_id}) ---")
    try:
        cursor.execute(f"SELECT ID, SpecialFlags FROM quest_template_addon WHERE ID = {q_id}")
        print(cursor.fetchone())
    except Exception as e: print(e)
    
    # Find NPC ID involved
    npc_id = 197 # From previous user logs
    
    print(f"\n--- Creature Template ({npc_id}) ---")
    try:
        cursor.execute(f"SELECT entry, name, gossip_menu_id, npcflag FROM creature_template WHERE entry = {npc_id}")
        print(cursor.fetchone())
    except Exception as e: print(e)
    
    # Assume MenuID was generated as 600000
    menu_id = 600000
    
    print(f"\n--- Gossip Menu (MenuID: {menu_id}) ---")
    try:
        cursor.execute(f"SELECT * FROM gossip_menu WHERE MenuID = {menu_id}")
        print(cursor.fetchall())
    except Exception as e: print(e)

    print(f"\n--- Gossip Menu Option (MenuID: {menu_id}) ---")
    try:
        cursor.execute(f"SELECT * FROM gossip_menu_option WHERE MenuID = {menu_id}")
        options = cursor.fetchall()
        print(options)
    except Exception as e: print(e)
    
    print(f"\n--- NPC Text (ID: {menu_id}) ---") # TextID matches MenuID in our logic
    try:
        cursor.execute(f"SELECT ID, text0_0, Probability0 FROM npc_text WHERE ID = {menu_id}")
        print(cursor.fetchone())
    except Exception as e: print(e)
    
    print(f"\n--- Smart Scripts (NPC: {npc_id}) ---")
    try:
        cursor.execute(f"SELECT * FROM smart_scripts WHERE entryorguid = {npc_id} AND source_type=0 AND event_type=62")
        print(cursor.fetchall())
    except Exception as e: print(e)

    conn.close()

if __name__ == "__main__":
    debug_quest()
