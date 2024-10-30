from copy import deepcopy
import json

import sys
import os
import inspect
import ast
import re
# Append the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(parent_dir)

from randomizer.Lists.Item import ItemList
from randomizer.Logic import RegionsOriginal
from randomizer.Enums.Items import Items
from randomizer.Enums.DoorType import DoorType
from randomizer.Enums.Levels import Levels
from randomizer.Enums.MoveTypes import MoveTypes
from randomizer.Enums.Types import Types
from randomizer.Enums.Events import Events


from ast_logic import ast_to_json

edges = {}


def strip_name(name):
    return name.replace(" ", "").replace(":", "").replace("-", "").replace("'", "").lower()


def item_to_node(id, item):

    itemType = item.type.name

    if(item.type == Types.Shop):
        itemType = "Move"

    return {
        "Key": id.name,
        "Name": item.name,
        "AltNames": [],
        "Type": itemType
    }


for id, item in ItemList.items():

    if (id == Items.TestItem):
        continue

    edges[id.name] = item_to_node(id, item)

def split_camel_case(name):
    return ' '.join([x for x in re.split('([A-Z][a-z]+)', name) if x])

# Treat events as items albeit there's not much metadata
for id in Events:

    # in the absence of a name lets just split the name by camel case
    # we can fix this in the overrides later
    edges[id.name] = {
        "Key": id.name,
        "Name": split_camel_case(id.name),
        "AltNames": [],
        "Type": "Event"
    }

world = {
    "item_nodes": edges
}

with open('./tools/cave_logic/Deltas/item_nodes.json', 'w') as json_file:
    json.dump(world, json_file, indent=4)
