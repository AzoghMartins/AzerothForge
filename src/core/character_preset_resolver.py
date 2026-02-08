class CharacterPresetResolver:
    """
    Deterministic resolver for character-model geoset presets.
    """

    # Slot -> geoset-group rules driven by NPCItemDisplay -> ItemDisplayInfo.
    SLOT_GROUP_RULES = {
        2: [{"group": 15, "mode": "plus1"}],  # shoulders
        3: [{"group": 15, "mode": "plus1"}],  # chest can drive shoulder/collar variant
        6: [{"group": 13, "mode": "plus1"}],  # pants / lower body
        7: [{"group": 5, "mode": "plus1"}],   # boots / lower legs
        8: [{"group": 4, "mode": "plus1"}],   # bracers / lower arms
        9: [{"group": 4, "mode": "plus1"}],   # gloves / lower arms
        10: [{"group": 12, "mode": "plus1"}], # tabard hem
    }

    GROUP_LABELS = {
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

    APPEARANCE_GROUPS = {
        1: "geoset100",
        2: "geoset200",
        3: "geoset300",
        7: "geoset700",
    }

    def _target_id(self, group, value, mode):
        if mode == "plus1":
            return (group * 100) + int(value) + 1
        if mode == "at_least_one":
            v = int(value)
            if v <= 0:
                v = 1
            return (group * 100) + v
        if mode == "raw":
            return (group * 100) + int(value)
        return None

    def _pick_from_candidates(self, candidate_ids, target_id):
        if not candidate_ids:
            return None, "missing_group"
        if target_id in candidate_ids:
            return target_id, "exact"
        # Choose nearest ID to avoid surprising jumps.
        if target_id is not None:
            nearest = min(candidate_ids, key=lambda cid: abs(cid - target_id))
            return nearest, "nearest"
        return min(candidate_ids), "fallback_base"

    def _resolve_facial_geosets(self, extra):
        out = {}
        facial = extra.get("resolved_facial_geosets")
        if isinstance(facial, dict):
            for group, key in self.APPEARANCE_GROUPS.items():
                if key in facial:
                    value = int(facial.get(key, 0) or 0)
                    # Group3 (300-range) is optional for many NPCs; a zero value
                    # means "no extra Group3 geoset", not "pick 301".
                    if group == 3 and value <= 0:
                        continue
                    out[group] = {
                        "value": value,
                        "source": f"facial:{key}",
                    }
        return out

    def _resolve_hair_geoset(self, extra):
        if "resolved_hair_geoset" in extra:
            return {
                "value": int(extra.get("resolved_hair_geoset", 0) or 0),
                "source": f"hair_geoset:{extra.get('resolved_hair_source', 'resolved')}",
            }

        # Fallback when CharHairGeosets is unavailable.
        return {
            "value": int(extra.get("hair_style", 0) or 0) + 1,
            "source": "hair_style:fallback_plus1",
        }

    def _resolve_default_appearance(self, extra):
        resolved = self._resolve_facial_geosets(extra)

        # If facial lookup is unavailable, keep deterministic defaults.
        if 1 not in resolved:
            resolved[1] = {"value": 1, "source": "default_base"}
        if 2 not in resolved:
            resolved[2] = {"value": 1, "source": "default_base"}
        if 7 not in resolved:
            resolved[7] = {
                "value": int(extra.get("facial_hair", 0) or 0) + 1,
                "source": "facial_hair:fallback_plus1",
            }
        return resolved

    def resolve(self, submeshes, extra):
        """
        Returns:
          {
            selected_indexes: set[int],
            selected_ids: set[int],
            decisions: {group: {...}},
            selected_reason_by_index: {idx: str}
          }
        """
        extra = extra if isinstance(extra, dict) else {}

        by_id = {}
        by_group = {}
        for idx, sub in enumerate(submeshes):
            sub_id = int(sub.get("id", 0))
            by_id.setdefault(sub_id, []).append(idx)
            if sub_id >= 100:
                by_group.setdefault(sub_id // 100, set()).add(sub_id)

        selected_indexes = set()
        selected_ids = set()
        selected_reason_by_index = {}
        decisions = {}

        def _select_submesh_id(sub_id, reason):
            idxs = list(by_id.get(int(sub_id), []))
            if not idxs:
                return []
            selected_ids.add(int(sub_id))
            for idx in idxs:
                selected_indexes.add(idx)
                selected_reason_by_index[idx] = reason
            return idxs

        def _deselect_submesh_id(sub_id):
            sub_id = int(sub_id)
            for idx in by_id.get(sub_id, []):
                selected_indexes.discard(idx)
                selected_reason_by_index.pop(idx, None)
            selected_ids.discard(sub_id)

        # Canonical body defaults: always keep base 0, and choose a hairstyle base
        # directly from CharHairGeosets when available (fallback to 1).
        secondary_base = int(extra.get("resolved_hair_geoset", 0) or 0)
        if secondary_base <= 0:
            secondary_base = 1

        base_defaults = [0]
        if secondary_base not in base_defaults:
            base_defaults.append(secondary_base)

        selected_secondary = False
        for base_id in base_defaults:
            idxs = by_id.get(base_id, [])
            if not idxs:
                continue
            _select_submesh_id(base_id, f"default_base_id={base_id}")
            if base_id != 0:
                selected_secondary = True

        if not selected_secondary and secondary_base != 1 and 1 in by_id:
            _select_submesh_id(1, "default_base_id=1_fallback")

        # Character appearance groups resolved from facial/hair DBC rows.
        appearance = self._resolve_default_appearance(extra)
        for group, row in sorted(appearance.items()):
            value = int(row.get("value", 0) or 0)
            source = row.get("source", "appearance")
            target_id = self._target_id(group, value, "at_least_one")
            candidates = sorted(by_group.get(group, set()))
            picked_id, status = self._pick_from_candidates(candidates, target_id)
            if picked_id is None:
                continue
            reason = f"{source}={value}"
            picked_idxs = _select_submesh_id(picked_id, reason)
            pick_idx = picked_idxs[0]
            decisions[group] = {
                "group": group,
                "source": reason,
                "label": self.GROUP_LABELS.get(group, f"Group{group}"),
                "target_id": target_id,
                "picked_id": picked_id,
                "picked_idx": pick_idx,
                "picked_idxs": picked_idxs,
                "status": status,
                "candidates": candidates,
            }

        # Equipment-driven groups from NPCItemDisplay -> ItemDisplayInfo.
        for row in (extra.get("npc_item_details") or []):
            slot = int(row.get("slot", 0) or 0)
            disp_id = int(row.get("display_id", 0) or 0)
            if disp_id == 0:
                continue

            rules = self.SLOT_GROUP_RULES.get(slot, [])
            for rule in rules:
                group = int(rule.get("group", 0))
                mode = rule.get("mode", "plus1")
                geo_value = int(row.get("geoset_group_1", 0) or 0)
                target_id = self._target_id(group, geo_value, mode)
                if target_id is None:
                    continue

                candidates = sorted(by_group.get(group, set()))
                picked_id, status = self._pick_from_candidates(candidates, target_id)
                if picked_id is None:
                    continue

                # Equipment should override character baseline for its driven groups.
                prev = decisions.get(group)
                if prev:
                    prev_id = int(prev.get("picked_id", -1))
                    if prev_id >= 0:
                        _deselect_submesh_id(prev_id)

                reason = f"slot{slot}_display{disp_id}_geo{geo_value}"
                picked_idxs = _select_submesh_id(picked_id, reason)
                pick_idx = picked_idxs[0]
                decisions[group] = {
                    "group": group,
                    "source": reason,
                    "label": self.GROUP_LABELS.get(group, f"Group{group}"),
                    "target_id": target_id,
                    "picked_id": picked_id,
                    "picked_idx": pick_idx,
                    "picked_idxs": picked_idxs,
                    "status": status,
                    "candidates": candidates,
                }

        # Group3 style variant is often not populated by facial-hair DBC rows.
        # Keep a deterministic baseline style (first candidate), then allow
        # later systems to override if a stronger source exists.
        if 3 not in decisions:
            candidates = sorted(by_group.get(3, set()))
            if candidates:
                picked_id = candidates[0]
                reason = "default_group3"
                picked_idxs = _select_submesh_id(picked_id, reason)
                pick_idx = picked_idxs[0]
                decisions[3] = {
                    "group": 3,
                    "source": reason,
                    "label": self.GROUP_LABELS.get(3, "Group3"),
                    "target_id": picked_id,
                    "picked_id": picked_id,
                    "picked_idx": pick_idx,
                    "picked_idxs": picked_idxs,
                    "status": "fallback_base",
                    "candidates": candidates,
                }

        # Group4 lower-arms mesh is part of the baseline character body shape.
        # When no equipment rule drives it, default to the first available variant.
        if 4 not in decisions:
            candidates = sorted(by_group.get(4, set()))
            if candidates:
                picked_id = candidates[0]
                reason = "default_group4"
                picked_idxs = _select_submesh_id(picked_id, reason)
                pick_idx = picked_idxs[0]
                decisions[4] = {
                    "group": 4,
                    "source": reason,
                    "label": self.GROUP_LABELS.get(4, "Group4"),
                    "target_id": picked_id,
                    "picked_id": picked_id,
                    "picked_idx": pick_idx,
                    "picked_idxs": picked_idxs,
                    "status": "fallback_base",
                    "candidates": candidates,
                }

        # Group5 (lower legs) baseline defaults to 501 when not driven by gear.
        if 5 not in decisions:
            candidates = sorted(by_group.get(5, set()))
            if candidates:
                target_id = 501
                picked_id, status = self._pick_from_candidates(candidates, target_id)
                if picked_id is not None:
                    reason = "default_group5"
                    picked_idxs = _select_submesh_id(picked_id, reason)
                    pick_idx = picked_idxs[0]
                    decisions[5] = {
                        "group": 5,
                        "source": reason,
                        "label": self.GROUP_LABELS.get(5, "Group5"),
                        "target_id": target_id,
                        "picked_id": picked_id,
                        "picked_idx": pick_idx,
                        "picked_idxs": picked_idxs,
                        "status": status,
                        "candidates": candidates,
                    }

        # Group15 (shoulders/cloak family) baseline defaults to 1501.
        if 15 not in decisions:
            candidates = sorted(by_group.get(15, set()))
            if candidates:
                target_id = 1501
                picked_id, status = self._pick_from_candidates(candidates, target_id)
                if picked_id is not None:
                    reason = "default_group15"
                    picked_idxs = _select_submesh_id(picked_id, reason)
                    pick_idx = picked_idxs[0]
                    decisions[15] = {
                        "group": 15,
                        "source": reason,
                        "label": self.GROUP_LABELS.get(15, "Group15"),
                        "target_id": target_id,
                        "picked_id": picked_id,
                        "picked_idx": pick_idx,
                        "picked_idxs": picked_idxs,
                        "status": status,
                        "candidates": candidates,
                    }

        return {
            "selected_indexes": selected_indexes,
            "selected_ids": selected_ids,
            "decisions": decisions,
            "selected_reason_by_index": selected_reason_by_index,
        }
