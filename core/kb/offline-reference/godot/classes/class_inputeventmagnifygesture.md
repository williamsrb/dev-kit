<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventmagnifygesture.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventmagnifygesture.md

# InputEventMagnifyGesture

**Inherits:** [InputEventGesture](class_inputeventgesture.md) **<** [InputEventWithModifiers](class_inputeventwithmodifiers.md) **<** [InputEventFromWindow](class_inputeventfromwindow.md) **<** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

Represents a magnifying touch gesture.

## Description

Stores the factor of a magnifying touch gesture. This is usually performed when the user pinches the touch screen and used for zooming in/out.

**Note:** On Android, this requires the [ProjectSettings.input_devices/pointing/android/enable_pan_and_scale_gestures](class_projectsettings.md) project setting to be enabled.

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

float | factor | `1.0`

## Property Descriptions

float **factor** = `1.0` 🔗

- void **set_factor**(value: float)
- float **get_factor**()

The amount (or delta) of the event. This value is closer to `1.0` the slower the gesture is performed.
