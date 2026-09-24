import hou

hou.hipFile.load('/tmp/hippogriff_render.hip', suppress_save_prompt=True,
                 ignore_load_warnings=True)
st = hou.node('/stage')


def setp(node, parm, val):
    if node is None:
        print("   ! no node for %s" % parm)
        return
    p = node.parm(parm)
    if p is None:
        print("   ! %s has no parm %r" % (node.name(), parm))
        return
    try:
        old = p.eval()
    except Exception:
        old = '?'
    try:
        p.set(val)
        print("   %s.%s: %s -> %s" % (node.name(), parm, old, val))
    except Exception as e:
        print("   ! %s.%s set FAILED (%s)" % (node.name(), parm, e))


print("=== 1. remove light prims ===")
for nm in ('sky', 'sun'):
    n = st.node(nm)
    if n:
        print("   destroying /stage/%s (%s)" % (nm, n.type().name()))
        n.destroy()

ml = st.node('matlib')
print("=== 2. emissive sky + clouds ===")
setp(ml.node('sky_mat'), 'emission', 6.0)
setp(ml.node('sky_mat'), 'emission_colorr', 0.62)
setp(ml.node('sky_mat'), 'emission_colorg', 0.74)
setp(ml.node('sky_mat'), 'emission_colorb', 0.95)
setp(ml.node('cloud_mat'), 'emission', 3.0)
setp(ml.node('cloud_mat'), 'emission_colorr', 0.95)
setp(ml.node('cloud_mat'), 'emission_colorg', 0.96)
setp(ml.node('cloud_mat'), 'emission_colorb', 1.0)
setp(ml.node('hippogriff_mat'), 'emission', 0.0)
setp(ml.node('hippogriff_mat'), 'base', 1.0)

print("=== 3. render settings (tolerant) ===")
rs = st.node('rendersettings')
setp(rs, 'resolutionx', 1280)
setp(rs, 'resolutiony', 720)
setp(rs, 'engine', 'cpu')
for sp in ('pathtracedsamples', 'samples', 'pathtracedsamplesmin'):
    if rs and rs.parm(sp):
        setp(rs, sp, 24)
hou.playbar.setFrameRange(1, 120)
print("   frame range", hou.playbar.frameRange())

print("=== 4. is the skydome actually in the merge? ===")
ms = st.node('merge_scene')
if ms:
    for ic in ms.inputConnections():
        print("   merge input <- %s idx=%s" % (ic.inputNode().name(), ic.inputIndex()))
    for p in ms.parms():
        if 'primpattern' in p.name() or 'refprim' in p.name():
            try:
                print("   %s = %s" % (p.name(), str(p.eval())[:80]))
            except Exception:
                pass

print("=== 5. usd export parms ===")
ex = st.node('usdexport')
outp = None
if ex:
    print("   type:", ex.type().name())
    for p in ex.parms():
        nm = p.name()
        low = nm.lower()
        if 'path' in low or 'output' in low or 'file' in low or 'lop' in low:
            try:
                print("   cand %-24s = %s" % (nm, str(p.eval())[:90]))
            except Exception:
                pass
            if outp is None and ('output' in low or 'lopoutput' in low):
                outp = p
    if outp:
        setp(ex, outp.name(), '/tmp/hippo_usd/hippogriff_render.usd')
    try:
        ex.render()
        print("   EXPORT_CALL_DONE")
    except Exception as e:
        print("   ! export render failed: %s" % e)
else:
    print("   ! no /stage/usdexport")

hou.hipFile.save('/tmp/hippogriff_render_fixed.hip')
print("SAVED /tmp/hippogriff_render_fixed.hip")
print("END_FIX")
