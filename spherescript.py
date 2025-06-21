import bpy
import os
import math

#### SETUP: Change export path as needed ####
export_path = os.path.expanduser("~/Desktop/sphere_dataset/")
os.makedirs(export_path, exist_ok=True)

#### PARAMETERS ####
SPHERE_RADIUS = 1.0
SPHERE_SEGMENTS = 64    # Smoother sphere
OPACITY = 0.4           # Between 0.0 and 1.0
OUTLINE_THICKNESS = 0.04
HOOP_THICKNESS = 0.02

RENDER_VIEWS = [
    ("front", (0, 0, 0)),
    ("side", (0, math.radians(90), 0)),
    ("top", (math.radians(90), 0, 0)),
    ("3quarter", (math.radians(35), math.radians(40), 0)),
]

#### HELPER FUNCTIONS ####

def delete_all():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Also clean up orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

def make_material(name, rgba, transparent=True):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Alpha'].default_value = rgba[3]
    if transparent:
        mat.blend_method = 'BLEND'
        mat.show_transparent_back = True
    return mat

def add_outline(obj, thickness):
    # Duplicate, scale up slightly, flip normals, make black
    outline = obj.copy()
    outline.data = obj.data.copy()
    bpy.context.collection.objects.link(outline)
    outline.scale = (1+thickness, 1+thickness, 1+thickness)
    # Flip normals
    bpy.context.view_layer.objects.active = outline
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')
    # Set black material, full opacity
    outline_mat = make_material("outline_black", (0,0,0,1))
    if outline.data.materials:
        outline.data.materials[0] = outline_mat
    else:
        outline.data.materials.append(outline_mat)
    outline.show_in_front = True
    outline.display_type = 'SOLID'
    outline.name = obj.name + "_outline"
    return outline

def add_hoop(radius, thickness, axis='Z'):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=thickness,
        major_segments=96,
        minor_segments=16
    )
    hoop = bpy.context.active_object
    # Orientation
    if axis == 'X':
        hoop.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y':
        hoop.rotation_euler = (math.radians(90), 0, 0)
    # Material
    hoop_mat = make_material("hoop_black", (0,0,0,1))
    if hoop.data.materials:
        hoop.data.materials[0] = hoop_mat
    else:
        hoop.data.materials.append(hoop_mat)
    hoop.name = f"hoop_{axis}"
    hoop["shape_tag"] = f"hoop_{axis}"
    return hoop

def add_camera_light():
    # Add camera and light for rendering
    if "Camera" not in bpy.data.objects:
        bpy.ops.object.camera_add(location=(0, -4, 0), rotation=(math.radians(90), 0, 0))
    cam = bpy.data.objects["Camera"]
    bpy.context.scene.camera = cam
    if "Light" not in bpy.data.objects:
        bpy.ops.object.light_add(type='AREA', location=(0, -3, 3))
    light = bpy.data.objects["Light"]
    light.data.energy = 500
    return cam, light

def export_mesh(obj_list, filename):
    # Select all objects in list
    bpy.ops.object.select_all(action='DESELECT')
    for obj in obj_list:
        obj.select_set(True)
    bpy.ops.export_scene.obj(
        filepath=os.path.join(export_path, filename),
        use_selection=True,
        use_materials=True,
    )
    # Deselect after export
    for obj in obj_list:
        obj.select_set(False)

def render_view(name, cam, target, rotation):
    # Reset cam position and rotate scene
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type != 'CAMERA':
            obj.select_set(True)
    bpy.ops.transform.rotate(value=rotation[0], orient_axis='X')
    bpy.ops.transform.rotate(value=rotation[1], orient_axis='Y')
    bpy.ops.transform.rotate(value=rotation[2], orient_axis='Z')
    # Set render params
    bpy.context.scene.render.filepath = os.path.join(export_path, f"sphere_{name}.png")
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    # Rotate back for next view
    bpy.ops.transform.rotate(value=-rotation[2], orient_axis='Z')
    bpy.ops.transform.rotate(value=-rotation[1], orient_axis='Y')
    bpy.ops.transform.rotate(value=-rotation[0], orient_axis='X')

#### MAIN SCRIPT ####

delete_all()

# 1. Make sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=SPHERE_RADIUS, segments=SPHERE_SEGMENTS, ring_count=SPHERE_SEGMENTS, location=(0,0,0))
sphere = bpy.context.active_object
sphere.name = "core_sphere"
sphere["shape_tag"] = "sphere_core"
sphere_mat = make_material("sphere_transparent", (1,1,1,OPACITY), transparent=True)
if sphere.data.materials:
    sphere.data.materials[0] = sphere_mat
else:
    sphere.data.materials.append(sphere_mat)

# 2. Outline
outline = add_outline(sphere, OUTLINE_THICKNESS)
outline["shape_tag"] = "sphere_outline"

# 3. Hoops
hoop1 = add_hoop(SPHERE_RADIUS, HOOP_THICKNESS, axis='Z')  # equator (latitude)
hoop2 = add_hoop(SPHERE_RADIUS, HOOP_THICKNESS, axis='X')  # meridian (longitude)

# Parent all to sphere (optional, keeps them together)
for child in [outline, hoop1, hoop2]:
    child.parent = sphere

# 4. Export mesh (all together)
export_mesh([sphere, outline, hoop1, hoop2], "core_sphere.obj")

# 5. Render images from multiple angles
cam, light = add_camera_light()
bpy.ops.object.select_all(action='DESELECT')
sphere.select_set(True)
outline.select_set(True)
hoop1.select_set(True)
hoop2.select_set(True)

for view_name, rot in RENDER_VIEWS:
    render_view(view_name, cam, sphere, rot)

# 6. Save a label file (CSV)
with open(os.path.join(export_path, "core_sphere_labels.csv"), "w") as f:
    f.write("object,shape_tag\n")
    f.write("core_sphere,sphere_core\n")
    f.write("core_sphere_outline,sphere_outline\n")
    f.write("hoop_Z,hoop_Z\n")
    f.write("hoop_X,hoop_X\n")

print(f"\nAll done! Check your folder: {export_path}\n")