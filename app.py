from flask import Flask, request, jsonify, send_file
import os
import tempfile
import base64
from io import BytesIO
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.TopAbs import (
    TopAbs_VERTEX,
    TopAbs_EDGE,
    TopAbs_FACE,
    TopAbs_WIRE,
    TopAbs_SHELL,
    TopAbs_SOLID,
    TopAbs_COMPOUND,
    TopAbs_COMPSOLID,
)
from OCC.Core.TopExp import TopExp_Explorer, topexp_MapShapesAndAncestors
from OCC.Core.TopTools import (
    TopTools_ListOfShape,
    TopTools_ListIteratorOfListOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape,
)
from OCC.Core.TopoDS import (
    topods,
    TopoDS_Wire,
    TopoDS_Vertex,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Compound,
    TopoDS_CompSolid,
    topods_Edge,
    topods_Vertex,
    topods_Face,
    TopoDS_Iterator,
    TopoDS_Shape,
)

# Additional imports for rendering
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.gp import gp_Trsf, gp_Pnt, gp_Dir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_MakeVertex
from OCC.Core.Graphic3d import Graphic3d_TOSM_FRAGMENT, Graphic3d_NameOfMaterial, Graphic3d_MaterialAspect
from OCC.Display.OCCViewer import Viewer3d
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB, Quantity_NOC_RED
from OCC.Core.AIS import AIS_Shape
from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import (
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere,
    GeomAbs_Torus, GeomAbs_SurfaceOfRevolution, GeomAbs_SurfaceOfExtrusion,
    GeomAbs_BezierSurface, GeomAbs_BSplineSurface
)
import numpy as np
from math import cos, sin, radians
import zipfile
import glob

class WireExplorer(object):
    """
    Wire traversal
    """

    def __init__(self, wire):
        assert isinstance(wire, TopoDS_Wire), "not a TopoDS_Wire"
        self.wire = wire
        self.wire_explorer = BRepTools_WireExplorer(self.wire)
        self.done = False

    def _reinitialize(self):
        self.wire_explorer = BRepTools_WireExplorer(self.wire)
        self.done = False

    def _loop_topo(self, edges=True):
        if self.done:
            self._reinitialize()
        topologyType = topods_Edge if edges else topods_Vertex
        seq = []
        hashes = []  # list that stores hashes to avoid redundancy
        occ_seq = TopTools_ListOfShape()
        while self.wire_explorer.More():
            # loop edges
            if edges:
                current_item = self.wire_explorer.Current()
            # loop vertices
            else:
                current_item = self.wire_explorer.CurrentVertex()
            current_item_hash = current_item.__hash__()
            if not current_item_hash in hashes:
                hashes.append(current_item_hash)
                occ_seq.Append(current_item)
            self.wire_explorer.Next()

        # Convert occ_seq to python list
        occ_iterator = TopTools_ListIteratorOfListOfShape(occ_seq)
        while occ_iterator.More():
            topo_to_add = topologyType(occ_iterator.Value())
            seq.append(topo_to_add)
            occ_iterator.Next()
        self.done = True
        return iter(seq)

    def ordered_edges(self):
        return self._loop_topo(edges=True)

    def ordered_vertices(self):
        return self._loop_topo(edges=False)


