import hou
import numpy as np
import os
import json

ORIG = '/Users/midir/hippogriff-test/houdini/hippogriff_flight.hip'
OUTDIR = '/tmp/hippo_anim'
hou.hipFile.load(ORIG, suppress_save_prompt=True, ignore_load_warnings=True)
os.makedirs(OUTDIR, exist_ok=True)
hou.playbar.setFrameRange(1, 120)
F0, F1 = 1, 120

dn = hou.node('/obj/hippogriff').displayNode()
print("display node:", dn.path())

hou.setFrame(F0)
g = dn.geometry()
npts = len(g.points())
nprims = len(g.prims())
nverts = g.vertexCount()
print("frame1: points=%d prims=%d vertices=%d" % (npts, nprims, nverts))
print("point attribs:", [(a.name(), a.size()) for a in g.pointAttribs()])
print("vertex attribs:", [(a.name(), a.size()) for a in g.vertexAttribs()])

counts, flat = [], []
for p in g.prims():
    vp = [v.point().number() for v in p.vertices()]
    counts.append(len(vp))
    flat.extend(vp)
counts = np.array(counts, dtype=np.int32)
flat = np.array(flat, dtype=np.int32)
print("topology: %d prims, %d indices (all tris: %s)"
      % (len(counts), len(flat), bool((counts == 3).all())))


def find_uv(g, npts, nverts):
    for scope, getter, count in (('vertex', g.vertexFloatAttribValues, nverts),
                                 ('point', g.pointFloatAttribValues, npts)):
        for cand in ('uv', 'UVMap', 'st'):
            try:
                v = getter(cand)
            except Exception:
                continue
            if count == 0 or len(v) % count != 0:
                continue
            size = len(v) // count
            if size < 2:
                continue
            a = np.array(v, dtype=np.float32).reshape(count, size)[:, :2]
            return scope, '%s(size=%d)' % (cand, size), a
    return None, None, None


kind, uvname, uvraw = find_uv(g, npts, nverts)
print("uv: kind=%s name=%s shape=%s" % (kind, uvname, None if uvraw is None else uvraw.shape))
if uvraw is None:
    raise SystemExit("no usable uv attribute found")

if kind == 'vertex':
    uv_loops = uvraw                       # already per loop
else:
    uv_loops = uvraw[flat]                 # expand per-point uvs to loops

pos = np.empty((F1 - F0 + 1, npts, 3), dtype=np.float32)
for i, f in enumerate(range(F0, F1 + 1)):
    hou.setFrame(f)
    a = np.array(dn.geometry().pointFloatAttribValues('P'), dtype=np.float32).reshape(-1, 3)
    if a.shape[0] != npts:
        raise SystemExit("point count changed at frame %d: %d" % (f, a.shape[0]))
    pos[i] = a

np.savez_compressed(os.path.join(OUTDIR, 'geometry.npz'),
                    counts=counts, indices=flat, uv_loops=uv_loops,
                    positions=pos, f0=F0, f1=F1, fps=24)
with open(os.path.join(OUTDIR, 'meta.json'), 'w') as fh:
    json.dump({'f0': F0, 'f1': F1, 'fps': 24, 'points': int(npts),
               'prims': int(nprims), 'uv_kind': kind, 'uv_name': uvname}, fh, indent=2)

p = os.path.join(OUTDIR, 'geometry.npz')
print("WROTE", p, os.path.getsize(p), "bytes")
print("motion: max |f1 - f60| = %.4f   max |f1 - f120| = %.4f"
      % (float(np.abs(pos[0] - pos[59]).max()), float(np.abs(pos[0] - pos[119]).max())))
print("END_EXPORT_ANIM")
