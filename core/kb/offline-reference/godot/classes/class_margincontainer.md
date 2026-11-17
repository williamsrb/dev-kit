<!-- src:https://docs.godotengine.org/en/4.7/classes/class_margincontainer.html format:llm-dense godot-4.7 -->
#DOC classes/class_margincontainer.md

# MarginContainer

**Inherits:** [Container](class_container.md) **<** [Control](class_control.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** EditorDock

A container that keeps a margin around its child controls.

## Description

**MarginContainer** adds an adjustable margin on each side of its child controls. The margins are added around all children, not around each individual one. To control the **MarginContainer**'s margins, use the `margin_*` theme properties listed below.

**Note:** The margin sizes are theme overrides, not normal properties. This is an example of how to change them in code:

```gdscript
# This code sample assumes the current script is extending MarginContainer.
var margin_value = 100
add_theme_constant_override("margin_top", margin_value)
add_theme_constant_override("margin_left", margin_value)
add_theme_constant_override("margin_bottom", margin_value)
add_theme_constant_override("margin_right", margin_value)
```

## Tutorials

- [Using Containers](../tutorials/ui/gui_containers.md)

## Theme Properties

int | margin_bottom | `0`
int | margin_left | `0`
int | margin_right | `0`
int | margin_top | `0`

## Theme Property Descriptions

int **margin_bottom** = `0` 🔗

Offsets towards the inside direct children of the container by this amount of pixels from the bottom.

int **margin_left** = `0` 🔗

Offsets towards the inside direct children of the container by this amount of pixels from the left.

int **margin_right** = `0` 🔗

Offsets towards the inside direct children of the container by this amount of pixels from the right.

int **margin_top** = `0` 🔗

Offsets towards the inside direct children of the container by this amount of pixels from the top.
