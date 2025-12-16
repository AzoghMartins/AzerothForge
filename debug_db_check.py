
import mysql.connector
from src.database.db_config import DbConfig

def check_quest_data():
    conn = mysql.connector.connect(**DbConfig.get_config(2)) # Realm 2
    cursor = conn.cursor(dictionary=True)
    
    # 1. Check Smart Script
    print("\n--- SmartAI Scripts (NPC 197, Event 62) ---")
    cursor.execute("SELECT * FROM smart_scripts WHERE entryorguid=197 AND event_type=62 AND action_type=15")
    rows = cursor.fetchall()
    for r in rows:
        print(r)
        
    if not rows:
        print("NO SmartAI Script found for Talk Objective!")
    else:
        # Get Menu ID from Param1
        menu_id = rows[0]['event_param1']
        print(f"\n--- Gossip Menu (MenuID {menu_id}) ---")
        
        # 2. Check Gossip Menu
        cursor.execute("SELECT * FROM gossip_menu WHERE entry=%s", (menu_id,))
        gm_rows = cursor.fetchall()
        for r in gm_rows:
            print(r)
            
        if gm_rows:
            text_id = gm_rows[0]['text_id']
            print(f"\n--- NPC Text (ID {text_id}) ---")
            cursor.execute("SELECT ID, text0_0, text0_1 FROM npc_text WHERE ID=%s", (text_id,))
            print(cursor.fetchall())
            
        # 3. Check Options
        print(f"\n--- Gossip Options (MenuID {menu_id}) ---")
        cursor.execute("SELECT * FROM gossip_menu_option WHERE MenuID=%s", (menu_id,))
        print(cursor.fetchall())
        
    conn.close()

if __name__ == "__main__":
    check_quest_data()
