# Image enhancer workflows

Drop **API-format** ComfyUI workflow JSONs here using these exact filenames:

| Mode | Filename |
|---|---|
| Global Enhance | `global.json` |
| Painted Detail | `detail.json` |
| Face Boost | `face.json` |
| Repair Pass | `repair.json` |

Each workflow should contain at least one `LoadImage` node and one `SaveImage` node.
If a mask is used, prefer a dedicated `LoadImageMask` or comparable mask input node.

The enhancer app will inject the first available `LoadImage`, `SaveImage`, and any obvious
`seed`/`strength`/`denoise`/`blend`/`opacity` inputs it can find.
