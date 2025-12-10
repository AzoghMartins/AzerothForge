from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListWidget, QFormLayout, QLineEdit, QSpinBox, 
                               QPushButton, QLabel, QMessageBox, QGroupBox, QScrollArea, QMenu, QTabWidget, QFileDialog, QCheckBox)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
from src.core.config_manager import ConfigManager
from src.utils.system_scanner import scan_for_services
from src.core.data_manager import DataManager
import os

class SettingsWindow(QDialog):
    config_saved = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Realm Configuration")
        self.resize(750, 600)
        self.config_manager = config_manager
        
        self.local_config = self.config_manager.config.copy()
        
        self.init_ui()
        self.load_realms()
        self.load_auth_config()
        self.load_client_data_config()

    def init_ui(self):
        # Main layout holds a Tab Widget now
        main_layout_base = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- Tab 1: Realm Config (Existing UI) ---
        realm_tab = QWidget()
        realm_layout = QHBoxLayout(realm_tab)
        
        # Left Side: Realm List
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Realms"))
        
        self.realm_list = QListWidget()
        self.realm_list.currentRowChanged.connect(self.on_realm_selected)
        left_panel.addWidget(self.realm_list)
        
        # Sync Button
        self.sync_btn = QPushButton("🔄 Sync Realms from DB")
        self.sync_btn.clicked.connect(self.sync_realms)
        self.sync_btn.setStyleSheet("background-color: #2196F3; color: white;")
        left_panel.addWidget(self.sync_btn)
        
        realm_layout.addLayout(left_panel, 1)
        
        # Right Side: Configuration
        right_panel = QVBoxLayout()
        
        # 1. Global Authentication
        auth_group = QGroupBox("Global Settings")
        auth_layout = QFormLayout()
        
        auth_service_layout = QHBoxLayout()
        self.auth_service_edit = QLineEdit()
        self.auth_service_edit.setPlaceholderText("systemd service (e.g. authserver)")
        self.auth_scan_btn = QPushButton("🔍")
        self.auth_scan_btn.setFixedWidth(30)
        self.auth_scan_btn.clicked.connect(lambda: self.show_service_menu(self.auth_service_edit))
        auth_service_layout.addWidget(self.auth_service_edit)
        auth_service_layout.addWidget(self.auth_scan_btn)
        
        self.db_host_edit = QLineEdit()
        self.db_port_spin = QSpinBox()
        self.db_port_spin.setRange(1, 65535)
        self.db_user_edit = QLineEdit()
        self.db_pass_edit = QLineEdit()
        self.db_pass_edit.setEchoMode(QLineEdit.Password)
        self.db_name_edit = QLineEdit()
        
        auth_layout.addRow("Auth Service Name:", auth_service_layout)
        auth_layout.addRow("DB Host:", self.db_host_edit)
        auth_layout.addRow("DB Port:", self.db_port_spin)
        auth_layout.addRow("DB User:", self.db_user_edit)
        auth_layout.addRow("DB Pass:", self.db_pass_edit)
        auth_layout.addRow("Auth DB Name:", self.db_name_edit)
        
        auth_group.setLayout(auth_layout)
        right_panel.addWidget(auth_group)
        
        # 2. Selected Realm Group (Container)
        self.realm_group = QGroupBox("Selected Realm Configuration")
        realm_main_layout = QVBoxLayout()
        
        # Read-Only Details
        details_layout = QHBoxLayout()
        self.r_id_label = QLabel("-")
        self.r_game_port_label = QLabel("-")
        details_layout.addWidget(QLabel("ID:"))
        details_layout.addWidget(self.r_id_label)
        details_layout.addSpacing(15)
        details_layout.addWidget(QLabel("Game Port:"))
        details_layout.addWidget(self.r_game_port_label)
        details_layout.addStretch()
        realm_main_layout.addLayout(details_layout)
        
        # A. Database Config
        db_group = QGroupBox("Database Configuration")
        db_layout = QFormLayout()
        
        self.world_db_edit = QLineEdit()
        self.world_db_edit.textChanged.connect(self.on_realm_field_changed)
        self.chars_db_edit = QLineEdit()
        self.chars_db_edit.textChanged.connect(self.on_realm_field_changed)
        
        db_layout.addRow("World DB:", self.world_db_edit)
        db_layout.addRow("Chars DB:", self.chars_db_edit)
        db_group.setLayout(db_layout)
        realm_main_layout.addWidget(db_group)
        
        # B. Service Config
        service_group = QGroupBox("Service Configuration")
        service_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_realm_field_changed)
        
        service_input_layout = QHBoxLayout()
        self.service_edit = QLineEdit()
        self.service_edit.setPlaceholderText("e.g. azerothcore-world")
        self.service_edit.textChanged.connect(self.on_realm_field_changed)
        self.world_scan_btn = QPushButton("🔍")
        self.world_scan_btn.setFixedWidth(30)
        self.world_scan_btn.clicked.connect(lambda: self.show_service_menu(self.service_edit))
        service_input_layout.addWidget(self.service_edit)
        service_input_layout.addWidget(self.world_scan_btn)
        
        self.soap_port_spin = QSpinBox()
        self.soap_port_spin.setRange(1, 65535)
        self.soap_port_spin.valueChanged.connect(self.on_realm_field_changed)
        
        self.soap_user_edit = QLineEdit()
        self.soap_user_edit.textChanged.connect(self.on_realm_field_changed)
        
        self.soap_pass_edit = QLineEdit()
        self.soap_pass_edit.setEchoMode(QLineEdit.Password)
        self.soap_pass_edit.textChanged.connect(self.on_realm_field_changed)
        
        service_layout.addRow("Local Name:", self.name_edit)
        service_layout.addRow("Service Name:", service_input_layout)
        service_layout.addRow("SOAP Port:", self.soap_port_spin)
        service_layout.addRow("SOAP User:", self.soap_user_edit)
        service_layout.addRow("SOAP Pass:", self.soap_pass_edit)
        
        # Playerbots Config
        self.bots_check = QCheckBox("Enable Playerbots Support")
        self.bots_check.stateChanged.connect(self.on_realm_field_changed)
        self.bots_check.toggled.connect(self.toggle_bot_prefix)
        
        self.bot_prefix_edit = QLineEdit()
        self.bot_prefix_edit.setPlaceholderText("Prefix (e.g. 'bot')")
        self.bot_prefix_edit.textChanged.connect(self.on_realm_field_changed)
        
        service_layout.addRow(self.bots_check)
        service_layout.addRow("Bot Prefix:", self.bot_prefix_edit)
        
        service_group.setLayout(service_layout)
        realm_main_layout.addWidget(service_group)
        
        self.realm_group.setLayout(realm_main_layout)
        right_panel.addWidget(self.realm_group)
        
        realm_layout.addLayout(right_panel, 2)
        self.tabs.addTab(realm_tab, "Realm Settings")
        
        # --- Tab 2: Client Data ---
        client_tab = QWidget()
        client_layout = QVBoxLayout(client_tab)
        
        path_group = QGroupBox("Client Data Location")
        path_layout = QHBoxLayout()
        
        self.client_path_edit = QLineEdit()
        self.client_path_edit.setPlaceholderText("/path/to/Wow/Data/enUS")
        path_layout.addWidget(self.client_path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_client_path)
        path_layout.addWidget(self.browse_btn)
        
        path_group.setLayout(path_layout)
        client_layout.addWidget(path_group)
        client_layout.addStretch()
        
        self.tabs.addTab(client_tab, "Client Data")
        
        main_layout_base.addWidget(self.tabs)
        
        # Save Button (Bottom of Dialog)
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setStyleSheet("background-color: #4caf50; color: white; font-weight: bold; padding: 10px;")
        main_layout_base.addWidget(save_btn)

    def load_auth_config(self):
        self.auth_service_edit.setText(self.local_config.get("auth_service_name", "authserver"))
        
        auth = self.local_config.get("auth_database", {})
        self.db_host_edit.setText(auth.get("host", "localhost"))
        self.db_port_spin.setValue(auth.get("port", 3306))
        self.db_user_edit.setText(auth.get("user", "acore"))
        self.db_pass_edit.setText(auth.get("password", ""))
        self.db_name_edit.setText(auth.get("db_name", "acore_auth"))

    def load_client_data_config(self):
        path = self.local_config.get("client_data_path", "")
        self.client_path_edit.setText(path)

    def browse_client_path(self):
        current_path = self.client_path_edit.text()
        start_dir = current_path if current_path and os.path.isdir(current_path) else ""
        
        path = QFileDialog.getExistingDirectory(self, "Select Client Data Directory", start_dir)
        if path:
            self.client_path_edit.setText(path)

    def update_global_config_from_ui(self):
        self.local_config["auth_service_name"] = self.auth_service_edit.text()
        self.local_config["client_data_path"] = self.client_path_edit.text()
        
        self.local_config["auth_database"] = {
            "host": self.db_host_edit.text(),
            "port": self.db_port_spin.value(),
            "user": self.db_user_edit.text(),
            "password": self.db_pass_edit.text(),
            "db_name": self.db_name_edit.text()
        }

    def load_realms(self):
        self.realm_list.clear()
        realms = self.local_config.get("realms", [])
        for realm in realms:
            r_id = realm.get("id", "?")
            name = realm.get("name", "Unnamed")
            self.realm_list.addItem(f"[{r_id}] {name}")
            
        if self.realm_list.count() > 0:
            self.realm_list.setCurrentRow(0)
        else:
            self.realm_group.setEnabled(False)

    def on_realm_selected(self, row):
        if row < 0:
            self.realm_group.setEnabled(False)
            return
            
        self.realm_group.setEnabled(True)
        realm = self.local_config["realms"][row]
        
        # Block signals
        self.name_edit.blockSignals(True)
        self.service_edit.blockSignals(True)
        self.soap_port_spin.blockSignals(True)
        self.soap_user_edit.blockSignals(True)
        self.soap_pass_edit.blockSignals(True)
        self.world_db_edit.blockSignals(True)

        self.chars_db_edit.blockSignals(True)
        self.bots_check.blockSignals(True)
        self.bot_prefix_edit.blockSignals(True)
        
        # Update details
        self.r_id_label.setText(str(realm.get("id", "-")))
        self.r_game_port_label.setText(str(realm.get("game_port", "-")))
        
        # Service Config
        self.name_edit.setText(realm.get("name", ""))
        self.service_edit.setText(realm.get("service_name", ""))
        self.soap_port_spin.setValue(int(realm.get("soap_port", 7878)))
        self.soap_user_edit.setText(realm.get("soap_user", ""))
        self.soap_pass_edit.setText(realm.get("soap_pass", ""))
        
        # DB Config
        self.world_db_edit.setText(realm.get("db_world_name", "acore_world"))
        self.chars_db_edit.setText(realm.get("db_chars_name", "acore_characters"))
        
        # Playerbots
        self.bots_check.setChecked(realm.get("playerbots_enabled", False))
        self.bot_prefix_edit.setText(realm.get("bot_prefix", "bot"))
        self.toggle_bot_prefix(self.bots_check.isChecked())
        
        # Unblock
        self.name_edit.blockSignals(False)
        self.service_edit.blockSignals(False)
        self.soap_port_spin.blockSignals(False)
        self.soap_user_edit.blockSignals(False)
        self.soap_pass_edit.blockSignals(False)
        self.world_db_edit.blockSignals(False)
        self.chars_db_edit.blockSignals(False)
        self.bots_check.blockSignals(False)
        self.bot_prefix_edit.blockSignals(False)

    def on_realm_field_changed(self):
        row = self.realm_list.currentRow()
        if row >= 0:
            realm = self.local_config["realms"][row]
            
            realm["name"] = self.name_edit.text()
            realm["service_name"] = self.service_edit.text()
            realm["soap_port"] = self.soap_port_spin.value()
            realm["soap_user"] = self.soap_user_edit.text()
            realm["soap_pass"] = self.soap_pass_edit.text()
            
            realm["db_world_name"] = self.world_db_edit.text()
            realm["db_chars_name"] = self.chars_db_edit.text()
            
            realm["playerbots_enabled"] = self.bots_check.isChecked()
            realm["bot_prefix"] = self.bot_prefix_edit.text()
            
            # Update list label if name changed
            self.realm_list.item(row).setText(f"[{realm.get('id','?')}] {realm['name']}")

    def toggle_bot_prefix(self, checked):
        self.bot_prefix_edit.setEnabled(checked)

    def show_service_menu(self, target_line_edit: QLineEdit):
        services = scan_for_services()
        if not services:
            QMessageBox.information(self, "Scanner", "No relevant services found.")
            return

        menu = QMenu(self)
        for service in services:
            action = QAction(service, self)
            action.triggered.connect(lambda checked=False, s=service: target_line_edit.setText(s))
            menu.addAction(action)
        
        menu.exec(target_line_edit.mapToGlobal(target_line_edit.rect().bottomLeft()))

    def sync_realms(self):
        # First, ensure DB config is up to date in local_config
        self.update_global_config_from_ui()
        self.config_manager.config["auth_database"] = self.local_config["auth_database"]
        self.config_manager.config["auth_service_name"] = self.local_config["auth_service_name"]
        
        # Call discovery
        new_realms = self.config_manager.discover_realms()
        self.local_config["realms"] = new_realms
        
        self.load_realms()
        QMessageBox.information(self, "Sync Complete", f"Found {len(new_realms)} realms from database.")

    def save_and_close(self):
        old_path = self.config_manager.config.get("client_data_path", "")
        self.update_global_config_from_ui()
        self.config_manager.save_config(self.local_config)
        self.config_saved.emit()
        
        new_path = self.local_config.get("client_data_path", "")
        if new_path != old_path:
             print("Client Data Path changed. Reloading data...")
             DataManager().load_data()
             
        self.accept()
