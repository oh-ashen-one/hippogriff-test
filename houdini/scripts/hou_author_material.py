from pxr import Usd, UsdShade, Sdf

SRC = '/tmp/hippo_usd/cam_test.usdnc'
OUT = '/tmp/hippo_usd/final.usd'
JPG = '/Users/midir/hippogriff-test/houdini/hippogriff_basecolor.jpg'
MAT = '/materials/hippogriff_mat'
SH = MAT + '/hippogriff_mat_preview'

stage = Usd.Stage.CreateNew(OUT)
stage.GetRootLayer().subLayerPaths.append(SRC)

# the mtlx material exports a UsdPreviewSurface sibling; Karma uses that one,
# so author the real texture onto it in this stronger layer
prev = stage.OverridePrim(SH)
shader = UsdShade.Shader(prev)
shader.CreateIdAttr('UsdPreviewSurface')

uv = UsdShade.Shader.Define(stage, MAT + '/uvreader')
uv.CreateIdAttr('UsdPrimvarReader_float2')
uv.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('st')
uv.CreateOutput('result', Sdf.ValueTypeNames.Float2)

tex = UsdShade.Shader.Define(stage, MAT + '/diffusetex')
tex.CreateIdAttr('UsdUVTexture')
tex.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(JPG)
tex.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), 'result')
tex.CreateInput('wrapS', Sdf.ValueTypeNames.Token).Set('repeat')
tex.CreateInput('wrapT', Sdf.ValueTypeNames.Token).Set('repeat')
tex.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)

shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(
    tex.ConnectableAPI(), 'rgb')
shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.65)
shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.0)
shader.CreateInput('useSpecularWorkflow', Sdf.ValueTypeNames.Int).Set(0)

m = stage.GetPrimAtPath(MAT)
mat = UsdShade.Material(m)
src = mat.ComputeSurfaceSource()
print("surface source now:", src[0].GetPath() if src and src[0] else None)

stage.GetRootLayer().Save()
print("WROTE", OUT)
print("END_AUTHOR")
