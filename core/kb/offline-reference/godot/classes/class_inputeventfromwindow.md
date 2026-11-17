<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventfromwindow.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventfromwindow.md

# InputEventFromWindow

**Inherits:** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

**Inherited By:** [InputEventScreenDrag](class_inputeventscreendrag.md), [InputEventScreenTouch](class_inputeventscreentouch.md), [InputEventWithModifiers](class_inputeventwithmodifiers.md)

Abstract base class for [Viewport](class_viewport.md)-based input events.

## Description

InputEventFromWindow represents events specifically received by windows. This includes mouse events, keyboard events in focused windows or touch screen actions.

## Properties

int | window_id | `0`

## Property Descriptions

int **window_id** = `0` 🔗

- void **set_window_id**(value: int)
- int **get_window_id**()

The ID of a Window that received this event.
