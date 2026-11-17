<!-- src:https://docs.godotengine.org/en/4.7/tutorials/2d/custom_drawing_in_2d.html format:llm-dense godot-4.7 -->
#DOC tutorials/2d/custom_drawing_in_2d.md

# Custom drawing in 2D

## Introduction

Godot has nodes to draw sprites, polygons, particles, text, and many other common game development needs. However, if you need something specific not covered with the standard nodes you can make any 2D node (for example, [Control](../../classes/class_control.md) or [Node2D](../../classes/class_node2d.md)-based) draw on screen using custom commands.

Custom drawing in a 2D node is *really* useful. Here are some use cases:

- Drawing shapes or logic that existing nodes can't do, such as an image with trails or a special animated polygon.
- Drawing a large number of simple objects, such as a grid or a board for a 2d game. Custom drawing avoids the overhead of using a large number of nodes, possibly lowering memory usage and improving performance.
- Making a custom UI control. There are plenty of controls available, but when you have unusual needs, you will likely need a custom control.

## Drawing

Add a script to any [CanvasItem](../../classes/class_canvasitem.md) derived node, like [Control](../../classes/class_control.md) or [Node2D](../../classes/class_node2d.md). Then override the [_draw()](../../classes/class_canvasitem.md) function.

```gdscript
extends Node2D

func _draw():
    pass  # Your draw commands here.
```

Draw commands are described in the [CanvasItem](../../classes/class_canvasitem.md) class reference. There are plenty of them and we will see some of them in the examples below.

## Updating

The [_draw](../../classes/class_canvasitem.md) function is only called once, and then the draw commands are cached and remembered, so further calls are unnecessary.

If re-drawing is required because a variable or something else changed, call [CanvasItem.queue_redraw](../../classes/class_canvasitem.md) in that same node and a new `_draw()` call will happen.

Here is a little more complex example, where we have a texture variable that can be modified at any time, and using a [setter](../scripting/gdscript/gdscript_basics.md), it forces a redraw of the texture when modified:

```gdscript
extends Node2D

@export var texture : Texture2D:
    set(value):
        texture = value
        queue_redraw()

func _draw():
    draw_texture(texture, Vector2())
```

To see it in action, you can set the texture to be the Godot icon on the editor by dragging and dropping the default `icon.svg` from the `FileSystem` tab to the Texture property on the `Inspector` tab. When changing the `Texture` property value while the previous script is running, the texture will also change automatically.

In some cases, we may need to redraw every frame. For this, call [queue_redraw](../../classes/class_canvasitem.md) from the [_process](../../classes/class_node.md) method, like this:

```gdscript
extends Node2D

func _draw():
    pass  # Your draw commands here.

func _process(_delta):
    queue_redraw()
```

## Coordinates and line width alignment

The drawing API uses the CanvasItem's coordinate system, not necessarily pixel coordinates. This means `_draw()` uses the coordinate space created after applying the CanvasItem's transform. Additionally, you can apply a custom transform on top of it by using [draw_set_transform](../../classes/class_canvasitem.md) or [draw_set_transform_matrix](../../classes/class_canvasitem.md).

When using [draw_line](../../classes/class_canvasitem.md), you should consider the width of the line. When using a width that is an odd size, the position of the start and end points should be shifted by `0.5` to keep the line centered, as shown below.

```gdscript
func _draw():
    draw_line(Vector2(1.5, 1.0), Vector2(1.5, 4.0), Color.GREEN, 1.0)
    draw_line(Vector2(4.0, 1.0), Vector2(4.0, 4.0), Color.GREEN, 2.0)
    draw_line(Vector2(7.5, 1.0), Vector2(7.5, 4.0), Color.GREEN, 3.0)
```

The same applies to the [draw_rect](../../classes/class_canvasitem.md) method with `filled = false`.

```gdscript
func _draw():
    draw_rect(Rect2(1.0, 1.0, 3.0, 3.0), Color.GREEN)
    draw_rect(Rect2(5.5, 1.5, 2.0, 2.0), Color.GREEN, false, 1.0)
    draw_rect(Rect2(9.0, 1.0, 5.0, 5.0), Color.GREEN)
    draw_rect(Rect2(16.0, 2.0, 3.0, 3.0), Color.GREEN, false, 2.0)
```

