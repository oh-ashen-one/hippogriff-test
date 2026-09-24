import bpy
import math
import numpy as np
from mathutils import Vector

CREATURE = 'tripo_2290e693_9a3e_4995_8858_c56a6a39ae89'
DETAIL_IMG = 'black+winged+dragon+3d+model_basecolor.jpg'
BAKE_IMG = 'Hippogriff_BaseColor'
BAKE_RES = 4096
ATTR = 'HippoRegion'


def s2l(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---- palette (sRGB, then converted to linear for scene-referred use) ----
P = {
    'beak':     (0.851, 0.635, 0.169),
    'head':     (0.290, 0.227, 0.165),
    'breast':   (0.478, 0.361, 0.235),
    'wing':     (0.420, 0.290, 0.184),
    'wingdark': (0.243, 0.173, 0.118),
    'barrel':   (0.541, 0.294, 0.133),
    'hindq':    (0.470, 0.250, 0.115),
    'lowerleg': (0.227, 0.141, 0.094),
    'hoof':     (0.165, 0.129, 0.110),
    'talon':    (0.788, 0.635, 0.290),
    'tail':     (0.200, 0.141, 0.102),
}
LIN = {k: s2l(v) for k, v in P.items()}

sc = bpy.context.scene
sc.render.use_motion_blur = False
ob = bpy.data.objects[CREATURE]
me = ob.data

n = len(me.vertices)
co = np.empty(n * 3, dtype=np.float32)
me.vertices.foreach_get('co', co)
co = co.reshape(-1, 3).astype(np.float64)
X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
AX = np.abs(X)


def sstep(a, b, t):
    x = np.clip((t - a) / (b - a), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def mix(base, target, m):
    m = m[:, None]
    return base * (1.0 - m) + target[None, :] * m


col = np.tile(LIN['barrel'], (n, 1))

# horse hindquarters deepen toward the rear
col = mix(col, LIN['hindq'], sstep(0.05, 0.55, Y))


def pnoise(p):
    s = np.zeros(len(p))
    for f, a in ((3.1, 1.0), (6.7, 0.55), (13.3, 0.28)):
        s += a * (np.sin(p[:, 0] * f + 0.7)
                  * np.sin(p[:, 1] * f * 1.3 + 1.1)
                  * np.sin(p[:, 2] * f * 0.9 + 2.3))
    return s / 1.83

# wings: lateral + above the belly line
m_wing = sstep(0.30, 0.50, AX) * sstep(0.80, 1.05, Z)
col = mix(col, LIN['wing'], m_wing)
# dark primaries toward the wing tips
col = mix(col, LIN['wingdark'], sstep(0.78, 1.05, AX) * sstep(0.95, 1.15, Z))
# feathered breast / neck ruff
m_breast = sstep(0.15, 0.55, -Y) * (1.0 - sstep(1.50, 1.95, Z)) * (1.0 - sstep(0.30, 0.52, AX))
col = mix(col, LIN['breast'], m_breast * 0.9)
# head feathers
m_head = sstep(0.58, 0.86, -Y) * sstep(1.20, 1.55, Z)
col = mix(col, LIN['head'], m_head)
# dark lower legs (not the wings)
m_low = (1.0 - sstep(0.55, 0.95, Z)) * (1.0 - m_wing)
col = mix(col, LIN['lowerleg'], m_low)
# hooves
col = mix(col, LIN['hoof'], (1.0 - sstep(0.06, 0.20, Z)) * (1.0 - sstep(0.25, 0.55, -Y)))
# golden talons on the forefeet
m_talon = (1.0 - sstep(0.30, 0.62, Z)) * sstep(0.25, 0.55, -Y)
col = mix(col, LIN['talon'], m_talon)
# golden beak
m_beak = sstep(0.88, 1.06, -Y) * sstep(1.55, 1.85, Z)
col = mix(col, LIN['beak'], m_beak)
# dark tail hair
col = mix(col, LIN['tail'], sstep(0.55, 0.82, Y))

# dappling on the horse body only (mottled lighter patches)
m_dap = ((1.0 - m_wing) * sstep(0.80, 1.05, Z) * (1.0 - sstep(1.75, 2.05, Z))
         * (1.0 - m_head) * (1.0 - sstep(0.55, 0.82, Y)))
dap = 1.0 + 0.20 * pnoise(co) * m_dap
col = col * dap[:, None]

rgba = np.ones((n, 4), dtype=np.float32)
rgba[:, :3] = col.astype(np.float32)

old = me.color_attributes.get(ATTR)
if old:
    me.color_attributes.remove(old)
attr = me.color_attributes.new(name=ATTR, type='FLOAT_COLOR', domain='POINT')
attr.data.foreach_set('color', rgba.ravel())
print("REGION attr set on %d verts" % n)

# ---- bake target ----
for img in list(bpy.data.images):
    if img.name.startswith(BAKE_IMG):
        bpy.data.images.remove(img)
bake = bpy.data.images.new(BAKE_IMG, BAKE_RES, BAKE_RES, alpha=False)
bake.colorspace_settings.name = 'sRGB'

detail = bpy.data.images[DETAIL_IMG]

# ---- temp bake material ----
mat = bpy.data.materials.new("Hippogriff_Bake")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
emit = nt.nodes.new('ShaderNodeEmission')
cattr = nt.nodes.new('ShaderNodeVertexColor')
cattr.layer_name = ATTR
tex = nt.nodes.new('ShaderNodeTexImage')
tex.image = detail
tgt = nt.nodes.new('ShaderNodeTexImage')
tgt.image = bake
nt.nodes.active = tgt
tgt.select = True

m1 = nt.nodes.new('ShaderNodeMix')
m1.data_type = 'RGBA'
m1.blend_type = 'MULTIPLY'
m1.inputs[0].default_value = 1.0
m1.inputs[7].default_value = (2.6, 2.6, 2.6, 1.0)

m2 = nt.nodes.new('ShaderNodeMix')
m2.data_type = 'RGBA'
m2.blend_type = 'ADD'
m2.inputs[0].default_value = 1.0
m2.inputs[7].default_value = (0.55, 0.55, 0.55, 1.0)

m3 = nt.nodes.new('ShaderNodeMix')
m3.data_type = 'RGBA'
m3.blend_type = 'MULTIPLY'
m3.inputs[0].default_value = 1.0
m3.clamp_result = True

nt.links.new(tex.outputs['Color'], m1.inputs[6])
nt.links.new(m1.outputs[2], m2.inputs[6])
nt.links.new(cattr.outputs['Color'], m3.inputs[6])
nt.links.new(m2.outputs[2], m3.inputs[7])
nt.links.new(m3.outputs[2], emit.inputs['Color'])
nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])

