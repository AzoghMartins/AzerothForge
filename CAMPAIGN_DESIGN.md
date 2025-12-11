1. The Campaign Dashboard
Create New: Input Name, ID Range Start (e.g., 60000), and Select GM Character (Dropdown from Char DB).

The Hub: A tabbed view specific to this campaign.

Overview: Stats (3 Quests, 5 NPCs).

Palette: Lists of only the content in this campaign.

2. The Smart Quest Editor
Quest Giver:

Input: Search for "Thrall".

Action: App adds Thrall (ID 4949) to the campaign's "Referenced NPCs" list automatically.

Logic: Generates INSERT INTO creature_questrelation (Start Quest).

Quest Ender/Objective:

Input: You create "Fallen Messenger" (ID 60000).

Action: You select it as the "Required NPC to Kill/Interact".

Logic: Generates INSERT INTO creature_involvedrelation (End Quest) or adds to quest_template requirements.

3. The "Director" Spawner
Prerequisite: The "Base GM Character" must be logged out (to read exact DB coords) OR we use the SOAP .gps trick.

Trick: Send .gps via SOAP. The console response usually contains the coordinates. We parse X, Y, Z, Map from the text response. This allows the GM to stay online!

Action:

Button: [Spawn @ GM]

Result: The NPC appears exactly where you are standing.