## Antialiased drawing

Godot offers method parameters in [draw_line](../../classes/class_canvasitem.md) to enable antialiasing, but not all custom drawing methods offer this `antialiased` parameter.

For custom drawing methods that don't provide an `antialiased` parameter, you can enable 2D MSAA instead, which affects rendering in the entire viewport. This provides high-quality antialiasing, but a higher performance cost and only on specific elements. See [2D antialiasing](2d_antialiasing.md) for more information.

Here is a comparison of a line of minimal width (`width=-1`) drawn with `antialiased=false`, `antialiased=true`, and `antialiased=false` with 2D MSAA 2x, 4x, and 8x enabled.

## Tools

Drawing your own nodes might also be desired while running them in the editor. This can be used as a preview or visualization of some feature or behavior.

To do this, you can use the [tool annotation](../scripting/gdscript/gdscript_basics.md) on both GDScript and C#. See the example below and Running code in the editor for more information.

## Example 1: drawing a custom shape

We will now use the custom drawing functionality of the Godot Engine to draw something that Godot doesn't provide functions for. We will recreate the Godot logo but with code- only using drawing functions.

You will have to code a function to perform this and draw it yourself.

> **Note:** The following instructions use a fixed set of coordinates that could be too small for high resolution screens (larger than 1080p). If that is your case, and the drawing is too small consider increasing your window scale in the project setting [Display > Window > Stretch > Scale](../../classes/class_projectsettings.md) to adjust the project to a higher resolution (a 2 or 4 scale tends to work well).

### Drawing a custom polygon shape

While there is a dedicated node to draw custom polygons ( Polygon2D), we will use in this case exclusively lower level drawing functions to combine them on the same node and be able to create more complex shapes later on.

First, we will define a set of points -or X and Y coordinates- that will form the base of our shape:

```gdscript
extends Node2D

var coords_head : Array = [
    [ 22.952, 83.271 ],  [ 28.385, 98.623 ],
    [ 53.168, 107.647 ], [ 72.998, 107.647 ],
    [ 99.546, 98.623 ],  [ 105.048, 83.271 ],
    [ 105.029, 55.237 ], [ 110.740, 47.082 ],
    [ 102.364, 36.104 ], [ 94.050, 40.940 ],
    [ 85.189, 34.445 ],  [ 85.963, 24.194 ],
    [ 73.507, 19.930 ],  [ 68.883, 28.936 ],
    [ 59.118, 28.936 ],  [ 54.494, 19.930 ],
    [ 42.039, 24.194 ],  [ 42.814, 34.445 ],
    [ 33.951, 40.940 ],  [ 25.637, 36.104 ],
    [ 17.262, 47.082 ],  [ 22.973, 55.237 ]
]
```

This format, while compact, is not the one that Godot understands to draw a polygon. In a different scenario we could have to load these coordinates from a file or calculate the positions while the application is running, so some transformation may be needed.

To transform these coordinates into the right format, we will create a new method `float_array_to_Vector2Array()`. Then we will override the `_ready()` function, which Godot will call only once -at the start of the execution- to load those coordinates into a variable:

```gdscript
var head : PackedVector2Array

func float_array_to_Vector2Array(coords : Array) -> PackedVector2Array:
    # Convert the array of floats into a PackedVector2Array.
    var array : PackedVector2Array = []
    for coord in coords:
        array.append(Vector2(coord[0], coord[1]))
    return array

func _ready():
    head = float_array_to_Vector2Array(coords_head);
```

To finally draw our first shape, we will use the method [draw_polygon](../../classes/class_canvasitem.md) and pass the points (as an array of Vector2 coordinates) and its color, like this:

```gdscript
func _draw():
    # We are going to paint with this color.
    var godot_blue : Color = Color("478cbf")
    # We pass the PackedVector2Array to draw the shape.
    draw_polygon(head, [ godot_blue ])
```

When running it you should see something like this:

Note the lower part of the logo looks segmented- this is because a low amount of points were used to define that part. To simulate a smooth curve, we could add more points to our array, or maybe use a mathematical function to interpolate a curve and create a smooth shape from code (see example 2).

Polygons will always **connect its last defined point to its first one** in order to have a closed shape.

