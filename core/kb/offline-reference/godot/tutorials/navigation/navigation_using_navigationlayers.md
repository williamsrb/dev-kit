<!-- src:https://docs.godotengine.org/en/4.7/tutorials/navigation/navigation_using_navigationlayers.html format:llm-dense godot-4.7 -->
#DOC tutorials/navigation/navigation_using_navigationlayers.md

# Using NavigationLayers

NavigationLayers are an optional feature to further control which navigation meshes are considered in a path query. They work similar to how physics layers control collision between collision objects or how visual layers control what is rendered to the Viewport.

NavigationLayers can be named in the **ProjectSettings** the same as physics layers or visual layers.

If a region has not a single compatible navigation layer with the `navigation_layers` parameter of a path query this regions navigation mesh will be skipped in pathfinding. See [Using NavigationPaths](navigation_using_navigationpaths.md) for more information on querying the NavigationServer for paths.

NavigationLayers are a single `int` value that is used as a **bitmask**. Many navigation related nodes have `set_navigation_layer_value()` and `get_navigation_layer_value()` functions to set and get a layer number directly without the need for more complex bitwise operations.

In scripts the following helper functions can be used to work with the `navigation_layers` bitmask.

**2D**

```gdscript
func change_layers():
    var region: NavigationRegion2D = get_node("NavigationRegion2D")
    # enables 4-th layer for this region
    region.navigation_layers = enable_bitmask_inx(region.navigation_layers, 4)
    # disables 1-rst layer for this region
    region.navigation_layers = disable_bitmask_inx(region.navigation_layers, 1)

    var agent: NavigationAgent2D = get_node("NavigationAgent2D")
    # make future path queries of this agent ignore regions with 4-th layer
    agent.navigation_layers = disable_bitmask_inx(agent.navigation_layers, 4)

    var path_query_navigation_layers: int = 0
    path_query_navigation_layers = enable_bitmask_inx(path_query_navigation_layers, 2)
    # get a path that only considers 2-nd layer regions
    var path: PackedVector2Array = NavigationServer2D.map_get_path(
        map,
        start_position,
        target_position,
        true,
        path_query_navigation_layers
        )

static func is_bitmask_inx_enabled(_bitmask: int, _index: int) -> bool:
    return _bitmask & (1 << _index) != 0

static func enable_bitmask_inx(_bitmask: int, _index: int) -> int:
    return _bitmask | (1 << _index)

static func disable_bitmask_inx(_bitmask: int, _index: int) -> int:
    return _bitmask & ~(1 << _index)
```

**3D**

```gdscript
func change_layers():
    var region: NavigationRegion3D = get_node("NavigationRegion3D")
    # enables 4-th layer for this region
    region.navigation_layers = enable_bitmask_inx(region.navigation_layers, 4)
    # disables 1-rst layer for this region
    region.navigation_layers = disable_bitmask_inx(region.navigation_layers, 1)

    var agent: NavigationAgent3D = get_node("NavigationAgent3D")
    # make future path queries of this agent ignore regions with 4-th layer
    agent.navigation_layers = disable_bitmask_inx(agent.navigation_layers, 4)

    var path_query_navigation_layers: int = 0
    path_query_navigation_layers = enable_bitmask_inx(path_query_navigation_layers, 2)
    # get a path that only considers 2-nd layer regions
    var path: PackedVector3Array = NavigationServer3D.map_get_path(
        map,
        start_position,
        target_position,
        true,
        path_query_navigation_layers
        )

static func is_bitmask_inx_enabled(_bitmask: int, _index: int) -> bool:
    return _bitmask & (1 << _index) != 0

static func enable_bitmask_inx(_bitmask: int, _index: int) -> int:
    return _bitmask | (1 << _index)

static func disable_bitmask_inx(_bitmask: int, _index: int) -> int:
    return _bitmask & ~(1 << _index)
```

Changing navigation layers for path queries is a performance friendly alternative to enabling / disabling entire navigation regions. Compared to region changes a navigation path query with different navigation layers does not trigger large scale updates on the NavigationServer.

Changing the navigation layers of NavigationAgent nodes will have an immediate effect on the next path query. Changing the navigation layers of regions will have an effect after the next NavigationServer sync.