class Topo(object):
    """
    Topology traversal
    """

    def __init__(self, myShape, ignore_orientation=False):
        self.myShape = myShape
        self.ignore_orientation = ignore_orientation

        # the topoFactory dicts maps topology types and functions that can
        # create this topology
        self.topoFactory = {
            TopAbs_VERTEX: topods.Vertex,
            TopAbs_EDGE: topods.Edge,
            TopAbs_FACE: topods.Face,
            TopAbs_WIRE: topods.Wire,
            TopAbs_SHELL: topods.Shell,
            TopAbs_SOLID: topods.Solid,
            TopAbs_COMPOUND: topods.Compound,
            TopAbs_COMPSOLID: topods.CompSolid,
        }

    def _loop_topo(
        self, topologyType, topologicalEntity=None, topologyTypeToAvoid=None
    ):
        topoTypes = {
            TopAbs_VERTEX: TopoDS_Vertex,
            TopAbs_EDGE: TopoDS_Edge,
            TopAbs_FACE: TopoDS_Face,
            TopAbs_WIRE: TopoDS_Wire,
            TopAbs_SHELL: TopoDS_Shell,
            TopAbs_SOLID: TopoDS_Solid,
            TopAbs_COMPOUND: TopoDS_Compound,
            TopAbs_COMPSOLID: TopoDS_CompSolid,
        }

        assert topologyType in topoTypes.keys(), "%s not one of %s" % (
            topologyType,
            topoTypes.keys(),
        )
        self.topExp = TopExp_Explorer()
        # use self.myShape if nothing is specified
        if topologicalEntity is None and topologyTypeToAvoid is None:
            self.topExp.Init(self.myShape, topologyType)
        elif topologicalEntity is None and topologyTypeToAvoid is not None:
            self.topExp.Init(self.myShape, topologyType, topologyTypeToAvoid)
        elif topologyTypeToAvoid is None:
            self.topExp.Init(topologicalEntity, topologyType)
        elif topologyTypeToAvoid:
            self.topExp.Init(topologicalEntity, topologyType, topologyTypeToAvoid)
        seq = []
        hashes = []  # list that stores hashes to avoid redundancy
        occ_seq = TopTools_ListOfShape()
        while self.topExp.More():
            current_item = self.topExp.Current()
            current_item_hash = current_item.__hash__()

            if not current_item_hash in hashes:
                hashes.append(current_item_hash)
                occ_seq.Append(current_item)

            self.topExp.Next()
        # Convert occ_seq to python list
        occ_iterator = TopTools_ListIteratorOfListOfShape(occ_seq)
        while occ_iterator.More():
            topo_to_add = self.topoFactory[topologyType](occ_iterator.Value())
            seq.append(topo_to_add)
            occ_iterator.Next()

        if self.ignore_orientation:
            # filter out those entities that share the same TShape
            # but do *not* share the same orientation
            filter_orientation_seq = []
            for i in seq:
                _present = False
                for j in filter_orientation_seq:
                    if i.IsSame(j):
                        _present = True
                        break
                if _present is False:
                    filter_orientation_seq.append(i)
            return filter_orientation_seq
        else:
            return iter(seq)

    def faces(self):
        """loops over all faces"""
        return self._loop_topo(TopAbs_FACE)

    def edges(self):
        """loops over all edges"""
        return self._loop_topo(TopAbs_EDGE)

    def vertices(self):
        """loops over all vertices"""
        return self._loop_topo(TopAbs_VERTEX)

    def wires(self):
        """loops over all wires"""
        return self._loop_topo(TopAbs_WIRE)

    def shells(self):
        """loops over all shells"""
        return self._loop_topo(TopAbs_SHELL, None)

    def solids(self):
        """loops over all solids"""
        return self._loop_topo(TopAbs_SOLID, None)

    def compounds(self):
        """loops over all compounds"""
        return self._loop_topo(TopAbs_COMPOUND)

    def edges_from_face(self, face):
        """Get edges from a face"""
        return self._loop_topo(TopAbs_EDGE, face)

    def vertices_from_edge(self, edge):
        """Get vertices from an edge"""
        return self._loop_topo(TopAbs_VERTEX, edge)

    def wires_from_face(self, face):
        """Get wires from a face"""
        return self._loop_topo(TopAbs_WIRE, face)

    def ordered_vertices_from_wire(self, wire):
        """Get ordered vertices from wire"""
        we = WireExplorer(wire)
        return we.ordered_vertices()

    def ordered_edges_from_wire(self, wire):
        """Get ordered edges from wire"""
        we = WireExplorer(wire)
        return we.ordered_edges()


# === Rendering Configuration === #
IMAGE_SIZE = (1280, 960)
RENDERS_FOLDER = './renders'
os.makedirs(RENDERS_FOLDER, exist_ok=True)

