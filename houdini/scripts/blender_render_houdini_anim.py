import bpy
import math
import os
import numpy as np
from mathutils import Vector

NPZ = '/tmp/hippo_anim/geometry.npz'
OUT = '/tmp/hippo_hframes'
TEX = '/tmp/hippogriff_basecolor_4096.png'
RES = (1920, 1080)

os.makedirs(OUT, exist_ok=True)
d = np.load(NPZ)
counts = d['counts']
indices = d['indices']
uv_loops = d['uv_loops']
positions = d['positions']
f0, f1 = int(d['f0']), int(d['f1'])
fps = int(d['fps'])
print("NPZ frames %d..%d  points=%d  prims=%d" % (f0, f1, positions.shape[1], len(counts)))

# Houdini is Y-up, Blender is Z-up: (x, y, z) -> (x, -z, y)
def to_blender(a):
    out = np.empty_like(a)
    out[..., 0] = a[..., 0]
    out[..., 1] = -a[..., 2]
    out[..., 2] = a[..., 1]
    return out

P = to_blender(positions)

faces = []
i = 0
for c in counts:
    faces.append(tuple(int(v) for v in indices[i:i + c]))
    i += c
print("built %d faces" % len(faces))

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene

me = bpy.data.meshes.new('HippogriffSim')
verts = [tuple(v) for v in P[0]]
me.from_pydata(verts, [], faces)
me.update()

uvl = me.uv_layers.new(name='UVMap')
flat_uv = np.asarray(uv_loops, dtype=np.float32).ravel()
uvl.data.foreach_set('uv', flat_uv)

ob = bpy.data.objects.new('HippogriffSim', me)
sc.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.shade_smooth()

# material: the recoloured hippogriff base colour from the earlier pass
mat = bpy.data.materials.new('HippogriffColour')
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Roughness'].default_value = 0.72
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Specular IOR Level'].default_value = 0.3
tex = nt.nodes.new('ShaderNodeTexImage')
tex.image = bpy.data.images.load(TEX)
tex.interpolation = 'Smart'
nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(bsdf.outputs['BSDF'], outn.inputs['Surface'])
me.materials.append(mat)

# lighting + sky
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.30, 0.38, 0.50, 1.0)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
sd = bpy.data.lights.new('Key', type='SUN')
sd.energy = 4.2
sd.angle = math.radians(3.0)
so = bpy.data.objects.new('Key', sd)
sc.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0.0, math.radians(38))
fd = bpy.data.lights.new('Fill', type='SUN')
fd.energy = 1.4
fo = bpy.data.objects.new('Fill', fd)
sc.collection.objects.link(fo)
fo.rotation_euler = (math.radians(72), 0.0, math.radians(-125))

# frame the whole animated range, not just frame 0
mn = P.reshape(-1, 3).min(axis=0)
mx = P.reshape(-1, 3).max(axis=0)
centre = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2))
size = float(max(mx - mn))
print("blender-space bbox %s .. %s (size %.3f)" % (
    [round(float(v), 2) for v in mn], [round(float(v), 2) for v in mx], size))

cd = bpy.data.cameras.new('Cam')
cd.lens = 62.0
cam = bpy.data.objects.new('Cam', cd)
sc.collection.objects.link(cam)
sc.camera = cam
dirv = Vector((1.0, -0.85, 0.35)).normalized()
cam.location = centre + dirv * size * 2.05
cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.render.use_motion_blur = False
sc.render.fps = fps

for i in range(P.shape[0]):
    v = [tuple(p) for p in P[i]]
    me.vertices.foreach_set('co', np.asarray(v, dtype=np.float32).ravel())
    me.update()
    sc.frame_set(i + 1)
    sc.render.filepath = os.path.join(OUT, 'f_%04d.png' % (i + 1))
    bpy.ops.render.render(write_still=True)
    if (i + 1) % 20 == 0:
        print("   rendered %d/%d" % (i + 1, P.shape[0]))

print("RENDERED_ALL")
