<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventjoypadmotion.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventjoypadmotion.md

# InputEventJoypadMotion

**Inherits:** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

Represents axis motions (such as joystick or analog triggers) from a gamepad.

## Description

Stores information about joystick motions. One **InputEventJoypadMotion** represents one axis at a time. For gamepad buttons, see [InputEventJoypadButton](class_inputeventjoypadbutton.md).

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

JoyAxis | axis | `0`
float | axis_value | `0.0`

## Property Descriptions

JoyAxis **axis** = `0` 🔗

- void **set_axis**(value: JoyAxis)
- JoyAxis **get_axis**()

Axis identifier.

float **axis_value** = `0.0` 🔗

- void **set_axis_value**(value: float)
- float **get_axis_value**()

Current position of the joystick on the given axis. The value ranges from `-1.0` to `1.0`. A value of `0` means the axis is in its resting position.
