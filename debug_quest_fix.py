
import sys
import os
# Ensure we are modifying the path correctly relative to script execution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.db_config import DbConfig

def diagnose_quest():
    conn = mysql.connector.connect(**DbConfig.get_config(2))
    cursor = conn.cursor(dictionary=True)
    
    QID = 60000
    
    print(f"--- Diagnosing Quest {QID} ---")
    
    # 1. Check Main Template (SortID, Log texts)
    cursor.execute("SELECT QuestSortID, LogTitle, LogDescription, QuestCompletionLog FROM quest_template WHERE ID=%s", (QID,))
    tpl = cursor.fetchone()
    print("\n[quest_template]")
    print(f"QuestSortID: {tpl['QuestSortID']} (If this is 0, that might be the 'Missing Header' cause)")
    print(f"QuestCompletionLog: '{tpl['QuestCompletionLog']}'")
    
    # 2. Check Offer Reward (NPC Text)
    cursor.execute("SELECT RewardText FROM quest_offer_reward WHERE ID=%s", (QID,))
    offer = cursor.fetchone()
    print("\n[quest_offer_reward]")
    if offer:
        print(f"RewardText: '{offer['RewardText']}'")
        if offer['RewardText'] == tpl['QuestCompletionLog']:
            print("  -> WARNING: RewardText matches QuestCompletionLog (Coupled!)")
    else:
        print("  -> No entry found!")
        
    conn.close()

if __name__ == "__main__":
    diagnose_quest()
