import sys
import os
import re
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel

try:
    from direct.showbase.ShowBase import ShowBase
    from panda3d.core import (WindowProperties, GeomVertexData, GeomVertexFormat, GeomVertexWriter, 
                              Geom, GeomNode, GeomPoints, GeomTriangles, NodePath, 
                              DirectionalLight, AmbientLight, VBase4, Material, Texture, TextureStage)
    import builtins

    PANDA_AVAILABLE = True
except ImportError:
    PANDA_AVAILABLE = False
    print("Panda3D not available.")

from src.core.mpq_manager import MpqManager
from src.core.character_preset_resolver import CharacterPresetResolver
from src.utils.m2_parser import M2Parser
from src.utils.skin_parser import SkinParser
from src.utils.blp_converter import BlpConverter

class Panda3DWidget(QWidget):
    layersChanged = Signal(list)
    hairTextureOptionsChanged = Signal(list)

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
        self.scene_root = None
        self.model_node = None
        self.flip_v = False
        self._cached_vertices = None
        self._cached_indices_lookup = None
        self._cached_triangles = None
        self._layer_defs = []
        self._active_layer_keys = set()
        self._attachment_meshes = []
        self._layer_texture_overrides = {}
        self._character_submesh_texture_types = {}
        self._character_submesh_render_modes = {}
        self._character_using_baked_texture = False
        self._current_model_path = ""
        self._current_display_extra = {}
        self._mpq = None
        self._manual_hair_texture_hint = ""
        self._hair_texture_options = []
        self._hair_layer_keys = set()
        self._facial_layer_keys = set()
        self._facial_uses_hair_uv = False
        self._facial_uv_scale_u = 1.0
        self._facial_uv_scale_v = 1.0
        self._facial_uv_offset_u = 0.0
        self._facial_uv_offset_v = 0.0
        self._hair_uv_scale_u = 0.5
        self._hair_uv_scale_v = 0.5
        self._hair_uv_offset_u = 0.0
        self._hair_uv_offset_v = 0.0
        self._active_hair_uv_scale_u = 0.5
        self._active_hair_uv_scale_v = 0.5
        self._active_hair_uv_offset_u = 0.0
        self._active_hair_uv_offset_v = 0.0
        self._preset_resolver = CharacterPresetResolver()
        
        # Attempt embedded init when Panda + display are available.
        if PANDA_AVAILABLE and os.environ.get("DISPLAY"):
            QTimer.singleShot(200, self.initialize_panda)
        else:
            self.disable_viewer()

    def initialize_panda(self):
        if not PANDA_AVAILABLE:
            return
        if self.is_initialized:
            return

        # Ensure we have a valid WinId (XID)
        win_id = int(self.winId())
        if not win_id:
            QTimer.singleShot(100, self.initialize_panda)
            return

        try:
            from panda3d.core import loadPrcFileData, WindowProperties

            # Use offscreen bootstrap first; will be reparented.
            if hasattr(builtins, 'base'):
                self.ShowBase = builtins.base
            else:
                loadPrcFileData("", "window-type none")
                self.ShowBase = ShowBase(windowType='none')

            props = WindowProperties()
            props.setParentWindow(win_id)
            props.setOrigin(0, 0)
            props.setSize(self.width(), self.height())

            self.ShowBase.openDefaultWindow(props=props)

            if not self.ShowBase.win:
                raise RuntimeError("Panda3D failed to open GLX window")

            self.ShowBase.setBackgroundColor(0, 0, 0)
            self.setup_lighting()
            self.setup_camera()
            self.scene_root = self.ShowBase.render.attachNewNode("scene_root")

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.step_panda)
            self.timer.start(16)

            self.is_initialized = True
        except Exception as e:
            # Graceful fallback: disable viewer to avoid GLX errors (BadMatch/BadDrawable)
            print(f"Panda3D init failed, disabling viewer: {e}")
            self.disable_viewer()

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

    def _dedupe_paths(self, paths):
        out = []
        seen = set()
        for p in paths:
            if not p:
                continue
            n = p.replace("/", "\\").lower()
            if n in seen:
                continue
            seen.add(n)
            out.append(p)
        return out

    def _internal_basename(self, path):
        if not path:
            return ""
        return path.replace("/", "\\").split("\\")[-1]

    def _internal_dirname(self, path):
        if not path:
            return ""
        parts = path.replace("/", "\\").split("\\")
        if len(parts) <= 1:
            return ""
        return "\\".join(parts[:-1])

    def _texture_score(self, path, model_name=""):
        p = path.lower()
        score = 0
        if "skin" in p:
            score += 30
        if "diffuse" in p:
            score += 20
        if model_name and model_name in p:
            score += 8
        if "01.blp" in p:
            score += 4

        # Reflection/env maps usually are not the creature diffuse texture.
        for noisy in ("reflect", "env", "gloss", "shine", "spec", "orb"):
            if noisy in p:
                score -= 40
        return score

    def _texture_path_candidates(self, resolved_model, texture_hint, prefer_hd=False):
        hint = (texture_hint or "").strip().replace("/", "\\")
        if not hint:
            return []

        model_dir = self._internal_dirname(resolved_model)
        basename = self._internal_basename(hint)
        base_no_ext, ext = os.path.splitext(basename)

        candidates = []

        def add_with_hd(base_path):
            if not base_path:
                return
            if base_path.lower().endswith(".blp"):
                hd_path = base_path[:-4] + "_HD.blp"
                if prefer_hd:
                    candidates.append(hd_path)
                    candidates.append(base_path)
                else:
                    candidates.append(base_path)
                    candidates.append(hd_path)
            else:
                if prefer_hd:
                    candidates.append(f"{base_path}_HD.blp")
                candidates.append(base_path)
                candidates.append(f"{base_path}.blp")

        # DBC texture variations are often plain names (e.g. "WolfSkinTimber")
        # and need to be resolved relative to the model directory.
        add_with_hd(hint)

        # Character baked textures are often only available as *_HD.blp.
        if base_no_ext.lower().startswith("creaturedisplayextra-") and ext.lower() != ".blp":
            candidates.append(f"{hint}_HD.blp")

        if model_dir:
            rel_base = f"{model_dir}\\{basename}"
            add_with_hd(rel_base)
            if ext.lower() != ".blp":
                add_with_hd(f"{model_dir}\\{base_no_ext}")

        return self._dedupe_paths(candidates)

    def _load_texture_from_candidates(self, mpq, candidates):
        for candidate in candidates:
            resolved = mpq.resolve_file_path(candidate) or candidate
            print(f"DEBUG: Trying texture candidate: {resolved}")
            tex_data = mpq.read_file(resolved)
            if tex_data:
                print(f"SUCCESS: Loaded texture candidate {resolved}")
                return tex_data
        return None

    def _model_hint_candidates(self, model_hint: str, slot: int = 0):
        hint = (model_hint or "").strip().replace("/", "\\")
        if not hint:
            return []

        lower = hint.lower()
        if lower.endswith(".mdx"):
            hint = hint[:-4] + ".m2"
        elif not lower.endswith(".m2"):
            hint = hint + ".m2"

        basename = self._internal_basename(hint)
        candidates = [hint]

        if "\\" not in hint:
            slot_dirs = {
                1: "Item\\ObjectComponents\\Head",
                2: "Item\\ObjectComponents\\Shoulder",
                11: "Item\\ObjectComponents\\Cape",
            }
            preferred_dir = slot_dirs.get(slot)
            if preferred_dir:
                candidates.append(f"{preferred_dir}\\{basename}")
            # Generic fallback if slot mapping is absent.
            candidates.append(f"Item\\ObjectComponents\\Shoulder\\{basename}")

        return self._dedupe_paths(candidates)

    def _build_texture(self, tex_data):
        if not tex_data:
            return None
        converter = BlpConverter()
        tex_info = converter.process_blp(tex_data)
        if not tex_info:
            return None

        width, height, image_data, tex_fmt = tex_info
        print(f"DEBUG: Texture Format: {tex_fmt} | Size: {width}x{height} | Data Len: {len(image_data)}")

        tex = Texture()
        tex.setXSize(width)
        tex.setYSize(height)
        tex.setFormat(Texture.F_rgba)

        if tex_fmt == "DXT1":
            tex.setCompression(Texture.CM_dxt1)
        elif tex_fmt == "DXT3":
            tex.setCompression(Texture.CM_dxt3)
        elif tex_fmt == "DXT5":
            tex.setCompression(Texture.CM_dxt5)
        else:
            tex.setCompression(Texture.CM_off)

        print(f"DEBUG: Texture Compression Mode: {tex.getCompression()}")
        tex.setRamImage(image_data, tex.getCompression())
        return tex

    def _load_mesh_payload(self, mpq, model_hint: str, texture_hint: str = None, slot: int = 0):
        model_candidates = self._model_hint_candidates(model_hint, slot=slot)
        if not model_candidates:
            return None

        resolved_model = None
        for candidate in model_candidates:
            resolved_model = mpq.resolve_file_path(candidate)
            if resolved_model:
                break

        if not resolved_model:
            base = os.path.splitext(self._internal_basename(model_hint or ""))[0]
            if base:
                hits = [h for h in mpq.search_files(base) if h.lower().endswith(".m2")]
                if slot == 2:
                    hits.sort(key=lambda p: ("objectcomponents\\shoulder" not in p.lower(), len(p)))
                if hits:
                    resolved_model = hits[0]

        if not resolved_model:
            print(f"DEBUG: Could not resolve attachment model: {model_hint}")
            return None

        print(f"DEBUG: Loading attachment model: {resolved_model}")
        m2_data = mpq.read_file(resolved_model)
        if not m2_data:
            return None

        parser = M2Parser()
        vertices = parser.parse_geometry(m2_data)
        if not vertices:
            return None

        model_name = os.path.splitext(self._internal_basename(resolved_model))[0].lower()
        tex_data = None

        if texture_hint:
            tex_candidates = self._texture_path_candidates(resolved_model, texture_hint, prefer_hd=True)
            tex_data = self._load_texture_from_candidates(mpq, tex_candidates)

        if not tex_data:
            internal_tex = parser.parse_textures(m2_data)
            if internal_tex:
                tex_data = mpq.read_file(internal_tex)

        if not tex_data:
            internal_list = parser.get_internal_texture_list(m2_data)
            if internal_list:
                internal_list.sort(key=lambda p: self._texture_score(p, model_name), reverse=True)
                tex_data = self._load_texture_from_candidates(mpq, internal_list[:8])

        if not tex_data:
            model_dir = self._internal_dirname(resolved_model)
            if model_dir:
                dir_hits = [p for p in mpq.search_files(model_dir) if p.lower().endswith(".blp")]
                if dir_hits:
                    dir_hits.sort(key=lambda p: self._texture_score(p, model_name), reverse=True)
                    tex_data = self._load_texture_from_candidates(mpq, dir_hits[:8])

        tex = self._build_texture(tex_data)

        base_path_lower = resolved_model.lower()
        if base_path_lower.endswith(".m2"):
            skin_path_candidate = resolved_model[:-3] + "00.skin"
        else:
            skin_path_candidate = resolved_model + "00.skin"

        resolved_skin = mpq.resolve_file_path(skin_path_candidate) or skin_path_candidate
        skin_data = mpq.read_file(resolved_skin)
        if not skin_data:
            print(f"DEBUG: Missing attachment skin: {resolved_skin}")
            return None

        indices_lookup, triangles, _submeshes = SkinParser().parse_skin(skin_data)
        if not indices_lookup or not triangles:
            return None

        return {
            "model": resolved_model,
            "vertices": vertices,
            "indices_lookup": indices_lookup,
            "triangles": triangles,
            "texture": tex,
        }

    def _find_attachment_pos(self, attachment_points, attach_id):
        for row in attachment_points or []:
            if int(row.get("id", -1)) == int(attach_id):
                return row.get("pos")
        return None

    def _find_attachment_pos_by_priority(self, attachment_points, ids):
        for attach_id in ids:
            pos = self._find_attachment_pos(attachment_points, attach_id)
            if pos:
                return pos, attach_id
        return None, None

    def _prepare_character_item_attachments(self, mpq, display_extra, attachment_points):
        self._attachment_meshes = []
        extra = display_extra if isinstance(display_extra, dict) else {}
        rows = extra.get("npc_item_details") or []
        if not rows:
            return

        for row in rows:
            slot = int(row.get("slot", 0) or 0)
            if slot != 2:
                continue

            left_model = (row.get("model_1") or "").strip()
            right_model = (row.get("model_2") or "").strip()
            left_tex = (row.get("model_texture_1") or "").strip()
            right_tex = (row.get("model_texture_2") or "").strip()

            # Shoulder anchors vary by model family; these priorities prefer
            # true shoulder points (5/6) and then fall back to legacy (3/4).
            left_pos, left_attach_id = self._find_attachment_pos_by_priority(attachment_points, [6, 4, 3, 5])
            right_pos, right_attach_id = self._find_attachment_pos_by_priority(attachment_points, [5, 3, 4, 6])
            print(
                f"DEBUG: Shoulder attachment pick -> left_id={left_attach_id}, right_id={right_attach_id}"
            )

            if left_model and left_pos:
                payload = self._load_mesh_payload(mpq, left_model, left_tex, slot=slot)
                if payload:
                    self._attachment_meshes.append({
                        "label": "LeftShoulder",
                        "attach_id": left_attach_id,
                        "pos": left_pos,
                        "mesh": payload,
                    })
                    print(f"DEBUG: Equipped left shoulder: {payload.get('model')}")

            if right_model and right_pos:
                payload = self._load_mesh_payload(mpq, right_model, right_tex, slot=slot)
                if payload:
                    self._attachment_meshes.append({
                        "label": "RightShoulder",
                        "attach_id": right_attach_id,
                        "pos": right_pos,
                        "mesh": payload,
                    })
                    print(f"DEBUG: Equipped right shoulder: {payload.get('model')}")

        if self._attachment_meshes:
            print(f"DEBUG: Prepared {len(self._attachment_meshes)} equipment attachments.")

    def _create_mesh_node(self, vertices, indices_lookup, triangles, texture=None, name="m2_mesh", parent=None):
        format = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData(name, format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        texcoord = GeomVertexWriter(vdata, "texcoord")

        for pos_data, norm_data, uv_data in vertices:
            x, y, z = pos_data
            nx, ny, nz = norm_data
            u, v = uv_data

            vertex.addData3f(-y, x, z)
            normal.addData3f(-ny, nx, nz)
            if self.flip_v:
                texcoord.addData2f(u, 1.0 - v)
            else:
                texcoord.addData2f(u, v)

        prim = GeomTriangles(Geom.UHStatic)
        max_v = len(vertices)
        for t_idx in triangles:
            if t_idx < len(indices_lookup):
                m2_idx = indices_lookup[t_idx]
                if m2_idx < max_v:
                    prim.addVertex(m2_idx)
        prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)

        target = parent if parent is not None else (self.scene_root if self.scene_root else self.ShowBase.render)
        node_path = target.attachNewNode(node)
        node_path.setColor(0.5, 0.5, 0.5, 1)
        node_path.setTwoSided(True)
        node_path.setShaderAuto()

        material = Material()
        material.setSpecular(VBase4(1, 1, 1, 1))
        material.setShininess(50)
        node_path.setMaterial(material, 1)

        if texture is not None:
            node_path.setTexture(texture, 1)
            node_path.setColor(1, 1, 1, 1)

        return node_path

    def _render_cached_attachments(self):
        if not self.model_node or self.model_node.isEmpty():
            return
        for idx, row in enumerate(self._attachment_meshes):
            mesh = row.get("mesh") or {}
            node = self._create_mesh_node(
                mesh.get("vertices") or [],
                mesh.get("indices_lookup") or [],
                mesh.get("triangles") or [],
                texture=mesh.get("texture"),
                name=f"attach_{idx}",
                parent=self.model_node,
            )
            pos = row.get("pos")
            if pos:
                x, y, z = pos
                node.setPos(-y, x, z)

    def _resolve_hair_family_candidates(self, mpq, hair_hint):
        """
        Build a list of HairXX_YY candidates for the same race/gender/color.
        We intentionally return a probe range (00-15) even when files may be
        missing so users can test families interactively.
        """
        hint = (hair_hint or "").replace("/", "\\")
        m = re.search(r"^(.*\\Hair)(\d{2})_(\d{2})\.blp$", hint, re.IGNORECASE)
        if not m:
            return []

        base = m.group(1)
        color = m.group(3)
        out = []
        for family in range(0, 16):
            probe = f"{base}{family:02d}_{color}.blp"
            out.append(probe.replace("/", "\\"))
        return self._dedupe_paths(out)

    def _update_hair_texture_options(self, mpq, hair_texture_hints):
        self._hair_texture_options = []
        hints = self._dedupe_paths([(h or "").replace("/", "\\") for h in (hair_texture_hints or []) if h])
        if not hints:
            self.hairTextureOptionsChanged.emit([])
            return

        base_hint = ""
        for hint in hints:
            if re.search(r"\\Hair\d{2}_\d{2}\.blp$", hint, re.IGNORECASE):
                base_hint = hint
                break
        if not base_hint:
            base_hint = hints[0]

        options = []
        dbc_hint = base_hint

        family_candidates = self._resolve_hair_family_candidates(mpq, base_hint)
        if family_candidates:
            for candidate in family_candidates:
                if candidate.lower() == dbc_hint.lower():
                    label = f"{self._internal_basename(candidate)} *"
                else:
                    label = self._internal_basename(candidate)
                options.append({
                    "label": label,
                    "hint": candidate,
                    "selected": (
                        candidate.lower() == (self._manual_hair_texture_hint or "").lower()
                        or (
                            not self._manual_hair_texture_hint
                            and candidate.lower() == dbc_hint.lower()
                        )
                    ),
                })
        else:
            for hint in hints:
                options.append({
                    "label": self._internal_basename(hint),
                    "hint": hint,
                    "selected": (
                        hint.lower() == (self._manual_hair_texture_hint or "").lower()
                        or (
                            not self._manual_hair_texture_hint
                            and hint.lower() == dbc_hint.lower()
                        )
                    ),
                })

        # Keep UI selection consistent if a stale manual path is set.
        if self._manual_hair_texture_hint and not any(o["selected"] for o in options):
            self._manual_hair_texture_hint = dbc_hint
            for option in options:
                option["selected"] = option.get("hint", "").lower() == dbc_hint.lower()

        self._hair_texture_options = options
        self.hairTextureOptionsChanged.emit(self._hair_texture_options)

    def set_hair_texture_hint(self, hint):
        normalized = (hint or "").replace("/", "\\").strip()
        if normalized.lower() == (self._manual_hair_texture_hint or "").lower():
            return
        self._manual_hair_texture_hint = normalized

        if self._mpq and self._current_display_extra:
            self._prepare_character_layer_textures(self._mpq, self._current_display_extra)
            if self._cached_vertices is not None and self._cached_indices_lookup is not None:
                triangles = self._triangles_from_active_layers()
                self.render_mesh(self._cached_vertices, self._cached_indices_lookup, triangles)

    def set_hair_uv_transform(self, scale_u, scale_v, offset_u, offset_v):
        self._hair_uv_scale_u = float(scale_u)
        self._hair_uv_scale_v = float(scale_v)
        self._hair_uv_offset_u = float(offset_u)
        self._hair_uv_offset_v = float(offset_v)
        self._active_hair_uv_scale_u = self._hair_uv_scale_u
        self._active_hair_uv_scale_v = self._hair_uv_scale_v
        self._active_hair_uv_offset_u = self._hair_uv_offset_u
        self._active_hair_uv_offset_v = self._hair_uv_offset_v

        if self._cached_vertices is None or self._cached_indices_lookup is None:
            return
        triangles = self._triangles_from_active_layers()
        self.render_mesh(self._cached_vertices, self._cached_indices_lookup, triangles)

    def _prepare_character_layer_textures(self, mpq, display_extra):
        self._layer_texture_overrides = {}
        self._hair_layer_keys = set()
        self._facial_layer_keys = set()
        self._facial_uses_hair_uv = False
        self._facial_uv_scale_u = 1.0
        self._facial_uv_scale_v = 1.0
        self._facial_uv_offset_u = 0.0
        self._facial_uv_offset_v = 0.0
        self._active_hair_uv_scale_u = self._hair_uv_scale_u
        self._active_hair_uv_scale_v = self._hair_uv_scale_v
        self._active_hair_uv_offset_u = self._hair_uv_offset_u
        self._active_hair_uv_offset_v = self._hair_uv_offset_v
        extra = display_extra if isinstance(display_extra, dict) else {}
        if not self._layer_defs or not extra:
            self.hairTextureOptionsChanged.emit([])
            return
        race = int(extra.get("race", 0) or 0)

        def _set_facial_uv_from_race():
            self._facial_uses_hair_uv = True
            race = int(extra.get("race", 0) or 0)
            if race == 4:  # Night Elf
                self._facial_uv_scale_u = 1.0
                self._facial_uv_scale_v = 1.0
            else:
                self._facial_uv_scale_u = self._active_hair_uv_scale_u
                self._facial_uv_scale_v = self._active_hair_uv_scale_v

        hair_texture_hints = self._dedupe_paths([
            (hint or "").replace("/", "\\")
            for hint in (extra.get("resolved_hair_textures") or [])
            if hint
        ])
        if hair_texture_hints:
            self._update_hair_texture_options(mpq, hair_texture_hints)
        else:
            self.hairTextureOptionsChanged.emit([])

        if self._manual_hair_texture_hint:
            manual_hint = self._manual_hair_texture_hint.replace("/", "\\")
            if manual_hint not in hair_texture_hints:
                hair_texture_hints = [manual_hint] + hair_texture_hints
            else:
                hair_texture_hints = [manual_hint] + [h for h in hair_texture_hints if h.lower() != manual_hint.lower()]
            print(f"DEBUG: Hair texture manual override: {manual_hint}")
        if hair_texture_hints:
            print(f"DEBUG: Hair texture hints from CharSections: {hair_texture_hints}")

        hair_tex = None
        selected_hair_hint = ""
        hair_tex_is_tiny = False
        hair_targeted_keys = []
        if hair_texture_hints:
            for idx, hint in enumerate(hair_texture_hints):
                candidates = self._texture_path_candidates(self._current_model_path, hint, prefer_hd=True)
                print(f"DEBUG: Hair texture hint {hint} -> candidates: {candidates}")
                tex_data = self._load_texture_from_candidates(mpq, candidates)
                if not tex_data:
                    continue
                tex = self._build_texture(tex_data)
                if tex is None:
                    continue
                tex.setWrapU(Texture.WM_clamp)
                tex.setWrapV(Texture.WM_clamp)
                hair_tex = tex
                selected_hair_hint = hint

                # If the first hit is tiny, probe remaining hints for a better atlas.
                if (
                    hair_tex.getXSize() <= 64
                    and hair_tex.getYSize() <= 64
                    and idx + 1 < len(hair_texture_hints)
                ):
                    best_alt = None
                    best_rank = (-1, -1)
                    for alt_hint in hair_texture_hints[idx + 1:]:
                        alt_candidates = self._texture_path_candidates(self._current_model_path, alt_hint, prefer_hd=True)
                        print(f"DEBUG: Hair fallback hint {alt_hint} -> candidates: {alt_candidates}")
                        alt_data = self._load_texture_from_candidates(mpq, alt_candidates)
                        if not alt_data:
                            continue
                        alt_tex = self._build_texture(alt_data)
                        if alt_tex is None:
                            continue
                        alt_tex.setWrapU(Texture.WM_clamp)
                        alt_tex.setWrapV(Texture.WM_clamp)
                        area = int(alt_tex.getXSize()) * int(alt_tex.getYSize())
                        name = os.path.basename(alt_hint).lower()
                        pref = 2 if "scalpupperhair" in name else (1 if "scalplowerhair" in name else 0)
                        rank = (pref, area)
                        if rank > best_rank:
                            best_rank = rank
                            best_alt = (alt_hint, alt_tex)
                    if best_alt is not None:
                        selected_hair_hint, hair_tex = best_alt
                        print(
                            "DEBUG: Switched hair override atlas from tiny base hint to "
                            f"{selected_hair_hint}."
                        )
                # Use the first successfully loaded hint unless we intentionally
                # replaced it via the tiny-texture fallback probe above.
                break
            if hair_tex is not None:
                print(
                    "DEBUG: Final hair override atlas: "
                    f"{selected_hair_hint} ({hair_tex.getXSize()}x{hair_tex.getYSize()})."
                )
                # Tiny section textures (e.g. 64x64) usually use full UV range.
                # Keep overriding, but switch to full-scale UV so the hair map
                # is sampled correctly instead of collapsing to a dark quadrant.
                if hair_tex.getXSize() <= 64 and hair_tex.getYSize() <= 64:
                    hair_tex_is_tiny = True
                    self._active_hair_uv_scale_u = 1.0
                    self._active_hair_uv_scale_v = 1.0
                    print(
                        "DEBUG: Hair section texture is tiny; using full hair UV scale "
                        "(1.0, 1.0) for this model."
                    )
                elif "scalp" in selected_hair_hint.lower():
                    self._active_hair_uv_scale_u = 1.0
                    self._active_hair_uv_scale_v = 1.0
                    print(
                        "DEBUG: Using scalp hair atlas; forcing hair UV scale "
                        "(1.0, 1.0) for this model."
                    )

        hair_base_id = int(extra.get("resolved_hair_geoset", 0) or 0)
        if hair_tex is not None and hair_base_id > 0:
            # Route hairstyle texture to the selected hairstyle base submesh only.
            # Texture type metadata is used as a guard, but we avoid painting every
            # type-6 layer (which includes other facial/hair pieces).
            targeted_keys = []
            for layer in self._layer_defs:
                if int(layer.get("id", 0)) != hair_base_id:
                    continue
                key = str(layer["key"])
                tex_type = self._character_submesh_texture_types.get(key)
                if tex_type is not None and int(tex_type) != 6:
                    continue
                targeted_keys.append(key)

            affected = 0
            for key in targeted_keys:
                self._layer_texture_overrides[key] = hair_tex
                self._hair_layer_keys.add(key)
                affected += 1
            hair_targeted_keys = list(targeted_keys)

            if affected:
                print(
                    f"DEBUG: Applied hair texture override to {affected} layer(s) "
                    f"for base geoset ID {hair_base_id}."
                )
        elif hair_base_id <= 0:
            print("DEBUG: No hairstyle base geoset selected; skipping base hair-layer override.")

        # Some races route beard/mustache/brow pieces through Group1/2/3/7 layers.
        # Use SectionType 2 facial texture atlases when available.
        facial_hints = self._dedupe_paths([
            (hint or "").replace("/", "\\")
            for hint in (extra.get("resolved_facial_textures") or [])
            if hint
        ])
        if facial_hints:
            print(f"DEBUG: Facial texture hints from CharSections: {facial_hints}")

        facial_tex = []
        for hint in facial_hints[:2]:
            candidates = self._texture_path_candidates(self._current_model_path, hint, prefer_hd=True)
            print(f"DEBUG: Facial texture hint {hint} -> candidates: {candidates}")
            f_data = self._load_texture_from_candidates(mpq, candidates)
            f_tex = self._build_texture(f_data)
            if f_tex is not None:
                f_tex.setWrapU(Texture.WM_clamp)
                f_tex.setWrapV(Texture.WM_clamp)
                facial_tex.append(f_tex)

        lower_tex = facial_tex[0] if facial_tex else None
        upper_tex = facial_tex[1] if len(facial_tex) > 1 else lower_tex

        # Undead/Scourge female entries can provide tiny SectionType-3 hair
        # textures that do not match the hairstyle mesh. Use facial upper atlas
        # for the selected hairstyle layer when available.
        always_baked_facial_groups = {7}
        scourge_baked_groups = {1, 3} if race == 5 else set()
        baked_facial_groups = set(always_baked_facial_groups) | set(scourge_baked_groups)
        if baked_facial_groups:
            print(
                "DEBUG: Keeping baked texture for facial groups "
                f"{sorted(baked_facial_groups)}."
            )
        def _pick_scourge_facial_tex(group):
            if race != 5:
                return None
            # Scourge: beard data can show up in Group1 on some models and
            # Group3 on others. Keep both routed the same way.
            if group in (1, 3):
                if upper_tex is not None:
                    return upper_tex
                if lower_tex is not None:
                    return lower_tex
            if group == 7:
                if lower_tex is not None:
                    return lower_tex
                if upper_tex is not None:
                    return upper_tex
            if group in (1, 3, 7) and hair_tex is not None:
                return hair_tex
            return None

        if (
            race == 5
            and hair_tex_is_tiny
            and upper_tex is not None
            and hair_targeted_keys
        ):
            for key in hair_targeted_keys:
                self._layer_texture_overrides[key] = upper_tex
            print(
                "DEBUG: Scourge fallback: using facial upper texture for base hair layer "
                f"(keys={hair_targeted_keys})."
            )

        use_hair_for_facial = False
        if hair_tex is not None and lower_tex is not None:
            lower_name = os.path.basename(facial_hints[0]).lower() if facial_hints else ""
            upper_name = os.path.basename(facial_hints[1]).lower() if len(facial_hints) > 1 else ""
            # CharSections often references facial mask atlases (FacialLower/UpperHair).
            # In those cases we need color from the main hair atlas, not from the mask.
            hint_looks_like_mask = any(
                token in lower_name or token in upper_name
                for token in (
                    "faciallowerhair",
                    "facialupperhair",
                    "facialhairlower",
                    "facialhairupper",
                )
            )
            size_looks_like_mask = (
                lower_tex.getXSize() <= hair_tex.getXSize()
                and lower_tex.getYSize() * 2 <= hair_tex.getYSize()
            )
            hint_and_size_compatible = (
                hint_looks_like_mask
                and lower_tex.getXSize() <= hair_tex.getXSize()
                and lower_tex.getYSize() <= hair_tex.getYSize()
            )
            if size_looks_like_mask or hint_and_size_compatible:
                use_hair_for_facial = True
                _set_facial_uv_from_race()
                print(
                    "DEBUG: Facial textures look mask-like; using hair atlas for facial color "
                    f"(hint_mask={hint_looks_like_mask}, size_mask={size_looks_like_mask}, "
                    f"hint_size_ok={hint_and_size_compatible}, "
                    f"facial_uv_scale={self._facial_uv_scale_u:.3f},{self._facial_uv_scale_v:.3f})."
                )
        elif hair_tex is not None and not facial_hints:
            # Some entries only provide SectionType 3 (hair color atlas). Reuse it
            # for facial geosets so beard/mustache/brows are tinted instead of black.
            use_hair_for_facial = True
            _set_facial_uv_from_race()
            print(
                "DEBUG: No facial texture hints found; using hair atlas for facial groups "
                f"(facial_uv_scale={self._facial_uv_scale_u:.3f},{self._facial_uv_scale_v:.3f})."
            )
        elif not facial_tex and facial_hints:
            print("DEBUG: Facial hints present but no facial textures could be loaded.")

        if not use_hair_for_facial and lower_tex is None and upper_tex is None:
            return

        facial_applied = {1: 0, 2: 0, 3: 0, 7: 0}
        facial_layers = []
        facial_layers_by_group = {1: [], 2: [], 3: [], 7: []}
        for layer in self._layer_defs:
            sid = int(layer.get("id", 0))
            if sid < 100:
                continue
            group = sid // 100
            if group not in (1, 2, 3, 7):
                continue
            if group in baked_facial_groups:
                continue
            key = str(layer["key"])
            facial_layers.append((group, key))
            facial_layers_by_group[group].append(key)
            tex_type = self._character_submesh_texture_types.get(key)
            if tex_type is not None and int(tex_type) != 6:
                continue

            scourge_tex = _pick_scourge_facial_tex(group)
            if scourge_tex is not None:
                tex = scourge_tex
            elif use_hair_for_facial and hair_tex is not None:
                tex = hair_tex
            elif group == 1 and lower_tex is not None:
                tex = lower_tex
            elif upper_tex is not None:
                tex = upper_tex
            elif lower_tex is not None:
                tex = lower_tex
            else:
                continue
            self._layer_texture_overrides[key] = tex
            self._facial_layer_keys.add(key)
            facial_applied[group] += 1

        fallback_groups = [group for group, count in facial_applied.items() if count == 0 and facial_layers_by_group[group]]
        if fallback_groups:
            # Some models mark these geosets with non-6 texture types.
            # Backfill missing groups without strict texture-type filtering.
            for group in fallback_groups:
                for key in facial_layers_by_group[group]:
                    if key in self._facial_layer_keys:
                        continue
                    scourge_tex = _pick_scourge_facial_tex(group)
                    if scourge_tex is not None:
                        tex = scourge_tex
                    elif use_hair_for_facial and hair_tex is not None:
                        tex = hair_tex
                    elif group == 1 and lower_tex is not None:
                        tex = lower_tex
                    elif upper_tex is not None:
                        tex = upper_tex
                    elif lower_tex is not None:
                        tex = lower_tex
                    else:
                        continue
                    self._layer_texture_overrides[key] = tex
                    self._facial_layer_keys.add(key)
                    facial_applied[group] += 1
            print(f"DEBUG: Facial override fallback applied for groups: {fallback_groups}")

        total_facial = sum(facial_applied.values())
        if total_facial == 0 and facial_layers:
            # Final fallback: if nothing applied at all, try by layer list.
            for group, key in facial_layers:
                scourge_tex = _pick_scourge_facial_tex(group)
                if scourge_tex is not None:
                    tex = scourge_tex
                elif use_hair_for_facial and hair_tex is not None:
                    tex = hair_tex
                elif group == 1 and lower_tex is not None:
                    tex = lower_tex
                elif upper_tex is not None:
                    tex = upper_tex
                elif lower_tex is not None:
                    tex = lower_tex
                else:
                    continue
                self._layer_texture_overrides[key] = tex
                self._facial_layer_keys.add(key)
                facial_applied[group] += 1
            total_facial = sum(facial_applied.values())
            if total_facial:
                print("DEBUG: Facial override fallback applied without texture-type filter.")

        if total_facial:
            print(
                "DEBUG: Applied facial texture overrides to "
                f"{total_facial} layer(s): "
                f"g1={facial_applied[1]} g2={facial_applied[2]} "
                f"g3={facial_applied[3]} g7={facial_applied[7]}"
            )

    def _prepare_character_texture_units(self, m2_parser, skin_parser, m2_data, skin_data):
        self._character_submesh_texture_types = {}
        self._character_submesh_render_modes = {}
        tex_defs = m2_parser.parse_texture_defs(m2_data)
        if not tex_defs:
            return

        tex_type_by_index = {int(row["index"]): int(row.get("type", 0)) for row in tex_defs}
        render_flags = m2_parser.parse_render_flags(m2_data)
        render_flags_by_index = {int(row["index"]): row for row in render_flags}
        tex_units = skin_parser.parse_texture_units(skin_data)
        if not tex_units:
            return

        for unit in tex_units:
            submesh_index = int(unit.get("submesh_index", -1))
            tex_index = int(unit.get("texture_index", -1))
            tex_type = tex_type_by_index.get(tex_index)
            if tex_type is None:
                continue
            # Keep first mapping; duplicate texture units are uncommon for characters.
            if str(submesh_index) not in self._character_submesh_texture_types:
                self._character_submesh_texture_types[str(submesh_index)] = tex_type

            if str(submesh_index) not in self._character_submesh_render_modes:
                rf_idx = int(unit.get("render_flags_index", -1))
                rf = render_flags_by_index.get(rf_idx)
                if rf:
                    self._character_submesh_render_modes[str(submesh_index)] = {
                        "flags": int(rf.get("flags", 0)),
                        "blend_mode": int(rf.get("blend_mode", 0)),
                    }

        if self._character_submesh_texture_types:
            hair_layers = [
                key for key, tex_type in self._character_submesh_texture_types.items()
                if int(tex_type) == 6
            ]
            print(
                "DEBUG: Character texture-unit routing built: "
                f"{len(self._character_submesh_texture_types)} submeshes, "
                f"hair_layers={hair_layers}"
            )

    def _apply_layer_render_state(self, node_path, layer_key):
        mode = self._character_submesh_render_modes.get(str(layer_key))
        if not mode:
            return

        flags = int(mode.get("flags", 0))
        if flags & 0x04:
            node_path.setTwoSided(True)

    def _reset_layer_state(self, emit=True):
        self._layer_defs = []
        self._active_layer_keys = set()
        self._layer_texture_overrides = {}
        self._hair_layer_keys = set()
        self._facial_layer_keys = set()
        self._facial_uses_hair_uv = False
        self._facial_uv_scale_u = 1.0
        self._facial_uv_scale_v = 1.0
        self._facial_uv_offset_u = 0.0
        self._facial_uv_offset_v = 0.0
        self._active_hair_uv_scale_u = self._hair_uv_scale_u
        self._active_hair_uv_scale_v = self._hair_uv_scale_v
        self._active_hair_uv_offset_u = self._hair_uv_offset_u
        self._active_hair_uv_offset_v = self._hair_uv_offset_v
        self._character_submesh_texture_types = {}
        self._character_submesh_render_modes = {}
        self._hair_texture_options = []
        if emit:
            self.layersChanged.emit([])
            self.hairTextureOptionsChanged.emit([])

    def _layer_column_label(self, submesh_id: int) -> str:
        if submesh_id < 100:
            return "BaseBodySubmesh"
        group = submesh_id // 100
        mapping = {
            1: "SkinID",
            2: "FaceID",
            3: "HairStyleID",
            4: "Group4 LowerArms",
            5: "Group5 LowerLegs",
            7: "FacialHairID",
            8: "Group8 SleeveEnds",
            9: "Group9 Knees",
            10: "Group10 ShirtHem",
            11: "Group11 LongShirtHem",
            12: "Group12 TabardHem",
            13: "Group13 LegsSkirt",
            15: "Group15 ShouldersCloak",
            17: "Group17 Unknown",
            18: "Group18 Belt",
        }
        return mapping.get(group, f"Group{group}")

    def _build_character_layers(self, submeshes, triangles, display_extra=None):
        extra = display_extra if isinstance(display_extra, dict) else {}
        if extra:
            print(
                "DEBUG: DisplayExtra columns: "
                f"DisplayRaceID={extra.get('race', 0)}, "
                f"DisplaySexID={extra.get('gender', 0)}, "
                f"SkinID={extra.get('skin', 0)}, "
                f"FaceID={extra.get('face', 0)}, "
                f"HairStyleID={extra.get('hair_style', 0)}, "
                f"HairColorID={extra.get('hair_color', 0)}, "
                f"FacialHairID={extra.get('facial_hair', 0)}"
            )
            item_displays = extra.get("npc_item_displays", []) or []
            item_map = ", ".join(
                f"NPCItemDisplay{i+1}={v}" for i, v in enumerate(item_displays)
            )
            if item_map:
                print(f"DEBUG: DisplayExtra equipment columns: {item_map}")
            for row in extra.get("npc_item_details", []) or []:
                disp_id = int(row.get("display_id", 0) or 0)
                if disp_id == 0:
                    continue
                tex_parts = [t for t in (row.get("textures") or []) if t]
                print(
                    "DEBUG: ItemDisplayInfo "
                    f"slot={row.get('slot')} display={disp_id} "
                    f"model1={row.get('model_1', '')} model2={row.get('model_2', '')} "
                    f"geo=({row.get('geoset_group_1', 0)},{row.get('geoset_group_2', 0)},{row.get('geoset_group_3', 0)}) "
                    f"texture_parts={tex_parts[:4]}"
                )
            facial = extra.get("resolved_facial_geosets")
            if isinstance(facial, dict):
                print(
                    "DEBUG: Resolved facial geosets: "
                    f"source={facial.get('source')} row_id={facial.get('row_id')} "
                    f"variation={facial.get('variation')} "
                    f"g100={facial.get('geoset100')} g200={facial.get('geoset200')} "
                    f"g300={facial.get('geoset300')} g700={facial.get('geoset700')}"
                )
            if "resolved_hair_geoset" in extra:
                print(
                    "DEBUG: Resolved hair geoset: "
                    f"source={extra.get('resolved_hair_source')} geoset={extra.get('resolved_hair_geoset')}"
                )

        resolution = self._preset_resolver.resolve(submeshes, extra)
        selected_keys = {str(idx) for idx in resolution.get("selected_indexes", set())}
        selected_reason_by_index = resolution.get("selected_reason_by_index", {})
        picked_by_group = resolution.get("decisions", {})
        for group, decision in sorted(picked_by_group.items()):
            print(
                f"DEBUG: Geoset {group} ({decision.get('label', f'Group{group}')}) "
                f"-> {decision.get('source')}, "
                f"target={decision.get('target_id')}, picked={decision.get('picked_id')}, "
                f"status={decision.get('status')}, available={decision.get('candidates')}"
            )

        layer_defs = []
        for idx, sub in enumerate(submeshes):
            sub_id = int(sub.get("id", 0))
            tri_start = int(sub.get("triangle_start", 0))
            tri_count = int(sub.get("triangle_count", 0))
            if tri_count <= 0:
                continue

            column = self._layer_column_label(sub_id)
            target_txt = ""
            if sub_id >= 100:
                group = sub_id // 100
                pick = picked_by_group.get(group)
                if pick:
                    target = int(pick.get("target_id", 0))
                    reason = pick.get("source", "")
                    target_txt = f" | target={target} ({reason}){' *' if sub_id == int(pick.get('picked_id', 0)) else ''}"
            if not target_txt and idx in selected_reason_by_index:
                target_txt = f" | {selected_reason_by_index[idx]} *"

            label = f"[{idx}] ID={sub_id} | {column} | tris={tri_count}{target_txt}"
            layer_defs.append({
                "key": str(idx),
                "label": label,
                "triangle_start": tri_start,
                "triangle_count": tri_count,
                "id": sub_id,
                "checked": str(idx) in selected_keys,
            })

        self._layer_defs = layer_defs
        self._active_layer_keys = {d["key"] for d in layer_defs if d.get("checked")}
        if not self._active_layer_keys and layer_defs:
            # Fallback safety.
            self._active_layer_keys = {layer_defs[0]["key"]}
            layer_defs[0]["checked"] = True
        self._cached_triangles = triangles

        chosen_labeled = [
            f"{d['id']}:{self._layer_column_label(d['id'])}"
            for d in layer_defs
            if d.get("checked")
        ]
        print(
            f"DEBUG: Character geoset defaults: {chosen_labeled[:40]}"
            f"{' ...' if len(chosen_labeled) > 40 else ''}"
        )
        self.layersChanged.emit(self._layer_defs)

    def _triangles_from_active_layers(self):
        if not self._layer_defs or self._cached_triangles is None:
            return self._cached_triangles or []

        kept = []
        tri_len = len(self._cached_triangles)
        for layer in self._layer_defs:
            if layer["key"] not in self._active_layer_keys:
                continue
            start = int(layer.get("triangle_start", 0))
            count = int(layer.get("triangle_count", 0))
            if count <= 0:
                continue
            a = max(0, min(start, tri_len))
            b = max(a, min(start + count, tri_len))
            kept.extend(self._cached_triangles[a:b])

        print(
            f"DEBUG: Character layer filter kept {len(kept)} / {len(self._cached_triangles)} indices "
            f"from {len(self._active_layer_keys)} / {len(self._layer_defs)} layers."
        )
        return kept

    def set_active_layers(self, keys):
        self._active_layer_keys = {str(k) for k in keys}
        for layer in self._layer_defs:
            layer["checked"] = layer["key"] in self._active_layer_keys

        if self._cached_vertices is None or self._cached_indices_lookup is None:
            return
        if not self._layer_defs:
            return

        triangles = self._triangles_from_active_layers()
        self.render_mesh(self._cached_vertices, self._cached_indices_lookup, triangles)

    def load_model(self, m2_path: str, texture_path: str = None, display_id: int = None, extra_id: int = None, display_extra: dict = None):
        print(f"DEBUG: load_model called. M2: {m2_path}, Texture: {texture_path}, DisplayID: {display_id}, ExtraID: {extra_id}")

        if not self.is_initialized:
            print("Viewer not ready.")
            return

        # Always clear previous geometry to avoid stacking models.
        self.clear_scene()
        self._cached_vertices = None
        self._cached_indices_lookup = None
        self._cached_triangles = None
        self._attachment_meshes = []
        self._layer_texture_overrides = {}
        self._character_submesh_texture_types = {}
        self._character_submesh_render_modes = {}
        self._character_using_baked_texture = False
        self._current_model_path = ""
        self._current_display_extra = {}
        self._manual_hair_texture_hint = ""
        self._hair_texture_options = []
        self._hair_layer_keys = set()
        self._facial_layer_keys = set()
        self._facial_uses_hair_uv = False
        self._facial_uv_scale_u = 1.0
        self._facial_uv_scale_v = 1.0
        self._facial_uv_offset_u = 0.0
        self._facial_uv_offset_v = 0.0
        self._hair_uv_scale_u = 0.5
        self._hair_uv_scale_v = 0.5
        self._hair_uv_offset_u = 0.0
        self._hair_uv_offset_v = 0.0
        self._active_hair_uv_scale_u = 0.5
        self._active_hair_uv_scale_v = 0.5
        self._active_hair_uv_offset_u = 0.0
        self._active_hair_uv_offset_v = 0.0
        self._reset_layer_state(emit=True)

        mpq = MpqManager()
        self._mpq = mpq
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
        resolved_model = mpq.resolve_file_path(m2_path) or m2_path
        self._current_model_path = resolved_model
        self._current_display_extra = display_extra if isinstance(display_extra, dict) else {}
        print(f"Loading M2: {resolved_model}")
        m2_data = mpq.read_file(resolved_model)
        if not m2_data:
            print(f"Could not find file: {m2_path}")
            return
            
        parser = M2Parser()
        vertices = parser.parse_geometry(m2_data)
        
        if not vertices:
            print("No vertices found.")
            return

        is_character_model = resolved_model.lower().startswith("character\\")
        attachment_points = parser.parse_attachments(m2_data) if is_character_model else []
        if attachment_points:
            print(f"DEBUG: Parsed {len(attachment_points)} attachment points.")

        # Keep the same UV orientation for both pipelines; texture selection is the main split.
        self.flip_v = False
        model_name = os.path.splitext(self._internal_basename(resolved_model))[0].lower()

        # 2. Textures
        tex_data = None

        if is_character_model:
            texture_hints = []
            if texture_path:
                texture_hints.append(texture_path)
            if isinstance(display_extra, dict):
                bake_name = (display_extra.get("bake_name") or "").strip()
                if bake_name:
                    if "\\" in bake_name or "/" in bake_name:
                        texture_hints.insert(0, bake_name)
                    else:
                        texture_hints.insert(0, f"Textures\\BakedNpcTextures\\{bake_name}")
            if display_id:
                texture_hints.append(f"Textures\\BakedNpcTextures\\CreatureDisplayExtra-{int(display_id):05d}")
            if extra_id:
                texture_hints.append(f"Textures\\BakedNpcTextures\\CreatureDisplayExtra-{int(extra_id):05d}")

            texture_hints = self._dedupe_paths(texture_hints)
            loaded_from_baked_hint = False

            # Character pipeline: only try explicit baked hints, no generic internal texture scan.
            for hint in texture_hints:
                hint_norm = (hint or "").replace("/", "\\").lower()
                prefer_hd = True
                if (
                    "bakednpctextures" in hint_norm
                    and "_hd" not in resolved_model.lower()
                ):
                    # Classic character models usually map correctly to SD baked atlases.
                    # Keep HD as fallback in candidate generation, but do not prioritize it.
                    prefer_hd = False
                candidates = self._texture_path_candidates(resolved_model, hint, prefer_hd=prefer_hd)
                print(f"DEBUG: Character texture hint {hint} -> candidates: {candidates}")
                tex_data = self._load_texture_from_candidates(mpq, candidates)
                if tex_data:
                    if "bakednpctextures" in hint.lower().replace("/", "\\"):
                        loaded_from_baked_hint = True
                    break

            # Fallback for characters if baked hints are missing.
            if not tex_data:
                model_dir = self._internal_dirname(resolved_model)
                if model_dir:
                    skin_hits = [
                        p for p in mpq.search_files(model_dir)
                        if p.lower().endswith(".blp") and "skin" in p.lower()
                    ]
                    if skin_hits:
                        skin_hits.sort(key=lambda p: self._texture_score(p, model_name), reverse=True)
                        print(f"DEBUG: Character directory skin candidates: {skin_hits[:8]}")
                        tex_data = self._load_texture_from_candidates(mpq, skin_hits[:8])
            self._character_using_baked_texture = loaded_from_baked_hint
        else:
            texture_hints = self._dedupe_paths([texture_path] if texture_path else [])

            # Creature pipeline.
            for hint in texture_hints:
                candidates = self._texture_path_candidates(resolved_model, hint, prefer_hd=False)
                print(f"DEBUG: Texture hint {hint} -> candidates: {candidates}")
                tex_data = self._load_texture_from_candidates(mpq, candidates)
                if tex_data:
                    break

            # B. Try internal parsing (Type 0)
            if not tex_data:
                 internal_tex = parser.parse_textures(m2_data)
                 if internal_tex:
                     if self._texture_score(internal_tex, model_name) >= 0:
                         print(f"Loading internal texture (Type 0): {internal_tex}")
                         tex_data = mpq.read_file(internal_tex)
                     else:
                         print(f"DEBUG: Skipping low-priority internal texture: {internal_tex}")
            
            # C. Try Regex Internal Scan
            if not tex_data:
                 print("DEBUG: Primary texture failed. Scanning M2 for internal textures...")
                 internal_list = parser.get_internal_texture_list(m2_data)
                 print(f"DEBUG: Internal M2 Textures: {internal_list}")
                 if internal_list:
                     # Sort by score descending
                     internal_list.sort(key=lambda p: self._texture_score(p, model_name), reverse=True)
                     
                     print(f"DEBUG: Sorted Textures: {internal_list}")

                     for int_tex in internal_list:
                         print(f"DEBUG: Trying internal texture: {int_tex}")
                         tex_data = mpq.read_file(int_tex)
                         if tex_data:
                             print(f"SUCCESS: Loaded internal texture {int_tex}")
                             break

            # D. Last resort: scan model directory BLPs and prioritize diffuse-like names.
            if not tex_data:
                 model_dir = self._internal_dirname(resolved_model)
                 if model_dir:
                     dir_hits = [p for p in mpq.search_files(model_dir) if p.lower().endswith(".blp")]
                     if dir_hits:
                         dir_hits.sort(key=lambda p: self._texture_score(p, model_name), reverse=True)
                         print(f"DEBUG: Directory texture candidates: {dir_hits[:8]}")
                         tex_data = self._load_texture_from_candidates(mpq, dir_hits[:8])

        print(f"DEBUG: BLP Data Found: {len(tex_data) if tex_data else 'None'}")
             
        if tex_data:
            converter = BlpConverter()
            # Returns (width, height, data, format)
            tex_info = converter.process_blp(tex_data)
            if tex_info:
                width, height, image_data, tex_fmt = tex_info
                print(f"DEBUG: Texture Format: {tex_fmt} | Size: {width}x{height} | Data Len: {len(image_data)}")
                
                tex = Texture()
                
                # 1. Set Size
                tex.setXSize(width)
                tex.setYSize(height)
                
                # 2. Set Format FIRST (Defaults to CM_off, so must be before Compression)
                tex.setFormat(Texture.F_rgba)
                
                # 3. Set Compression SECOND (Overrides format default for internal storage)
                if tex_fmt == "DXT1":
                    tex.setCompression(Texture.CM_dxt1)
                elif tex_fmt == "DXT3":
                    tex.setCompression(Texture.CM_dxt3)
                elif tex_fmt == "DXT5":
                    tex.setCompression(Texture.CM_dxt5)
                else:
                    tex.setCompression(Texture.CM_off)
                    
                # Debug Verification
                print(f"DEBUG: Texture Compression Mode: {tex.getCompression()}")

                # 4. Feed Data
                # CRITICAL: Must pass compression mode here, otherwise it defaults to CM_off and fails assertion
                tex.setRamImage(image_data, tex.getCompression())
                
                # Apply to Node (will apply after mesh generation)
                self.pending_texture = tex
            else:
                print("Failed to convert BLP.")
                self.pending_texture = None
        else:
            print("No Texture found (Hardcoded or DBC).")
            self.pending_texture = None

        # 3. Read Skin File
        # Try finding the corresponding skin file
        # Rules: replace .m2/M2 with 00.skin
        # M2 paths are often mixed case.
        # Try constructing skin path and using search?
        
        # Simple string replacement first
        base_path_lower = resolved_model.lower()
        if base_path_lower.endswith('.m2'):
            skin_path_candidate = resolved_model[:-3] + "00.skin"
        else:
            skin_path_candidate = resolved_model + "00.skin"
            
        # We need to find the ACTUAL filename in the MPQ because standard case might not match?
        # MpqManager.read_file handles case sensitivity attempts now!
        
        resolved_skin = mpq.resolve_file_path(skin_path_candidate) or skin_path_candidate
        print(f"Loading Skin: {resolved_skin}")
        skin_data = mpq.read_file(resolved_skin)
        
        if not skin_data:
             print("Skin file not found. Falling back to Point Cloud.")
             self.render_point_cloud(vertices)
             return
             
        skin_parser = SkinParser()
        indices_lookup, triangles, submeshes = skin_parser.parse_skin(skin_data)
        
        if not indices_lookup or not triangles:
             print("Failed to parse Skin. Falling back to Point Cloud.")
             self.render_point_cloud(vertices)
             return

        self._cached_vertices = vertices
        self._cached_indices_lookup = indices_lookup
        self._cached_triangles = triangles

        if is_character_model and submeshes:
            self._prepare_character_texture_units(parser, skin_parser, m2_data, skin_data)
            self._build_character_layers(submeshes, triangles, display_extra)
            self._prepare_character_layer_textures(mpq, display_extra)
            triangles = self._triangles_from_active_layers()
        else:
            self._reset_layer_state(emit=True)

        if is_character_model:
            self._prepare_character_item_attachments(mpq, display_extra, attachment_points)

        self.render_mesh(vertices, indices_lookup, triangles)

    def render_point_cloud(self, vertices):
        self.clear_scene()
            
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
        
        target = self.scene_root if self.scene_root else self.ShowBase.render
        self.model_node = target.attachNewNode(node)
        self.model_node.setColor(1, 1, 0, 1) # Yellow Points
        self.model_node.setRenderModeThickness(3)
        
        self.zoom_to_fit()

    def render_mesh(self, vertices, indices_lookup, triangles):
        self.clear_scene()

        if self._layer_defs:
            target = self.scene_root if self.scene_root else self.ShowBase.render
            self.model_node = target.attachNewNode("m2_mesh_root")
            tri_len = len(self._cached_triangles or [])
            default_tex = getattr(self, "pending_texture", None)

            rendered_any = False
            for layer in self._layer_defs:
                if layer["key"] not in self._active_layer_keys:
                    continue
                start = int(layer.get("triangle_start", 0))
                count = int(layer.get("triangle_count", 0))
                if count <= 0:
                    continue
                a = max(0, min(start, tri_len))
                b = max(a, min(start + count, tri_len))
                layer_tris = (self._cached_triangles or [])[a:b]
                if not layer_tris:
                    continue

                layer_tex = self._layer_texture_overrides.get(layer["key"], default_tex)
                node = self._create_mesh_node(
                    vertices,
                    indices_lookup,
                    layer_tris,
                    texture=layer_tex,
                    name=f"m2_layer_{layer['key']}",
                    parent=self.model_node,
                )
                if (
                    layer["key"] in self._hair_layer_keys
                    or (
                        self._facial_uses_hair_uv
                        and layer["key"] in self._facial_layer_keys
                    )
                ):
                    stage = TextureStage.getDefault()
                    if layer["key"] in self._hair_layer_keys:
                        node.setTexScale(stage, self._active_hair_uv_scale_u, self._active_hair_uv_scale_v)
                        node.setTexOffset(stage, self._active_hair_uv_offset_u, self._active_hair_uv_offset_v)
                    else:
                        node.setTexScale(stage, self._facial_uv_scale_u, self._facial_uv_scale_v)
                        node.setTexOffset(stage, self._facial_uv_offset_u, self._facial_uv_offset_v)
                self._apply_layer_render_state(node, layer["key"])
                rendered_any = True

            if not rendered_any:
                self.model_node = self._create_mesh_node(
                    vertices,
                    indices_lookup,
                    triangles,
                    texture=default_tex,
                    name="m2_mesh",
                )
        else:
            self.model_node = self._create_mesh_node(
                vertices,
                indices_lookup,
                triangles,
                texture=getattr(self, "pending_texture", None),
                name="m2_mesh",
            )
        self._render_cached_attachments()

        # Center Pivot on Model
        self.zoom_to_fit()

    def zoom_to_fit(self):
        if not self.model_node or self.model_node.isEmpty():
            return

        bounds_node = self.scene_root if self.scene_root is not None else self.model_node
        min_pt, max_pt = bounds_node.getTightBounds()
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

    def disable_viewer(self):
        # Replace the viewer content with a simple label when GLX is unavailable.
        self.is_initialized = False
        try:
            if self.ShowBase and self.ShowBase.win:
                self.ShowBase.closeWindow(self.ShowBase.win)
        except Exception:
            pass
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        self.layout.addWidget(QLabel("3D preview disabled (no GLX context)."), 1)

    def clear_scene(self):
        # Remove previously rendered models from this widget scene root.
        if self.model_node is not None:
            try:
                if not self.model_node.isEmpty():
                    self.model_node.removeNode()
            except Exception:
                pass
            self.model_node = None

        if self.scene_root is not None:
            try:
                for child in self.scene_root.getChildren():
                    child.removeNode()
            except Exception:
                pass
