
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                               QLabel, QComboBox, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Signal
from src.ui.dashboard import DashboardWidget, SettingsWindow
from src.core.config_manager import ConfigManager
from src.core.campaign_manager import CampaignManager
from src.ui.tabs.account_tab import AccountTab
from src.ui.tabs.character_tab import CharacterTab
from src.ui.tabs.npc_tab import NpcTab
from src.ui.tabs.item_tab import ItemTab
from src.ui.tabs.quest_tab import QuestTab
from src.ui.tabs.campaign_tab import CampaignTab

class MainWindow(QMainWindow):
    realm_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AzerothForge")
        self.resize(1280, 800)
        
        # Initialize Core Services
        self.config_manager = ConfigManager()
        self.campaign_manager = CampaignManager(self.config_manager)
        
        # Setup Theme
        self.setup_dark_theme()

        self.init_ui()

    def init_ui(self):
        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top Toolbar
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel("Active Realm:"))
        
        self.realm_combo = QComboBox()
        self.realm_combo.setMinimumWidth(200)
        self.realm_combo.currentIndexChanged.connect(self.on_realm_changed)
        top_layout.addWidget(self.realm_combo)
        
        top_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                border: 1px solid #555; 
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #555; }
        """)
        top_layout.addWidget(settings_btn)

        viewer_btn = QPushButton("Model Viewer")
        viewer_btn.clicked.connect(self.open_model_viewer)
        viewer_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white;
                border: 1px solid #1976D2; 
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #42A5F5; }
        """)
        top_layout.addWidget(viewer_btn)
        
        main_layout.addLayout(top_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Dashboard
        self.dashboard = DashboardWidget(self.config_manager)
        # Connect signal
        # Connect signal
        self.realm_changed.connect(self.dashboard.on_realm_changed)
        self.tabs.addTab(self.dashboard, "Mission Control")
        
        # Tab 2: Campaigns
        self.campaign_tab = CampaignTab(self.campaign_manager, self.config_manager)
        self.tabs.addTab(self.campaign_tab, "Campaigns")
        
        # Manager Tabs
        self.account_tab = AccountTab(self.config_manager)
        self.tabs.addTab(self.account_tab, "Accounts")
        
        self.character_tab = CharacterTab(self.config_manager)
        self.tabs.addTab(self.character_tab, "Characters")
        
        self.npc_tab = NpcTab(self.campaign_manager)
        self.tabs.addTab(self.npc_tab, "NPCs")
        
        self.item_tab = ItemTab(self.config_manager)
        self.tabs.addTab(self.item_tab, "Items")
        
        self.quest_tab = QuestTab(self.campaign_manager)
        self.tabs.addTab(self.quest_tab, "Quests")
        
        # Connect Manager Tabs to Realm Change
        self.realm_changed.connect(self.account_tab.on_realm_changed)
        self.realm_changed.connect(self.character_tab.on_realm_changed)
        self.realm_changed.connect(self.item_tab.on_realm_changed)
        # NPC and Quest Tabs use CampaignManager, which reads active realm dynamically, 
        # but they might need refresh if displaying data? They are mostly editors.
        # Let's add them if they have the method.
        if hasattr(self.npc_tab, 'on_realm_changed'):
            self.realm_changed.connect(self.npc_tab.on_realm_changed)
        if hasattr(self.quest_tab, 'on_realm_changed'):
            self.realm_changed.connect(self.quest_tab.on_realm_changed)
            
        # Initialize Realm List
        self.refresh_realm_selector()
        
    def refresh_realm_selector(self):
        self.realm_combo.blockSignals(True)
        self.realm_combo.clear()
        realms = self.config_manager.get_realms()
        for r in realms:
            self.realm_combo.addItem(f"[{r.get('id', '?')}] {r.get('name', 'Unnamed')}")
            
        current_idx = self.config_manager.config.get("active_realm_index", 0)
        if 0 <= current_idx < self.realm_combo.count():
            self.realm_combo.setCurrentIndex(current_idx)
            
        self.realm_combo.blockSignals(False)

    def on_realm_changed(self, index):
        self.config_manager.set_active_realm_index(index)
        self.realm_changed.emit()

    def open_settings(self):
        dialog = SettingsWindow(self.config_manager, self)
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec()

    def open_model_viewer(self):
        from src.ui.tools.model_viewer_window import ModelViewerWindow
        self.viewer_window = ModelViewerWindow(self)
        self.viewer_window.show()

    def on_config_saved(self):
        # Refresh realm list in case names/IDs changed or new realms added
        self.refresh_realm_selector()
        self.realm_changed.emit()

    def setup_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background: #2b2b2b;
            }
            QTabBar::tab {
                background: #3c3c3c;
                color: #ffffff;
                padding: 8px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #505050;
                border-bottom: 2px solid #5c6bc0;
                font-weight: bold;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555;
                margin-top: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #aaa;
            }
        """)
