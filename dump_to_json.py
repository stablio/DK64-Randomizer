"""Dump information from various custom location files into a json format in tools/dump."""

import inspect
import json
import os
import sys
import subprocess
from copy import deepcopy
from enum import IntEnum, auto
import ast


from randomizer.Enums.Levels import Levels
from randomizer.Lists.BananaCoinLocations import BananaCoinGroupList
from randomizer.Lists.CustomLocations import CustomLocations
from randomizer.Lists.DoorLocations import door_locations
from randomizer.Lists.FairyLocations import fairy_locations
from randomizer.Lists.KasplatLocations import KasplatLocationList
from randomizer.Enums.Maps import Maps
from randomizer.Logic import RegionsOriginal

from randomizer.LogicClasses import ast_to_json

# USAGE OF FILE
# - python ./dumper.py {format} {desired-files}
# Eg: python ./dumper.py json cb door fairy
# Valid formats: "csv", "json", "md"

# Create an empty dictionary to store the data
data = {}

# ast_tree = ast.parse('self.deathwarp = TransitionFront(deathwarp, lambda l: True)')
# ast_json = ast_to_json(ast_tree.body[0], None)

# print(ast_json)

#Iterate over the regions
for region_key, region_value in list(RegionsOriginal.items())[:100]:
    print(region_key)
    if(region_key.name == "DonkeyTemple"):
        print(region_value)
    # Convert the region value to a dictionary
    abc = region_value.to_dict()

    # Add the region data to the main dictionary
    data[region_key] = abc

# Write the data to the json file
with open('./tools/dumps/abc.json', 'w') as f:
    json.dump(data, f)