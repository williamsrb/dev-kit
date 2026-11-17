<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputeventshortcut.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputeventshortcut.md

# InputEventShortcut

**Inherits:** [InputEvent](class_inputevent.md) **<** [Resource](class_resource.md) **<** RefCounted **<** Object

Represents a triggered keyboard Shortcut.

## Description

InputEventShortcut is a special event that can be received in [Node._input()](class_node.md), [Node._shortcut_input()](class_node.md), and [Node._unhandled_input()](class_node.md). It is typically sent by the editor's Command Palette to trigger actions, but can also be sent manually using [Viewport.push_input()](class_viewport.md).

## Properties

Shortcut | shortcut

## Property Descriptions

Shortcut **shortcut** 🔗

- void **set_shortcut**(value: Shortcut)
- Shortcut **get_shortcut**()

The Shortcut represented by this event. Its Shortcut.matches_event() method will always return `true` for this event.
