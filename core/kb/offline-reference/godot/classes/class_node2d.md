<!-- src:https://docs.godotengine.org/en/4.7/classes/class_node2d.html format:llm-dense godot-4.7 -->
#DOC classes/class_node2d.md

# Node2D

**Inherits:** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** [AnimatedSprite2D](class_animatedsprite2d.md), AudioListener2D, [AudioStreamPlayer2D](class_audiostreamplayer2d.md), BackBufferCopy, Bone2D, [Camera2D](class_camera2d.md), CanvasGroup, CanvasModulate, CollisionObject2D, [CollisionPolygon2D](class_collisionpolygon2d.md), [CollisionShape2D](class_collisionshape2d.md), [CPUParticles2D](class_cpuparticles2d.md), [GPUParticles2D](class_gpuparticles2d.md), Joint2D, Light2D, LightOccluder2D, Line2D, Marker2D, MeshInstance2D, [MultiMeshInstance2D](class_multimeshinstance2d.md), NavigationLink2D, NavigationObstacle2D, [NavigationRegion2D](class_navigationregion2d.md), [Parallax2D](class_parallax2d.md), ParallaxLayer, Path2D, PathFollow2D, Polygon2D, [RayCast2D](class_raycast2d.md), RemoteTransform2D, [ShapeCast2D](class_shapecast2d.md), Skeleton2D, [Sprite2D](class_sprite2d.md), [TileMap](class_tilemap.md), [TileMapLayer](class_tilemaplayer.md), TouchScreenButton, VisibleOnScreenNotifier2D

A 2D game object, inherited by all 2D-related nodes. Has a position, rotation, scale, and skew.

## Description

A 2D game object, with a transform (position, rotation, and scale). All 2D nodes, including physics objects and sprites, inherit from Node2D. Use Node2D as a parent node to move, scale and rotate children in a 2D project. Also gives control of the node's render order.

**Note:** Since both **Node2D** and [Control](class_control.md) inherit from [CanvasItem](class_canvasitem.md), they share several concepts from the class such as the [CanvasItem.z_index](class_canvasitem.md) and [CanvasItem.visible](class_canvasitem.md) properties.

## Tutorials

