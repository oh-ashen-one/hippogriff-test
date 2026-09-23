"""Re-bake rig anim with verification, fix camera arc, tame cloth, lighten render."""
import bpy, sys, math
sys.path.insert(0, "/Users/midir/hippogriff-test/blender")
import fkcore
from fkcore import capture_rest, solve, apply_pose, q
from mathutils import Vector, Quaternion

scn = bpy.context.scene
F0, F1, T, WD = 1, 120, 30.0, 13.0
arm = bpy.data.objects["Rig"]
capture_rest(arm)

def lerp_cos(a, b, u):
    u = max(0.0, min(1.0, u))
    return a + (b - a) * (1.0 - math.cos(math.pi * u)) / 2.0

def flap_phase(tt):
    u = tt % T
    if u < WD:
        return lerp_cos(32.0, -42.0, u / WD) - 50.0
    return lerp_cos(-42.0, 32.0, (u - WD) / (T - WD)) - 50.0

def dive_amount(f):
    if f < 48: return 0.0
    if f < 58: return (f - 48) / 10.0
    if f < 88: return 1.0
    if f < 100: return 1.0 - (f - 88) / 12.0
    return 0.0

def recover_boost(f):
    if f < 88: return 1.0
    if f < 104: return 1.0 + 0.45 * math.sin(math.pi * (f - 88) / 16.0)
    return 1.0

def wing_pose(f, S, s):
    d = dive_amount(f)
    boost = recover_boost(f)
    amp_scale = (1.0 - 0.72 * d) * boost
    base = flap_phase(f) * amp_scale
    elb = flap_phase(f - 2.0) * 0.72 * amp_scale
    tip = flap_phase(f - 4.5) * 0.9 * amp_scale
    u = f % T
    fold = 0.0
    if u > WD + 2:
        fold = math.sin(math.pi * min(1.0, (u - WD - 2) / (T - WD - 2)))
    sweep_up = 22.0 * fold * (1.0 - d)
    sweep_dive = 38.0 * d
    tuck = 25.0 * d
    p = {}
    p[f"arm_{S}0"] = q((0, 1, 0), -base * s) @ q((0, 0, 1), (sweep_dive * 0.5 + 6.0 * fold) * s)
    p[f"arm_{S}1"] = q((0, 1, 0), -(elb - base) * s * 0.5) @ q((0, 0, 1), (sweep_up + sweep_dive * 0.6) * s)
    spread = 6.0 * (1.0 - fold) - 4.0 * fold
    p[f"fing1_{S}"] = q((0, 1, 0), -(tip - elb) * s * 0.35) @ q((0, 0, 1), sweep_dive * 0.4 * s)
    p[f"fing2_{S}"] = q((0, 1, 0), (-(tip - elb) * 0.4 - spread * 0.2) * s)
    p[f"fing3_{S}"] = q((0, 1, 0), (-(tip - elb) * 0.45 - spread * 0.5 - tuck * 0.2) * s)
    return p

def body_pose(f):
    d = dive_amount(f)
    p = {}
    if f < 60: neck_extra = 0.0
    elif f < 90: neck_extra = 14.0 * (f - 60) / 30.0
    elif f < 110: neck_extra = 14.0 - 20.0 * (f - 90) / 20.0
    else: neck_extra = -6.0 + 6.0 * (f - 110) / 10.0
    p["neck0"] = q((1, 0, 0), -8.0 + neck_extra * 0.4)
    p["neck1"] = q((1, 0, 0), -6.0 + neck_extra * 0.35)
    p["head"] = q((1, 0, 0), 6.0 + neck_extra * 0.25)
    tail_lift = 10.0 * d - (6.0 * (recover_boost(f) - 1.0) / 0.45 if recover_boost(f) > 1.0 else 0.0)
    wag = 3.0 * math.sin(2 * math.pi * f / 45.0)
    p["tail0"] = q((1, 0, 0), 4.0 + tail_lift) @ q((0, 0, 1), wag)
    p["tail1"] = q((1, 0, 0), 3.0 + tail_lift * 0.5) @ q((0, 0, 1), wag * 1.4)
    p["tail2"] = q((1, 0, 0), 2.0) @ q((0, 0, 1), wag * 1.8)
    for S, s in (("R", 1), ("L", -1)):
        p[f"fore_{S}0"] = q((1, 0, 0), -38.0)
        p[f"fore_{S}1"] = q((1, 0, 0), 55.0)
        p[f"foretoe_{S}"] = q((1, 0, 0), 20.0)
        p[f"hind_{S}0"] = q((1, 0, 0), -30.0)
        p[f"hind_{S}1"] = q((1, 0, 0), 48.0)
        p[f"hindtoe_{S}"] = q((1, 0, 0), 25.0)
    return p

