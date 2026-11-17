<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventpangesture.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventpangesture.md

# InputEventPanGesture

**Inherits:** [InputEventGesture](class_inputeventgesture.md) **<** [InputEventWithModifiers](class_inputeventwithmodifiers.md) **<** [InputEventFromWindow](class_inputeventfromwindow.md) **<** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

Represents a panning touch gesture.

## Description

Stores information about pan gestures. A pan gesture is performed when the user swipes the touch screen with two fingers. It's typically used for panning/scrolling.

**Note:** On Android, this requires the [ProjectSettings.input_devices/pointing/android/enable_pan_and_scale_gestures](class_projectsettings.md) project setting to be enabled.

## Tutorials

- [Using InputEvent](../tutorials/inputs/inputevent.md)

## Properties

[Vector2](class_vector2.md) | delta | `Vector2(0, 0)`

## Property Descriptions

[Vector2](class_vector2.md) **delta** = `Vector2(0, 0)` 🔗

- void **set_delta**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_delta**()

Panning amount since last pan event.
