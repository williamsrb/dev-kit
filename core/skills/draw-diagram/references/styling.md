# Styling Defaults

Every diagram should look intentional. Apply a consistent palette unless the user asks for something else:

- Start/info: `#a5d8ff`
- Success/positive path: `#b2f2bb`
- Important/configuration: `#ffec99`
- Decisions/warnings/errors: `#ffc9c9`
- Storage/external systems/alternate path: `#d0bfff`

Use these heuristics:
- Action steps: `fillStyle: "hachure"`
- States and outcomes: `fillStyle: "solid"`
- Error or debug paths: dashed arrows or stronger red/pink accents
- Keep rounded, hand-drawn defaults unless the user asks for a rigid style
