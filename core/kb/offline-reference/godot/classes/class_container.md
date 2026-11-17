<!-- src:https://docs.godotengine.org/en/4.7/classes/class_container.html format:llm-dense godot-4.7 -->
#DOC classes/class_container.md

# Container

**Inherits:** [Control](class_control.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** AspectRatioContainer, [BoxContainer](class_boxcontainer.md), CenterContainer, EditorProperty, FlowContainer, FoldableContainer, GraphElement, [GridContainer](class_gridcontainer.md), [MarginContainer](class_margincontainer.md), PanelContainer, ScrollContainer, SplitContainer, SubViewportContainer, TabContainer

Base class for all GUI containers.

## Description

Base class for all GUI containers. A **Container** automatically arranges its child controls in a certain way. This class can be inherited to make custom container types.

## Tutorials

- [Using Containers](../tutorials/ui/gui_containers.md)

## Properties

bool | accessibility_region | `false`
[MouseFilter](class_control.md) | mouse_filter | `1` (overrides [Control](class_control.md))
bool | propagate_maximum_size | `true` (overrides [Control](class_control.md))

## Methods

PackedInt32Array | _get_allowed_size_flags_horizontal() virtual const
PackedInt32Array | _get_allowed_size_flags_vertical() virtual const
void | fit_child_in_rect(child: [Control](class_control.md), rect: Rect2)
void | queue_sort()

## Signals

**pre_sort_children**() 🔗

Emitted when children are going to be sorted.

**sort_children**() 🔗

Emitted when sorting the children is needed.

## Constants

**NOTIFICATION_PRE_SORT_CHILDREN** = `50` 🔗

Notification just before children are going to be sorted, in case there's something to process beforehand.

**NOTIFICATION_SORT_CHILDREN** = `51` 🔗

Notification for when sorting the children, it must be obeyed immediately.

## Property Descriptions

bool **accessibility_region** = `false` 🔗

- void **set_accessibility_region**(value: bool)
- bool **is_accessibility_region**()

If `true`, this container is marked as a region for accessibility. Use [Control.accessibility_name](class_control.md) to give the region a descriptive name. Screen readers can navigate between regions using landmark navigation.

## Method Descriptions

PackedInt32Array **_get_allowed_size_flags_horizontal**() virtual const 🔗

Implement to return a list of allowed horizontal [SizeFlags](class_control.md) for child nodes. This doesn't technically prevent the usages of any other size flags, if your implementation requires that. This only limits the options available to the user in the Inspector dock.

**Note:** Having no size flags is equal to having [Control.SIZE_SHRINK_BEGIN](class_control.md). As such, this value is always implicitly allowed.

PackedInt32Array **_get_allowed_size_flags_vertical**() virtual const 🔗

Implement to return a list of allowed vertical [SizeFlags](class_control.md) for child nodes. This doesn't technically prevent the usages of any other size flags, if your implementation requires that. This only limits the options available to the user in the Inspector dock.

**Note:** Having no size flags is equal to having [Control.SIZE_SHRINK_BEGIN](class_control.md). As such, this value is always implicitly allowed.

void **fit_child_in_rect**(child: [Control](class_control.md), rect: Rect2) 🔗

Fit a child control in a given rect. This is mainly a helper for creating custom container classes.

void **queue_sort**() 🔗

Queue resort of the contained children. This is called automatically anyway, but can be called upon request.
