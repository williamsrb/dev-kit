<!-- src:https://docs.godotengine.org/en/4.7/classes/class_multimeshinstance3d.html format:llm-dense godot-4.7 -->
#DOC classes/class_multimeshinstance3d.md

# MultiMeshInstance3D

**Inherits:** GeometryInstance3D **<** VisualInstance3D **<** [Node3D](class_node3d.md) **<** [Node](class_node.md) **<** Object

Node that instances a [MultiMesh](class_multimesh.md).

## Description

**MultiMeshInstance3D** is a specialized node to instance GeometryInstance3Ds based on a [MultiMesh](class_multimesh.md) resource.

This is useful to optimize the rendering of a high number of instances of a given mesh (for example trees in a forest or grass strands).

## Tutorials

- [Using MultiMeshInstance](../tutorials/3d/using_multi_mesh_instance.md)
- [Optimization using MultiMeshes](../tutorials/performance/using_multimesh.md)
- Animating thousands of fish with MultiMeshInstance

## Properties

[MultiMesh](class_multimesh.md) | multimesh

## Property Descriptions

[MultiMesh](class_multimesh.md) **multimesh** 🔗

- void **set_multimesh**(value: [MultiMesh](class_multimesh.md))
- [MultiMesh](class_multimesh.md) **get_multimesh**()

The [MultiMesh](class_multimesh.md) resource that will be used and shared among all instances of the **MultiMeshInstance3D**.
