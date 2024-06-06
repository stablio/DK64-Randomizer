"""Contains classes used in the logic system."""

from __future__ import annotations

import inspect
import ast

from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple, Union

from randomizer.Enums.Kongs import Kongs
from randomizer.Enums.Levels import Levels
from randomizer.Enums.Regions import Regions
from randomizer.Enums.Time import Time
from randomizer.Enums.Locations import Locations
from randomizer.Lists.EnemyTypes import enemy_location_list

if TYPE_CHECKING:
    from randomizer.Enums.Collectibles import Collectibles
    from randomizer.Enums.Events import Events
    from randomizer.Enums.Locations import Locations
    from randomizer.Enums.MinigameType import MinigameType
    from randomizer.Enums.Transitions import Transitions
    from randomizer.Logic import LogicVarHolder


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
            "Name": ast_to_json(node.left, params)["Name"],
            node.comparators[0].attr: True
        }
    elif isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.In) and isinstance(node.comparators[0], ast.Tuple):
        return None
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
            "Name": f"{node.left.attr}",
            "Amount": f"{node.comparators[0].value}",
        }
    elif isinstance(node, ast.Compare) and not hasattr(node.left, 'func'):
        if (node.left.value.attr == "settings"):
            return {"Name": node.left.attr, "Params": [node.comparators[0].attr, isinstance(node.ops[0], ast.Eq)],  "isFunction": True}
        return {
            "Name": f"{node.left.value.attr}.{node.left.attr}",
            "Value": f"{node.comparators[0].value.id}.{node.comparators[0].attr}",
            "Equals": isinstance(node.ops[0], ast.Eq)
        }
    elif isinstance(node, ast.Tuple):
        return [ast_to_json(item, params) for item in node.elts]
    elif isinstance(node, ast.keyword):
        return {node.arg: ast_to_json(node.value, params)}
    elif isinstance(node, ast.Expr):
        return ast_to_json(node.value, params)
    elif isinstance(node, ast.List):
        return [ast_to_json(item, params) for item in node.elts]
    elif isinstance(node, ast.Dict):
        # return [ast_to_json(item) for item in node.values]
        result = {}

        for key_node, value_node in zip(node.keys, node.values):
            result.update({key_node.attr: ast_to_json(value_node, params)})

        if (params is None):
            return result

        if ("type" in params):
            if params["type"] == "transition":
                return result
            if params["type"] == "fullregion":
                return result[node.keys[0].attr][4][1]

        return None
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        args = node.args
        vals = [ast_to_json(item, params) for item in args]

        # vals = [ast.unparse(item) for item in args]
        length = len(vals)

        if (params is None):
            return vals[1]

        return vals
        # return {"Name": func_name, "Params": vals, "Length": length}
    elif isinstance(node, ast.Call):
        return ast_to_json(node.func, params)
    elif isinstance(node, ast.Attribute):
        name = node.attr
        if hasattr(node.value, 'id'):
            name = f"{node.value.id}.{name}"
        if hasattr(node.value, 'attr'):
            name = f"{node.value.attr}.{name}"
        return name
    elif isinstance(node, ast.Name):
        return {"Name": node.id}
    elif isinstance(node, ast.Lambda):
        return ast.unparse(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.NameConstant):
        return node.value
    elif isinstance(node, ast.AnnAssign):
        return {node.target.attr: ast_to_json(node.annotation)}
    elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
        return None
    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        return ast_to_json(node.value, params)
    elif isinstance(node, ast.UnaryOp):
        return None
    else:
        return None


def get_class_that_defined_method(meth):
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # fallback to __objclass__


