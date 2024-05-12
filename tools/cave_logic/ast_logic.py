import ast
import copy
import json
import re

from utils import array_to_object

# load nameNormaliser.json into object
nameNormaliser = {}
with open("./tools/cave_logic/Utils/nameNormaliser.json", 'r') as f:
    json_data = json.load(f)
    nameNormaliser.update(json_data)


def normalise_name(name):
    if not isinstance(name, str):
        return name
    return nameNormaliser[name] if name in nameNormaliser else name


def camel_to_spaces(s):
    return re.sub('([a-z])([A-Z])', r'\1 \2', s).title()


level_names = {
    "DKIsles": "Isles",
    "JungleJapes": "Japes",
    "AngryAztec": "Aztec",
    "FranticFactory": "Factory",
    "GloomyGalleon": "Galleon",
    "FungiForest": "Forest",
    "CrystalCaves": "Caves",
    "CreepyCastle": "Castle",
}

glitches = ["CanSTS", "phasewalk", "CanSkew", "CanPhaseswim",
            "phaseswim", "ledgeclip", "CanMoonkick", "CanOStandTBSNoclip",
            "CanAccessRNDRoom", "generalclips", "tbs", "spawn_snags", "advanced_platforming"]


def get_level_name(level):
    return level_names[level.replace(" ", "")]


