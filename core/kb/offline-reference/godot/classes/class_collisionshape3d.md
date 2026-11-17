<!-- src:https://docs.godotengine.org/en/4.7/classes/class_collisionshape3d.html format:llm-dense godot-4.7 -->
#DOC classes/class_collisionshape3d.md

# CollisionShape3D

**Inherits:** [Node3D](class_node3d.md) **<** [Node](class_node.md) **<** Object

A node that provides a Shape3D to a CollisionObject3D parent.

## Description

A node that provides a Shape3D to a CollisionObject3D parent and allows it to be edited. This can give a detection shape to an [Area3D](class_area3d.md) or turn a [PhysicsBody3D](class_physicsbody3d.md) into a solid object.

**Warning:** A non-uniformly scaled **CollisionShape3D** will likely not behave as expected. Make sure to keep its scale the same on all axes and adjust its shape resource instead.

## Tutorials

- [Physics introduction](../tutorials/physics/physics_introduction.md)
- [3D Kinematic Character Demo](https://godotengine.org/asset-library/asset/2739)
- [3D Platformer Demo](https://godotengine.org/asset-library/asset/2748)
- [Third Person Shooter (TPS) Demo](https://godotengine.org/asset-library/asset/2710)

## Properties

Color | debug_color | `Color(0, 0, 0, 0)`
bool | debug_fill | `true`
bool | disabled | `false`
Shape3D | shape |

## Methods

void | make_convex_from_siblings()
void | resource_changed(resource: [Resource](class_resource.md))

## Property Descriptions

Color **debug_color** = `Color(0, 0, 0, 0)` 🔗

- void **set_debug_color**(value: Color)
- Color **get_debug_color**()

The collision shape color that is displayed in the editor, or in the running project if **Debug > Visible Collision Shapes** is checked at the top of the editor.

**Note:** The default value is [ProjectSettings.debug/shapes/collision/shape_color](class_projectsettings.md). The `Color(0, 0, 0, 0)` value documented here is a placeholder, and not the actual default debug color.

bool **debug_fill** = `true` 🔗

- void **set_enable_debug_fill**(value: bool)
- bool **get_enable_debug_fill**()

If `true`, when the shape is displayed, it will show a solid fill color in addition to its wireframe.

bool **disabled** = `false` 🔗

- void **set_disabled**(value: bool)
- bool **is_disabled**()

A disabled collision shape has no effect in the world. This property should be changed with Object.set_deferred().

Shape3D **shape** 🔗

- void **set_shape**(value: Shape3D)
- Shape3D **get_shape**()

The actual shape owned by this collision shape.

## Method Descriptions

void **make_convex_from_siblings**() 🔗

Sets the collision shape's shape to the addition of all its convexed [MeshInstance3D](class_meshinstance3d.md) siblings geometry.

void **resource_changed**(resource: [Resource](class_resource.md)) 🔗

**Deprecated:** Use [Resource.changed](class_resource.md) instead.

This method does nothing.