def parse_logic_raw(func: Callable):
    logic_raw = " ".join([x.strip() for x in inspect.getsourcelines(
                func)[0]]).replace("\n", "").replace("\t", "")
    logic_raw = logic_raw.strip()

    params = None

    try:
        # Try to parse the entire string
        ast_tree = ast.parse(logic_raw)
    except SyntaxError:
        cls = get_class_that_defined_method(func)

       
        try:
            if cls is Region: 
                ast_tree = ast.parse('TransitionFront(' + logic_raw)
                params = {"type": "transition"}
                print("Reparsing appening TransitionFront.")
        except SyntaxError:
            print("Reparsing with bracket at the start failed.")
            # If a SyntaxError is raised, check if the string contains a colon
            if ':' in logic_raw:
                try:
                    parsed = ast.parse('{' + logic_raw + '}')
                    ast_tree = parsed
                    params = {"type": "fullregion"}

                    print("Reparsing with dictionary braces was successful.")
                except SyntaxError:
                    # If a SyntaxError is raised, the value is likely the problem
                    print("The value is likely causing the syntax error.")

    return ast_to_json(ast_tree.body[0], params)


def format_logic_lambda(func: Callable) -> str:
    """Convert a function to a string."""
    ast_json = parse_logic_raw(func)
    return ast_json


class LocationLogic:
    """Logic for a location."""

    def __init__(self, id: Union[int, Locations], logic: Callable, bonusBarrel: Optional[MinigameType] = None, isAuxiliary: bool = False) -> None:
        """Initialize with given parameters."""
        self.id = id
        self.logic = logic  # Lambda function for accessibility
        if id >= Locations.JapesMainEnemy_Start and id <= Locations.IslesMainEnemy_LowerFactoryPath1:
            # Handle enemy logic
            self.logic = lambda l: logic(
                l) and enemy_location_list[id].canDropItem(l)
        self.bonusBarrel = bonusBarrel  # Uses MinigameType enum
        self.isAuxiliaryLocation = (
            # For when the Location needs to be in a region but not count as in the region (used for locations that need to be accessible in different regions depending on settings)
            isAuxiliary
        )

    def to_dict(self, includeId: bool = False) -> dict:
        """Convert the class to a dictionary."""

        bonusBarrel_dict = None
        if self.bonusBarrel is not None:
            bonusBarrel_dict = self.bonusBarrel

        as_dict = {
            "name": self.id.name,
            "logic": format_logic_lambda(self.logic),
            "bonusBarrel": bonusBarrel_dict,
            "isAuxiliaryLocation": self.isAuxiliaryLocation,
        }
        if includeId:
            as_dict["id"] = self.id.value
        return as_dict


class Event:
    """Event within a region.

    Events act as statically placed items
    For example, if Lanky must press a button in region x to open something in region y,
    that can be represented as a button press event in region x which is checked for in region y.
    """

    def __init__(self, name: Events, logic: Callable) -> None:
        """Initialize with given parameters."""
        self.name = name
        self.logic = logic  # Lambda function for accessibility

    def to_dict(self) -> dict:
        """Convert the class to a dictionary."""
        return {"name": self.name, "logic": format_logic_lambda(self.logic)}


class Collectible:
    """Class used for colored bananas and banana coins."""

    def __init__(
        self,
        type: Collectibles,
        kong: Kongs,
        logic: Callable,
        coords: Optional[Tuple[float, float, float]] = None,
        amount: int = 1,
        enabled: bool = True,
        vanilla: bool = True,
        name: str = "vanilla",
        locked: bool = False,
    ) -> None:
        """Initialize with given parameters."""
        self.type = type
        self.kong = kong
        self.logic = logic
        self.amount = amount
        # None for vanilla collectibles for now. For custom, use (x,y,z) format
        self.coords = coords
        self.added = False
        self.enabled = enabled
        self.vanilla = vanilla
        self.name = name
        self.locked = locked