def ast_to_json(node, params):
    if isinstance(node, ast.BoolOp):
        operator = "AND" if isinstance(node.op, ast.And) else "OR"
        conditions = [ast_to_json(operand, params) for operand in node.values]
        return {"combinator": operator, "rules": conditions}
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        operator = "NOT"
        conditions = [ast_to_json(node.operand, params)]
        return {"combinator": operator, "rules": conditions}
    elif isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.In) and hasattr(node.comparators[0], 'attr'):
        return {
            "Name": normalise_name(ast_to_json(node.left, params)["Name"]),
            node.comparators[0].attr: True
        }
    elif isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.In) and isinstance(node.comparators[0], ast.Tuple):
        return None
    elif isinstance(node, ast.Compare) and hasattr(node.comparators[0], 'attr') and node.comparators[0].attr == 'medal_cb_req':
        kong = node.left.slice.attr.lower()

        # cond1 = {
        #     "Name": normalise_name(node.left.value.value.attr),
        #     "Persona": kong,
        #     "Level": node.left.value.slice.attr,
        #     "Amount": f"{node.comparators[0].value.attr}.{node.comparators[0].attr}"
        # }
        cond2 = {
            "Name": normalise_name(kong)
        }
        shortlevel = get_level_name(node.left.value.slice.attr).lower()
        cond3 = {
            "Name": "_".join(["banana", shortlevel, kong]),
            "Amount": 40
        }
        return {"combinator": "AND", "rules": [cond3, cond2]}
    elif isinstance(node, ast.Compare) and not hasattr(node.left, 'func') and isinstance(node.ops[0], ast.GtE):
        return {
            "Name": normalise_name(f"{node.left.attr}"),
            "Amount": f"{node.comparators[0].value}",
        }
    elif isinstance(node, ast.Compare) and not hasattr(node.left, 'func'):
        if (node.left.value.attr == "settings"):
            return {"Name": node.left.attr, "Params": [node.comparators[0].attr, isinstance(node.ops[0], ast.Eq)],  "isFunction": True}
        return {
            "Name": normalise_name(f"{node.left.value.attr}.{node.left.attr}"),
            "Value": f"{node.comparators[0].value.id}.{node.comparators[0].attr}",
            "Equals": isinstance(node.ops[0], ast.Eq)
        }
    elif isinstance(node, ast.keyword):
        return {node.arg: ast_to_json(node.value, params)}
    elif isinstance(node, ast.Expr):
        return ast_to_json(node.value, params)
    elif isinstance(node, ast.List):
        return [ast_to_json(item, params) for item in node.elts]
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        args = node.args
        vals = [ast_to_json(item, params) for item in args]
        length = len(vals)

        if func_name == "Region":
            hint_name = vals[1]
            if (hint_name) == "Hideout Helm":
                hint_name = "Helm"

            return {
                "Name": vals[0],
                "HintName": hint_name,
                "Level": vals[2]['Name'],
                "Checks": array_to_object(vals[5]+vals[6]),
                "Neighbourhood": array_to_object(vals[7])
            }
        elif func_name == "LocationLogic":
            ll = {
                "Key": vals[0]['Name'],
                "Requires": vals[1]['Requires']
            }

            if length > 2:
                ll.update({"MiniGame": vals[2]})
            return ll
        elif func_name == "Event":
            e = {
                "Key": vals[0]['Name'],
                "Class": "Event",
                "Requires": vals[1]['Requires'],
                "Level": params['file_name'],
                "Rewards": {"Name": vals[0]['Name']}
            }
            if length > 2:
                e.update({"Other": vals[2:]})
            return e
        elif func_name == "TransitionFront":
            arrive = vals[0]['Name']
            depart = params["special2"]

            if (depart.startswith(params["file_name"]) and arrive.startswith(params["file_name"])):
                arrive = arrive.replace(params["file_name"], "")

            arrive = camel_to_spaces(arrive)
            # example is special2 = 'FranticFactoryStart'
            # vals[0]['Name'] = 'FranticFactoryMedals'
            # we want transition_name to be 'Frantic Factory Start to Medals'
            transition_name = camel_to_spaces(depart) + " to " + arrive
            tf = {
                "Key": vals[0]['Name'],
                "Name": transition_name,
                "Requires": vals[1]['Requires']
            }
            if length > 2:
                tf.update({"Name": vals[0]['Name']})
                tf.update({"Transition": vals[2]})
                tf.update({"Other": vals[3:]})
            return tf
        elif func_name == "Location":
            lo = {
                "Name": vals[1],
                "Level": vals[0]['Name'],
                "Types": vals[3]['Name'],
                "Class": "Check"
            }
            if length > 4:
                lo.update({"Persona": vals[4]})
            if (params['special2'] == "Rewards"):
                lo.update({"Rewards": vals[2]})
            return lo
        elif func_name == "ItemReference":

            return {
                "Key": normalise_name(vals[0]['Name']),
                "Name": vals[1],
                "AltNames": [],
                "Type": "Move"
            }
        elif func_name == "TransitionBack":
            tb = {
                "Key": vals[0]['Name'],
                "Name": vals[2],
                "Suffix": vals[1],
            }
            if length > 3:
                tb.update({"Reverse": vals[3]})
            return tb
        elif func_name == "ShufflableExit":
            lo = {
                "Key": params['special'],
                "Name": vals[0],
                "source": vals[1]['Name'],
                "target": vals[2]['Key'],
                "type": 'Neighbourhood',
                "targetType": "Location",
                "ReverseName":  vals[2]['Name'],
                "ReverseSuffix": vals[2]['Suffix'],
                "Transition": {
                    "Name": vals[0]
                }
            }

            if "Reverse" in vals[2]:
                lo.update({"Reverse": vals[2]['Reverse']['Name']})
            return lo
        elif func_name == "Collectible":
            key = params['special'] + vals[1]['Name'].capitalize() + \
                vals[0]['Name'].capitalize() + str(node.end_lineno)
            short_name = vals[1]['Name'].capitalize() + \
                " " + vals[0]['Name'].capitalize()
            if params['special2'] == "Location":
                return key

            reward_name = vals[0]['Name'] + "_" + \
                get_level_name(params['file_name']) + "_" + vals[1]['Name']
            lo = {
                "Name": short_name,
                "Key": key,
                "Rewards": {"Name": normalise_name(reward_name.lower()), "Amount": vals[4]},
                "Persona": vals[1],
                "Requires": vals[2]['Requires'],
                "Class": "Collectible",
                "Level": params['file_name']
                # "Coordinates": vals[3],
            }
            return lo
        elif func_name == "Minigame":
            vals = [ast_to_json(item, params) for item in node.keywords]
            # each value of the vals array is a single object
            # iterate over these and turn them into a single object
            minigame_obj = {}
            for val in vals:
                minigame_obj.update(val)
            length = len(vals)

            return {
                "Key": params['special'],
                "Name": minigame_obj['name'],
                "Requires": minigame_obj['logic']['Requires'],
                "Class": "Minigame",
                "Types": minigame_obj['group'],
            }
        elif func_name == "KasplatLocation":
            vals = [ast_to_json(item, params) for item in node.keywords]
            minigame_obj = {}
            for val in vals:
                minigame_obj.update(val)
            length = len(vals)

            req = True
            if 'additional_logic' in minigame_obj:
                req = minigame_obj['additional_logic']['Requires']

            vanilla = False
            if 'vanilla' in minigame_obj:
                vanilla = minigame_obj['vanilla']

            class_type = "Check" if vanilla else "Custom Check"
            key = minigame_obj['name'].replace(" ", "").replace(":", "")
            return {
                "Region": minigame_obj['region']['Name'],
                "Level": minigame_obj['map_id']['Name'],
                "Name": minigame_obj['name'],
                "Key": key,
                "Requires": req,
                "Class": class_type,
                "Persona": vals[2]['kong_lst']
            }
        elif func_name == "FairyData":
            vals = [ast_to_json(item, params) for item in node.keywords]
            minigame_obj = {}
            for val in vals:
                minigame_obj.update(val)
            length = len(vals)

            req = {"Name": "camera"}
            if 'logic' in minigame_obj:
                req = minigame_obj['logic']['Requires']

            vanilla = False
            if 'is_vanilla' in minigame_obj:
                vanilla = minigame_obj['is_vanilla']

            class_type = "Check" if vanilla else "Custom Check"
            key = minigame_obj['name'].replace(" ", "").replace(":", "")
            return {
                "Region": minigame_obj['region']['Name'],
                "Level": minigame_obj['map']['Name'],
                "Name": minigame_obj['name'],
                "Key": key,
                "Requires": req,
                "Class": class_type,
                "Types": "Fairy"
            }
        elif func_name == "CustomLocation":
            vals = [ast_to_json(item, params) for item in node.keywords]
            minigame_obj = {}
            for val in vals:
                minigame_obj.update(val)
            length = len(vals)

            req = True
            if 'logic' in minigame_obj:
                req = minigame_obj['logic']['Requires']

            key = minigame_obj['name'].replace(" ", "").replace(":", "")
            return {
                "Region": minigame_obj['logic_region']['Name'],
                "Level": minigame_obj['map']['Name'],
                "Name": minigame_obj['name'],
                "Key": key,
                "Requires": req,
                "Class": "Custom Check",
            }
        elif func_name == "ShopLocation":
            source = vals[3]['Name']
            target = vals[2]['Name']
            name = camel_to_spaces(source) + " to " + camel_to_spaces(target)
            key = source + target + "Exit"
            lo = {
                "Key": key.replace(" ", "").lower(),
                "Name": name,
                "source": source.lower(),
                "target": target.lower(),
                "type": 'Neighbourhood',
                "targetType": "Location"
            }

            return lo
        else:
            return None
    elif isinstance(node, ast.Call) and not (hasattr(node.func, 'id')):
        func_name = node.func.attr
        args = node.args
        length = len(args)

        # for each arg in args, return the value to the key "Value"
        parsed_value = [ast_to_json(item, params)
                        for item in args]
        parsed_params = []
        for item in parsed_value:
            if isinstance(item, dict) and len(item) == 1 and "Name" in item:
                parsed_params.append(item["Name"])
            else:
                parsed_params.append(item)

        lo = {"Name": func_name, "Params": parsed_params,  "isFunction": True}
        if func_name in glitches:
            lo["isGlitch"] = True
        return lo
    elif isinstance(node, ast.Call):
        return ast_to_json(node.func, params)
    elif isinstance(node, ast.Attribute):
        name = normalise_name(node.attr)
        if name in glitches:
            return {"Name": name, "isGlitch": True}
        return {"Name": name}
    elif isinstance(node, ast.BinOp):
        left = ast_to_json(node.left, params)
        right = ast_to_json(node.right, params)
        operator = node.op.__class__.__name__
        return {"Left": left, "Right": right, "Operator": operator}
    elif isinstance(node, ast.Name):
        return {"Name": normalise_name(node.id)}
    elif isinstance(node, ast.Lambda):
        return {"Requires": ast_to_json(node.body, params)}
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.NameConstant):
        return node.value
    elif isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Dict):
        # return [ast_to_json(item) for item in node.values]
        result = {}
        for key_node, value_node in zip(node.keys, node.values):
            if (params['special'] == "Collectibles"):

                new_params = copy.deepcopy(params)
                new_params['special'] = key_node.attr

                if params['special2'] == "Location":
                    collectible = {"Collectibles": ast_to_json(
                        value_node, new_params)}
                    result.update({key_node.attr: collectible})

                else:
                    # params['special2'] = 'Registry'
                    collectible = array_to_object(
                        ast_to_json(value_node, new_params))
                    result.update(collectible)
            elif (params['file_name'] == "Minigame"):
                new_params = copy.deepcopy(params)
                new_params['special'] = key_node.attr
                result.update(
                    {key_node.attr: ast_to_json(value_node, new_params)})
            elif (params['file_name'] == "ShufflableExit"):
                new_params = copy.deepcopy(params)
                new_params['special'] = key_node.attr
                result.update(
                    {key_node.attr: ast_to_json(value_node, new_params)})
            elif (params['special'] == "Regions"):
                new_params = copy.deepcopy(params)
                new_params['special2'] = key_node.attr
                result.update(
                    {key_node.attr: ast_to_json(value_node, new_params)})
            else:
                result.update({key_node.attr: ast_to_json(value_node, params)})
        return result
    elif isinstance(node, ast.AnnAssign):
        return {node.target.attr: ast_to_json(node.annotation)}
    elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
        return None
    elif isinstance(node, ast.Assign) and hasattr(node.targets[0], 'id') and node.targets[0].id in ('LogicRegions'):
        # NORMALLY THIS WOULD BE THE FIRST POINT OF ENTRY
        return ast_to_json(node.value, params)
    elif isinstance(node, ast.Assign):
        if hasattr(node.targets[0], 'attr') and (node.targets[0].attr in ('location_references')):
            return {"Items": array_to_object(ast_to_json(node.value, params))}
        if hasattr(node.targets[0], 'id') and (node.targets[0].id in ('MinigameRequirements')):
            return {"Minigames": ast_to_json(node.value, params)}
        if hasattr(node.targets[0], 'id') and (node.targets[0].id in ('ShufflableExits', "LocationListOriginal")):
            return {node.targets[0].id: ast_to_json(node.value, params)}
        if hasattr(node.targets[0], 'id') and (node.targets[0].id in ('KasplatLocationList')):
            locations = ast_to_json(node.value, params)
            merged_arrays = []
            for value in locations.values():
                merged_arrays.extend(value)
            return {"Kasplats":  merged_arrays}
        if hasattr(node.targets[0], 'id') and (node.targets[0].id in ('CustomLocations', "fairy_locations")):
            locations = ast_to_json(node.value, params)
            merged_arrays = []
            for value in locations.values():
                merged_arrays.extend(value)
            return {node.targets[0].id:  merged_arrays}
        if hasattr(node.targets[0], 'id') and (node.targets[0].id in ("available_shops")):
            # return turn the resulting array into object
            locations = ast_to_json(node.value, params)
            merged_arrays = []
            for value in locations.values():
                merged_arrays.extend(value)
            return {node.targets[0].id:  array_to_object(merged_arrays)}
        return None
    elif isinstance(node, ast.UnaryOp):
        return None
    elif isinstance(node, ast.FunctionDef):
        if (node.name == 'ShuffleMisc'):
            abc = [ast_to_json(item, params) for item in node.body]
            # remove  all the values in abc that are None
            abc = [x for x in abc if x is not None]
            return abc
        return None
    else:
        return None
