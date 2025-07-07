import os
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRep import BRep_Builder
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.gp import gp_Trsf, gp_Pnt
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.gp import gp_Dir
from OCC.Core.Graphic3d import Graphic3d_BufferType
from OCC.Display.OCCViewer import Viewer3d
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Graphic3d import Graphic3d_TOSM_FRAGMENT
from OCC.Core.Graphic3d import (
    Graphic3d_TOSM_FRAGMENT,
    Graphic3d_NameOfMaterial,
    Graphic3d_MaterialAspect,
)
from OCC.Core.V3d import V3d_DirectionalLight, V3d_ZBUFFER
from math import cos, sin, radians
from OCC.Core.gp import gp_Pnt, gp_Dir

from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Display.OCCViewer import get_color_from_name
import numpy as np

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCC.Core.Quantity import Quantity_NOC_RED
from OCC.Core.BRep import BRep_Tool

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import (
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere,
    GeomAbs_Torus, GeomAbs_SurfaceOfRevolution, GeomAbs_SurfaceOfExtrusion,
    GeomAbs_BezierSurface, GeomAbs_BSplineSurface
)
import numpy as np
from tqdm import tqdm



# === Configuration === #
OUTPUT_DIR = "/media/aliSSD/04_DATASETS/ABC_BRep_Annotation/imgs/abc_0004_imgs_v00/" #"/media/aliSSD/04_DATASETS/CC3D-OPS/CC3D-OPS/imgs" #cad_renders
IMAGE_SIZE = (1280, 960)

# View directions in the form: (eye, center, up)
CAMERA_VIEWS = {
    "front": gp_Dir(0, -1, 0),
    "rear": gp_Dir(0, 1, 0),
    "left": gp_Dir(-1, 0, 0),
    "right": gp_Dir(1, 0, 0),
    "top": gp_Dir(0, 0, 1),
    "bottom": gp_Dir(0, 0, -1),
    "iso": gp_Dir(1, -1, 1),
}

