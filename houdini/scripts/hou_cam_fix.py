import math
import hou

hou.hipFile.load('/tmp/hippogriff_render_fixed.hip', suppress_save_prompt=True,
                 ignore_load_warnings=True)
st = hou.node('/stage')
ml = st.node('matlib')
cam = st.node('/stage/cam')

# creature occupies x -1.37..1.37, y -0.13..2.02, z -1.17..1.20  (Houdini Z-up)
P = (5.5, 2.6, 8.0)      # camera position
T = (0.0, 0.95, 0.02)    # look-at point
d = [T[i] - P[i] for i in range(3)]
L = math.sqrt(sum(c * c for c in d))
dn = [c / L for c in d]
rx = math.degrees(math.asin(dn[1]))
ry = math.degrees(math.atan2(-dn[0], -dn[2]))
print("distance to target %.3f  rx=%.2f ry=%.2f" % (L, rx, ry))

for nm, val in (('tx', P[0]), ('ty', P[1]), ('tz', P[2]),
                ('rx', rx), ('ry', ry), ('rz', 0.0)):
    p = cam.parm(nm)
    if p is None:
        print("  ! no parm", nm)
        continue
    old = p.eval()
    try:
        p.set(val)
        print("  cam.%s: %s -> %s" % (nm, old, val))
    except Exception as e:
        print("  ! cam.%s failed %s" % (nm, e))


def setp(node, parm, val):
    if node is None or node.parm(parm) is None:
        print("  ! %s.%s unavailable" % (node.name() if node else '?', parm))
        return
    p = node.parm(parm)
    try:
        old = p.eval()
    except Exception:
        old = '?'
    try:
        p.set(val)
        print("  %s.%s: %s -> %s" % (node.name(), parm, old, val))
    except Exception as e:
        print("  ! %s.%s failed %s" % (node.name(), parm, e))


print("=== tone down the emissive background ===")
setp(ml.node('sky_mat'), 'emission', 3.0)
setp(ml.node('cloud_mat'), 'emission', 1.0)
print("=== creature lit by the dome, not self-lit ===")
setp(ml.node('hippogriff_mat'), 'emission', 0.0)

ex = st.node('usdexport')
setp(ex, 'lopoutput', '/tmp/hippo_usd/cam_test.usd')
ex.render()
print("EXPORTED")
hou.hipFile.save('/tmp/hippogriff_cam_fixed.hip')
print("END_CAMFIX")
