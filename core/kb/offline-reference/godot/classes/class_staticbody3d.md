<!-- src:https://docs.godotengine.org/en/4.7/classes/class_staticbody3d.html format:llm-dense godot-4.7 -->
#DOC classes/class_staticbody3d.md

# StaticBody3D

**Inherits:** [PhysicsBody3D](class_physicsbody3d.md) **<** CollisionObject3D **<** [Node3D](class_node3d.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** [AnimatableBody3D](class_animatablebody3d.md)

A 3D physics body that can't be moved by external forces. When moved manually, it doesn't affect other bodies in its path.

## Description

A static 3D physics body. It can't be moved by external forces or contacts, but can be moved manually by other means such as code, [AnimationMixer](class_animationmixer.md)s (with [AnimationMixer.callback_mode_process](class_animationmixer.md) set to [AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS](class_animationmixer.md)), and RemoteTransform3D.

When **StaticBody3D** is moved, it is teleported to its new position without affecting other physics bodies in its path. If this is not desired, use [AnimatableBody3D](class_animatablebody3d.md) instead.

**StaticBody3D** is useful for completely static objects like floors and walls, as well as moving surfaces like conveyor belts and circular revolving platforms (by using constant_linear_velocity and constant_angular_velocity).

## Tutorials

- [Physics introduction](../tutorials/physics/physics_introduction.md)
- [Troubleshooting physics issues](../tutorials/physics/troubleshooting_physics_issues.md)
- [3D Physics Tests Demo](https://godotengine.org/asset-library/asset/2747)
- [Third Person Shooter (TPS) Demo](https://godotengine.org/asset-library/asset/2710)
- [3D Voxel Demo](https://godotengine.org/asset-library/asset/2755)

## Properties

[Vector3](class_vector3.md) | constant_angular_velocity | `Vector3(0, 0, 0)`
[Vector3](class_vector3.md) | constant_linear_velocity | `Vector3(0, 0, 0)`
PhysicsMaterial | physics_material_override |

## Property Descriptions

[Vector3](class_vector3.md) **constant_angular_velocity** = `Vector3(0, 0, 0)` 🔗

- void **set_constant_angular_velocity**(value: [Vector3](class_vector3.md))
- [Vector3](class_vector3.md) **get_constant_angular_velocity**()

The body's constant angular velocity. This does not rotate the body, but affects touching bodies, as if it were rotating.

[Vector3](class_vector3.md) **constant_linear_velocity** = `Vector3(0, 0, 0)` 🔗

- void **set_constant_linear_velocity**(value: [Vector3](class_vector3.md))
- [Vector3](class_vector3.md) **get_constant_linear_velocity**()

The body's constant linear velocity. This does not move the body, but affects touching bodies, as if it were moving.

PhysicsMaterial **physics_material_override** 🔗

- void **set_physics_material_override**(value: PhysicsMaterial)
- PhysicsMaterial **get_physics_material_override**()

The physics material override for the body.

If a material is assigned to this property, it will be used instead of any other physics material, such as an inherited one.