def normalize_shape(shape):
    """Normalize shape into [-1, 1]^3 bounding box"""
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    center = gp_Pnt((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
    scale = 2.0 / max(xmax - xmin, ymax - ymin, zmax - zmin)
    trsf = gp_Trsf()
    trsf.SetScale(center, scale)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

def read_step_file(filepath):
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP reader error code {status} for file: {filepath}")
    
    ok = reader.TransferRoots()
    if ok == 0:
        raise RuntimeError(f"Failed to transfer shape from STEP file: {filepath}")

    shape = reader.OneShape()
    return shape

def warmup_renderer():
    dummy = Viewer3d()
    dummy.Create()
    dummy.SetSize(256, 256)
    dummy.Repaint()
    print("OpenGL warmup done.")

def render_step_model(filepath, output_base):
    shape = read_step_file(filepath)
    shape = normalize_shape(shape)

    renderer = Viewer3d()
    renderer.Create()
    renderer.SetSize(*IMAGE_SIZE)
    renderer.set_bg_gradient_color([255, 255, 255], [255, 255, 255])
    renderer.SetModeShaded()
    renderer.View.SetShadingModel(Graphic3d_TOSM_FRAGMENT)

    # Face: transparent teal
    # face_color = Quantity_Color(0.3, 0.8, 0.8, Quantity_TOC_RGB)
    # ais_shape = AIS_Shape(shape)
    # ais_shape.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
    # ais_shape.SetTransparency(0.2)  # ~20% transparent
    # renderer.Context.SetColor(ais_shape, face_color, False)
    # renderer.Context.Display(ais_shape, False)
    face_coloring_mode = "uniform"  # CHANGE TO "uniform" or "by_type" or "by_index" if desired
    for face, color in assign_face_colors(shape, mode=face_coloring_mode):
        face_ais = AIS_Shape(face)
        face_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
        face_ais.SetTransparency(0.2)  # subtle transparency
        renderer.Context.SetColor(face_ais, color, False)
        renderer.Context.Display(face_ais, False)

    # Edge: black with increased thickness
    edge_color = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
    for edge in TopologyExplorer(shape).edges():
        edge_ais = AIS_Shape(edge)
        edge_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
        edge_ais.SetWidth(4.0)  # thicker edges
        renderer.Context.SetColor(edge_ais, edge_color, False)
        renderer.Context.Display(edge_ais, False)

    # -- Display corner vertices as large red dots --
    vertex_color = Quantity_Color(Quantity_NOC_RED)
    for vertex in TopologyExplorer(shape).vertices():
        pnt = BRep_Tool.Pnt(vertex)  # Extract gp_Pnt from TopoDS_Vertex
        vertex_shape = BRepBuilderAPI_MakeVertex(pnt).Shape()
        vertex_ais = AIS_Shape(vertex_shape)

        vertex_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
        renderer.Context.SetColor(vertex_ais, vertex_color, False)
        renderer.Context.Display(vertex_ais, False)

        # Increase the point size (important for visibility)
        vertex_ais.SetWidth(25.0)  # This controls visual size in screen space
        
    renderer.FitAll()
    renderer.Repaint()

    # Simulate orbit camera around Z with azimuth angle (e.g., 45 deg inclination)
    radius = 3.0  # distance from object center
    inclination_deg = 45
    inclination_rad = radians(inclination_deg)
    center = gp_Pnt(0, 0, 0)

    for i, theta_deg in enumerate(range(0, 360, 30)):  # every 30°, 12 views
        theta_rad = radians(theta_deg)
        x = radius * cos(theta_rad) * cos(inclination_rad)
        y = radius * sin(theta_rad) * cos(inclination_rad)
        z = radius * sin(inclination_rad)

        eye = gp_Pnt(x, y, z)
        renderer.camera.SetEye(eye)
        renderer.camera.SetCenter(center)
        renderer.camera.SetUp(gp_Dir(0, 0, 1))  # Z-up
        renderer.FitAll()
        renderer.SetSize(*IMAGE_SIZE)

        filename = f"{output_base}_orbit_{i:02d}.png"
        renderer.View.Dump(filename)
        print(f"[✓] Saved: {filename}")

def get_all_step_files(root_dir):
    step_paths = []
    for dirpath, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith((".step", ".stp")):
                step_paths.append(os.path.join(dirpath, file))
    return step_paths

def has_rendered_all_views(output_base, num_views=12):
    """Check if all orbit image files already exist for this model."""
    for i in range(num_views):
        view_file = f"{output_base}_orbit_{i:02d}.png"
        if not os.path.exists(view_file):
            return False
    return True

# def batch_render_all(input_root, output_root):
#     os.makedirs(output_root, exist_ok=True)
#     step_files = get_all_step_files(input_root)
#     print(f"Found {len(step_files)} STEP files.")

#     #Assuming step_files is already defined as a list of file paths
#     for step_file in tqdm(step_files, desc="Rendering STEP files"):
#        try:
#            model_name = os.path.splitext(os.path.basename(step_file))[0]
#            parent_folder = os.path.basename(os.path.dirname(step_file))
#            output_dir = os.path.join(output_root, parent_folder)
#            os.makedirs(output_dir, exist_ok=True)

#            output_base = os.path.join(output_dir, model_name)
#            render_step_model(step_file, output_base)
#        except Exception as e:
#            print(f"[!] Failed: {step_file} | {e}")

#     # for step_file in step_files:
#     #      model_name = os.path.splitext(os.path.basename(step_file))[0]
#     #      output_dir = os.path.join(output_root, os.path.basename(os.path.dirname(step_file)))
#     #      #output_dir = os.path.join(output_root, model_name)
#     #      os.makedirs(output_dir, exist_ok=True)
#     #      output_base = os.path.join(output_dir, model_name)
#     #      try:
#     #          render_step_model(step_file, output_base)
#     #      except Exception as e:
#     #          print(f"[!] Failed: {step_file} | {e}")

def batch_render_all(input_root, output_root):
    os.makedirs(output_root, exist_ok=True)
    step_files = get_all_step_files(input_root)
    print(f"Found {len(step_files)} STEP files.")

    #Assuming step_files is already defined as a list of file paths
    for step_file in tqdm(step_files, desc="Rendering STEP files"):
        try:
            model_name = os.path.splitext(os.path.basename(step_file))[0]
            parent_folder = os.path.basename(os.path.dirname(step_file))
            output_dir = os.path.join(output_root, parent_folder)
            os.makedirs(output_dir, exist_ok=True)

            output_base = os.path.join(output_dir, model_name)

            # ✅ Skip rendering if all orbit views exist
            if has_rendered_all_views(output_base):
                print(f"[↪] Skipping already-rendered model: {model_name}")
                continue

            render_step_model(step_file, output_base)

        except Exception as e:
            print(f"[!] Failed: {step_file} | {e}")

def generate_face_membership_colors(face_ids):
    base_colors = [
        [1.00, 0.67, 0.60], [0.00, 0.00, 0.70], [1.00, 1.00, 0.40],
        [1.00, 0.60, 0.80], [0.10, 1.00, 1.00], [0.75, 0.70, 1.00],
        [1.00, 0.90, 0.70], [0.40, 0.70, 1.00], [0.60, 0.00, 0.30],
        [0.90, 1.00, 0.70], [0.40, 0.00, 0.40]
    ]
    n_faces = max(face_ids) + 1
    if n_faces > len(base_colors):
        import colorsys
        extra = [colorsys.hsv_to_rgb(i / (n_faces - 11) + 0.27, 1, 1) for i in range(n_faces - 11)]
        base_colors.extend(extra)
    return np.array([base_colors[fid] for fid in face_ids])


def generate_face_type_colors(face_types):
    type_colors = [
        [1.00, 0.47, 0.20], [1.00, 0.87, 0.20], [0.67, 1.00, 0.00],
        [0.00, 0.70, 0.58], [0.10, 1.00, 1.00], [0.00, 0.58, 0.70],
        [0.00, 0.33, 1.00], [0.50, 0.40, 1.00]
    ]
    return np.array([type_colors[ft] if ft < len(type_colors) else [0.5, 0.5, 0.5] for ft in face_types])

def get_face_type_code(face):
    surf = BRepAdaptor_Surface(face, True)
    surf_type = surf.GetType()
    return {
        GeomAbs_Plane: 0,
        GeomAbs_Cylinder: 1,
        GeomAbs_Cone: 2,
        GeomAbs_Sphere: 3,
        GeomAbs_Torus: 4,
        GeomAbs_SurfaceOfRevolution: 5,
        GeomAbs_SurfaceOfExtrusion: 6,
        GeomAbs_BezierSurface: 7,
        GeomAbs_BSplineSurface: 8
    }.get(surf_type, 7)  # fallback to Bezier for unknowns

def assign_face_colors(shape: TopoDS_Shape, mode="uniform"):
    faces = list(TopologyExplorer(shape).faces())
    color_map = []

    if mode == "uniform":
        rgb = [0.3, 0.8, 0.8]  # teal
        color_map = [Quantity_Color(*rgb, Quantity_TOC_RGB) for _ in faces]

    elif mode == "by_index":
        face_ids = list(range(len(faces)))
        colors = generate_face_membership_colors(face_ids)
        color_map = [Quantity_Color(*rgb, Quantity_TOC_RGB) for rgb in colors]

    elif mode == "by_type":
        face_types = [get_face_type_code(f) for f in faces]
        colors = generate_face_type_colors(face_types)
        color_map = [Quantity_Color(*rgb, Quantity_TOC_RGB) for rgb in colors]

    else:
        raise ValueError(f"Unsupported coloring mode: {mode}")

    return list(zip(faces, color_map))

# ---------- Entry Point ---------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=False, default=".", help="Directory containing STEP files")
    parser.add_argument("--input_file", required=False, help="Single STEP file to process")
    parser.add_argument("--output_dir", required=False, default="./output", help="Directory to save rendered images")
    args = parser.parse_args()

    warmup_renderer()
    
    if args.input_file:
        # Process single file
        os.makedirs(args.output_dir, exist_ok=True)
        model_name = os.path.splitext(os.path.basename(args.input_file))[0]
        output_base = os.path.join(args.output_dir, model_name)
        try:
            render_step_model(args.input_file, output_base)
            print(f"✅ Successfully rendered {args.input_file}")
        except Exception as e:
            print(f"❌ Failed to render {args.input_file}: {e}")
    else:
        # Process directory (existing functionality)
        batch_render_all(args.input_dir, args.output_dir)

    #shape = read_step_file("/media/aliSSD/BITS_Pilani/CAD_Research/Vinci4D_BITS/v4d-cad/Assets/step2/decoded_soap_another_morph_again.step")
    #print("Loaded shape type:", type(shape))
