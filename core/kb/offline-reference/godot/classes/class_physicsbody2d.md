<!-- src:https://docs.godotengine.org/en/4.7/classes/class_physicsbody2d.html format:llm-dense godot-4.7 -->
#DOC classes/class_physicsbody2d.md

# PhysicsBody2D

**Inherits:** CollisionObject2D **<** [Node2D](class_node2d.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

**Inherited By:** [CharacterBody2D](class_characterbody2d.md), [RigidBody2D](class_rigidbody2d.md), [StaticBody2D](class_staticbody2d.md)

Abstract base class for 2D game objects affected by physics.

## Description

**PhysicsBody2D** is an abstract base class for 2D game objects affected by physics. All 2D physics bodies inherit from it.

## Tutorials

- [Physics introduction](../tutorials/physics/physics_introduction.md)
- [Troubleshooting physics issues](../tutorials/physics/troubleshooting_physics_issues.md)

## Properties

bool | input_pickable | `false` (overrides CollisionObject2D)

## Methods

void | add_collision_exception_with(body: [Node](class_node.md))
[Array](class_array.md)[PhysicsBody2D] | get_collision_exceptions()
[Vector2](class_vector2.md) | get_gravity() const
KinematicCollision2D | move_and_collide(motion: [Vector2](class_vector2.md), test_only: bool = false, safe_margin: float = 0.08, recovery_as_collision: bool = false)
void | remove_collision_exception_with(body: [Node](class_node.md))
bool | test_move(from: [Transform2D](class_transform2d.md), motion: [Vector2](class_vector2.md), collision: KinematicCollision2D = null, safe_margin: float = 0.08, recovery_as_collision: bool = false)

## Method Descriptions

void **add_collision_exception_with**(body: [Node](class_node.md)) 🔗

Adds a body to the list of bodies that this body can't collide with.

[Array](class_array.md)[PhysicsBody2D] **get_collision_exceptions**() 🔗

Returns an array of nodes that were added as collision exceptions for this body.

[Vector2](class_vector2.md) **get_gravity**() const 🔗

Returns the gravity vector computed from all sources that can affect the body, including all gravity overrides from [Area2D](class_area2d.md) nodes and the global world gravity.

KinematicCollision2D **move_and_collide**(motion: [Vector2](class_vector2.md), test_only: bool = false, safe_margin: float = 0.08, recovery_as_collision: bool = false) 🔗

Moves the body along the vector `motion`. In order to be frame rate independent in [Node._physics_process()](class_node.md) or [Node._process()](class_node.md), `motion` should be computed using `delta`.

Returns a KinematicCollision2D, which contains information about the collision when stopped, or when touching another body along the motion.

If `test_only` is `true`, the body does not move but the would-be collision information is given.

`safe_margin` is the extra margin used for collision recovery (see [CharacterBody2D.safe_margin](class_characterbody2d.md) for more details).

If `recovery_as_collision` is `true`, any depenetration from the recovery phase is also reported as a collision; this is used e.g. by [CharacterBody2D](class_characterbody2d.md) for improving floor detection during floor snapping.

void **remove_collision_exception_with**(body: [Node](class_node.md)) 🔗

Removes a body from the list of bodies that this body can't collide with.

bool **test_move**(from: [Transform2D](class_transform2d.md), motion: [Vector2](class_vector2.md), collision: KinematicCollision2D = null, safe_margin: float = 0.08, recovery_as_collision: bool = false) 🔗

Checks for collisions without moving the body. In order to be frame rate independent in [Node._physics_process()](class_node.md) or [Node._process()](class_node.md), `motion` should be computed using `delta`.

Virtually sets the node's position, scale and rotation to that of the given [Transform2D](class_transform2d.md), then tries to move the body along the vector `motion`. Returns `true` if a collision would stop the body from moving along the whole path.

`collision` is an optional object of type KinematicCollision2D, which contains additional information about the collision when stopped, or when touching another body along the motion.

`safe_margin` is the extra margin used for collision recovery (see [CharacterBody2D.safe_margin](class_characterbody2d.md) for more details).

If `recovery_as_collision` is `true`, any depenetration from the recovery phase is also reported as a collision; this is useful for checking whether the body would *touch* any other bodies.