### Drawing connected lines

Drawing a sequence of connected lines that don't close down to form a polygon is very similar to the previous method. We will use a connected set of lines to draw Godot's logo mouth.

First, we will define the list of coordinates that form the mouth shape, like this:

```gdscript
var coords_mouth = [
    [ 22.817, 81.100 ], [ 38.522, 82.740 ],
    [ 39.001, 90.887 ], [ 54.465, 92.204 ],
    [ 55.641, 84.260 ], [ 72.418, 84.177 ],
    [ 73.629, 92.158 ], [ 88.895, 90.923 ],
    [ 89.556, 82.673 ], [ 105.005, 81.100 ]
]
```

We will load these coordinates into a variable and define an additional variable with the configurable line thickness:

```gdscript
var mouth : PackedVector2Array
var _mouth_width : float = 4.4

func _ready():
    head = float_array_to_Vector2Array(coords_head);
    mouth = float_array_to_Vector2Array(coords_mouth);
```

And finally we will use the method [draw_polyline](../../classes/class_canvasitem.md) to actually draw the line, like this:

```gdscript
func _draw():
    # We will use white to draw the line.
    var white : Color = Color.WHITE
    var godot_blue : Color = Color("478cbf")

    draw_polygon(head, [ godot_blue ])

    # We draw the while line on top of the previous shape.
    draw_polyline(mouth, white, _mouth_width)
```

You should get the following output:

Unlike `draw_polygon()`, polylines can only have a single unique color for all its points (the second argument). This method has 2 additional arguments: the width of the line (which is as small as possible by default) and enabling or disabling the antialiasing (it is disabled by default).

The order of the `_draw` calls is important- like with the Node positions on the tree hierarchy, the different shapes will be drawn from top to bottom, resulting in the latest shapes hiding earlier ones if they overlap. In this case we want the mouth drawn over the head, so we put it afterwards.

Notice how we can define colors in different ways, either with a hexadecimal code or a predefined color name. Check the class Color for other constants and ways to define Colors.

### Drawing circles

To create the eyes, we are going to add 4 additional calls to draw the eye shapes, in different sizes, colors and positions.

To draw a circle, you position it based on its center using the [draw_circle](../../classes/class_canvasitem.md) method. The first parameter is a [Vector2](../../classes/class_vector2.md) with the coordinates of its center, the second is its radius, and the third is its color:

```gdscript
func _draw():
    var white : Color = Color.WHITE
    var godot_blue : Color = Color("478cbf")
    var grey : Color = Color("414042")

    draw_polygon(head, [ godot_blue ])
    draw_polyline(mouth, white, _mouth_width)

    # Four circles for the 2 eyes: 2 white, 2 grey.
    draw_circle(Vector2(42.479, 65.4825), 9.3905, white)
    draw_circle(Vector2(85.524, 65.4825), 9.3905, white)
    draw_circle(Vector2(43.423, 65.92), 6.246, grey)
    draw_circle(Vector2(84.626, 66.008), 6.246, grey)
```

When executing it, you should have something like this:

For partial, unfilled arcs (portions of a circle shape between certain arbitrary angles), you can use the method [draw_arc](../../classes/class_canvasitem.md).

### Drawing lines

To draw the final shape (the nose) we will use a line to approximate it.

[draw_line](../../classes/class_canvasitem.md) can be used to draw a single segment by providing its start and end coordinates as arguments, like this:

```gdscript
func _draw():
    var white : Color = Color.WHITE
    var godot_blue : Color = Color("478cbf")
    var grey : Color = Color("414042")

    draw_polygon(head, [ godot_blue ])
    draw_polyline(mouth, white, _mouth_width)
    draw_circle(Vector2(42.479, 65.4825), 9.3905, white)
    draw_circle(Vector2(85.524, 65.4825), 9.3905, white)
    draw_circle(Vector2(43.423, 65.92), 6.246, grey)
    draw_circle(Vector2(84.626, 66.008), 6.246, grey)

    # Draw a short but thick white vertical line for the nose.
    draw_line(Vector2(64.273, 60.564), Vector2(64.273, 74.349), white, 5.8)
```

You should now be able to see the following shape on screen:

