"""Recompute skin weights: wing membrane must follow wing bones, not head/neck."""
import bpy, numpy as np

obj = bpy.data.objects["tripo_2290e693_9a3e_4995_8858_c56a6a39ae89"]
arm = bpy.data.objects["Rig"]

# bone segments in armature space (= world, armature at origin... use bone head/tail local)
SEG = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in arm.data.bones}

me = obj.data
n = len(me.vertices)
co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)

def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)

x, y, z = co[:, 0], co[:, 1], co[:, 2]
ax = np.abs(x)
wing_region = (ax > 0.90) | ((z > 1.85) & (ax > 0.60))   # scaled units (~m)

def eligible(name):
    side = 1 if name.endswith("_R") else -1
    is_wing = name.startswith(("arm_", "fing"))
    base = np.ones(n, dtype=bool)
    if is_wing:
        e = x * side > 0.10
    elif name.startswith(("head", "neck")):
        e = (y < -0.30) & (ax < 0.40) & (z < 2.2)
    elif name.startswith("tail"):
        e = (y > 0.20) & (ax < 0.35)
    elif name.startswith(("fore", "hind")):
        ly = -0.78 if name.startswith("fore") else 0.31
        e = (z < 1.62) & (np.abs(y - ly) < 0.73) & (ax < 0.58)
    else:
        e = base.copy()
    # wing region: only same-side wing bones + spine1 allowed
    if is_wing:
        pass
    elif name != "spine1":
        e = e & ~wing_region
    return e

names = list(SEG.keys())
dists = np.full((n, len(names)), 1e9)
for i, nm in enumerate(names):
    d = seg_dist(co, SEG[nm][0], SEG[nm][1])
    d[~eligible(nm)] = 1e9
    dists[:, i] = d

# verts where nothing eligible (far wing region edge cases): fall back to spine1
none_el = dists.min(axis=1) > 1e8
dists[none_el, names.index("spine1")] = 0.01

order = np.argsort(dists, axis=1)
d0 = dists[np.arange(n), order[:, 0]]
d1 = dists[np.arange(n), order[:, 1]]
w0 = 1.0 / np.maximum(d0, 0.02) ** 3
w1 = 1.0 / np.maximum(d1, 0.02) ** 3
w1[d1 > 2.5 * d0] *= 0.15
tot = w0 + w1
bone_w = np.zeros((n, len(names)))
bone_w[np.arange(n), order[:, 0]] = w0 / tot
bone_w[np.arange(n), order[:, 1]] += w1 / tot

for g in list(obj.vertex_groups):
    obj.vertex_groups.remove(g)
qw = np.round(bone_w, 3)
for i, nm in enumerate(names):
    vg = obj.vertex_groups.new(name=nm)
    col = qw[:, i]
    for val in np.unique(col):
        if val <= 0.001:
            continue
        sel = np.where(col == val)[0]
        vg.add(sel.tolist(), float(val), 'REPLACE')

bpy.ops.wm.save_as_mainfile(filepath="/Users/midir/hippogriff-test/blender/hippogriff_flight.blend")
print("WEIGHTS REDONE")
