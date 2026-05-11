# Upscaler workflows

Drop **API-format** ComfyUI workflow JSONs here using these exact filenames:

| Model        | Filename       |
|--------------|----------------|
| Real-ESRGAN  | `esrgan.json`  |
| DiffBIR-v2   | `diffbir.json` |
| SUPIR        | `supir.json`   |

In ComfyUI: top-right menu → **Save (API Format)**. The graphical `.json`
exports from File → Save will NOT work (different schema).

Each workflow should contain at least one `LoadImage` node (input image is
injected into the first one) and one `SaveImage` node (output prefix is
overwritten on the first one). KSampler `seed` and Upscale `scale_by` are
optionally overridden when the corresponding nodes are present.