class Region:
    """Region contains shufflable locations, events, and transitions to other regions."""

    def __init__(
        self,
        name: str,
        hint_name: str,
        level: Levels,
        tagbarrel: bool,
        deathwarp: Optional[Union[int, TransitionFront, Regions]],
        locations: List[Union[LocationLogic, Any]],
        events: List[Union[Event, Any]],
        transitionFronts: List[Union[TransitionFront, Any]],
        restart: Optional[Union[Transitions, int]] = None,
    ) -> None:
        """Initialize with given parameters."""
        self.name = name
        self.hint_name = hint_name
        self.level = level
        self.tagbarrel = tagbarrel
        self.deathwarp = None
        self.locations = locations
        self.events = events
        # In the context of a region, exits are how you leave the region
        self.exits = transitionFronts
        self.restart = restart

        self.dayAccess = [False] * 5
        self.nightAccess = [False] * 5

        # If possible to die in this region, add an exit to where dying will take you
        # deathwarp is also set to none in regions in which a deathwarp would take you to itself
        # Or if there is loading-zone-less free access to the region it would take you to already
        if deathwarp is not None:
            self.deathwarp = self.SetDeathWarp(deathwarp)

        self.ResetAccess()

    def SetDeathWarp(self, deathwarp: Optional[Union[int, TransitionFront, Regions]]) -> TransitionFront:
        # If possible to die in this region, add an exit to where dying will take you
        # deathwarp is also set to none in regions in which a deathwarp would take you to itself
        # Or if there is loading-zone-less free access to the region it would take you to already
        if deathwarp is not None:
            # If deathwarp is itself an exit class (necessary when deathwarp requires custom logic) just add it directly
            if isinstance(deathwarp, TransitionFront):
                return deathwarp
            else:
                # If deathwarp is -1, indicates to use the default value for it, which is the starting area of the level
                if deathwarp == -1:
                    deathwarp = self.GetDefaultDeathwarp()
                if deathwarp is not None:
                    if isinstance(deathwarp, Regions):
                        return TransitionFront(
                            deathwarp, lambda l: True)
                    else:
                        return TransitionFront(
                            Regions(deathwarp), lambda l: True)

    def ResetAccess(self) -> None:
        """Clear access variables set during search."""
        # Time access
        self.dayAccess = [False] * 5
        self.nightAccess = [False] * 5

    def GetDefaultDeathwarp(self) -> Regions:
        """Get the default deathwarp depending on the region's level."""
        if self.level == Levels.DKIsles:
            return Regions.IslesMain
        elif self.level == Levels.JungleJapes:
            return Regions.JungleJapesStart
        elif self.level == Levels.AngryAztec:
            return Regions.AngryAztecStart
        elif self.level == Levels.FranticFactory:
            return Regions.FranticFactoryStart
        elif self.level == Levels.GloomyGalleon:
            return Regions.GloomyGalleonStart
        elif self.level == Levels.FungiForest:
            return Regions.FungiForestStart
        elif self.level == Levels.CrystalCaves:
            return Regions.CrystalCavesMain
        elif self.level == Levels.CreepyCastle:
            return Regions.CreepyCastleMain
        elif self.level == Levels.HideoutHelm:
            return Regions.HideoutHelmEntry
        return Regions.GameStart

    def to_dict(self) -> dict:
        """Convert the class to a dictionary."""
        location_dicts = []
        for location in self.locations:
            location_dict = location.to_dict()
            location_dicts.append(location_dict)

        exit_dicts = []
        for transition in self.exits:
            transition_dict = transition.to_dict()
            exit_dicts.append(transition_dict)

        event_dicts = []
        for event in self.events:
            event_dict = event.to_dict()
            event_dicts.append(event_dict)

        deathwarp_dict = None
        if self.deathwarp is not None:
            deathwarp_dict = self.deathwarp.to_dict()

        return {
            "name": self.name,
            "hint_name": self.hint_name,
            "level": self.level.name,
            "tagbarrel": self.tagbarrel,
            "deathwarp": deathwarp_dict,
            "locations": location_dicts,
            "events": event_dicts,
            "exits": exit_dicts,
            "restart": self.restart,
            "dayAccess": self.dayAccess,
            "nightAccess": self.nightAccess,
        }


