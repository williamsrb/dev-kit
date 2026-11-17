<!-- src:https://docs.godotengine.org/en/4.7/classes/class_gridcontainer.html format:llm-dense godot-4.7 -->
#DOC classes/class_gridcontainer.md

# GridContainer

**Inherits:** [Container](class_container.md) **<** [Control](class_control.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

A container that arranges its child controls in a grid layout.

## Description

**GridContainer** arranges its child controls in a grid layout. The number of columns is specified by the columns property, whereas the number of rows depends on how many are needed for the child controls. The number of rows and columns is preserved for every size of the container.

**Note:** **GridContainer** only works with child nodes inheriting from [Control](class_control.md). It won't rearrange child nodes inheriting from [Node2D](class_node2d.md).

## Tutorials

- [Using Containers](../tutorials/ui/gui_containers.md)
- [Operating System Testing Demo](https://godotengine.org/asset-library/asset/2789)

## Properties

int | columns | `1`

## Theme Properties

int | h_separation | `4`
int | v_separation | `4`

## Property Descriptions

int **columns** = `1` 🔗

- void **set_columns**(value: int)
- int **get_columns**()

The number of columns in the **GridContainer**. If modified, **GridContainer** reorders its Control-derived children to accommodate the new layout.

## Theme Property Descriptions

int **h_separation** = `4` 🔗

The horizontal separation of child nodes.

int **v_separation** = `4` 🔗

The vertical separation of child nodes.
