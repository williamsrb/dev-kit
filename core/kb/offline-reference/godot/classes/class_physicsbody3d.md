<!-- src:https://docs.godotengine.org/en/4.7/classes/class_physicsbody3d.html format:llm-dense godot-4.7 -->
#DOC classes/class_physicsbody3d.md

# PhysicsBody3D

**Inherits:** CollisionObject3D **<** [Node3D](class_node3d.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** [CharacterBody3D](class_characterbody3d.md), PhysicalBone3D, [RigidBody3D](class_rigidbody3d.md), [StaticBody3D](class_staticbody3d.md)

Abstract base class for 3D game objects affected by physics.

## Description

**PhysicsBody3D** is an abstract base class for 3D game objects affected by physics. All 3D physics bodies inherit from it.

**Warning:** With a non-uniform scale, this node will likely not behave as expected. It is advised to keep its scale the same on all axes and adjust its collision shape(s) instead.

## Tutorials

- [Physics introduction](../tutorials/physics/physics_introduction.md)
- [Troubleshooting physics issues](../tutorials/physics/troubleshooting_physics_issues.md)

## Properties

bool | axis_lock_angular_x | `false`
bool | axis_lock_angular_y | `false`
bool | axis_lock_angular_z | `false`
bool | axis_lock_linear_x | `false`
bool | axis_lock_linear_y | `false`
bool | axis_lock_linear_z | `false`

## Methods

void | add_collision_exception_with(body: [Node](class_node.md))
bool | get_axis_lock(axis: BodyAxis) const
[Array](class_array.md)[PhysicsBody3D] | get_collision_exceptions()
[Vector3](class_vector3.md) | get_gravity() const
KinematicCollision3D | move_and_collide(motion: [Vector3](class_vector3.md), test_only: bool = false, safe_margin: float = 0.001, recovery_as_collision: bool = false, max_collisions: int = 1)
void | remove_collision_exception_with(body: [Node](class_node.md))
void | set_axis_lock(axis: BodyAxis, lock: bool)
bool | test_move(from: [Transform3D](class_transform3d.md), motion: [Vector3](class_vector3.md), collision: KinematicCollision3D = null, safe_margin: float = 0.001, recovery_as_collision: bool = false, max_collisions: int = 1)

## Property Descriptions

bool **axis_lock_angular_x** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's rotation in the X axis.

bool **axis_lock_angular_y** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's rotation in the Y axis.

bool **axis_lock_angular_z** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's rotation in the Z axis.

bool **axis_lock_linear_x** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's linear movement in the X axis.

bool **axis_lock_linear_y** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's linear movement in the Y axis.

bool **axis_lock_linear_z** = `false` 🔗

- void **set_axis_lock**(axis: BodyAxis, lock: bool)
- bool **get_axis_lock**(axis: BodyAxis) const

Lock the body's linear movement in the Z axis.

## Method Descriptions

void **add_collision_exception_with**(body: [Node](class_node.md)) 🔗

Adds a body to the list of bodies that this body can't collide with.

bool **get_axis_lock**(axis: BodyAxis) const 🔗

Returns `true` if the specified linear or rotational `axis` is locked.

[Array](class_array.md)[PhysicsBody3D] **get_collision_exceptions**() 🔗

Returns an array of nodes that were added as collision exceptions for this body.

[Vector3](class_vector3.md) **get_gravity**() const 🔗

Returns the gravity vector computed from all sources that can affect the body, including all gravity overrides from [Area3D](class_area3d.md) nodes and the global world gravity.

KinematicCollision3D **move_and_collide**(motion: [Vector3](class_vector3.md), test_only: bool = false, safe_margin: float = 0.001, recovery_as_collision: bool = false, max_collisions: int = 1) 🔗

Moves the body along the vector `motion`. In order to be frame rate independent in [Node._physics_process()](class_node.md) or [Node._process()](class_node.md), `motion` should be computed using `delta`.

The body will stop if it collides. Returns a KinematicCollision3D, which contains information about the collision when stopped, or when touching another body along the motion.

If `test_only` is `true`, the body does not move but the would-be collision information is given.

`safe_margin` is the extra margin used for collision recovery (see [CharacterBody3D.safe_margin](class_characterbody3d.md) for more details).

If `recovery_as_collision` is `true`, any depenetration from the recovery phase is also reported as a collision; this is used e.g. by [CharacterBody3D](class_characterbody3d.md) for improving floor detection during floor snapping.

`max_collisions` allows to retrieve more than one collision result.

void **remove_collision_exception_with**(body: [Node](class_node.md)) 🔗

Removes a body from the list of bodies that this body can't collide with.

void **set_axis_lock**(axis: BodyAxis, lock: bool) 🔗

Locks or unlocks the specified linear or rotational `axis` depending on the value of `lock`.

bool **test_move**(from: [Transform3D](class_transform3d.md), motion: [Vector3](class_vector3.md), collision: KinematicCollision3D = null, safe_margin: float = 0.001, recovery_as_collision: bool = false, max_collisions: int = 1) 🔗

Checks for collisions without moving the body. In order to be frame rate independent in [Node._physics_process()](class_node.md) or [Node._process()](class_node.md), `motion` should be computed using `delta`.

Virtually sets the node's position, scale and rotation to that of the given [Transform3D](class_transform3d.md), then tries to move the body along the vector `motion`. Returns `true` if a collision would stop the body from moving along the whole path.

`collision` is an optional object of type KinematicCollision3D, which contains additional information about the collision when stopped, or when touching another body along the motion.

`safe_margin` is the extra margin used for collision recovery (see [CharacterBody3D.safe_margin](class_characterbody3d.md) for more details).

If `recovery_as_collision` is `true`, any depenetration from the recovery phase is also reported as a collision; this is useful for checking whether the body would *touch* any other bodies.

`max_collisions` allows to retrieve more than one collision result.
