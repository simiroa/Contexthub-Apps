## 2026-07-10T10:32:52Z

You are a teamwork_preview_worker. Your working directory is C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_pr1_gen2.
Your task is to implement the PR1 (Docs Freeze) phase of the Qt GUI Design System Simplification project.

Please perform the following updates on the 4 files in `agent-docs/`:

1. `agent-docs/qt-component-catalog.md`:
   - Remove all the conceptual "phantom" components that are not actually implemented in the codebase (such as InputCard, PreviewCard, StatusCard, QueueCard, QueueManagerCard, ExecutionCard, FullSplitWorkspace, ImagePreviewCard, AudioPreviewCard, VideoPreviewCard, DocumentPreviewCard, Viewport3DCard, DropZoneCard, BatchListCard, PromptCard, HistoryPanel, PresetSelectorCard, PresetParameterCard, ParameterControlsCard, ModelSelectorCard, ParameterStrip, ExportFoldoutCard, OutputOptionsCard, ProgressStatusBar, DependencyStatusCard, EmptyStateCard, ResultInspectorCard, ToolbarRow, CompareWorkspace, ChannelMapCard).
   - Only list the components that actually exist in the live API surface (Core components: build_shell_stylesheet, HeaderSurface, apply_app_icon, attach_size_grip, get_shell_metrics, get_shell_palette, refresh_runtime_preferences, runtime_settings_signature, run_confirm_dialog, set_surface_role/set_button_role/set_badge_role, qt_t. Common components: ExportFoldoutPanel, FixedParameterPanel. Optional components: PreviewListPanel, AssetWorkspacePanel, ComparativePreviewWidget, CollapsibleSection, ElidedLabel, DropListWidget, get_shell_accent_cycle, set_transparent_surface).
   - Explicitly document that the following 5 panels and Hub's VideoPreviewCard are deleted/banned: ExportRunPanel, PresetParameterPanel, ParameterControlsPanel, QueueManagerPanel, ResultInspectorPanel.
   - Simplify the Template Mapping section to refer only to real components and recipes.

2. `agent-docs/gui-runtime-contract.md`:
   - Explicitly list the deleted/banned panels (ExportRunPanel, PresetParameterPanel, ParameterControlsPanel, QueueManagerPanel, ResultInspectorPanel).
   - Document the template=tag policy: ui.template in the manifest is purely a metadata/inventory and capture-sweep tag, not a runtime framework class loader.
   - Document K2: Prohibit shared BaseAppWindow / template base classes globally across all application tiers.
   - Document the Two-Plane SSOT concept:
     - Product Shared runtime original = Hub Runtimes/Shared.
     - Dev Shared mirror original = Apps dev-tools/runtime/Shared.
     - Market ZIP never contains Shared runtime code.
     - Release Gate (K13) requirement: any shared runtime behavior changes must name a linked Hub commit/PR or sync.

3. `agent-docs/gui-runtime-status.md`:
   - Update to reflect exactly 28 active apps.
   - Remove the out-of-scope description stating that audio and comfyui categories are excluded from standard sweeps (since they are actively swept).

4. `agent-docs/agent.md`:
   - Update the total market count from 43 to 28.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

After finishing, write a handoff.md in your working directory C:\Users\HG_maison\Documents\Contexthub-Apps\.agents\worker_pr1_gen2 detailing the modifications made, how you verified them, and pass results.
