import bpy

# Hide environment meshes: keep only the hippogriff (tripo mesh, TailStreamer),
# rig, lights, cameras and control empties.
for o in bpy.data.objects:
    if o.name.startswith(("CirrusHigh", "CloudDeck")):
        o.hide_render = True

# Flat neutral gray world so the model reads on its own.
world = bpy.context.scene.world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.05, 0.05, 0.06, 1.0)
bg.inputs["Strength"].default_value = 0.35

scene = bpy.context.scene
scene.render.film_transparent = False
scene.render.filepath = "/Users/midir/hippogriff-test/blender/frames_solo/f_"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.engine = "BLENDER_EEVEE"
