<!-- src:https://docs.godotengine.org/en/4.7/classes/class_animatablebody3d.html format:llm-dense godot-4.7 -->
#DOC classes/class_animatablebody3d.md

# AnimatableBody3D

**Inherits:** [StaticBody3D](class_staticbody3d.md) **<** [PhysicsBody3D](class_physicsbody3d.md) **<** CollisionObject3D **<** [Node3D](class_node3d.md) **<** [Node](class_node.md) **<** Object

A 3D physics body that can't be moved by external forces. When moved manually, it affects other bodies in its path.

## Description

An animatable 3D physics body. It can't be moved by external forces or contacts, but can be moved manually by other means such as code, [AnimationMixer](class_animationmixer.md)s (with [AnimationMixer.callback_mode_process](class_animationmixer.md) set to [AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS](class_animationmixer.md)), and RemoteTransform3D.

When **AnimatableBody3D** is moved, its linear and angular velocity are estimated and used to affect other physics bodies in its path. This makes it useful for moving platforms, doors, and other moving objects.

## Tutorials

- [Physics introduction](../tutorials/physics/physics_introduction.md)
- [Troubleshooting physics issues](../tutorials/physics/troubleshooting_physics_issues.md)
- [3D Physics Tests Demo](https://godotengine.org/asset-library/asset/2747)
- [Third Person Shooter (TPS) Demo](https://godotengine.org/asset-library/asset/2710)
- [3D Voxel Demo](https://godotengine.org/asset-library/asset/2755)

## Properties

bool | sync_to_physics | `true`

## Property Descriptions

bool **sync_to_physics** = `true` 🔗

- void **set_sync_to_physics**(value: bool)
- bool **is_sync_to_physics_enabled**()

If `true`, the body's movement will be synchronized to the physics frame. This is useful when animating movement via [AnimationPlayer](class_animationplayer.md), for example on moving platforms. Do **not** use together with [PhysicsBody3D.move_and_collide()](class_physicsbody3d.md).