class TransitionBack:
    """The exited side of a transition between regions."""

    def __init__(self, regionId: Regions, exitName: str, spoilerName: str, reverse: Optional[Transitions] = None) -> None:
        """Initialize with given parameters."""
        self.regionId = regionId  # Destination region
        self.name = exitName
        self.spoilerName = spoilerName
        self.reverse = reverse  # Indicates a reverse direction transition, if one exists


class TransitionFront:
    """The entered side of a transition between regions."""

    def __init__(
        self,
        dest: Regions,
        logic: Callable,
        exitShuffleId: Optional[Transitions] = None,
        assumed: bool = False,
        time: Time = Time.Both,
        isGlitchTransition: bool = False,
        isBananaportTransition: bool = False,
    ) -> None:
        """Initialize with given parameters."""
        self.dest = dest  # Planning to remove this
        self.logic = logic  # Lambda function for accessibility
        self.exitShuffleId = exitShuffleId  # Planning to remove this
        self.time = time
        self.assumed = assumed  # Indicates this is an assumed exit attached to the root
        # Indicates if this is a glitch-logic transition for this entrance
        self.isGlitchTransition = isGlitchTransition
        # Indicates if this transition is due to a Bananaport
        self.isBananaportTransition = isBananaportTransition

    def to_dict(self) -> dict:
        """Convert the class to a dictionary."""
        return {
            "dest": self.dest.name,
            "logic": format_logic_lambda(self.logic),
            "exitShuffleId": self.exitShuffleId,
            "time": self.time.name,
            "assumed": self.assumed,
            "isGlitchTransition": self.isGlitchTransition,
            "isBananaportTransition": self.isBananaportTransition,
        }


class Sphere:
    """A randomizer concept often used in spoiler logs.

    A 'sphere' is a collection of locations and items that are accessible
    or obtainable with only the items available from earlier, smaller spheres.
    Sphere 0 items are what you start with in a seed, sphere 1 items can be
    obtained with those items, sphere 2 items can be obtained with sphere 0
    and sphere 1 items, and so on.
    """

    def __init__(self) -> None:
        """Initialize with given parameters."""
        self.seedBeaten = False
        self.availableGBs = 0
        self.locations: List[Union[LocationLogic, Any]] = []


class ColoredBananaGroup:
    """Stores data for each group of colored bananas."""

    def __init__(self, *, group=0, name="No Location", map_id=0, konglist=[], region=None, logic=None, vanilla=False, locations=[]) -> None:
        """Initialize with given parameters."""
        self.group = group
        self.name = name
        self.map = map_id
        self.kongs = konglist
        # 5 numbers: {int amount, float scale, int x, y, z}
        self.locations = locations
        self.region = region
        if logic is None:
            self.logic = lambda l: True
        else:
            self.logic = logic
        self.selected = False


class Balloon:
    """Stores data for each balloon."""

    def __init__(self, *, id=0, name="No Location", map_id=0, speed=0, konglist=[], region=None, logic=None, vanilla=False, points=[]) -> None:
        """Initialize with given parameters."""
        self.id = id
        self.name = name
        self.map = map_id
        self.speed = speed
        self.kongs = konglist
        self.points = points  # 3 numbers: [int x, y, z]
        self.region = region
        if logic is None:
            self.logic = lambda l: True
        else:
            self.logic = logic
        self.spawnPoint = self.setSpawnPoint(points)
        self.selected = False

    def setSpawnPoint(self, points: List[List[int]] = []) -> List[int]:
        """Set the spawn point of a balloon based on its path."""
        spawnX = 0.0
        spawnY = 0.0
        spawnZ = 0.0
        for p in points:
            spawnX += p[0]
            spawnY += p[1]
            spawnZ += p[2]
        spawnX /= len(points)
        spawnY /= len(points)
        spawnY -= 100.0  # Most balloons are at least 100 units off the ground
        spawnZ /= len(points)
        return [int(spawnX), int(spawnY), int(spawnZ)]
