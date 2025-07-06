from flask import Flask, request, jsonify
import os
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopoDS import topods_Face, topods_Edge, topods_Vertex
from OCC.Core.gp import gp_Pnt

app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/parse-step', methods=['POST'])
def parse_step():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)

    if status != IFSelect_RetDone:
        return jsonify({'error': 'Failed to read STEP file'}), 500

    reader.TransferRoot()
    shape = reader.OneShape()

    # Mesh the shape for face triangulation
    BRepMesh_IncrementalMesh(shape, 0.01)

    faces = []
    edges = []
    vertices = []

    # Extract faces
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods_Face(exp.Current())

        # You *must* pass a real TopLoc_Location:
        loc = TopLoc_Location()            # or face.Location()
        triangulation = BRep_Tool.Triangulation(face, loc)

        if triangulation:                  # may still be None if meshing failed
            nodes      = triangulation.Nodes()
            triangles  = triangulation.Triangles()
            verts = [[nodes.Value(i+1).X(),
                    nodes.Value(i+1).Y(),
                    nodes.Value(i+1).Z()] for i in range(nodes.Length())]
            tris  = [[t.Value(1)-1, t.Value(2)-1, t.Value(3)-1]
                    for t in triangles]
            faces.append({'vertices': verts, 'indices': tris})

        exp.Next()

    # Extract edges
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        edge = topods_Edge(exp.Current())
        curve, first, last = BRep_Tool.Curve(edge)
        if curve:
            points = []
            for i in range(30):
                param = first + (last - first) * i / 29.0
                pnt = curve.Value(param)
                points.append([pnt.X(), pnt.Y(), pnt.Z()])
            edges.append(points)
        exp.Next()

    # Extract vertices
    exp = TopExp_Explorer(shape, TopAbs_VERTEX)
    while exp.More():
        vertex = topods_Vertex(exp.Current())
        pnt = BRep_Tool.Pnt(vertex)
        vertices.append([pnt.X(), pnt.Y(), pnt.Z()])
        exp.Next()

    return jsonify({
        'faces': faces,
        'edges': edges,
        'vertices': vertices
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)