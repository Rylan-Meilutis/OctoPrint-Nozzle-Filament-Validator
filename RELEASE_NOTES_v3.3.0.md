# Nozzle Filament Validator 3.3.0dev1

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
