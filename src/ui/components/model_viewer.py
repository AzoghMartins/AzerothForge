import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer

try:
    from direct.showbase.ShowBase import ShowBase
    from panda3d.core import (WindowProperties, GeomVertexData, GeomVertexFormat, GeomVertexWriter, 
                              Geom, GeomNode, GeomPoints, GeomTriangles, NodePath, 
                              DirectionalLight, AmbientLight, VBase4, Material)
    import builtins

    PANDA_AVAILABLE = True
except ImportError:
    PANDA_AVAILABLE = False
    print("Panda3D not available.")

from src.core.mpq_manager import MpqManager
from src.utils.m2_parser import M2Parser
from src.utils.skin_parser import SkinParser

class Panda3DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Critical for Embedding on X11/Linux
        self.setAttribute(Qt.WA_NativeWindow, True) 
        self.setAttribute(Qt.WA_PaintOnScreen, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        self.ShowBase = None
        self.is_initialized = False
        self.pivot = None
        
        if PANDA_AVAILABLE:
            # We defer initialization until we are sure the window has an XID
            # usually showEvent or a slightly longer timer
            QTimer.singleShot(200, self.initialize_panda)

    def initialize_panda(self):
        if not PANDA_AVAILABLE:
            return
            
        if self.is_initialized:
            return

        # Ensure we have a valid WinId (XID)
        win_id = int(self.winId())
        if not win_id:
            # Try again later if window not ready
            QTimer.singleShot(100, self.initialize_panda)
            return

        # Prerequisite: Configure Panda
        from panda3d.core import loadPrcFileData, WindowProperties
        
        # Check if ShowBase exists globally
        if hasattr(builtins, 'base'):
            self.ShowBase = builtins.base
            # If we are reusing, we might need to open a NEW window or reuse existing?
            # Creating a new window on an existing base is possible.
        else:
            # Force offscreen first to avoid creating a new window before we reparent
            loadPrcFileData("", "window-type none")
            # We create ShowBase
            self.ShowBase = ShowBase(windowType='none') 

        # Open Window attached to this widget
        props = WindowProperties()
        props.setParentWindow(win_id)
        props.setOrigin(0, 0)
        props.setSize(self.width(), self.height())
        
        self.ShowBase.openDefaultWindow(props=props)
        
        if not self.ShowBase.win:
             print("Panda3D failed to open window.")
             return

        # Setup Scene
        self.setup_lighting()
        self.setup_camera()
        
        # Start Update Loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step_panda)
        self.timer.start(16) # ~60 FPS
        
        self.is_initialized = True
        
        # Handle Resize
        # Overriding resizeEvent ensures Panda window scales.

    def setup_lighting(self):
        # Clear existing lights if any
        self.ShowBase.render.clearLight()
        
        # 1. Key Light (Directional)
        dlight = DirectionalLight('dlight')
        dlight.setColor(VBase4(1, 1, 1, 1))
        dlnp = self.ShowBase.render.attachNewNode(dlight)
        dlnp.setHpr(45, -45, 0) # Direction roughly (1, 1, -1)
        self.ShowBase.render.setLight(dlnp)
        
        # 2. Fill Light (Ambient)
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.3, 0.3, 0.3, 1))
        alnp = self.ShowBase.render.attachNewNode(alight)
        self.ShowBase.render.setLight(alnp)

    def setup_camera(self):
        # Orbit Logic
        self.ShowBase.disableMouse() # Disable default trackball
        
        # Pivot Node (Center of Rotation)
        if self.pivot:
            self.pivot.removeNode()
        self.pivot = self.ShowBase.render.attachNewNode("pivot")
        
        # Camera is child of Pivot
        self.ShowBase.cam.reparentTo(self.pivot)
        self.ShowBase.cam.setPos(0, -5, 0) # Start distance
        self.ShowBase.cam.lookAt(self.pivot)
        
        # Input Logic Task
        self.ShowBase.taskMgr.add(self.update_camera_task, "UpdateCameraTask")
        
        self.last_mouse_x = 0
        self.last_mouse_y = 0

    def update_camera_task(self, task):
        # We need to check if mouse is inside window?
        # Using Panda's MouseWatcher
        if not self.ShowBase.mouseWatcherNode.hasMouse():
            return task.cont
            
        md = self.ShowBase.win.getPointer(0)
        x = md.getX()
        y = md.getY()
        
        if self.ShowBase.mouseWatcherNode.isButtonDown('mouse1'):
            # Left Click Drag -> Rotate
            # Calculate delta
            dx = x - self.last_mouse_x
            dy = y - self.last_mouse_y
            
            # Application of rotation to pivot
            # H (Heading) = Yaw, P (Pitch) = vertical
            self.pivot.setH(self.pivot.getH() - dx * 0.5)
            self.pivot.setP(self.pivot.getP() - dy * 0.5)
            
        elif self.ShowBase.mouseWatcherNode.isButtonDown('mouse3'):
             # Right Click Drag -> Zoom
             dy = y - self.last_mouse_y
             
             # Move camera closer/further
             # Cam is child of pivot, so just change Y local
             current_y = self.ShowBase.cam.getY()
             new_y = current_y - dy * 0.05
             self.ShowBase.cam.setY(new_y)
             
        self.last_mouse_x = x
        self.last_mouse_y = y
        
        return task.cont

    def resizeEvent(self, event):
        if self.ShowBase and self.ShowBase.win:
            props = WindowProperties()
            props.setSize(self.width(), self.height())
            self.ShowBase.win.requestProperties(props)
        super().resizeEvent(event)

    def step_panda(self):
        if self.ShowBase:
            self.ShowBase.taskMgr.step()

    def load_model(self, m2_path: str):
        if not self.is_initialized:
            print("Viewer not ready.")
            return

        mpq = MpqManager()
        if not mpq.client_path:
             from src.core.config_manager import ConfigManager
             cm = ConfigManager()
             client_path = cm.config.get("wow_client_path") 
             if client_path:
                 mpq.initialize(client_path)
             else:
                 print("WoW Client Path not configured.")
                 return

        # 1. Read M2 File
        print(f"Loading M2: {m2_path}")
        m2_data = mpq.read_file(m2_path)
        if not m2_data:
            print(f"Could not find file: {m2_path}")
            return
            
        parser = M2Parser()
        vertices = parser.parse_geometry(m2_data)
        
        if not vertices:
            print("No vertices found.")
            return

        # 2. Read Skin File
        # Try finding the corresponding skin file
        # Rules: replace .m2/M2 with 00.skin
        # M2 paths are often mixed case.
        # Try constructing skin path and using search?
        
        # Simple string replacement first
        base_path_lower = m2_path.lower()
        if base_path_lower.endswith('.m2'):
            skin_path_candidate = m2_path[:-3] + "00.skin"
        else:
            skin_path_candidate = m2_path + "00.skin"
            
        # We need to find the ACTUAL filename in the MPQ because standard case might not match?
        # MpqManager.read_file handles case sensitivity attempts now!
        
        print(f"Loading Skin: {skin_path_candidate}")
        skin_data = mpq.read_file(skin_path_candidate)
        
        if not skin_data:
             print("Skin file not found. Falling back to Point Cloud.")
             self.render_point_cloud(vertices)
             return
             
        skin_parser = SkinParser()
        indices_lookup, triangles = skin_parser.parse_skin(skin_data)
        
        if not indices_lookup or not triangles:
             print("Failed to parse Skin. Falling back to Point Cloud.")
             self.render_point_cloud(vertices)
             return
             
        self.render_mesh(vertices, indices_lookup, triangles)

    def render_point_cloud(self, vertices):
        # Clear previous
        if getattr(self, 'model_node', None):
            self.model_node.removeNode()
            
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('points', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        for v_data in vertices:
            # Handle both (pos, normal) tuple and just pos (legacy safety)
            if isinstance(v_data, tuple) and len(v_data) == 2 and isinstance(v_data[0], tuple):
                 pos = v_data[0]
            else:
                 pos = v_data
                 
            x, y, z = pos
            vertex.addData3f(-y, x, z)
            
        prim = GeomPoints(Geom.UHStatic)
        prim.addNextVertices(len(vertices))
        prim.closePrimitive()
        
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode('m2_points')
        node.addGeom(geom)
        
        self.model_node = self.ShowBase.render.attachNewNode(node)
        self.model_node.setColor(1, 1, 0, 1) # Yellow Points
        self.model_node.setRenderModeThickness(3)
        
        self.zoom_to_fit()

    def render_mesh(self, vertices, indices_lookup, triangles):
        # Clear previous
        if getattr(self, 'model_node', None):
            self.model_node.removeNode()
            
        format = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData('mesh', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        
        # Optimize: 
        # Construct a mapped vertex list for Panda?
        # Panda allows direct indexing.
        # But we have two layers of indirection: Triangle -> SkinIndex -> M2Index -> Vertex
        # Panda supports GeomTriangles with an index buffer.
        # If we load ALL M2 vertices into the vdata, we can create an index buffer that matches the Skin logic?
        # Skin "indices_lookup" maps the Skin's local vertex concept to the M2's implementation.
        # "triangles" refers to the Skin's local vertices.
        # So: triangle[0] = 5  -> means use Skin Vertex 5.
        # indices_lookup[5] = 132 -> means Skin Vertex 5 is M2 Vertex 132.
        # So we want to tell Panda to use Index 132?
        
        # Approach A: Load all M2 vertices into Panda VData.
        # Then create a GeomPrimitives array using: indices_lookup[triangles[i]].
        # This is efficient because invalid/unused M2 vertices just sit there unused.
        
        # Add ALL vertices
        for v_data in vertices:
            # v_data is ((x,y,z), (nx,ny,nz))
            pos_data, norm_data = v_data
            
            x, y, z = pos_data
            nx, ny, nz = norm_data
            
            # Apply Coordinate Transform: WoW (X, Y, Z) -> Panda (-Y, X, Z)
            vertex.addData3f(-y, x, z)
            normal.addData3f(-ny, nx, nz)
            
        # Create Primitives
        # Standard GeomTriangles
        prim = GeomTriangles(Geom.UHStatic)
        
        # We need to resolve the indices
        # triangle_indices = [indices_lookup[t_idx] for t_idx in triangles]
        # But wait, 'triangles' is a list of uint16.
        # We can write these directly if we map them first.
        
        # Error Check: Ensure indices are within bounds
        max_v = len(vertices)
        
        # Add in batches?
        for t_idx in triangles:
             if t_idx < len(indices_lookup):
                 m2_idx = indices_lookup[t_idx]
                 if m2_idx < max_v:
                     prim.addVertex(m2_idx)
                     
        prim.closePrimitive()
        
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode('m2_mesh')
        node.addGeom(geom)
        
        self.model_node = self.ShowBase.render.attachNewNode(node)
        self.model_node.setColor(0.5, 0.5, 0.5, 1) # Clay Grey
        self.model_node.setTwoSided(True) 
        self.model_node.setShaderAuto() # Enable lighting/shadows 
        
        # Apply Default Material
        m = Material()
        m.setSpecular(VBase4(1, 1, 1, 1))
        m.setShininess(50)
        self.model_node.setMaterial(m, 1) # Override
        
        # Center Pivot on Model
        self.zoom_to_fit()

    def zoom_to_fit(self):
        if self.model_node.isEmpty(): return
        min_pt, max_pt = self.model_node.getTightBounds()
        if min_pt.isNan() or max_pt.isNan(): return
        
        center = (min_pt + max_pt) / 2
        diag = (max_pt - min_pt).length()
        if diag < 0.001: diag = 1.0
        
        # Move Model to Origin relative to Pivot? 
        # Or Move Pivot to Model Center?
        # Easier: Move Pivot to Model Center.
        if self.pivot:
             self.pivot.setPos(center)
             
        # Offset Camera
        # Cam is child of Pivot.
        self.ShowBase.cam.setPos(0, -diag * 1.5, 0)
        self.ShowBase.cam.lookAt(self.pivot)
        
    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            
        if self.ShowBase:
            if self.ShowBase.win:
                 self.ShowBase.closeWindow(self.ShowBase.win)
            
            # Remove task
            self.ShowBase.taskMgr.remove("UpdateCameraTask")
            
        self.is_initialized = False