me.materials.clear()
me.materials.append(mat)

# ---- bake ----
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 1
sc.render.bake.use_clear = True
sc.render.bake.margin = 16
sc.render.bake.use_selected_to_active = False

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.bake(type='EMIT')
print("BAKE done, image size %s" % (bake.size[:],))

bake.filepath_raw = '/tmp/hippogriff_basecolor_4096.png'
bake.file_format = 'PNG'
bake.save()
print("BAKE saved /tmp/hippogriff_basecolor_4096.png")

# ---- final material using the baked texture (glTF friendly) ----
fmat = bpy.data.materials.new("Hippogriff_Recolored")
fmat.use_nodes = True
fnt = fmat.node_tree
fnt.nodes.clear()
fout = fnt.nodes.new('ShaderNodeOutputMaterial')
fb = fnt.nodes.new('ShaderNodeBsdfPrincipled')
fb.inputs['Roughness'].default_value = 0.78
fb.inputs['Metallic'].default_value = 0.0
fb.inputs['Specular IOR Level'].default_value = 0.28
ft = fnt.nodes.new('ShaderNodeTexImage')
ft.image = bake
ft.interpolation = 'Smart'
fnt.links.new(ft.outputs['Color'], fb.inputs['Base Color'])
fnt.links.new(fb.outputs['BSDF'], fout.inputs['Surface'])
me.materials.clear()
me.materials.append(fmat)
print("FINAL material assigned")

# ---- preview renders (rest pose) ----
for m in ob.modifiers:
    m.show_render = False
for o in bpy.data.objects:
    if o.name != CREATURE and o.type != 'EMPTY':
        o.hide_render = True

bg = sc.world.node_tree.nodes['Background']
for l in list(sc.world.node_tree.links):
    if l.to_node == bg:
        sc.world.node_tree.links.remove(l)
bg.inputs['Color'].default_value = (0.30, 0.32, 0.36, 1.0)
bg.inputs['Strength'].default_value = 1.0

for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)
kd = bpy.data.lights.new("KKey", type='SUN')
kd.energy = 4.0
ko = bpy.data.objects.new("KKey", kd)
sc.collection.objects.link(ko)
ko.rotation_euler = (math.radians(55), 0.0, math.radians(35))
fd = bpy.data.lights.new("KFill", type='SUN')
fd.energy = 1.2
fo = bpy.data.objects.new("KFill", fd)
sc.collection.objects.link(fo)
fo.rotation_euler = (math.radians(70), 0.0, math.radians(-130))

w = (np.hstack([co.astype(np.float32), np.ones((n, 1), dtype=np.float32)])
     @ np.array(ob.matrix_world).T)[:, :3]
mn, mx = w.min(axis=0), w.max(axis=0)
center = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2))
size = float(max(mx - mn))

cd = bpy.data.cameras.new("KCam")
cd.type = 'ORTHO'
cd.ortho_scale = size * 1.18
cam = bpy.data.objects.new("KCam", cd)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.resolution_x = 820
sc.render.resolution_y = 820
sc.render.engine = 'BLENDER_EEVEE'

for label, d in [("side", Vector((1, 0, 0))),
                 ("iso", Vector((1, -1, 0.6)).normalized()),
                 ("front", Vector((0, -1, 0)))]:
    cam.location = center + d * size * 3.0
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = '/tmp/recolor_%s.png' % label
    bpy.ops.render.render(write_still=True)
    print("RENDERED", label)

bpy.ops.wm.save_as_mainfile(filepath='/tmp/hippogriff_recolored.blend')
print("SAVED /tmp/hippogriff_recolored.blend")
print("END_RECOLOR")
