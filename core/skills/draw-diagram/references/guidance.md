# Diagram Guidance

Prefer one of these patterns:

- Flowchart: stacked nodes, labeled yes/no arrows from diamonds
- Architecture: left-to-right services, stores, and external systems with protocol labels
- Decision tree: diamonds at branch points, short outcome labels
- Data flow: inputs, transforms, stores, and outputs with directional arrows

For large diagrams:
- Use a light background rectangle with low opacity to group zones
- Keep labels short
- Split dense concepts into multiple nodes instead of multiline labels

If the user asks for a sequence diagram, Gantt chart, pie chart, or bar chart, say this tool is a poor fit and suggest Mermaid instead.
