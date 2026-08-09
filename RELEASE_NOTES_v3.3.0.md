# Nozzle Filament Validator 3.3.0b2

## Early file validation

- Added an opt-in setting to validate local machine-code files automatically after upload.
- Added a checkmark action to local G-code rows in OctoPrint's Files panel for on-demand
  validation. Printer SD files are excluded because their contents are not locally readable.
- Successful results are stored in OctoPrint's file metadata and can be reused at print start,
  including after a server restart.
- Cached results are accepted only when the file signature and all validation inputs are
  unchanged. Changes to the printer profile, build plate, extruder nozzles, loaded filament or
  spool names, validation settings, or tool mapping force a fresh pre-print check.
- User overrides are deliberately not cached; continuing past a warning applies only to that
  validation request.
- Upload and on-demand validation run in a background worker so validation prompts do not block
  OctoPrint's upload or plugin API request handling.

## Operation without SpoolManager

- Fixed the remaining issue #17 failure where the extruder-info API indexed an empty spool-name
  list and left the plugin settings page blank when SpoolManager was not installed.
- Added persistent per-extruder loaded-material selectors when SpoolManager is unavailable, so
  filament-type validation can still run.
- Added an installation notice and disabled filament/spool-name validation when neither supported
  spool plugin is available. Manual material selections intentionally do not stand in for unique
  spool names.
- Added first-class support for the OctoPrint Spoolman plugin. Selected Spoolman materials feed
  filament-type validation, while the unique `spoolman:<id>` value supports optional spool-name
  validation. If both integrations are installed, SpoolManager remains the preferred source.
- Added RME Compatibility as a fallback metadata provider when neither SpoolManager nor Spoolman is
  available. Its `rme-filament-report-v1` per-tool loadout supplies filament materials, and
  inventory-backed spools expose stable `rme:<provider>:<id>` identifiers for name validation.

## Filament provider compatibility

- Validation provider priority is SpoolManager, Spoolman, RME Compatibility, then the manual
  per-extruder material selections.
- SpoolManager supplies the loaded material and spool name. Spoolman supplies the loaded material
  and a stable `spoolman:<id>` identity.
- RME Compatibility's internal spool backend supplies the same validation inputs: loaded material
  plus a stable `rme:<provider>:<id>` identity. If RME is backed by an installed Spoolman plugin,
  NFV uses Spoolman directly because it has higher priority.
- RME firmware-only loadouts still support material, nozzle, build-plate, upload, and cached
  pre-print validation. They cannot perform unique spool-name validation because firmware metadata
  does not identify a specific physical spool.
