<!-- src:https://docs.godotengine.org/en/4.7/tutorials/inputs/inputevent.html format:llm-dense godot-4.7 -->
#DOC tutorials/inputs/inputevent.md

# Using InputEvent

## What is it?

Managing input is usually complex, no matter the OS or platform. To ease this a little, a special built-in type is provided, [InputEvent](../../classes/class_inputevent.md). This datatype can be configured to contain several types of input events. Input events travel through the engine and can be received in multiple locations, depending on the purpose.

Here is a quick example, closing your game if the escape key is hit:

```gdscript
func _unhandled_input(event):
    if event is InputEventKey:
        if event.pressed and event.keycode == KEY_ESCAPE:
            get_tree().quit()
```

However, it is cleaner and more flexible to use the provided [InputMap](../../classes/class_inputmap.md) feature, which allows you to define input actions and assign them different keys. This way, you can define multiple keys for the same action (e.g. the keyboard escape key and the start button on a gamepad). You can then more easily change this mapping in the project settings without updating your code, and even build a key mapping feature on top of it to allow your game to change the key mapping at runtime!

You can set up your InputMap under **Project > Project Settings > Input Map** and then use those actions like this:

```gdscript
func _process(delta):
    if Input.is_action_pressed("ui_right"):
        # Move right.
```

## How does it work?