# View directions for orbit rendering
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

def get_face_type_code(face):
    """Get surface type code for face coloring"""
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

def generate_face_membership_colors(face_ids):
    """Generate colors for face membership visualization"""
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
    """Generate colors for face type visualization"""
    type_colors = [
        [1.00, 0.47, 0.20], [1.00, 0.87, 0.20], [0.67, 1.00, 0.00],
        [0.00, 0.70, 0.58], [0.10, 1.00, 1.00], [0.00, 0.58, 0.70],
        [0.00, 0.33, 1.00], [0.50, 0.40, 1.00]
    ]
    return np.array([type_colors[ft] if ft < len(type_colors) else [0.5, 0.5, 0.5] for ft in face_types])

def assign_face_colors(shape: TopoDS_Shape, mode="uniform"):
    """Assign colors to faces based on the specified mode"""
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

def render_step_model(shape, output_dir, model_name, render_options=None):
    """Render STEP model to multiple view images"""
    if render_options is None:
        render_options = {
            'face_coloring_mode': 'uniform',
            'show_edges': True,
            'show_vertices': True,
            'num_orbit_views': 12
        }
    
    # Normalize shape
    shape = normalize_shape(shape)
    
    # Create renderer
    renderer = Viewer3d()
    renderer.Create()
    renderer.SetSize(*IMAGE_SIZE)
    renderer.set_bg_gradient_color([255, 255, 255], [255, 255, 255])
    renderer.SetModeShaded()
    renderer.View.SetShadingModel(Graphic3d_TOSM_FRAGMENT)

    # Render faces with coloring
    face_coloring_mode = render_options.get('face_coloring_mode', 'uniform')
    for face, color in assign_face_colors(shape, mode=face_coloring_mode):
        face_ais = AIS_Shape(face)
        face_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
        face_ais.SetTransparency(0.2)  # subtle transparency
        renderer.Context.SetColor(face_ais, color, False)
        renderer.Context.Display(face_ais, False)

    # Render edges if requested
    if render_options.get('show_edges', True):
        edge_color = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
        for edge in TopologyExplorer(shape).edges():
            edge_ais = AIS_Shape(edge)
            edge_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
            edge_ais.SetWidth(4.0)  # thicker edges
            renderer.Context.SetColor(edge_ais, edge_color, False)
            renderer.Context.Display(edge_ais, False)

    # Render vertices if requested
    if render_options.get('show_vertices', True):
        vertex_color = Quantity_Color(Quantity_NOC_RED)
        for vertex in TopologyExplorer(shape).vertices():
            pnt = BRep_Tool.Pnt(vertex)  # Extract gp_Pnt from TopoDS_Vertex
            vertex_shape = BRepBuilderAPI_MakeVertex(pnt).Shape()
            vertex_ais = AIS_Shape(vertex_shape)
            vertex_ais.SetMaterial(Graphic3d_MaterialAspect(Graphic3d_NameOfMaterial.Graphic3d_NOM_PLASTIC))
            renderer.Context.SetColor(vertex_ais, vertex_color, False)
            renderer.Context.Display(vertex_ais, False)
            vertex_ais.SetWidth(25.0)  # This controls visual size in screen space

    renderer.FitAll()
    renderer.Repaint()

    # Generate orbit views
    rendered_files = []
    radius = 3.0
    inclination_deg = 45
    inclination_rad = radians(inclination_deg)
    center = gp_Pnt(0, 0, 0)
    
    num_views = render_options.get('num_orbit_views', 12)
    angle_step = 360 // num_views

    for i, theta_deg in enumerate(range(0, 360, angle_step)):
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

        filename = f"{model_name}_orbit_{i:02d}.png"
        filepath = os.path.join(output_dir, filename)
        renderer.View.Dump(filepath)
        rendered_files.append(filepath)

    return rendered_files

