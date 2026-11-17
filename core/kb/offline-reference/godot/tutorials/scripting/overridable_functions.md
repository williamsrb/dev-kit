<!-- src:https://docs.godotengine.org/en/4.7/tutorials/scripting/overridable_functions.html format:llm-dense godot-4.7 -->
#DOC tutorials/scripting/overridable_functions.md

# Overridable functions

Godot's Node class provides virtual functions you can override to update nodes every frame or on specific events, like when they enter the scene tree.

This document presents the ones you'll use most often.

> **See also:** Under the hood, these functions rely on Godot's low-level notifications system. To learn more about it, see [Godot notifications](../best_practices/godot_notifications.md).

Two functions allow you to initialize and get nodes besides the class's constructor: `_enter_tree()` and `_ready()`.

When the node enters the Scene Tree, it becomes active and the engine calls its `_enter_tree()` method. That node's children may not be part of the active scene yet. As you can remove and re-add nodes to the scene tree, this function may be called multiple times throughout a node's lifetime.

Most of the time, you'll use `_ready()` instead. This function is called only once in a node's lifetime, after `_enter_tree()`. `_ready()` ensures that all children have entered the scene tree first, so you can safely call `get_node()` on them.

> **See also:** To learn more about getting node references, read [Nodes and scene instances](nodes_and_scene_instances.md).

Another related callback is `_exit_tree()`, which the engine calls every time a node is about to exit the scene tree. This can be when you call [Node.remove_child()](../../classes/class_node.md) or when you free a node.

```gdscript
# Called every time the node enters the scene tree.
func _enter_tree():
    pass

# Called when both the node and its children have entered the scene tree.
func _ready():
    pass

# Called when the node is about to leave the scene tree, after all its
# children received the _exit_tree() callback.
func _exit_tree():
    pass
```

The two virtual methods `_process()` and `_physics_process()` allow you to update the node, every frame and every physics frame respectively. For more information, read the dedicated documentation: [Idle and Physics Processing](idle_and_physics_processing.md).

```gdscript
# Called every frame.
func _process(delta):
    pass

# Called every physics frame.
func _physics_process(delta):
    pass
```

Two more essential built-in node callback functions are [Node._unhandled_input()](../../classes/class_node.md) and [Node._input()](../../classes/class_node.md), which you use to both receive and process individual input events. The `_unhandled_input()` method receives every key press, mouse click, etc. that have not been handled already in an `_input()` callback or in a user interface component. You want to use it for gameplay input in general. The `_input()` callback allows you to intercept and process input events before `_unhandled_input()` gets them.

To learn more about inputs in Godot, see the Input section.

```gdscript
# Called once for every event.
func _unhandled_input(event):
    pass

# Called once for every event before _unhandled_input(), allowing you to
# consume some events.
func _input(event):
    pass
```

There are some more overridable functions like [Node._get_configuration_warnings()](../../classes/class_node.md). Specialized node types provide more callbacks like [CanvasItem._draw()](../../classes/class_canvasitem.md) to draw programmatically or [Control._gui_input()](../../classes/class_control.md) to handle clicks and input on UI elements.
