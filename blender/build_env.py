"""Sky, sun, cloud deck, haze, cloth secondary-motion strips, wind, render settings."""
import bpy, math
from mathutils import Vector

scn = bpy.context.scene
WD = "/Users/midir/hippogriff-test/blender"

# ---------- world: Nishita sky ----------
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scn.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = 'MULTIPLE_SCATTERING'
sky.sun_elevation = math.radians(14)
sky.sun_rotation = math.radians(215)
sky.altitude = 0.2
sky.air_density = 1.0
sky.ozone_density = 1.2
bg.inputs["Strength"].default_value = 0.9
nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

# ---------- sun ----------
sun = bpy.data.objects.get("Sun")
if sun is None:
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    scn.collection.objects.link(sun)
sun.data.energy = 2.6
sun.data.angle = math.radians(1.0)
sun.rotation_euler = (math.radians(76), 0, math.radians(35))

# ---------- cloud deck: two displaced-noise shader planes ----------
def cloud_plane(name, z, size, scale, detail, coverage, bright):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    ob.location = (0, -20, z)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = 'DITHERED'
    n = mat.node_tree; n.nodes.clear()
    o = n.nodes.new("ShaderNodeOutputMaterial")
    bs = n.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.95
    bs.inputs["Base Color"].default_value = (bright, bright * 0.97, bright * 0.94, 1)
    noise = n.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = '3D'
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.75
    noise.inputs["Distortion"].default_value = 0.4
    ramp = n.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = coverage
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = min(0.99, coverage + 0.28)
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    tex = n.nodes.new("ShaderNodeTexCoord")
    n.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    n.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    n.links.new(ramp.outputs["Color"], bs.inputs["Alpha"])
    n.links.new(bs.outputs["BSDF"], o.inputs["Surface"])
    me.materials.append(mat)
    return ob

cloud_plane("CloudDeck", 22.0, 900, 3.2, 7.0, 0.42, 0.96)
cloud_plane("CirrusHigh", 88.0, 900, 6.5, 4.0, 0.62, 0.9)

# ---------- haze volume (aerial perspective around flight path) ----------
hc = bpy.data.objects.get("Haze")
if hc is None:
    me = bpy.data.meshes.new("Haze")
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bm.to_mesh(me); bm.free()
    hc = bpy.data.objects.new("Haze", me)
    scn.collection.objects.link(hc)
hc.location = (0, -25, 45)
hc.scale = (150, 130, 40)
hmat = bpy.data.materials.new("Haze")
hmat.use_nodes = True
n = hmat.node_tree; n.nodes.clear()
o = n.nodes.new("ShaderNodeOutputMaterial")
pv = n.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Density"].default_value = 0.0012
pv.inputs["Anisotropy"].default_value = 0.25
pv.inputs["Color"].default_value = (0.75, 0.8, 0.9, 1)
n.links.new(pv.outputs["Volume"], o.inputs["Volume"])
hc.data.materials.append(hmat)
hc.display_type = 'WIRE'

# ---------- cloth strips (simulated secondary motion) ----------
rig = bpy.data.objects["Rig"]

def strip(name, length, width, segs, bone, offset):
    me = bpy.data.meshes.new(name)
    verts = []
    faces = []
    for i in range(segs + 1):
        y = -length * i / segs
        verts.append((-width / 2, y, 0))
        verts.append((width / 2, y, 0))
    for i in range(segs):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    ob.parent = rig
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    ob.matrix_parent_inverse.identity()
    ob.location = offset
    # pin group: first row
    vg = ob.vertex_groups.new(name="Pin")
    vg.add([0, 1], 1.0, 'REPLACE')
    cm = ob.modifiers.new("Cloth", 'CLOTH')
    cm.settings.vertex_group_mass = "Pin"
    cm.settings.mass = 0.12
    cm.settings.tension_stiffness = 12
    cm.settings.compression_stiffness = 12
    cm.settings.shear_stiffness = 8
    cm.settings.bending_stiffness = 0.4
    cm.settings.tension_damping = 4
    cm.settings.air_damping = 2.0
    # reuse the hippogriff material so strips read as hide/feather
    src = bpy.data.objects["tripo_2290e693_9a3e_4995_8858_c56a6a39ae89"]
    if src.data.materials:
        me.materials.append(src.data.materials[0])
    return ob

# clear old
for nm in ("TailStreamer", "ManeStrip", "WingStreamR", "WingStreamL"):
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)

strip("TailStreamer", 1.4, 0.28, 10, "tail2", Vector((0, 0.15, 0)))
strip("ManeStrip", 0.9, 0.35, 8, "neck1", Vector((0, 0.05, 0.12)))
strip("WingStreamR", 0.8, 0.22, 7, "fing3_R", Vector((0, 0.1, 0)))
strip("WingStreamL", 0.8, 0.22, 7, "fing3_L", Vector((0, 0.1, 0)))

# ---------- wind (relative airflow from forward flight) ----------
wind = bpy.data.objects.get("FlightWind")
if wind is None:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.effector_add(type='WIND', location=(0, 0, 50))
    wind = bpy.context.active_object
    wind.name = "FlightWind"
wind.field.strength = 6.0
wind.field.noise = 1.5
# blow toward +Y (from front -Y toward back +Y), slight downward
wind.rotation_euler = (math.radians(90), 0, 0)   # wind points along local +Z

# ---------- render settings ----------
try:
    scn.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    scn.render.engine = 'BLENDER_EEVEE'
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.render.image_settings.file_format = 'PNG'
scn.render.image_settings.color_mode = 'RGB'
scn.render.film_transparent = False
scn.render.use_motion_blur = True
scn.render.motion_blur_shutter = 0.6
scn.render.filepath = WD + "/frames/f_"
scn.render.image_settings.color_depth = '8'
scn.view_settings.look = 'AgX - Medium High Contrast'

bpy.ops.wm.save_as_mainfile(filepath=WD + "/hippogriff_flight.blend")
print("ENV DONE, engine:", scn.render.engine)