Note that if multiple unconnected lines are going to be drawn at the same time, you may get additional performance by drawing all of them in a single call, using the [draw_multiline](../../classes/class_canvasitem.md) method.

### Drawing text

While using the [Label](../../classes/class_label.md) Node is the most common way to add text to your application, the low-level *_draw* function includes functionality to add text to your custom Node drawing. We will use it to add the name "GODOT" under the robot head.

We will use the [draw_string](../../classes/class_canvasitem.md) method to do it, like this:

```gdscript
var default_font : Font = ThemeDB.fallback_font;

func _draw():
    var white : Color = Color.WHITE
    var godot_blue : Color = Color("478cbf")
    var grey : Color = Color("414042")

    draw_polygon(head, [ godot_blue ])
    draw_polyline(mouth, white, _mouth_width)
    draw_circle(Vector2(42.479, 65.4825), 9.3905, white)
    draw_circle(Vector2(85.524, 65.4825), 9.3905, white)
    draw_circle(Vector2(43.423, 65.92), 6.246, grey)
    draw_circle(Vector2(84.626, 66.008), 6.246, grey)
    draw_line(Vector2(64.273, 60.564), Vector2(64.273, 74.349), white, 5.8)

    # Draw GODOT text below the logo with the default font, size 22.
    draw_string(default_font, Vector2(20, 130), "GODOT",
                HORIZONTAL_ALIGNMENT_CENTER, 90, 22)
```

Here we first load into the defaultFont variable the configured default theme font (a custom one can be set instead) and then we pass the following parameters: font, position, text, horizontal alignment, width, and font size.

You should see the following on your screen:

Additional parameters as well as other methods related to text and characters can be found on the [CanvasItem](../../classes/class_canvasitem.md) class reference.

### Show the drawing while editing

While the code so far is able to draw the logo on a running window, it will not show up on the `2D view` on the editor. In certain cases you would also like to show your custom Node2D or control on the editor, to position and scale it appropriately, like most other nodes do.

To show the logo directly on the editor (without running it), you can use the [@tool](../scripting/gdscript/gdscript_basics.md) annotation to request the custom drawing of the node to also appear while editing, like this:

```gdscript
@tool
extends Node2D
```

