# Nozzle Filament Validator 3.2.0

## Highlights

- Validation now runs before print-file G-code is allowed to reach the printer.
- Validation failures are fail-closed while still allowing an explicit, time-limited
  **Continue anyway** decision.
- Active validation and spool-selection prompts survive page reloads and reconnects.
- Filament type validation and filament/spool name validation can now be enabled independently.

## Pre-print safety gate

- Added an OctoPrint G-code queuing hook that validates the selected local G-code file before
  allowing job or file commands through.
- Commands are suppressed when validation fails, and OctoPrint cancellation and safety commands
  remain allowed so cancellation can complete normally.
- The gate covers prints started from the OctoPrint UI, API, or another plugin.
- Printer SD-card jobs are blocked because OctoPrint cannot read the remote file contents for
  validation.

## Validation prompts

- Missing, unreadable, malformed, or mismatched slicer metadata now produces a warning prompt.
- Users can explicitly continue or cancel the print.
- No response before the configured validation timeout blocks the print automatically.
- Prompt deadlines are enforced by the backend and cannot be reset by reloading the page.
- Reconnecting clients receive the active prompt with the actual remaining timeout.
- Duplicate prompt notifications are suppressed on clients that already displayed the prompt.
- Spool-selection prompts now use the same reconnect and remaining-time behavior.

## Filament controls

- Added a **Validate filament types** setting for material comparison with SpoolManager.
- Renamed the existing spool check in the UI to **Validate filament/spool names** for clarity.
- Either filament check can be disabled without disabling nozzle, build-plate, printer-model,
  or tool-count validation.
- Existing installations are migrated with filament type validation enabled by default.

## Reliability fixes

- Fixed plugin initialization when SpoolManager is not installed.
- Fixed anonymous-user checks in the Simple API.
- Registered API commands that were implemented but not exposed.
- Fixed the validation timeout command mismatch and boolean setting parsing.
- Fixed build-plate creation and selection behavior, including selection after deleting the
  current plate.
- Fixed short G-code files losing their first character during parsing.
- Added tolerant UTF-8 parsing and stricter, explicit `skip_validation` matching.
- Added structural and numeric slicer metadata validation.
- Fixed frontend promise rejection and filament setting display logic.

## Verification

- Added unit coverage for the preflight gate, cancellation passthrough, fail-closed metadata
  handling, explicit overrides, independent filament toggles, and active prompt replay.
- Python compilation, JavaScript syntax checks, and whitespace validation pass.
