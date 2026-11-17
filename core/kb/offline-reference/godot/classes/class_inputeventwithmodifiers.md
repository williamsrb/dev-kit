<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventwithmodifiers.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventwithmodifiers.md

# InputEventWithModifiers

**Inherits:** [InputEventFromWindow](class_inputeventfromwindow.md) **<** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

**Inherited By:** [InputEventGesture](class_inputeventgesture.md), [InputEventKey](class_inputeventkey.md), [InputEventMouse](class_inputeventmouse.md)

Abstract base class for input events affected by modifier keys like `Shift` and `Alt`.

## Description

Stores information about mouse, keyboard, and touch gesture input events. This includes information about which modifier keys are pressed, such as `Shift` or `Alt`. See [Node._input()](class_node.md).

**Note:** Modifier keys are considered modifiers only when used in combination with another key. As a result, their corresponding member variables, such as ctrl_pressed, will return `false` if the key is pressed on its own.

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

bool | alt_pressed | `false`
bool | command_or_control_autoremap | `false`
bool | ctrl_pressed | `false`
int | device | `16` (overrides [InputEvent](class_inputevent.md))
bool | meta_pressed | `false`
bool | shift_pressed | `false`

## Methods

BitField[KeyModifierMask] | get_modifiers_mask() const
bool | is_command_or_control_pressed() const

## Property Descriptions

bool **alt_pressed** = `false` 🔗

- void **set_alt_pressed**(value: bool)
- bool **is_alt_pressed**()

State of the `Alt` modifier.

bool **command_or_control_autoremap** = `false` 🔗

- void **set_command_or_control_autoremap**(value: bool)
- bool **is_command_or_control_autoremap**()

Automatically use `Meta` (`Cmd`) on macOS and `Ctrl` on other platforms. If `true`, ctrl_pressed and meta_pressed cannot be set.

bool **ctrl_pressed** = `false` 🔗

- void **set_ctrl_pressed**(value: bool)
- bool **is_ctrl_pressed**()

State of the `Ctrl` modifier.

bool **meta_pressed** = `false` 🔗

- void **set_meta_pressed**(value: bool)
- bool **is_meta_pressed**()

State of the `Meta` modifier. On Windows and Linux, this represents the Windows key (sometimes called "meta" or "super" on Linux). On macOS, this represents the Command key.

bool **shift_pressed** = `false` 🔗

- void **set_shift_pressed**(value: bool)
- bool **is_shift_pressed**()

State of the `Shift` modifier.

## Method Descriptions

BitField[KeyModifierMask] **get_modifiers_mask**() const 🔗

Returns the keycode combination of modifier keys.

bool **is_command_or_control_pressed**() const 🔗

On macOS, returns `true` if `Meta` (`Cmd`) is pressed.

On other platforms, returns `true` if `Ctrl` is pressed.
