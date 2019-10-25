import os
import json

DATA_PATH = os.getenv('DATA_PATH')
CODE_PATH = os.getenv('CODE_PATH')
FIGURE_PATH = os.getenv('FIGURE_PATH')

data_path = os.path.join("d3map", "data")
data_path2 = os.path.join(FIGURE_PATH, "main", "d3map", "data")


def resetCoords():
    xyCoordsPath = os.path.join(data_path, "xycoords.json")
    with open(xyCoordsPath, 'r') as fr:
        xycoords = json.load(fr)
    xyCoordsLabPath = os.path.join(data_path, "xycoords_lab.json")
    with open(xyCoordsLabPath, 'r') as fr:
        xycoords_lab = json.load(fr)

    baseGraphPath = os.path.join(data_path, "graph.json")
    with open(baseGraphPath, 'r') as fr:
        graph = json.load(fr)
    newnodes = []
    labels = []
    for el in graph['nodes']:
        el['coords'] = xycoords[el["shortNm"]]
        newnodes.append(el)
        if el["shortNm"] in xycoords_lab:
            labels.append({'shortNm':el["shortNm"],
                           'coords':xycoords_lab[el["shortNm"]]})
    graph['nodes'] = newnodes
    graph['labels'] = labels

    graphPath_out = os.path.join(data_path, "graph2.json")
    with open(graphPath_out, 'w') as fw:
        json.dump(graph, fw)


def addDataNodes(graph, field, data, gkey="nodes"):
    for el in graph[gkey]:
        if el["shortNm"] in data:
            el[field] = data[el["shortNm"]]
    return graph