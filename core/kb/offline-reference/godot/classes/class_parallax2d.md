<!-- src:https://docs.godotengine.org/en/4.7/classes/class_parallax2d.html format:llm-dense godot-4.7 -->
#DOC classes/class_parallax2d.md

# Parallax2D

**Inherits:** [Node2D](class_node2d.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

A node used to create a parallax scrolling background.

## Description

A **Parallax2D** is used to create a parallax effect. It can move at a different speed relative to the camera movement using scroll_scale. This creates an illusion of depth in a 2D game. If manual scrolling is desired, the [Camera2D](class_camera2d.md) position can be ignored with ignore_camera_scroll.

**Note:** Any changes to this node's position made after it enters the scene tree will be overridden if ignore_camera_scroll is `false` or screen_offset is modified.

## Tutorials

- [2D Parallax](../tutorials/2d/2d_parallax.md)

## Properties

[Vector2](class_vector2.md) | autoscroll | `Vector2(0, 0)`
bool | follow_viewport | `true`
bool | ignore_camera_scroll | `false`
[Vector2](class_vector2.md) | limit_begin | `Vector2(-10000000, -10000000)`
[Vector2](class_vector2.md) | limit_end | `Vector2(10000000, 10000000)`
[PhysicsInterpolationMode](class_node.md) | physics_interpolation_mode | `2` (overrides [Node](class_node.md))
[Vector2](class_vector2.md) | repeat_size | `Vector2(0, 0)`
int | repeat_times | `1`
[Vector2](class_vector2.md) | screen_offset | `Vector2(0, 0)`
[Vector2](class_vector2.md) | scroll_offset | `Vector2(0, 0)`
[Vector2](class_vector2.md) | scroll_scale | `Vector2(1, 1)`

## Property Descriptions

[Vector2](class_vector2.md) **autoscroll** = `Vector2(0, 0)` 🔗

- void **set_autoscroll**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_autoscroll**()

Velocity at which the offset scrolls automatically, in pixels per second.

bool **follow_viewport** = `true` 🔗

- void **set_follow_viewport**(value: bool)
- bool **get_follow_viewport**()

If `true`, this **Parallax2D** is offset by the current camera's position. If the **Parallax2D** is in a [CanvasLayer](class_canvaslayer.md) separate from the current camera, it may be desired to match the value with [CanvasLayer.follow_viewport_enabled](class_canvaslayer.md).

bool **ignore_camera_scroll** = `false` 🔗

- void **set_ignore_camera_scroll**(value: bool)
- bool **is_ignore_camera_scroll**()

If `true`, **Parallax2D**'s position is not affected by the position of the camera.

[Vector2](class_vector2.md) **limit_begin** = `Vector2(-10000000, -10000000)` 🔗

- void **set_limit_begin**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_limit_begin**()

Top-left limits for scrolling to begin. If the camera is outside of this limit, the **Parallax2D** stops scrolling. Must be lower than limit_end minus the viewport size to work.

[Vector2](class_vector2.md) **limit_end** = `Vector2(10000000, 10000000)` 🔗

- void **set_limit_end**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_limit_end**()

Bottom-right limits for scrolling to end. If the camera is outside of this limit, the **Parallax2D** will stop scrolling. Must be higher than limit_begin and the viewport size combined to work.

[Vector2](class_vector2.md) **repeat_size** = `Vector2(0, 0)` 🔗

- void **set_repeat_size**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_repeat_size**()

Repeats the Texture2D of each of this node's children and offsets them by this value. When scrolling, the node's position loops, giving the illusion of an infinite scrolling background if the values are larger than the screen size. If an axis is set to `0`, the Texture2D will not be repeated.

int **repeat_times** = `1` 🔗

- void **set_repeat_times**(value: int)
- int **get_repeat_times**()

Overrides the amount of times the texture repeats. Each texture copy spreads evenly from the original by repeat_size. Useful for when zooming out with a camera.

[Vector2](class_vector2.md) **screen_offset** = `Vector2(0, 0)` 🔗

- void **set_screen_offset**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_screen_offset**()

Offset used to scroll this **Parallax2D**. This value is updated automatically unless ignore_camera_scroll is `true`.

[Vector2](class_vector2.md) **scroll_offset** = `Vector2(0, 0)` 🔗

- void **set_scroll_offset**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_scroll_offset**()

The **Parallax2D**'s offset. Similar to screen_offset and [Node2D.position](class_node2d.md), but will not be overridden.

**Note:** Values will loop if repeat_size is set higher than `0`.

[Vector2](class_vector2.md) **scroll_scale** = `Vector2(1, 1)` 🔗

- void **set_scroll_scale**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_scroll_scale**()

Multiplier to the final **Parallax2D**'s offset. Can be used to simulate distance from the camera.

For example, a value of `1` scrolls at the same speed as the camera. A value greater than `1` scrolls faster, making objects appear closer. Less than `1` scrolls slower, making objects appear further, and a value of `0` stops the objects completely.
