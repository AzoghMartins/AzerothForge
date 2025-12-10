# AzerothForge: Software Design Document

**Version:** 1.2.0 (Linux Native Edition)
**Date:** 2025-12-10
**Target System:** AzerothCore 3.3.5a (WotLK)
**Platform:** Linux Mint (Primary/Native), Windows 10/11 (Secondary)

---

## 🤖 AI Context & Directives
*(This section is for the AI Coding Assistant. Keep this at the top of the file.)*

* **Role:** You are building a **Native Desktop Application** using **Python 3.12+** and **PySide6 (Qt)**.
* **Constraint 1 (UI):** The UI must be responsive, follow native Linux/Qt styling, and support Dark Mode.
* **Constraint 2 (Safety):** Do NOT execute SQL directly against the live database for content creation. Generate `.sql` files for review.
* **Constraint 3 (Ops):** Dashboard operations (Restarts) must use `systemd` (Linux) or fallback logic (Windows), coupled with SOAP commands for graceful shutdowns.
* **Constraint 4 (Code):** Code must be modular. Separate UI logic (`/ui`) from Business logic (`/core`) and Data logic (`/db`).

---

## 1. Executive Summary
**AzerothForge** is a comprehensive management and content creation suite for AzerothCore servers. It replaces manual SQL injection and terminal commands with a modern GUI. It allows administrators to:
1.  **Monitor & Control** the server (Restart, Shutdown, Chat, Uptime).
2.  **Create Content** (NPCs, Quests, Items) using visual editors.
3.  **Visualize** assets (3D Models) and data connections.

---

## 2. Technology Stack

| Component | Choice | Reason |
| :--- | :--- | :--- |
| **Language** | **Python 3.12+** | Rapid iteration, strong library support, native AI fluency. |
| **GUI Framework** | **PySide6 (Qt 6)** | Native Linux integration, high performance, professional widgets. |
| **Database Driver** | **mysql-connector-python** | Standard connectivity for MySQL/MariaDB. |
| **Server Comms** | **SOAP (requests)** | Sending GM commands (Restart, Announce) via AC's remote console (Port 7878). |
| **System Comms** | **subprocess / systemd** | Managing the binary processes (Worldserver/Authserver). |
| **3D Rendering** | **QtWebEngine + Three.js** | Embedding a WebGL viewer for model previews (avoids complex OpenGL bindings). |
| **Data Parsing** | **pywowlib** (or struct) | Reading client `.dbc` files for accurate dropdown data (Map names, Factions). |

---

## 3. Application Architecture

### 3.1 Project Structure

    /azerothforge
    ├── /assets            # Icons, static images, HTML templates for 3D viewer
    ├── /data              # Parsed DBC data (JSON cache)
    ├── /src
    │   ├── /core          # Business logic (Stats calc, SQL generation, ID management)
    │   ├── /db            # MySQL and SOAP connection managers
    │   ├── /ui            # PySide6 Widgets and Windows
    │   │   ├── /components  # Reusable bits (Spinners, 3DViewerWidget, LogStream)
    │   │   └── /editors     # Specific forms (NpcEditor, QuestEditor, Dashboard)
    │   └── /utils         # File I/O, Logging, Systemd wrappers, DBC parsers
    ├── /output            # Where generated .sql files are saved
    ├── main.py            # Entry point
    └── requirements.txt

### 3.2 Data Flow
1.  **Input:** User interacts with GUI (e.g., types "Lich King" into Name field).
2.  **Validation:** `src/core` validates logic (e.g., ensures `MinLevel` <= `MaxLevel`).
3.  **Persistence:** Work-in-progress is saved to a local `.forge` (JSON) file.
4.  **Export:** When ready, `src/core/sql_generator.py` translates the JSON state into valid 3.3.5a SQL statements.

---

## 4. Functional Specifications

### 4.1 Server Dashboard (Mission Control)
* **Status Indicators:** Visual "Traffic Lights" (Green/Red) for `authserver` and `worldserver` services.
* **Live Metrics:** Fetch Uptime and Online Player Count via SOAP (`.server info`).
* **Log Stream:** A read-only text widget that tails the local `server.log` file in real-time.
* **Control Actions:**
    * **Graceful Restart:**
        1.  Send SOAP: `.announce Restarting in 30s...`
        2.  Wait 30s.
        3.  Send SOAP: `.save`
        4.  Execute System: `systemctl restart worldserver`

### 4.2 Content Creator (The Forge)
* **Project System:** User creates a "Project" (e.g., "Custom Zone"). The app manages a safe range of IDs (e.g., 500000-510000) to prevent collisions with Blizzard data.
* **Smart Asset Linking (DBC):**
    * Instead of typing `ModelID: 1123`, the user selects "Human Male" from a searchable dropdown.
    * This requires parsing `CreatureDisplayInfo.dbc`, `Faction.dbc`, and `Item.dbc`.
* **3D Viewer:**
    * Embed a `QtWebEngineView` widget.
    * Load a local HTML/JS page (using `wow-model-viewer.js`).
    * Bridge Python signals to JS to change models dynamically when a user selects a Model ID.

### 4.3 Editors
* **NPC Editor:**
    * **Stats:** Auto-calculate HP/Mana/Armor based on input Level, Class, and Rank.
    * **Flags:** Checkbox groups for `NpcFlags` (Gossip, Vendor, Trainer) and `UnitFlags`.
* **Quest Editor:**
    * **Narrative:** Fields for Title, Log Description, Quest Details, Offer Reward Text.
    * **Logic:** Dropdown search to link "Quest Giver" (NPC) and "Quest Ender".
    * **Rewards:** XP, Gold, Items, Reputation (calculated based on server rates).

---

## 5. Data Specifications

### 5.1 Save File Format (`.forge`)
We use JSON for local project saving.

    {
      "meta": {
        "project_name": "New Dungeon",
        "version": "1.0",
        "id_range": [500000, 501000],
        "author": "Admin"
      },
      "creatures": [
        {
          "entry": 500001,
          "name": "Boss Malig",
          "subname": "The Betrayer",
          "model_id": 1123,
          "level": 83,
          "rank": 3,
          "stats": { "hp": 150000, "mana": 0 },
          "flags": { "npc": 1, "unit": 0 }
        }
      ],
      "quests": []
    }

### 5.2 SQL Output Standards
All generated SQL must be **idempotent** (safe to run multiple times).

    -- [NPC] 500001 - Boss Malig
    DELETE FROM `creature_template` WHERE `entry` = 500001;
    INSERT INTO `creature_template`
    (`entry`, `modelid1`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `npcflag`, `unit_class`, `HealthModifier`)
    VALUES
    (500001, 1123, 'Boss Malig', 'The Betrayer', 83, 83, 14, 1, 1, 10.5);

    -- [Optional] Cleanup linked tables
    DELETE FROM `creature_loot_template` WHERE `entry` = 500001;

---

## 6. Implementation Roadmap

1.  **Phase 1: The Dashboard (MVP)**
    * Set up PySide6 main window.
    * Implement SOAP connection to AC server.
    * Implement Systemd service checking.
    * *Result:* A working Server Manager.
2.  **Phase 2: The Data Layer**
    * Implement DBC file parser (pywowlib).
    * Create "New Project" workflow.
3.  **Phase 3: The Editors**
    * Build NPC Editor UI.
    * Implement SQL Generator logic.
4.  **Phase 4: Visuals**
    * Integrate 3D WebGL viewer using QtWebEngine.