if arm.animation_data:
    arm.animation_data_clear()

for f in range(F0, F1 + 1):
    pose = body_pose(f)
    for S, s in (("R", 1), ("L", -1)):
        pose.update(wing_pose(f, S, s))
    d = dive_amount(f)
    bobA = 0.14 * (1.0 - 0.8 * d) * recover_boost(f)
    bob = bobA * math.sin(2 * math.pi * (f - WD - 4) / T)
    pitch_osc = math.radians(2.2) * math.sin(2 * math.pi * (f - WD) / T + 0.6)
    mats = solve(pose, root_rot=Quaternion((1, 0, 0), pitch_osc), root_off=Vector((0, 0, bob)))
    apply_pose(arm, mats, frame=f)

# VERIFY
act = arm.animation_data.action
cb = act.layers[0].strips[0].channelbags[0]
for fc in cb.fcurves:
    if fc.data_path == 'pose.bones["arm_R0"].rotation_quaternion' and fc.array_index == 0:
        print("VERIFY arm_R0 quat.w @10,22,36,75:", [round(fc.evaluate(x), 3) for x in (10, 22, 36, 75)])

# ---------- camera fix ----------
cam = bpy.data.objects["HeroCam"]
if cam.animation_data:
    cam.animation_data_clear()
target = bpy.data.objects["CamTarget"]
if target.animation_data:
    target.animation_data_clear()
flight = bpy.data.objects["Flight"]

flight_pos = {}; flight_yaw = {}
for f in range(F0 - 8, F1 + 1):
    scn.frame_set(max(F0, f))
    flight_pos[f] = flight.matrix_world.to_translation().copy()
    flight_yaw[f] = flight.matrix_world.to_quaternion()

LAG = 6
cam_pos = {}
for f in range(F0, F1 + 1):
    src = max(F0, f - LAG)
    base = flight_pos[src]; yq = flight_yaw[src]
    u = (f - F0) / (F1 - F0)
    ang = math.radians(-135.0 - 100.0 * u)
    r = 11.5 - 1.5 * math.sin(math.pi * u)
    off = yq @ Vector((r * math.cos(ang), r * math.sin(ang), 3.2 + 0.8 * math.sin(math.pi * u)))
    n = Vector((0.10 * math.sin(f * 0.9) + 0.06 * math.sin(f * 2.3 + 1.0),
                0.09 * math.sin(f * 0.7 + 2.0) + 0.05 * math.sin(f * 1.9),
                0.07 * math.sin(f * 1.1 + 4.0)))
    cam_pos[f] = base + off + n
for _ in range(2):
    sm = {}
    for f in range(F0, F1 + 1):
        a = cam_pos.get(f - 1, cam_pos[f]); b = cam_pos[f]; c = cam_pos.get(f + 1, cam_pos[f])
        sm[f] = (a + 2 * b + c) * 0.25
    cam_pos = sm
for f in range(F0, F1 + 1):
    cam.location = cam_pos[f]
    cam.keyframe_insert("location", frame=f)
    vel = flight_pos[min(F1, f + 4)] - flight_pos[f]
    target.location = flight_pos[f] + Vector((0, 0, 1.4)) + vel * 0.55
    target.keyframe_insert("location", frame=f)

# ---------- cloth taming ----------
wind = bpy.data.objects.get("FlightWind")
if wind and wind.field:
    wind.field.strength = 2.2
    wind.field.noise = 0.8
for nm in ("TailStreamer", "ManeStrip", "WingStreamR", "WingStreamL"):
    o = bpy.data.objects.get(nm)
    if not o:
        continue
    cm = o.modifiers.get("Cloth")
    if cm:
        cm.settings.mass = 0.25
        cm.settings.tension_damping = 8
        cm.settings.air_damping = 4.0
        cm.settings.bending_stiffness = 1.2

# ---------- lighten render ----------
hz = bpy.data.objects.get("Haze")
if hz:
    bpy.data.objects.remove(hz, do_unlink=True)
cd = bpy.data.objects.get("CloudDeck")
if cd:
    ramp = [n for n in cd.data.materials[0].node_tree.nodes if n.bl_idname == "ShaderNodeValToRGB"][0]
    ramp.color_ramp.elements[0].position = 0.52
sun = bpy.data.objects.get("Sun")
sun.data.energy = 3.2
sun.data.color = (1.0, 0.93, 0.82)
try:
    scn.eevee.taa_render_samples = 16
except Exception as e:
    print("samples:", e)

scn.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath="/Users/midir/hippogriff-test/blender/hippogriff_flight.blend")
print("REBAKE DONE")