app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_face_data(face):
    """Extract triangulation data from a face"""
    # Mesh the face for triangulation
    BRepMesh_IncrementalMesh(face, 0.01)
    
    loc = TopLoc_Location()
    triangulation = BRep_Tool.Triangulation(face, loc)
    
    if triangulation:
        nodes = triangulation.Nodes()
        triangles = triangulation.Triangles()
        
        # Extract vertices
        vertices = []
        for i in range(nodes.Length()):
            node = nodes.Value(i + 1)
            vertices.append([node.X(), node.Y(), node.Z()])
        
        # Extract triangle indices
        indices = []
        for i in range(triangles.Length()):
            tri = triangles.Value(i + 1)
            indices.append([tri.Value(1) - 1, tri.Value(2) - 1, tri.Value(3) - 1])
        
        return {
            'vertices': vertices,
            'indices': indices
        }
    
    return None


def extract_edge_data(edge):
    """Extract curve data from an edge"""
    curve, first, last = BRep_Tool.Curve(edge)
    if curve:
        points = []
        # Sample 30 points along the curve
        for i in range(30):
            param = first + (last - first) * i / 29.0
            pnt = curve.Value(param)
            points.append([pnt.X(), pnt.Y(), pnt.Z()])
        
        return {
            'points': points,
            'length': BRep_Tool.CurveLength(edge) if hasattr(BRep_Tool, 'CurveLength') else 0
        }
    
    return None


def extract_vertex_data(vertex):
    """Extract point data from a vertex"""
    pnt = BRep_Tool.Pnt(vertex)
    return [pnt.X(), pnt.Y(), pnt.Z()]


@app.route('/parse-step', methods=['POST'])
def parse_step():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        # Read STEP file
        reader = STEPControl_Reader()
        status = reader.ReadFile(filepath)

        if status != IFSelect_RetDone:
            return jsonify({'error': 'Failed to read STEP file'}), 500

        reader.TransferRoot()
        shape = reader.OneShape()

        # Create topology explorer
        topo = Topo(shape)

        # Extract faces with detailed information
        faces_data = []
        for face in topo.faces():
            face_info = extract_face_data(face)
            if face_info:
                # Add topological information
                face_info['edges'] = []
                for edge in topo.edges_from_face(face):
                    edge_data = extract_edge_data(edge)
                    if edge_data:
                        face_info['edges'].append(edge_data)
                
                face_info['wires'] = []
                for wire in topo.wires_from_face(face):
                    wire_info = {
                        'ordered_edges': [],
                        'ordered_vertices': []
                    }
                    # Get ordered edges and vertices from wire
                    for edge in topo.ordered_edges_from_wire(wire):
                        edge_data = extract_edge_data(edge)
                        if edge_data:
                            wire_info['ordered_edges'].append(edge_data)
                    
                    for vertex in topo.ordered_vertices_from_wire(wire):
                        vertex_data = extract_vertex_data(vertex)
                        wire_info['ordered_vertices'].append(vertex_data)
                    
                    face_info['wires'].append(wire_info)
                
                faces_data.append(face_info)

        # Extract edges
        edges_data = []
        for edge in topo.edges():
            edge_info = extract_edge_data(edge)
            if edge_info:
                # Add vertex information
                edge_info['vertices'] = []
                for vertex in topo.vertices_from_edge(edge):
                    vertex_data = extract_vertex_data(vertex)
                    edge_info['vertices'].append(vertex_data)
                edges_data.append(edge_info)

        # Extract vertices
        vertices_data = []
        for vertex in topo.vertices():
            vertex_data = extract_vertex_data(vertex)
            vertices_data.append(vertex_data)

        # Extract higher-level topology
        solids_data = []
        for solid in topo.solids():
            solid_info = {
                'faces_count': len(list(topo._loop_topo(TopAbs_FACE, solid))),
                'edges_count': len(list(topo._loop_topo(TopAbs_EDGE, solid))),
                'vertices_count': len(list(topo._loop_topo(TopAbs_VERTEX, solid)))
            }
            solids_data.append(solid_info)

        shells_data = []
        for shell in topo.shells():
            shell_info = {
                'faces_count': len(list(topo._loop_topo(TopAbs_FACE, shell))),
                'edges_count': len(list(topo._loop_topo(TopAbs_EDGE, shell))),
                'vertices_count': len(list(topo._loop_topo(TopAbs_VERTEX, shell)))
            }
            shells_data.append(shell_info)

        wires_data = []
        for wire in topo.wires():
            wire_info = {
                'ordered_edges': [],
                'ordered_vertices': [],
                'edges_count': len(list(topo._loop_topo(TopAbs_EDGE, wire))),
                'vertices_count': len(list(topo._loop_topo(TopAbs_VERTEX, wire)))
            }
            
            # Get ordered topology from wire
            for edge in topo.ordered_edges_from_wire(wire):
                edge_data = extract_edge_data(edge)
                if edge_data:
                    wire_info['ordered_edges'].append(edge_data)
            
            for vertex in topo.ordered_vertices_from_wire(wire):
                vertex_data = extract_vertex_data(vertex)
                wire_info['ordered_vertices'].append(vertex_data)
            
            wires_data.append(wire_info)

        # Cleanup uploaded file
        os.remove(filepath)

        return jsonify({
            'topology': {
                'faces': faces_data,
                'edges': edges_data,
                'vertices': vertices_data,
                'wires': wires_data,
                'shells': shells_data,
                'solids': solids_data
            },
            'summary': {
                'faces_count': len(faces_data),
                'edges_count': len(edges_data),
                'vertices_count': len(vertices_data),
                'wires_count': len(wires_data),
                'shells_count': len(shells_data),
                'solids_count': len(solids_data)
            }
        })

    except Exception as e:
        # Cleanup uploaded file in case of error
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Failed to parse STEP file: {str(e)}'}), 500