- [Custom drawing in 2D](../tutorials/2d/custom_drawing_in_2d.md)
- [All 2D Demos](https://github.com/godotengine/godot-demo-projects/tree/master/2d)

## Properties

[Vector2](class_vector2.md) | global_position |
float | global_rotation |
float | global_rotation_degrees |
[Vector2](class_vector2.md) | global_scale |
float | global_skew |
[Transform2D](class_transform2d.md) | global_transform |
[Vector2](class_vector2.md) | position | `Vector2(0, 0)`
float | rotation | `0.0`
float | rotation_degrees |
[Vector2](class_vector2.md) | scale | `Vector2(1, 1)`
float | skew | `0.0`
[Transform2D](class_transform2d.md) | transform |

## Methods

void | apply_scale(ratio: [Vector2](class_vector2.md))
float | get_angle_to(point: [Vector2](class_vector2.md)) const
[Transform2D](class_transform2d.md) | get_relative_transform_to_parent(parent: [Node](class_node.md)) const
void | global_translate(offset: [Vector2](class_vector2.md))
void | look_at(point: [Vector2](class_vector2.md))
void | move_local_x(delta: float, scaled: bool = false)
void | move_local_y(delta: float, scaled: bool = false)
void | rotate(radians: float)
[Vector2](class_vector2.md) | to_global(local_point: [Vector2](class_vector2.md)) const
[Vector2](class_vector2.md) | to_local(global_point: [Vector2](class_vector2.md)) const
void | translate(offset: [Vector2](class_vector2.md))

## Property Descriptions

[Vector2](class_vector2.md) **global_position** 🔗

- void **set_global_position**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_global_position**()

Global position. See also position.

float **global_rotation** 🔗

- void **set_global_rotation**(value: float)
- float **get_global_rotation**()

Global rotation in radians. See also rotation.

float **global_rotation_degrees** 🔗

- void **set_global_rotation_degrees**(value: float)
- float **get_global_rotation_degrees**()

Helper property to access global_rotation in degrees instead of radians. See also rotation_degrees.

[Vector2](class_vector2.md) **global_scale** 🔗

- void **set_global_scale**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_global_scale**()

Global scale. See also scale.

float **global_skew** 🔗

- void **set_global_skew**(value: float)
- float **get_global_skew**()

Global skew in radians. See also skew.

[Transform2D](class_transform2d.md) **global_transform** 🔗

- void **set_global_transform**(value: [Transform2D](class_transform2d.md))
- [Transform2D](class_transform2d.md) **get_global_transform**()

Global [Transform2D](class_transform2d.md). See also transform.

[Vector2](class_vector2.md) **position** = `Vector2(0, 0)` 🔗

- void **set_position**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_position**()

Position, relative to the node's parent. See also global_position.

float **rotation** = `0.0` 🔗

- void **set_rotation**(value: float)
- float **get_rotation**()

Rotation in radians, relative to the node's parent. See also global_rotation.

**Note:** This property is edited in the inspector in degrees. If you want to use degrees in a script, use rotation_degrees.

float **rotation_degrees** 🔗

- void **set_rotation_degrees**(value: float)
- float **get_rotation_degrees**()

Helper property to access rotation in degrees instead of radians. See also global_rotation_degrees.

[Vector2](class_vector2.md) **scale** = `Vector2(1, 1)` 🔗

- void **set_scale**(value: [Vector2](class_vector2.md))
- [Vector2](class_vector2.md) **get_scale**()

The node's scale, relative to the node's parent. Unscaled value: `(1, 1)`. See also global_scale.

**Note:** Negative X scales in 2D are not decomposable from the transformation matrix. Due to the way scale is represented with transformation matrices in Godot, negative scales on the X axis will be changed to negative scales on the Y axis and a rotation of 180 degrees when decomposed.

float **skew** = `0.0` 🔗

- void **set_skew**(value: float)
- float **get_skew**()

If set to a non-zero value, slants the node in one direction or another. This can be used for pseudo-3D effects. See also global_skew.

**Note:** Skew is performed on the X axis only, and *between* rotation and scaling.

**Note:** This property is edited in the inspector in degrees. If you want to use degrees in a script, use `skew = deg_to_rad(value_in_degrees)`.

[Transform2D](class_transform2d.md) **transform** 🔗

- void **set_transform**(value: [Transform2D](class_transform2d.md))
- [Transform2D](class_transform2d.md) **get_transform**()

The node's [Transform2D](class_transform2d.md), relative to the node's parent. See also global_transform.

## Method Descriptions

void **apply_scale**(ratio: [Vector2](class_vector2.md)) 🔗

Multiplies the current scale by the `ratio` vector.

float **get_angle_to**(point: [Vector2](class_vector2.md)) const 🔗

Returns the angle between the node and the `point` in radians. See also look_at().

[Illustration of the returned angle.](https://raw.githubusercontent.com/godotengine/godot-docs/master/img/node2d_get_angle_to.png)

[Transform2D](class_transform2d.md) **get_relative_transform_to_parent**(parent: [Node](class_node.md)) const 🔗

Returns the [Transform2D](class_transform2d.md) relative to this node's parent.

void **global_translate**(offset: [Vector2](class_vector2.md)) 🔗

Adds the `offset` vector to the node's global position.

void **look_at**(point: [Vector2](class_vector2.md)) 🔗

Rotates the node so that its local +X axis points towards the `point`, which is expected to use global coordinates. This method is a combination of both rotate() and get_angle_to().

`point` should not be the same as the node's position, otherwise the node always looks to the right.

void **move_local_x**(delta: float, scaled: bool = false) 🔗

Applies a local translation on the node's X axis with the amount specified in `delta`. If `scaled` is `false`, normalizes the movement to occur independently of the node's scale.

void **move_local_y**(delta: float, scaled: bool = false) 🔗

Applies a local translation on the node's Y axis with the amount specified in `delta`. If `scaled` is `false`, normalizes the movement to occur independently of the node's scale.

void **rotate**(radians: float) 🔗

Applies a rotation to the node, in radians, starting from its current rotation. This is equivalent to `rotation += radians`.

[Vector2](class_vector2.md) **to_global**(local_point: [Vector2](class_vector2.md)) const 🔗

Transforms the provided local position into a position in global coordinate space. The input is expected to be local relative to the **Node2D** it is called on. e.g. Applying this method to the positions of child nodes will correctly transform their positions into the global coordinate space, but applying it to a node's own position will give an incorrect result, as it will incorporate the node's own transformation into its global position.

[Vector2](class_vector2.md) **to_local**(global_point: [Vector2](class_vector2.md)) const 🔗

Transforms the provided global position into a position in local coordinate space. The output will be local relative to the **Node2D** it is called on. e.g. It is appropriate for determining the positions of child nodes, but it is not appropriate for determining its own position relative to its parent.

void **translate**(offset: [Vector2](class_vector2.md)) 🔗

Translates the node by the given `offset` in local coordinates. This is equivalent to `position += offset`.
