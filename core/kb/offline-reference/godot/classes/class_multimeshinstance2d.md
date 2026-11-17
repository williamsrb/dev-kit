<!-- src:https://docs.godotengine.org/en/4.7/classes/class_multimeshinstance2d.html format:llm-dense godot-4.7 -->
#DOC classes/class_multimeshinstance2d.md

# MultiMeshInstance2D

**Inherits:** [Node2D](class_node2d.md) **<** [CanvasItem](class_canvasitem.md) **<** [Node](class_node.md) **<** Object

Node that instances a [MultiMesh](class_multimesh.md) in 2D.

## Description

**MultiMeshInstance2D** is a specialized node to instance a [MultiMesh](class_multimesh.md) resource in 2D. This can be faster to render compared to displaying many [Sprite2D](class_sprite2d.md) nodes with large transparent areas, especially if the nodes take up a lot of space on screen at high viewport resolutions. This is because using a mesh designed to fit the sprites' opaque areas will reduce GPU fill rate utilization (at the cost of increased vertex processing utilization).

Usage is the same as [MultiMeshInstance3D](class_multimeshinstance3d.md).

## Properties

[MultiMesh](class_multimesh.md) | multimesh
Texture2D | texture

## Signals

**texture_changed**() 🔗

Emitted when the texture is changed.

## Property Descriptions

[MultiMesh](class_multimesh.md) **multimesh** 🔗

- void **set_multimesh**(value: [MultiMesh](class_multimesh.md))
- [MultiMesh](class_multimesh.md) **get_multimesh**()

The [MultiMesh](class_multimesh.md) that will be drawn by the **MultiMeshInstance2D**.

Texture2D **texture** 🔗

- void **set_texture**(value: Texture2D)
- Texture2D **get_texture**()

The Texture2D that will be used if using the default CanvasItemMaterial. Can be accessed as `TEXTURE` in CanvasItem shader.
