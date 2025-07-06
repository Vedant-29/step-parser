from flask import Flask, request, jsonify
import os
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
)


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)