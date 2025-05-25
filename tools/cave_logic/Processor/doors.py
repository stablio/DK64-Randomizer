import json
import sys
import os
import inspect
import ast
import re
# Append the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../../../'))
sys.path.append(parent_dir)

from copy import deepcopy

from tools.cave_logic.Processor.Utils import parse_ast_by_separator, parse_ast_to_dict
from tools.cave_logic.ast_logic import ast_to_json
from randomizer.Enums.Levels import Levels
from randomizer.Enums.DoorType import DoorType
from randomizer.Lists.DoorLocations import door_locations,GetBossLobbyRegionIdForRegion
from randomizer.ShuffleDoors import level_to_name
from randomizer.Enums.Items import Items
from randomizer.Logic import RegionsOriginal

RegionList = deepcopy(RegionsOriginal)

def strip_name(name):
    return name.replace(" ", "").replace(":", "").replace("-", "").replace("'","").lower()

def door_to_edge(door, level):

    id =  "d-" + str(door.map) + "-" + strip_name(door.name)
    name = f"{level_to_name[level]} Hint Door: {door.name}"

    portal_region = RegionList[door.logicregion]

    edgeClass = "Check"
    edgeType = "Door"
    edgeTargetType= "Item"
    target = Items.NoItem.name


    req = parse_ast_by_separator(door.logic,  "logic = lambda l: ")
    req_ast = req.body[0].value
    req2 = ast_to_json(req_ast, {})

    requires = req2["Requires"] if req2 is not None else True

    return {
        "id": id,
        "Name": name,
        "source": door.logicregion.name.lower(),
        "target": target.lower(),
        "sourceType": "Region",
        "targetType": edgeTargetType,
        "Requires": requires,
        "Class":edgeClass,
        "Type": edgeType,

    }

def build_doors():
    edges = {}
    for level,doors in door_locations.items():
        for door in doors:
            edge = door_to_edge(door, level)
            edges[edge["id"]] = edge
    return edges

world = {
   "door_edges": build_doors()
}

with open('./tools/cave_logic/Deltas/door_edges.json', 'w') as json_file:
    json.dump(world, json_file, indent=4)