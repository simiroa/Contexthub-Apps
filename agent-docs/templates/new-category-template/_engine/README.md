# Category Engine Template

Create shared code here when more than one app in the category needs it.

Suggested layout:

- `core/`: menu routing, path resolution, category bootstrap
- `features/`: feature entry scripts used by app wrappers
- `utils/`: helper modules shared across apps
- `setup/`: model downloads or first-run setup when needed
- `manuals/`: sample inputs or internal helper assets

If the category will contain only truly independent apps, you may keep `_engine` minimal or omit it after validating that the category does not need shared behavior.
