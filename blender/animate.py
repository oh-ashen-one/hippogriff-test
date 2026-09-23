"""Bake the full 120-frame flight animation: wingbeat FK, flight path, camera."""
import bpy, sys, math
sys.path.insert(0, "/Users/midir/hippogriff-test/blender")
import fkcore
from fkcore import capture_rest, solve, apply_pose, q, PARENT
from mathutils import Vector, Quaternion, Matrix

FPS = 24
F0, F1 = 1, 120
T = 30.0          # wingbeat period (frames)
WD = 13.0         # downstroke length

scn = bpy.context.scene
scn.frame_start = F0; scn.frame_end = F1
scn.render.fps = FPS
arm = bpy.data.objects["Rig"]
capture_rest(arm)

# ---------- empties hierarchy: Flight (path+yaw) > Bank (roll/pitch) > Rig ----------
def get_empty(name):
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, None)
        scn.collection.objects.link(o)
    return o

flight = get_empty("Flight")
bank = get_empty("Bank")
if bank.parent is not flight:
    bank.parent = flight
if arm.parent is not bank:
    mw = arm.matrix_world.copy()
    arm.parent = bank
    arm.matrix_world = mw

# ---------- flight path keys ----------
# (frame, x, y, z, yaw_deg)
PATH = [
    (1,    2.0,  30.0, 60.0,   0.0),
    (45,   0.0, -10.0, 60.0,   2.0),
    (60,  -1.5, -22.0, 58.5,  -8.0),
    (85,  -6.0, -42.0, 52.0, -24.0),
    (100, -9.0, -56.0, 52.5, -30.0),
    (112, -10.0, -68.0, 55.0, -26.0),
    (120, -10.5, -77.0, 55.5, -22.0),
]
# (frame, roll_deg, pitch_deg)
BANK = [
    (1,   0.0,  0.0),
    (45,  3.0, -2.0),
    (60, -8.0, -14.0),
    (78, -28.0, -19.0),
    (92, -30.0, -6.0),
    (102, -18.0, 11.0),
    (112, -8.0,  6.0),
    (120, -2.0,  2.0),
]

def clear_anim(o):
    if o.animation_data:
        o.animation_data_clear()

for o in (flight, bank):
    clear_anim(o)
for f, x, y, z, yaw in PATH:
    flight.location = (x, y, z)
    flight.rotation_euler = (0, 0, math.radians(yaw))
    flight.keyframe_insert("location", frame=f)
    flight.keyframe_insert("rotation_euler", frame=f)
for f, roll, pitch in BANK:
    bank.rotation_euler = (math.radians(roll), 0, math.radians(pitch))
    bank.keyframe_insert("rotation_euler", frame=f)
# bank local axes: X=pitch (lateral), Y=roll (forward axis)
for f, roll, pitch in BANK:
    bank.rotation_euler = (math.radians(pitch), math.radians(roll), 0.0)
    bank.keyframe_insert("rotation_euler", frame=f)

# (default keyframe interpolation is already BEZIER)

def eval_loc(o, f):
    scn.frame_set(f)
    return o.matrix_world.to_translation().copy(), o.matrix_world.to_quaternion()

# ---------- wingbeat profile ----------
def lerp_cos(a, b, u):
    u = max(0.0, min(1.0, u))
    return a + (b - a) * (1.0 - math.cos(math.pi * u)) / 2.0

def flap_phase(tt):
    """tt in frames; returns base wing elevation angle deg (positive = up)."""
    u = tt % T
    if u < WD:
        return lerp_cos(32.0, -42.0, u / WD)      # power downstroke
    return lerp_cos(-42.0, 32.0, (u - WD) / (T - WD))  # upstroke

