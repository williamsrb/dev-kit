<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventjoypadbutton.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventjoypadbutton.md

# InputEventJoypadButton

**Inherits:** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

Represents a gamepad button being pressed or released.

## Description

Input event type for gamepad buttons. For gamepad analog sticks and joysticks, see [InputEventJoypadMotion](class_inputeventjoypadmotion.md).

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

JoyButton | button_index | `0`
bool | pressed | `false`
float | pressure | `0.0`

## Property Descriptions

JoyButton **button_index** = `0` 🔗

- void **set_button_index**(value: JoyButton)
- JoyButton **get_button_index**()

Button identifier. One of the JoyButton button constants.

bool **pressed** = `false` 🔗

- void **set_pressed**(value: bool)
- bool **is_pressed**()

If `true`, the button's state is pressed. If `false`, the button's state is released.

float **pressure** = `0.0` 🔗

- void **set_pressure**(value: float)
- float **get_pressure**()

**Deprecated:** This property is never set by the engine and is always `0`.
