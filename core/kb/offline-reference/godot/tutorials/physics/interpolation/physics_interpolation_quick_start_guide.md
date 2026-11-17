<!-- src:https://docs.godotengine.org/en/4.7/tutorials/physics/interpolation/physics_interpolation_quick_start_guide.html format:llm-dense godot-4.7 -->
#DOC tutorials/physics/interpolation/physics_interpolation_quick_start_guide.md

# Quick start guide

- Turn on physics interpolation: [Project Settings > Physics > Common > Physics Interpolation](../../../classes/class_projectsettings.md)
- Make sure you move objects and run your game logic in `_physics_process()` rather than `_process()`. This includes moving objects directly *and indirectly* (by e.g. moving a parent, or using another mechanism to automatically move nodes).
- Be sure to call [Node.reset_physics_interpolation](../../../classes/class_node.md) on nodes *after* you first position or teleport them, to prevent "streaking".
- Temporarily try setting [Project Settings > Physics > Common > Physics Ticks per Second](../../../classes/class_projectsettings.md) to 10 to see the difference with and without interpolation.