def dive_amount(f):
    """0 cruise, 1 full tuck during dive."""
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
    """local rotations for one wing at frame f."""
    d = dive_amount(f)
    boost = recover_boost(f)
    amp_scale = (1.0 - 0.72 * d) * boost
    lag_e, lag_f = 2.0, 4.5
    base = flap_phase(f) * amp_scale
    elb = flap_phase(f - lag_e) * 0.72 * amp_scale
    tip = flap_phase(f - lag_f) * 0.9 * amp_scale
    # upstroke fold: wrist sweeps back + tips fold when wing is rising
    u = (f % T)
    fold = 0.0
    if u > WD + 2:
        fold = math.sin(math.pi * min(1.0, (u - WD - 2) / (T - WD - 2)))
    sweep_up = 22.0 * fold * (1.0 - d)
    # dive tuck: sweep wings back hard, fold
    sweep_dive = 38.0 * d
    tuck = 25.0 * d
    p = {}
    p[f"arm_{S}0"] = q((0, 1, 0), -base * s) @ q((0, 0, 1), (sweep_dive * 0.5 + 6.0 * fold) * s)
    p[f"arm_{S}1"] = q((0, 1, 0), -(elb - base) * s * 0.8) @ q((0, 0, 1), (sweep_up + sweep_dive * 0.6) * s)
    # fingers: fan; follow tip with spread on downstroke, close on upstroke
    spread = 6.0 * (1.0 - fold) - 4.0 * fold
    droop = (tip - elb) * 0.9 - tuck
    p[f"fing1_{S}"] = q((0, 1, 0), -(tip - elb) * s * 0.7) @ q((0, 0, 1), sweep_dive * 0.4 * s)
    p[f"fing2_{S}"] = q((0, 1, 0), (-(tip - elb) * 0.9 - spread * 0.4) * s)
    p[f"fing3_{S}"] = q((0, 1, 0), (-(tip - elb) * 1.05 - spread - tuck * 0.4) * s)
    return p

def body_pose(f):
    d = dive_amount(f)
    p = {}
    # neck counter-pitch: keep head level through dive
    if f < 60:
        neck_extra = 0.0
    elif f < 90:
        neck_extra = 14.0 * (f - 60) / 30.0
    elif f < 110:
        neck_extra = 14.0 - 20.0 * (f - 90) / 20.0
    else:
        neck_extra = -6.0 + 6.0 * (f - 110) / 10.0
    p["neck0"] = q((1, 0, 0), -8.0 + neck_extra * 0.4)
    p["neck1"] = q((1, 0, 0), -6.0 + neck_extra * 0.35)
    p["head"] = q((1, 0, 0), 6.0 + neck_extra * 0.25)
    # tail: streams, lifts during dive, spreads on recovery
    tail_lift = 10.0 * d - 6.0 * (recover_boost(f) - 1.0) / 0.45 if recover_boost(f) > 1.0 else 10.0 * d
    wag = 3.0 * math.sin(2 * math.pi * f / 45.0)
    p["tail0"] = q((1, 0, 0), 4.0 + tail_lift) @ q((0, 0, 1), wag)
    p["tail1"] = q((1, 0, 0), 3.0 + tail_lift * 0.5) @ q((0, 0, 1), wag * 1.4)
    p["tail2"] = q((1, 0, 0), 2.0) @ q((0, 0, 1), wag * 1.8)
    # legs tucked in flight
    for S, s in (("R", 1), ("L", -1)):
        p[f"fore_{S}0"] = q((1, 0, 0), -38.0)
        p[f"fore_{S}1"] = q((1, 0, 0), 55.0)
        p[f"foretoe_{S}"] = q((1, 0, 0), 20.0)
        p[f"hind_{S}0"] = q((1, 0, 0), -30.0)
        p[f"hind_{S}1"] = q((1, 0, 0), 48.0)
        p[f"hindtoe_{S}"] = q((1, 0, 0), 25.0)
    return p

# ---------- bake all frames ----------
# clear old pose animation
if arm.animation_data:
    arm.animation_data_clear()

