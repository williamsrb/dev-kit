<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventmouse.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventmouse.md

# InputEventMouse

**Inherits:** [InputEventWithModifiers](class_inputeventwithmodifiers.md) **<** [InputEventFromWindow](class_inputeventfromwindow.md) **<** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

**Inherited By:** [InputEventMouseButton](class_inputeventmousebutton.md), [InputEventMouseMotion](class_inputeventmousemotion.md)

Base input event type for mouse events.

## Description

Stores general information about mouse events.

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

BitField[MouseButtonMask] | button_mask | `0`
int | device | `32` (overrides [InputEvent](class_inputevent.md))
[Vector2](class_vector2.md) | global_position | `Vector2(0, 0)`
[Vector2](class_vector2.md) | position | `Vector2(0, 0)`

## Property Descriptions

BitField[MouseButtonMask] **button_mask** = `0` 🔗

- void **set_button_mask**(value: BitField[MouseButtonMask])
- BitField[MouseButtonMask] **get_button_mask**()

The mouse button mask identifier, one of or a bitwise combination of the MouseButton button masks.

[Vector2](class_vector2.md) **global_position** = `Vector2(0, 0)` 🔗

- void **set_global_position**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_global_position**()

When received in [Node._input()](class_node.md) or [Node._unhandled_input()](class_node.md), returns the mouse's position in the root [Viewport](class_viewport.md) using the coordinate system of the root [Viewport](class_viewport.md).

When received in [Control._gui_input()](class_control.md), returns the mouse's position in the [CanvasLayer](class_canvaslayer.md) that the [Control](class_control.md) is in using the coordinate system of the [CanvasLayer](class_canvaslayer.md).

[Vector2](class_vector2.md) **position** = `Vector2(0, 0)` 🔗

- void **set_position**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_position**()

When received in [Node._input()](class_node.md) or [Node._unhandled_input()](class_node.md), returns the mouse's position in the [Viewport](class_viewport.md) this [Node](class_node.md) is in using the coordinate system of this [Viewport](class_viewport.md).

When received in [Control._gui_input()](class_control.md), returns the mouse's position in the [Control](class_control.md) using the local coordinate system of the [Control](class_control.md).