@app.route('/render-step', methods=['POST'])
def render_step():
    """Render STEP file to images with various viewing angles"""
    print("[render-step] Received request", flush=True)
    file = request.files.get('file')
    if not file:
        print("[render-step] No file uploaded", flush=True)
        return jsonify({'error': 'No file uploaded'}), 400

    # Get render options from request
    render_options = {
        'face_coloring_mode': request.form.get('face_coloring_mode', 'uniform'),
        'show_edges': request.form.get('show_edges', 'true').lower() == 'true',
        'show_vertices': request.form.get('show_vertices', 'true').lower() == 'true',
        'num_orbit_views': int(request.form.get('num_orbit_views', '12')),
        'return_format': request.form.get('return_format', 'zip')  # 'zip' or 'json'
    }
    print(f"[render-step] Render options: {render_options}", flush=True)

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    print(f"[render-step] Saving uploaded file to: {filepath}", flush=True)
    file.save(filepath)

    try:
        # Read STEP file
        print(f"[render-step] Reading STEP file: {filepath}", flush=True)
        reader = STEPControl_Reader()
        status = reader.ReadFile(filepath)

        if status != IFSelect_RetDone:
            print(f"[render-step] Failed to read STEP file: {filepath}", flush=True)
            return jsonify({'error': 'Failed to read STEP file'}), 500

        print(f"[render-step] STEP file read successfully: {filepath}", flush=True)
        reader.TransferRoot()
        shape = reader.OneShape()

        # Create unique output directory for this render
        model_name = os.path.splitext(file.filename)[0]
        render_id = f"{model_name}_{int(os.urandom(4).hex(), 16)}"
        output_dir = os.path.join(RENDERS_FOLDER, render_id)
        print(f"[render-step] Creating output directory: {output_dir}", flush=True)
        os.makedirs(output_dir, exist_ok=True)

        # Render the model
        print(f"[render-step] Starting rendering for model: {model_name}", flush=True)
        rendered_files = render_step_model(shape, output_dir, model_name, render_options)
        print(f"[render-step] Rendering complete. Rendered files: {rendered_files}", flush=True)

        # Cleanup uploaded file
        print(f"[render-step] Removing uploaded file: {filepath}", flush=True)
        os.remove(filepath)

        # Return based on requested format
        if render_options['return_format'] == 'zip':
            # Create ZIP file with all rendered images
            zip_path = os.path.join(output_dir, f"{model_name}_renders.zip")
            print(f"[render-step] Creating ZIP archive: {zip_path}", flush=True)
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for rendered_file in rendered_files:
                    zipf.write(rendered_file, os.path.basename(rendered_file))
            print(f"[render-step] Returning ZIP file: {zip_path}", flush=True)
            return send_file(zip_path, as_attachment=True, download_name=f"{model_name}_renders.zip")

        else:  # return_format == 'json'
            # Convert images to base64 and return in JSON
            images_data = []
            for rendered_file in rendered_files:
                with open(rendered_file, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    images_data.append({
                        'filename': os.path.basename(rendered_file),
                        'data': img_data
                    })
            print(f"[render-step] Returning {len(images_data)} images as JSON", flush=True)
            # Cleanup render directory
            import shutil
            print(f"[render-step] Removing render directory: {output_dir}", flush=True)
            shutil.rmtree(output_dir)

            return jsonify({
                'model_name': model_name,
                'render_options': render_options,
                'images': images_data,
                'count': len(images_data)
            })

    except Exception as e:
        # Cleanup uploaded file and render directory in case of error
        print(f"[render-step] Exception occurred: {str(e)}", flush=True)
        if os.path.exists(filepath):
            print(f"[render-step] Removing uploaded file due to error: {filepath}", flush=True)
            os.remove(filepath)
        if 'output_dir' in locals() and os.path.exists(output_dir):
            import shutil
            print(f"[render-step] Removing output directory due to error: {output_dir}", flush=True)
            shutil.rmtree(output_dir)
        return jsonify({'error': f'Failed to render STEP file: {str(e)}'}), 500


@app.route('/render-step-batch', methods=['POST'])
def render_step_batch():
    """Render multiple STEP files in batch"""
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files uploaded'}), 400

    # Get render options from request
    render_options = {
        'face_coloring_mode': request.form.get('face_coloring_mode', 'uniform'),
        'show_edges': request.form.get('show_edges', 'true').lower() == 'true',
        'show_vertices': request.form.get('show_vertices', 'true').lower() == 'true',
        'num_orbit_views': int(request.form.get('num_orbit_views', '12'))
    }

    batch_id = f"batch_{int(os.urandom(4).hex(), 16)}"
    batch_output_dir = os.path.join(RENDERS_FOLDER, batch_id)
    os.makedirs(batch_output_dir, exist_ok=True)

    results = []
    
    for file in files:
        if not file.filename:
            continue
            
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        try:
            # Read STEP file
            reader = STEPControl_Reader()
            status = reader.ReadFile(filepath)

            if status != IFSelect_RetDone:
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': 'Failed to read STEP file'
                })
                continue

            reader.TransferRoot()
            shape = reader.OneShape()

            # Create output directory for this model
            model_name = os.path.splitext(file.filename)[0]
            model_output_dir = os.path.join(batch_output_dir, model_name)
            os.makedirs(model_output_dir, exist_ok=True)

            # Render the model
            rendered_files = render_step_model(shape, model_output_dir, model_name, render_options)

            results.append({
                'filename': file.filename,
                'status': 'success',
                'rendered_count': len(rendered_files),
                'model_dir': model_name
            })

        except Exception as e:
            results.append({
                'filename': file.filename,
                'status': 'error',
                'error': str(e)
            })
        finally:
            # Cleanup uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    # Create ZIP file with all batch results
    zip_path = os.path.join(batch_output_dir, f"{batch_id}_renders.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(batch_output_dir):
            for file in files:
                if file.endswith('.png'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, batch_output_dir)
                    zipf.write(file_path, arcname)

    return send_file(zip_path, as_attachment=True, download_name=f"{batch_id}_renders.zip")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the service is running"""
    return jsonify({
        'status': 'healthy',
        'service': 'STEP Parser & Renderer',
        'endpoints': {
            'parse': '/parse-step',
            'render': '/render-step',
            'batch_render': '/render-step-batch',
            'test_rendering': '/test-rendering',
            'test_opencascade': '/test-opencascade'
        }
    })


@app.route('/test-rendering', methods=['GET'])
def test_rendering():
    """Test the rendering capability with Xvfb"""
    try:
        print("[test-rendering] Starting test...", flush=True)
        print(f"[test-rendering] DISPLAY env var: {os.environ.get('DISPLAY', 'Not set')}", flush=True)
        print(f"[test-rendering] XAUTHORITY env var: {os.environ.get('XAUTHORITY', 'Not set')}", flush=True)
        
        # Import the viewer class
        print("[test-rendering] Importing Viewer3d...", flush=True)
        from OCC.Display.OCCViewer import Viewer3d
        print("[test-rendering] Viewer3d imported successfully", flush=True)
        
        # Test if we can create a viewer (this will fail if X11/Xvfb is not working)
        print("[test-rendering] Creating Viewer3d instance...", flush=True)
        test_viewer = Viewer3d()
        print("[test-rendering] Viewer3d instance created successfully", flush=True)
        
        print(">>> DISPLAY:", os.environ.get("DISPLAY"))
        print("[test-rendering] Calling Create() method...", flush=True)
        test_viewer.Create()
        print("[test-rendering] Create() method completed successfully", flush=True)
        
        print("[test-rendering] Setting size to 256x256...", flush=True)
        test_viewer.SetSize(256, 256)
        print("[test-rendering] Size set successfully", flush=True)
        
        print("[test-rendering] Test completed successfully!", flush=True)
        return jsonify({
            'status': 'success',
            'message': 'Rendering system is working correctly',
            'display': os.environ.get('DISPLAY', 'Not set'),
            'xvfb_status': 'OK'
        })
    except Exception as e:
        print(f"[test-rendering] Exception caught: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(f"[test-rendering] Full traceback:\n{traceback.format_exc()}", flush=True)
        return jsonify({
            'status': 'error',
            'message': f'Rendering system error: {str(e)}',
            'display': os.environ.get('DISPLAY', 'Not set'),
            'xvfb_status': 'Failed'
        }), 500


@app.route('/test-opencascade', methods=['GET'])
def test_opencascade():
    """Test basic OpenCASCADE functionality without viewer"""
    try:
        print("[test-opencascade] Starting OpenCASCADE test...", flush=True)
        
        # Test basic imports
        print("[test-opencascade] Testing basic imports...", flush=True)
        from OCC.Core.gp import gp_Pnt, gp_Dir
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        print("[test-opencascade] Basic imports successful", flush=True)
        
        # Test creating a simple geometry
        print("[test-opencascade] Creating simple geometry...", flush=True)
        point = gp_Pnt(0.0, 0.0, 0.0)
        vertex = BRepBuilderAPI_MakeVertex(point)
        shape = vertex.Shape()
        print("[test-opencascade] Simple geometry created successfully", flush=True)
        
        # Test STEP reader (without file)
        print("[test-opencascade] Testing STEP reader creation...", flush=True)
        from OCC.Core.STEPControl import STEPControl_Reader
        reader = STEPControl_Reader()
        print("[test-opencascade] STEP reader created successfully", flush=True)
        
        # Test topology utils
        print("[test-opencascade] Testing topology utils...", flush=True)
        from OCC.Extend.TopologyUtils import TopologyExplorer
        topo = TopologyExplorer(shape)
        vertices = list(topo.vertices())
        print(f"[test-opencascade] Found {len(vertices)} vertices", flush=True)
        
        print("[test-opencascade] All OpenCASCADE tests passed!", flush=True)
        return jsonify({
            'status': 'success',
            'message': 'Basic OpenCASCADE functionality working',
            'tests_passed': ['imports', 'geometry_creation', 'step_reader', 'topology']
        })
        
    except Exception as e:
        print(f"[test-opencascade] Exception: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(f"[test-opencascade] Traceback:\n{traceback.format_exc()}", flush=True)
        return jsonify({
            'status': 'error',
            'message': f'OpenCASCADE error: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)