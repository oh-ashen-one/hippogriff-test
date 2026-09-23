"""FK posing core. pose = {bone: Quaternion local rotation about joint}.
Fast apply via matrix_basis (no pb.matrix setter -> no per-bone depsgraph eval).
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion

REST = {}    # bone -> dict(head, matrix_local, basis_rel)
PARENT = {
    "spine1": "spine0",
    "neck0": "spine1", "neck1": "neck0", "head": "neck1",
    "tail0": "spine0", "tail1": "tail0", "tail2": "tail1",
}
for S in ("R", "L"):
    PARENT[f"arm_{S}0"] = "spine1"
    PARENT[f"arm_{S}1"] = f"arm_{S}0"
    for f in (1, 2, 3):
        PARENT[f"fing{f}_{S}"] = f"arm_{S}1"
    PARENT[f"fore_{S}0"] = "spine1"
    PARENT[f"fore_{S}1"] = f"fore_{S}0"
    PARENT[f"foretoe_{S}"] = f"fore_{S}1"
    PARENT[f"hind_{S}0"] = "spine0"
    PARENT[f"hind_{S}1"] = f"hind_{S}0"
    PARENT[f"hindtoe_{S}"] = f"hind_{S}1"

ORDER = []

def capture_rest(arm):
    REST.clear(); ORDER.clear()
    for b in arm.data.bones:
        REST[b.name] = {"head": b.head_local.copy(), "ml": b.matrix_local.copy()}
    done = set()
    names = list(REST.keys())
    while len(done) < len(names):
        for nm in names:
            if nm in done:
                continue
            p = PARENT.get(nm)
            if p is None or p in done:
                ORDER.append(nm); done.add(nm)

def solve(pose, root_rot=Quaternion((1, 0, 0, 0)), root_off=Vector((0, 0, 0))):
    """-> {bone: armature-space pose matrix}"""
    R = {}; T = {}; out = {}
    for nm in ORDER:
        h = REST[nm]["head"]; ml = REST[nm]["ml"]
        ori = ml.to_3x3().normalized()
        p = PARENT.get(nm)
        L = pose.get(nm, Quaternion((1, 0, 0, 0)))
        if p is None:
            R[nm] = root_rot @ L
            T[nm] = root_rot @ h + root_off
        else:
            R[nm] = R[p] @ L
            T[nm] = R[p] @ (h - REST[p]["head"]) + T[p]
        out[nm] = Matrix.Translation(T[nm]) @ R[nm].to_matrix().to_4x4() @ ori.to_4x4()
    return out

def apply_pose(arm, mats, frame=None):
    for nm, M in mats.items():
        b = arm.data.bones[nm]
        p = PARENT.get(nm)
        if p is None:
            basis = b.matrix_local.inverted() @ M
        else:
            rel = arm.data.bones[p].matrix_local.inverted() @ b.matrix_local
            basis = (mats[p] @ rel).inverted() @ M
        pb = arm.pose.bones[nm]
        pb.location = basis.to_translation()
        pb.rotation_quaternion = basis.to_quaternion()
        if frame is not None:
            pb.keyframe_insert("location", frame=frame, group=nm)
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=nm)

def q(axis, deg):
    return Quaternion(axis, math.radians(deg))
