from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QDoubleSpinBox
from PySide6.QtCore import Qt
from src.ui.components.model_viewer import Panda3DWidget
from src.core.data_manager import DataManager
from src.core.mpq_manager import MpqManager
from src.core.config_manager import ConfigManager

class ModelViewerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WoW Model Viewer (Native)")
        self.resize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Controls
        controls = QWidget()
        c_layout = QVBoxLayout(controls)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter M2 Path or Search Term")
        self.path_input.setText("Creature\\LichKing\\LichKing.m2")
        
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Model")
        self.load_btn.clicked.connect(self.load_model)
        
        self.search_btn = QPushButton("Search DBC")
        self.search_btn.clicked.connect(self.search_dbc)
        
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.search_btn)
        
        c_layout.addWidget(self.path_input)
        c_layout.addLayout(btn_layout)
        
        # Search Results
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(150)
        self.result_list.itemDoubleClicked.connect(self.on_result_clicked)
        self.result_list.setVisible(False) # Hide initially
        c_layout.addWidget(self.result_list)

        self.layer_buttons = QHBoxLayout()
        self.layers_all_btn = QPushButton("All Layers")
        self.layers_all_btn.clicked.connect(self.enable_all_layers)
        self.layers_none_btn = QPushButton("No Layers")
        self.layers_none_btn.clicked.connect(self.disable_all_layers)
        self.layer_buttons.addWidget(self.layers_all_btn)
        self.layer_buttons.addWidget(self.layers_none_btn)
        c_layout.addLayout(self.layer_buttons)

        self.layer_lists_row = QHBoxLayout()

        layer_col = QVBoxLayout()
        self.layer_list_label = QLabel("Submeshes")
        layer_col.addWidget(self.layer_list_label)
        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(220)
        self.layer_list.itemChanged.connect(self.on_layer_changed)
        layer_col.addWidget(self.layer_list)
        self.layer_lists_row.addLayout(layer_col, 2)

        hair_col = QVBoxLayout()
        self.hair_texture_label = QLabel("Hair Texture Families")
        hair_col.addWidget(self.hair_texture_label)
        self.hair_texture_list = QListWidget()
        self.hair_texture_list.setMaximumHeight(220)
        self.hair_texture_list.itemSelectionChanged.connect(self.on_hair_texture_changed)
        hair_col.addWidget(self.hair_texture_list)

        uv_row_1 = QHBoxLayout()
        self.hair_uv_scale_u = QDoubleSpinBox()
        self.hair_uv_scale_u.setRange(0.01, 4.0)
        self.hair_uv_scale_u.setSingleStep(0.05)
        self.hair_uv_scale_u.setDecimals(3)
        self.hair_uv_scale_u.setValue(0.5)
        self.hair_uv_scale_v = QDoubleSpinBox()
        self.hair_uv_scale_v.setRange(0.01, 4.0)
        self.hair_uv_scale_v.setSingleStep(0.05)
        self.hair_uv_scale_v.setDecimals(3)
        self.hair_uv_scale_v.setValue(0.5)
        self.hair_uv_scale_u_label = QLabel("Scale U")
        uv_row_1.addWidget(self.hair_uv_scale_u_label)
        uv_row_1.addWidget(self.hair_uv_scale_u)
        self.hair_uv_scale_v_label = QLabel("Scale V")
        uv_row_1.addWidget(self.hair_uv_scale_v_label)
        uv_row_1.addWidget(self.hair_uv_scale_v)
        hair_col.addLayout(uv_row_1)

        uv_row_2 = QHBoxLayout()
        self.hair_uv_offset_u = QDoubleSpinBox()
        self.hair_uv_offset_u.setRange(-1.0, 1.0)
        self.hair_uv_offset_u.setSingleStep(0.01)
        self.hair_uv_offset_u.setDecimals(3)
        self.hair_uv_offset_u.setValue(0.0)
        self.hair_uv_offset_v = QDoubleSpinBox()
        self.hair_uv_offset_v.setRange(-1.0, 1.0)
        self.hair_uv_offset_v.setSingleStep(0.01)
        self.hair_uv_offset_v.setDecimals(3)
        self.hair_uv_offset_v.setValue(0.0)
        self.hair_uv_offset_u_label = QLabel("Offset U")
        uv_row_2.addWidget(self.hair_uv_offset_u_label)
        uv_row_2.addWidget(self.hair_uv_offset_u)
        self.hair_uv_offset_v_label = QLabel("Offset V")
        uv_row_2.addWidget(self.hair_uv_offset_v_label)
        uv_row_2.addWidget(self.hair_uv_offset_v)
        hair_col.addLayout(uv_row_2)

        self.reset_uv_btn = QPushButton("Reset UV")
        self.reset_uv_btn.clicked.connect(self.reset_hair_uv)
        hair_col.addWidget(self.reset_uv_btn)

        self.hair_uv_scale_u.valueChanged.connect(self.on_hair_uv_changed)
        self.hair_uv_scale_v.valueChanged.connect(self.on_hair_uv_changed)
        self.hair_uv_offset_u.valueChanged.connect(self.on_hair_uv_changed)
        self.hair_uv_offset_v.valueChanged.connect(self.on_hair_uv_changed)
        self.layer_lists_row.addLayout(hair_col, 1)

        c_layout.addLayout(self.layer_lists_row)
        self._show_layer_controls(False)
        self._updating_layer_list = False
        self._updating_hair_texture_list = False
        self._updating_hair_uv = False
        
        layout.addWidget(controls)
        
        # Viewer
        # Check if Panda is available
        try:
            import panda3d.core
            self.viewer = Panda3DWidget()
            self.viewer.layersChanged.connect(self.populate_layer_list)
            self.viewer.hairTextureOptionsChanged.connect(self.populate_hair_texture_list)
            layout.addWidget(self.viewer, 1) # Stretch
        except ImportError:
            self.viewer = None
            layout.addWidget(QPushButton("Panda3D not installed. Cannot view models."))

    def _show_layer_controls(self, visible):
        self.layer_list_label.setVisible(visible)
        self.layer_list.setVisible(visible)
        self.layers_all_btn.setVisible(visible)
        self.layers_none_btn.setVisible(visible)
        if not visible:
            self.hair_texture_label.setVisible(False)
            self.hair_texture_list.setVisible(False)
            self.hair_uv_scale_u.setVisible(False)
            self.hair_uv_scale_v.setVisible(False)
            self.hair_uv_offset_u.setVisible(False)
            self.hair_uv_offset_v.setVisible(False)
            self.hair_uv_scale_u_label.setVisible(False)
            self.hair_uv_scale_v_label.setVisible(False)
            self.hair_uv_offset_u_label.setVisible(False)
            self.hair_uv_offset_v_label.setVisible(False)
            self.reset_uv_btn.setVisible(False)

    def load_model(self):
        if self.viewer:
            path = self.path_input.text()
            self.viewer.load_model(path)

    def search_dbc(self):
        term = self.path_input.text()
        if not term:
            return
            
        dm = DataManager()
        # Ensure data is loaded
        if not dm.display_infos:
            dm.load_data()
            
        results = dm.search_models(term)
        mpq = MpqManager()
        if not mpq.archives:
            cm = ConfigManager()
            wow_path = cm.config.get("wow_client_path")
            if wow_path:
                mpq.initialize(wow_path)
        
        self.result_list.clear()
        if results:
            self.result_list.setVisible(True)
            added = 0
            for did, path, tex in results:
                resolved = mpq.resolve_file_path(path) if mpq.archives else path
                if not resolved:
                    continue
                info = dm.display_infos.get(did, {})
                display_text = f"[{did}] {path}"
                if tex:
                    display_text += f" (Skin: {tex})"
                
                item = QListWidgetItem(display_text)
                # Store full data for loading
                item.setData(Qt.UserRole, {
                    'model': resolved,
                    'texture': tex,
                    'display_id': did,
                    'extra_id': info.get('extra_id'),
                    'extra': info.get('extra', {})
                })
                self.result_list.addItem(item)
                added += 1
            if added == 0:
                self.result_list.addItem("No MPQ-backed model paths found for this search.")
        else:
            self.result_list.setVisible(True)
            self.result_list.addItem("No results found in DBC.")

    def search_mpq(self):
        from src.core.mpq_manager import MpqManager
        term = self.path_input.text()
        if not term:
            return
            
        # Ensure MPQ is init (via viewer or manually)
        # Viewer inits MPQ on load... we might need to trigger init if not loaded.
        # But MpqManager is singleton. 
        mpq = MpqManager()
        if not mpq.archives:
             # Try forcing init via viewer logic or getting config
             from src.core.config_manager import ConfigManager
             cm = ConfigManager()
             path = cm.config.get("wow_client_path")
             if path:
                 mpq.initialize(path)
        
        results = mpq.search_files(term)
        self.result_list.clear()
        if results:
            self.result_list.setVisible(True)
            for r in results:
                self.result_list.addItem(r)
        else:
            self.result_list.setVisible(True)
            self.result_list.addItem("No results found.")

    def on_result_clicked(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.path_input.setText(data['model'])
            self.viewer.load_model(
                data['model'],
                texture_path=data.get('texture'),
                display_id=data.get('display_id'),
                extra_id=data.get('extra_id'),
                display_extra=data.get('extra')
            )
        else:
            # Fallback for plain string items (e.g. from MPQ search if we kept it)
            self.path_input.setText(item.text())
            self.load_model()

    def populate_layer_list(self, layers):
        self._updating_layer_list = True
        self.layer_list.clear()
        if not layers:
            self._show_layer_controls(False)
            self._updating_layer_list = False
            return

        for layer in layers:
            item = QListWidgetItem(layer.get("label", "Layer"))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setData(Qt.UserRole, layer.get("key"))
            item.setCheckState(Qt.Checked if layer.get("checked", True) else Qt.Unchecked)
            self.layer_list.addItem(item)

        self._show_layer_controls(True)
        self._updating_layer_list = False

    def on_layer_changed(self, _item):
        if self._updating_layer_list or not self.viewer:
            return
        active = []
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            if item.checkState() == Qt.Checked:
                active.append(item.data(Qt.UserRole))
        self.viewer.set_active_layers(active)

    def enable_all_layers(self):
        if self.layer_list.count() == 0:
            return
        self._updating_layer_list = True
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.Checked)
        self._updating_layer_list = False
        self.on_layer_changed(None)

    def populate_hair_texture_list(self, options):
        self._updating_hair_texture_list = True
        self.hair_texture_list.clear()

        if not options:
            self.hair_texture_label.setVisible(False)
            self.hair_texture_list.setVisible(False)
            self.hair_uv_scale_u.setVisible(False)
            self.hair_uv_scale_v.setVisible(False)
            self.hair_uv_offset_u.setVisible(False)
            self.hair_uv_offset_v.setVisible(False)
            self.hair_uv_scale_u_label.setVisible(False)
            self.hair_uv_scale_v_label.setVisible(False)
            self.hair_uv_offset_u_label.setVisible(False)
            self.hair_uv_offset_v_label.setVisible(False)
            self.reset_uv_btn.setVisible(False)
            self._updating_hair_texture_list = False
            return

        self.hair_texture_label.setVisible(True)
        self.hair_texture_list.setVisible(True)
        self.hair_uv_scale_u.setVisible(True)
        self.hair_uv_scale_v.setVisible(True)
        self.hair_uv_offset_u.setVisible(True)
        self.hair_uv_offset_v.setVisible(True)
        self.hair_uv_scale_u_label.setVisible(True)
        self.hair_uv_scale_v_label.setVisible(True)
        self.hair_uv_offset_u_label.setVisible(True)
        self.hair_uv_offset_v_label.setVisible(True)
        self.reset_uv_btn.setVisible(True)
        selected_item = None
        for option in options:
            item = QListWidgetItem(option.get("label", "Texture"))
            item.setData(Qt.UserRole, option.get("hint", ""))
            self.hair_texture_list.addItem(item)
            if option.get("selected"):
                selected_item = item

        if selected_item is None and self.hair_texture_list.count() > 0:
            selected_item = self.hair_texture_list.item(0)
        if selected_item is not None:
            self.hair_texture_list.setCurrentItem(selected_item)

        self._updating_hair_texture_list = False

    def on_hair_texture_changed(self):
        if self._updating_hair_texture_list or not self.viewer:
            return
        item = self.hair_texture_list.currentItem()
        if not item:
            return
        self.viewer.set_hair_texture_hint(item.data(Qt.UserRole) or "")

    def on_hair_uv_changed(self):
        if self._updating_hair_uv or not self.viewer:
            return
        self.viewer.set_hair_uv_transform(
            self.hair_uv_scale_u.value(),
            self.hair_uv_scale_v.value(),
            self.hair_uv_offset_u.value(),
            self.hair_uv_offset_v.value(),
        )

    def reset_hair_uv(self):
        self._updating_hair_uv = True
        self.hair_uv_scale_u.setValue(0.5)
        self.hair_uv_scale_v.setValue(0.5)
        self.hair_uv_offset_u.setValue(0.0)
        self.hair_uv_offset_v.setValue(0.0)
        self._updating_hair_uv = False
        self.on_hair_uv_changed()

    def disable_all_layers(self):
        if self.layer_list.count() == 0:
            return
        self._updating_layer_list = True
        for i in range(self.layer_list.count()):
            self.layer_list.item(i).setCheckState(Qt.Unchecked)
        self._updating_layer_list = False
        self.on_layer_changed(None)

    def closeEvent(self, event):
        if self.viewer:
            self.viewer.cleanup()
            self.viewer.close() # Ensure widget close event fires too
        super().closeEvent(event)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    
    # Mock Config for MPQ (Quick Hack for testing if run directly)
    # Ideally should run via main app
    win = ModelViewerWindow()
    win.show()
    app.exec()
