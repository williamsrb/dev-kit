<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventgesture.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventgesture.md

# InputEventGesture

**Inherits:** [InputEventWithModifiers](class_inputeventwithmodifiers.md) **<** [InputEventFromWindow](class_inputeventfromwindow.md) **<** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

**Inherited By:** [InputEventMagnifyGesture](class_inputeventmagnifygesture.md), [InputEventPanGesture](class_inputeventpangesture.md)

Abstract base class for touch gestures.

## Description

InputEventGestures are sent when a user performs a supported gesture on a touch screen. Gestures can't be emulated using mouse, because they typically require multi-touch.

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

int | device | `0` (overrides [InputEvent](class_inputevent.md))
[Vector2](class_vector2.md) | position | `Vector2(0, 0)`

## Property Descriptions

[Vector2](class_vector2.md) **position** = `Vector2(0, 0)` 🔗

- void **set_position**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_position**()

The local gesture position relative to the [Viewport](class_viewport.md). If used in [Control._gui_input()](class_control.md), the position is relative to the current [Control](class_control.md) that received this gesture.
