"""Build armature + procedural weights for the hippogriff.
Local coords: front = -Y, up = +Z, right = +X. Mesh transform applied first.
"""
import bpy, numpy as np
from mathutils import Vector, Matrix

MESH = "tripo_2290e693_9a3e_4995_8858_c56a6a39ae89"

# ---------- 1. flatten transforms ----------
obj = bpy.data.objects[MESH]
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
obj.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# delete leftover empty
for o in list(bpy.data.objects):
    if o.name == "RootNode" or o.name == "DiagCam":
        bpy.data.objects.remove(o, do_unlink=True)

# ---------- 2. bone layout (world = local mesh coords) ----------
def mirror(side, p):
    return (side * p[0], p[1], p[2])

# name: (head, tail)  — chains per side
BONES = {}
def chain(prefix, pts):
    for i in range(len(pts) - 1):
        BONES[f"{prefix}{i}"] = (pts[i], pts[i + 1])

chain("spine", [(0, 0.16, 0.58), (0, 0.02, 0.62), (0, -0.15, 0.65)])
chain("neck", [(0, -0.15, 0.65), (0, -0.26, 0.70), (0, -0.36, 0.74)])
BONES["head"] = ((0, -0.36, 0.74), (0, -0.48, 0.72))
chain("tail", [(0, 0.14, 0.55), (0, 0.26, 0.42), (0, 0.38, 0.28), (0, 0.47, 0.14)])

for s in (1, -1):
    S = "R" if s == 1 else "L"
    chain(f"arm_{S}", [mirror(s, (0.09, -0.08, 0.62)), mirror(s, (0.20, -0.18, 0.75)), mirror(s, (0.30, -0.27, 0.95))])
    # fingers fan from wrist
    w = mirror(s, (0.30, -0.27, 0.95))
    BONES[f"fing1_{S}"] = (w, mirror(s, (0.465, -0.07, 0.89)))
    BONES[f"fing2_{S}"] = (w, mirror(s, (0.40, 0.02, 0.70)))
    BONES[f"fing3_{S}"] = (w, mirror(s, (0.33, 0.07, 0.50)))
    # foreleg
    chain(f"fore_{S}", [mirror(s, (0.10, -0.26, 0.52)), mirror(s, (0.11, -0.28, 0.28)), mirror(s, (0.11, -0.33, 0.10))])
    BONES[f"foretoe_{S}"] = (mirror(s, (0.11, -0.33, 0.10)), mirror(s, (0.11, -0.44, 0.02)))
    # hind leg
    chain(f"hind_{S}", [mirror(s, (0.09, 0.10, 0.55)), mirror(s, (0.10, 0.16, 0.30)), mirror(s, (0.10, 0.10, 0.12))])
    BONES[f"hindtoe_{S}"] = (mirror(s, (0.10, 0.10, 0.12)), mirror(s, (0.10, 0.17, 0.03)))

# ---------- 3. build armature ----------
arm_data = bpy.data.armatures.new("Rig")
arm = bpy.data.objects.new("Rig", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t) in BONES.items():
    b = arm_data.edit_bones.new(name)
    b.head = h
    b.tail = t
bpy.ops.object.mode_set(mode='OBJECT')

# ---------- 4. procedural weights ----------
me = obj.data
n = len(me.vertices)
co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)

def seg_dist(P, a, b):
    ab = b - a
    t = ((P - a) @ ab) / (ab @ ab)
    t = np.clip(t, 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)

def eligible(name, co):
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    side = 1 if name.endswith("_R") else -1
    if name.startswith(("arm_", "fing")):
        return (x * side > 0.045)
    if name.startswith("head") or name.startswith("neck"):
        return (y < -0.13) & (ax < 0.16)
    if name.startswith("tail"):
        return (y > 0.08) & (ax < 0.14)
    if name.startswith(("fore", "hind")):
        ly = -0.30 if name.startswith("fore") else 0.12
        return (z < 0.62) & (np.abs(y - ly) < 0.28) & (ax < 0.22)
    return np.ones(len(co), dtype=bool)  # spine chain always eligible

names = list(BONES.keys())
dists = np.full((n, len(names)), 1e9)
for i, nm in enumerate(names):
    a = np.array(BONES[nm][0]); b = np.array(BONES[nm][1])
    d = seg_dist(co, a, b)
    d[~eligible(nm, co)] = 1e9
    dists[:, i] = d

# two nearest bones, inverse-power blend
order = np.argsort(dists, axis=1)
d0 = dists[np.arange(n), order[:, 0]]
d1 = dists[np.arange(n), order[:, 1]]
EPS = 1e-4
w0 = 1.0 / np.maximum(d0, 0.015) ** 3
w1 = 1.0 / np.maximum(d1, 0.015) ** 3
# suppress second bone when clearly dominated
w1[d1 > 2.5 * d0] *= 0.15
tot = w0 + w1

vg = {nm: obj.vertex_groups.new(name=nm) for nm in names}
idx0 = order[:, 0]; idx1 = order[:, 1]
final_w = np.zeros(n)
final_w[np.arange(n)] = 0.0
w0n = w0 / tot; w1n = w1 / tot
# per-vertex weight for bone i = w0n if it's nearest, w1n if second
bone_w = np.zeros((n, len(names)))
bone_w[np.arange(n), idx0] = w0n
bone_w[np.arange(n), idx1] += w1n
# batch by rounded weight to keep add() calls low
qw = np.round(bone_w, 3)
for i, nm in enumerate(names):
    col = qw[:, i]
    for val in np.unique(col):
        if val <= 0.001:
            continue
        sel = np.where(col == val)[0]
        vg[nm].add(sel.tolist(), float(val), 'REPLACE')

# ---------- 5. bind ----------
mod = obj.modifiers.new("Armature", 'ARMATURE')
mod.object = arm
obj.parent = arm

bpy.ops.wm.save_as_mainfile(filepath="/Users/midir/hippogriff-test/blender/hippogriff_flight.blend")
print("RIG DONE: bones=", len(names))
