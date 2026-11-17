<!-- src:https://docs.godotengine.org/en/4.7/classes/class_inputmap.html format:llm-dense godot-4.7 -->
#DOC classes/class_inputmap.md

# InputMap

**Inherits:** Object

A singleton that manages all [InputEventAction](class_inputeventaction.md)s.

## Description

Manages all [InputEventAction](class_inputeventaction.md) which can be created/modified from the project settings menu **Project > Project Settings > Input Map** or in code with add_action() and action_add_event(). See [Node._input()](class_node.md).

## Tutorials

- [Using InputEvent: InputMap](../tutorials/inputs/inputevent.md)

## Methods

void | action_add_event(action: StringName, event: [InputEvent](class_inputevent.md))
void | action_erase_event(action: StringName, event: [InputEvent](class_inputevent.md))
void | action_erase_events(action: StringName)
float | action_get_deadzone(action: StringName)
[Array](class_array.md)[[InputEvent](class_inputevent.md)] | action_get_events(action: StringName)
bool | action_has_event(action: StringName, event: [InputEvent](class_inputevent.md))
void | action_set_deadzone(action: StringName, deadzone: float)
void | add_action(action: StringName, deadzone: float = 0.2)
void | erase_action(action: StringName)
bool | event_is_action(event: [InputEvent](class_inputevent.md), action: StringName, exact_match: bool = false) const
[String](class_string.md) | get_action_description(action: StringName) const
[Array](class_array.md)[StringName] | get_actions()
bool | has_action(action: StringName) const
void | load_from_project_settings()

## Signals

**project_settings_loaded**() 🔗

Emitted when the [ProjectSettings](class_projectsettings.md) **InputMap** has been loaded.

## Method Descriptions

void **action_add_event**(action: StringName, event: [InputEvent](class_inputevent.md)) 🔗

Adds an [InputEvent](class_inputevent.md) to an action. This [InputEvent](class_inputevent.md) will trigger the action.

void **action_erase_event**(action: StringName, event: [InputEvent](class_inputevent.md)) 🔗

Removes an [InputEvent](class_inputevent.md) from an action.

void **action_erase_events**(action: StringName) 🔗

Removes all events from an action.

float **action_get_deadzone**(action: StringName) 🔗

Returns a deadzone value for the action.

[Array](class_array.md)[[InputEvent](class_inputevent.md)] **action_get_events**(action: StringName) 🔗

Returns an array of [InputEvent](class_inputevent.md)s associated with a given action.

**Note:** When used in the editor (e.g. a tool script or EditorPlugin), this method will return events for the editor action. If you want to access your project's input binds from the editor, read the `input/*` settings from [ProjectSettings](class_projectsettings.md).

bool **action_has_event**(action: StringName, event: [InputEvent](class_inputevent.md)) 🔗

Returns `true` if the action has the given [InputEvent](class_inputevent.md) associated with it.

void **action_set_deadzone**(action: StringName, deadzone: float) 🔗

Sets a deadzone value for the action.

void **add_action**(action: StringName, deadzone: float = 0.2) 🔗

Adds an empty action to the **InputMap** with a configurable `deadzone`.

An [InputEvent](class_inputevent.md) can then be added to this action with action_add_event().

void **erase_action**(action: StringName) 🔗

Removes an action from the **InputMap**.

bool **event_is_action**(event: [InputEvent](class_inputevent.md), action: StringName, exact_match: bool = false) const 🔗

Returns `true` if the given event is part of an existing action. This method ignores keyboard modifiers if the given [InputEvent](class_inputevent.md) is not pressed (for proper release detection). See action_has_event() if you don't want this behavior.

If `exact_match` is `false`, it ignores additional input modifiers for [InputEventKey](class_inputeventkey.md) and [InputEventMouseButton](class_inputeventmousebutton.md) events, and the direction for [InputEventJoypadMotion](class_inputeventjoypadmotion.md) events.

[String](class_string.md) **get_action_description**(action: StringName) const 🔗

Returns the human-readable description of the given action.

[Array](class_array.md)[StringName] **get_actions**() 🔗

Returns an array of all actions in the **InputMap**.

bool **has_action**(action: StringName) const 🔗

Returns `true` if the **InputMap** has a registered action with the given name.

void **load_from_project_settings**() 🔗

Clears all [InputEventAction](class_inputeventaction.md) in the **InputMap** and load it anew from [ProjectSettings](class_projectsettings.md).
