
import sys
import os

# Add src to path
import sys
import os
sys.path.append('/home/azoghmartins/azerothforge/')

from src.database.db_config import DbConfig
import mysql.connector

def check_gossip():
    conn = mysql.connector.connect(**DbConfig.get_config(2)) # Realm 2
    cursor = conn.cursor(dictionary=True)
    
    QUEST_ID = 60000
    NPC_ID = 197
    
    print(f"--- Checking Gossip Data for Quest {QUEST_ID} / NPC {NPC_ID} ---\n")
    
    # 1. Check Smart Scripts (The Link)
    print("1. Smart Scripts (Event 62 - GOSSIP_SELECT, Action 15 - QUEST_CREDIT):")
    cursor.execute("""
        SELECT * FROM smart_scripts 
        WHERE entryorguid=%s AND source_type=0 AND event_type=62 AND action_type=15
    """, (NPC_ID,))
    scripts = cursor.fetchall()
    for s in scripts:
        print(s)
        
    if not scripts:
        print("  [FAIL] No Smart Script found linking NPC to Quest Credit.")
        return
        
    menu_id = scripts[0]['event_param1']
    target_quest = scripts[0]['action_param1']
    
    print(f"\n  > Found Link: MenuID={menu_id}, TargetQuest={target_quest}")
    
    if target_quest != QUEST_ID:
        print(f"  [FAIL] Script points to Quest {target_quest}, expected {QUEST_ID}")
    
    # 2. Check Gossip Menu (The Structure)
    print(f"\n2. Gossip Menu (MenuID {menu_id}):")
    cursor.execute("SELECT * FROM gossip_menu WHERE MenuID=%s", (menu_id,))
    menus = cursor.fetchall()
    for m in menus:
        print(m)
        
    text_id = 0
    if not menus:
        print("  [FAIL] No gossip_menu entry found.")
    else:
        text_id = menus[0]['TextID']
        print(f"  > Found TextID={text_id}")

    # 3. Check NPC Text (The Content - NPC Say)
    print(f"\n3. NPC Text (TextID {text_id}):")
    cursor.execute("SELECT ID, text0_0, text0_1 FROM npc_text WHERE ID=%s", (text_id,))
    texts = cursor.fetchall()
    for t in texts:
        print(t)
        
    if not texts:
        print("  [FAIL] No npc_text entry found.")
    else:
        print(f"  > NPC Text: '{texts[0]['text0_0']}'")

    # 4. Check Gossip Menu Option (The Content - Player Reply)
    print(f"\n4. Gossip Menu Option (MenuID {menu_id}):")
    cursor.execute("SELECT * FROM gossip_menu_option WHERE MenuID=%s", (menu_id,))
    options = cursor.fetchall()
    for o in options:
        print(o)
        
    if not options:
        print("  [FAIL] No gossip_menu_option found.")
    else:
        print(f"  > Option Text: '{options[0]['OptionText']}'")

    conn.close()

if __name__ == "__main__":
    check_gossip()