Every input event is originated from the user/player (though it's possible to generate an InputEvent and feed them back to the engine, which is useful for gestures). The DisplayServer for each platform will read events from the operating system, then feed them to the root Window.

The window's [Viewport](../../classes/class_viewport.md) does quite a lot of stuff with the received input, in order:

1. If the Viewport is embedding Windows, the Viewport tries to interpret the event in its capability as a Window-Manager (e.g. for resizing or moving Windows).
2. Next if an embedded Window is focused, the event is sent to that Window and processed in the Window's Viewport and afterwards treated as handled. If no embedded Window is focused, the event is sent to the nodes of the current viewport in the following order.
3. First of all, the standard [Node._input()](../../classes/class_node.md) function will be called in any node that overrides it (and hasn't disabled input processing with [Node.set_process_input()](../../classes/class_node.md)). If any function consumes the event, it can call [Viewport.set_input_as_handled()](../../classes/class_viewport.md), and the event will not spread any more. This ensures that you can filter all events of interest, even before the GUI. For gameplay input, [Node._unhandled_input()](../../classes/class_node.md) is generally a better fit, because it allows the GUI to intercept the events.
4. Second, it will try to feed the input to the GUI, and see if any control can receive it. If so, the [Control](../../classes/class_control.md) will be called via the virtual function [Control._gui_input()](../../classes/class_control.md) and the signal "gui_input" will be emitted (this function is re-implementable by script by inheriting from it). If the control wants to "consume" the event, it will call [Control.accept_event()](../../classes/class_control.md) and the event will not spread any more. Use the [Control.mouse_filter](../../classes/class_control.md) property to control whether a [Control](../../classes/class_control.md) is notified of mouse events via [Control._gui_input()](../../classes/class_control.md) callback, and whether these events are propagated further.
5. If so far no one consumed the event, the [Node._shortcut_input()](../../classes/class_node.md) callback will be called if overridden (and not disabled with [Node.set_process_shortcut_input()](../../classes/class_node.md)). This happens only for [InputEventKey](../../classes/class_inputeventkey.md), [InputEventShortcut](../../classes/class_inputeventshortcut.md) and [InputEventJoypadButton](../../classes/class_inputeventjoypadbutton.md). If any function consumes the event, it can call [Viewport.set_input_as_handled()](../../classes/class_viewport.md), and the event will not spread any more. The shortcut input callback is ideal for treating events that are intended as shortcuts.
6. If so far no one consumed the event, the [Node._unhandled_key_input()](../../classes/class_node.md) callback will be called if overridden (and not disabled with [Node.set_process_unhandled_key_input()](../../classes/class_node.md)). This happens only if the event is an [InputEventKey](../../classes/class_inputeventkey.md). If any function consumes the event, it can call [Viewport.set_input_as_handled()](../../classes/class_viewport.md), and the event will not spread any more. The unhandled key input callback is ideal for key events.
7. If so far no one consumed the event, the [Node._unhandled_input()](../../classes/class_node.md) callback will be called if overridden (and not disabled with [Node.set_process_unhandled_input()](../../classes/class_node.md)). If any function consumes the event, it can call [Viewport.set_input_as_handled()](../../classes/class_viewport.md), and the event will not spread any more. The unhandled input callback is ideal for full-screen gameplay events, so they are not received when a GUI is active.
8. If no one wanted the event so far, and [Object Picking](../../classes/class_viewport.md) is turned on, the event is used for object picking. For the root viewport, this can also be enabled in [Project Settings](../../classes/class_projectsettings.md). In the case of a 3D scene if a [Camera3D](../../classes/class_camera3d.md) is assigned to the Viewport, a ray to the physics world (in the ray direction from the click) will be cast. If this ray hits an object, it will call the CollisionObject3D._input_event() function in the relevant physics object. In the case of a 2D scene, conceptually the same happens with CollisionObject2D._input_event().

When sending events to its child and descendant nodes, the viewport will do so, as depicted in the following graphic, in a reverse depth-first order, starting with the node at the bottom of the scene tree, and ending at the root node. Excluded from this process are Windows and SubViewports.

> **Note:** This order doesn't apply to [Control._gui_input()](../../classes/class_control.md), which uses a different method based on event location or focused Control. GUI **mouse** events also travel up the scene tree, subject to the [Control.mouse_filter](../../classes/class_control.md) restrictions described above. However, since these events target specific Controls, only direct ancestors of the targeted Control node receive the event. GUI **keyboard and joypad** events *do not* travel up the scene tree, and can only be handled by the Control that received them. Otherwise, they will be propagated as non-GUI events through [Node._unhandled_input()](../../classes/class_node.md).

Since Viewports don't send events to other SubViewports, one of the following methods has to be used:

1. Use a SubViewportContainer, which automatically sends events to its child SubViewports after [Node._input()](../../classes/class_node.md) or [Control._gui_input()](../../classes/class_control.md).
2. Implement event propagation based on the individual requirements.

In accordance with Godot's node-based design, this enables specialized child nodes to handle and consume particular events, while their ancestors, and ultimately the scene root, can provide more generalized behavior if needed.

## Anatomy of an InputEvent

[InputEvent](../../classes/class_inputevent.md) is just a base built-in type, it does not represent anything and only contains some basic information, such as event ID (which is increased for each event), device index, etc.

There are several specialized types of InputEvent, described in the table below:

Event | Description
[InputEvent](../../classes/class_inputevent.md) | Empty Input Event.
[InputEventKey](../../classes/class_inputeventkey.md) | Contains a keycode and Unicode value, as well as modifiers.
[InputEventMouseButton](../../classes/class_inputeventmousebutton.md) | Contains click information, such as button, modifiers, etc.
[InputEventMouseMotion](../../classes/class_inputeventmousemotion.md) | Contains motion information, such as relative and absolute positions and speed.
[InputEventJoypadMotion](../../classes/class_inputeventjoypadmotion.md) | Contains Joystick/Joypad analog axis information.
[InputEventJoypadButton](../../classes/class_inputeventjoypadbutton.md) | Contains Joystick/Joypad button information.
[InputEventScreenTouch](../../classes/class_inputeventscreentouch.md) | Contains multi-touch press/release information. (only available on mobile devices)
[InputEventScreenDrag](../../classes/class_inputeventscreendrag.md) | Contains multi-touch drag information. (only available on mobile devices)
[InputEventMagnifyGesture](../../classes/class_inputeventmagnifygesture.md) | Contains a position, a factor as well as modifiers.
[InputEventPanGesture](../../classes/class_inputeventpangesture.md) | Contains a position, a delta as well as modifiers.
[InputEventMIDI](../../classes/class_inputeventmidi.md) | Contains MIDI-related information.
[InputEventShortcut](../../classes/class_inputeventshortcut.md) | Contains a shortcut.
[InputEventAction](../../classes/class_inputeventaction.md) | Contains a generic action. These events are often generated by the programmer as feedback. (more on this below)

## Input actions

Input actions are a grouping of zero or more InputEvents into a commonly understood title (for example, the default "ui_left" action grouping both joypad-left input and a keyboard's left arrow key). They are not required to represent an InputEvent but are useful because they abstract various inputs when programming the game logic.

This allows for:

- The same code to work on different devices with different inputs (e.g., keyboard on PC, Joypad on console).
- Input to be reconfigured at runtime.
- Actions to be triggered programmatically at runtime.

Actions can be created from the Project Settings menu in the **Input Map** tab and assigned input events.

Any event has the methods [InputEvent.is_action()](../../classes/class_inputevent.md), [InputEvent.is_pressed()](../../classes/class_inputevent.md) and [InputEvent.is_echo()](../../classes/class_inputevent.md).

Alternatively, it may be desired to supply the game back with an action from the game code (a good example of this is detecting gestures). The Input singleton has a method for this: [Input.parse_input_event()](../../classes/class_input.md). You would normally use it like this:

```gdscript
var ev = InputEventAction.new()
# Set as ui_left, pressed.
ev.action = "ui_left"
ev.pressed = true
# Feedback.
Input.parse_input_event(ev)
```

> **See also:** See [Creating input actions](../../getting_started/first_3d_game/02.player_input.md) for a tutorial on adding input actions in the project settings.

## InputMap

Customizing and re-mapping input from code is often desired. If your whole workflow depends on actions, the [InputMap](../../classes/class_inputmap.md) singleton is ideal for reassigning or creating different actions at runtime. This singleton is not saved (must be modified manually) and its state is run from the project settings (project.godot). So any dynamic system of this type needs to store settings in the way the programmer best sees fit.
