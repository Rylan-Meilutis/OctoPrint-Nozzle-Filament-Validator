# OctoPrint-Nozzle-Filament-Validator

This plugin validates nozzle size, build plate, and filament type before starting a print.
It uses provided gcode setting to work, it is not a replacement for checking yourself but can help to prevent simple
mistakes from occurring

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/archive/master.zip

## Configuration

Go to plugin settings and set your nozzle size, and build plate.
Filament type should be set automatically if you have spool manager installed and have set
the filament type for the
spool.
When you go to print, the plugin will check if the gcode settings match the settings you
have set, and that the current filament is supported by the selected build plate. If it
does not match, it will notify you of the error. If it does match, it will notify you of a
successful validation.

## Multi Extruder Support

When configured in octoprint, this plugin supports multi material printers. It will check filament type on each extruder
and nozzle size on each extruder (if your printer has more than 1 nozzle). It will also check the build plate for all
filaments being used. If any of the extruders do not match the settings, it will notify you of the error and cancel the
print.

## In Development
Nothing major at the moment, just bug fixes, removing unused functions, and other minor improvements.