You will need to save your scene, rebuild your project (for C# only) and reload the current scene manually at the menu option `Scene > Reload Saved Scene` to refresh the current node in the `2D` view the first time you add or remove the `@tool` annotation.

### Animation

If we wanted to make the custom shape change at runtime, we could modify the methods called or its arguments at execution time, or apply a transform.

For example, if we want the custom shape we just designed to rotate, we could add the following variable and code to the `_ready` and `_process` methods:

```gdscript
extends Node2D

@export var rotation_speed : float = 1  # In radians per second.

func _ready():
    rotation = 0
    ...

func _process(delta: float):
    rotation -= rotation_speed * delta
```

The problem with the above code is that because we have created the points approximately on a rectangle starting from the upper left corner, the `(0, 0)` coordinate and extending to the right and down, we see that the rotation is done using the top left corner as pivot. A position transform change on the node won't help us here, as the rotation transform is applied first.

While we could rewrite all of the points' coordinates to be centered around `(0, 0)`, including negative coordinates, that would be a lot of work.

One possible way to work around this is to use the lower level [draw_set_transform](../../classes/class_canvasitem.md) method to fix this issue, translating all points in the CanvasItem's own space, and then moving it back to its original place with a regular node transform, either in the editor or in code, like this:

```gdscript
func _ready():
    rotation = 0
    position = Vector2(60, 60)
    ...

func _draw():
    draw_set_transform(Vector2(-60, -60))
    ...
```

This is the result, rotating around a pivot now on `(60, 60)`:

If what we wanted to animate was a property inside the `_draw()` call, we must remember to call `queue_redraw()` to force a refresh, as otherwise it would not be updated on screen.

For example, this is how we can make the robot appear to open and close its mouth, by changing the width of its mouth line follow a sinusoidal (sin) curve:

```gdscript
var _mouth_width : float = 4.4
var _max_width : float = 7
var _time : float = 0

func _process(delta : float):
    _time += delta
    _mouth_width = abs(sin(_time) * _max_width)
    queue_redraw()

func _draw():
    ...
    draw_polyline(mouth, white, _mouth_width)
    ...
```

It will look somewhat like this when run:

Please note that `_mouth_width` is a user defined property like any other and it or any other used as a drawing argument can be animated using more standard and high-level methods such as a [Tween](../../classes/class_tween.md) or an [AnimationPlayer](../../classes/class_animationplayer.md) Node. The only difference is that a `queue_redraw()` call is needed to apply those changes so they get shown on screen.

## Example 2: drawing a dynamic line

The previous example was useful to learn how to draw and modify nodes with custom shapes and animations. This could have some advantages, such as using exact coordinates and vectors for drawing, rather than bitmaps -which means they will scale well when transformed on screen. In some cases, similar results could be achieved composing higher level functionality with nodes such as [sprites](../../classes/class_sprite2d.md) or [AnimatedSprites](../../classes/class_animatedsprite2d.md) loading SVG resources (which are also images defined with vectors) and the [AnimationPlayer](../../classes/class_animationplayer.md) node.

In other cases that will not be possible because we will not know what the resulting graphical representation will be before running the code. Here we will see how to draw a dynamic line whose coordinates are not known beforehand, and are affected by the user's input.

### Drawing a straight line between 2 points

Let's assume we want to draw a straight line between 2 points, the first one will be fixed on the upper left corner `(0, 0)` and the second will be defined by the cursor position on screen.

We could draw a dynamic line between those 2 points like this:

```gdscript
extends Node2D

var point1 : Vector2 = Vector2(0, 0)
var width : int = 10
var color : Color = Color.GREEN

var _point2 : Vector2

func _process(_delta):
    var mouse_position = get_viewport().get_mouse_position()
    if mouse_position != _point2:
        _point2 = mouse_position
        queue_redraw()

func _draw():
    draw_line(point1, _point2, color, width)
```

In this example we obtain the position of the mouse in the default viewport every frame with the method [get_mouse_position](../../classes/class_viewport.md). If the position has changed since the last draw request (a small optimization to avoid redrawing on every frame)- we will schedule a redraw. Our `_draw()` method only has one line: requesting the drawing of a green line of width 10 pixels between the top left corner and that obtained position.

The width, color, and position of the starting point can be configured with with the corresponding properties.

It should look like this when run:

### Drawing an arc between 2 points

The above example works, but we may want to join those 2 points with a different shape or function, other than a straight line.

Let's try now creating an arc (a portion of a circumference) between both points.

Exporting the line starting point, segments, width, color, and antialiasing will allow us to modify those properties very easily directly from the editor inspector panel:

```gdscript
extends Node2D

@export var point1 : Vector2 = Vector2(0, 0)
@export_range(1, 1000) var segments : int = 100
@export var width : int = 10
@export var color : Color = Color.GREEN
@export var antialiasing : bool = false

var _point2 : Vector2
```

To draw the arc, we can use the method [draw_arc](../../classes/class_canvasitem.md). There are many arcs that pass through 2 points, so we will chose for this example the semicircle that has its center in the middle point between the 2 initial points.

Calculating this arc will be more complex than in the case of the line:

```gdscript
func _draw():
    # Average points to get center.
    var center : Vector2 = Vector2((_point2.x + point1.x) / 2,
                                   (_point2.y + point1.y) / 2)
    # Calculate the rest of the arc parameters.
    var radius : float = point1.distance_to(_point2) / 2
    var start_angle : float = (_point2 - point1).angle()
    var end_angle : float = (point1 - _point2).angle()
    if end_angle < 0:  # end_angle is likely negative, normalize it.
        end_angle += TAU

    # Finally, draw the arc.
    draw_arc(center, radius, start_angle, end_angle, segments, color,
             width, antialiasing)
```

The center of the semicircle will be the middle point between both points. The radius will be half the distance between both points. The start and end angles will be the angles of the vector from point1 to point2 and vice-versa. Note we had to normalize the `end_angle` in positive values because if `end_angle` is less than `start_angle`, the arc will be drawn counter-clockwise, which we don't want in this case (the arc would be upside-down).

The result should be something like this, with the arc going down and between the points:

Feel free to play with the parameters in the inspector to obtain different results: change the color, the width, the antialiasing, and increase the number of segments to increase the curve smoothness, at the cost of extra performance.