chest_track = {}
for f in range(F0, F1 + 1):
    pose = body_pose(f)
    for S, s in (("R", 1), ("L", -1)):
        pose.update(wing_pose(f, S, s))
    # body bob: peaks shortly after downstroke ends; damped in dive
    d = dive_amount(f)
    bobA = 0.14 * (1.0 - 0.8 * d) * recover_boost(f)
    bob = bobA * math.sin(2 * math.pi * (f - WD - 4) / T)
    pitch_osc = math.radians(2.2) * math.sin(2 * math.pi * (f - WD) / T + 0.6)
    root_rot = Quaternion((1, 0, 0), pitch_osc)
    mats = solve(pose, root_rot=root_rot, root_off=Vector((0, 0, bob)))
    apply_pose(arm, mats, frame=f)

print("rig baked")

# ---------- camera ----------
cam = bpy.data.objects.get("HeroCam")
if cam is None:
    cam = bpy.data.objects.new("HeroCam", bpy.data.cameras.new("HeroCam"))
    scn.collection.objects.link(cam)
cam.data.lens = 55
cam.data.sensor_width = 36
clear_anim(cam)
scn.camera = cam

target = get_empty("CamTarget")
clear_anim(target)

# gather flight world positions per frame
flight_pos = {}
flight_yaw = {}
for f in range(F0 - 8, F1 + 1):
    scn.frame_set(max(F0, f))
    flight_pos[f] = flight.matrix_world.to_translation().copy()
    flight_yaw[f] = flight.matrix_world.to_quaternion()

LAG = 6
cam_pos = {}
for f in range(F0, F1 + 1):
    src = max(F0, f - LAG)
    base = flight_pos[src]
    yq = flight_yaw[src]
    # viewpoint drift: ahead-left -> left -> behind-left
    u = (f - F0) / (F1 - F0)
    ang = math.radians(-135 + 105 * u)      # orbit around creature
    r = 10.5 - 1.5 * math.sin(math.pi * u)
    off_local = Vector((r * math.cos(ang), -r * math.sin(ang) * -1.0, 2.6 + 0.8 * math.sin(math.pi * u)))
    # creature front is -Y; build offset in yaw frame (x right, y back(+), z up)
    off_local = Vector((r * math.cos(ang), -r * math.sin(ang), 2.6 + 0.8 * math.sin(math.pi * u)))
    off = yq @ off_local
    # subtle handheld
    n = Vector((0.12 * math.sin(f * 0.9) + 0.07 * math.sin(f * 2.3 + 1.0),
                0.10 * math.sin(f * 0.7 + 2.0) + 0.06 * math.sin(f * 1.9),
                0.08 * math.sin(f * 1.1 + 4.0)))
    cam_pos[f] = base + off + n
# smooth pass (1-2-1)
for _ in range(2):
    sm = {}
    for f in range(F0, F1 + 1):
        a = cam_pos.get(f - 1, cam_pos[f]); b = cam_pos[f]; c = cam_pos.get(f + 1, cam_pos[f])
        sm[f] = (a + 2 * b + c) * 0.25
    cam_pos = sm

for f in range(F0, F1 + 1):
    cam.location = cam_pos[f]
    cam.keyframe_insert("location", frame=f)
    # target: chest + lead ahead of motion
    vel = flight_pos[min(F1, f + 4)] - flight_pos[f]
    tgt = flight_pos[f] + Vector((0, 0, 1.4)) + vel * 0.55
    target.location = tgt
    target.keyframe_insert("location", frame=f)

# track-to
for c in list(cam.constraints):
    cam.constraints.remove(c)
tc = cam.constraints.new('TRACK_TO')
tc.target = target
tc.track_axis = 'TRACK_NEGATIVE_Z'
tc.up_axis = 'UP_Y'

# DOF
cam.data.dof.use_dof = True
cam.data.dof.focus_object = target
cam.data.dof.aperture_fstop = 5.6

scn.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath="/Users/midir/hippogriff-test/blender/hippogriff_flight.blend")
print("ANIM DONE")
