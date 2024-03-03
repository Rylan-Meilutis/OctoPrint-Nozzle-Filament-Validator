# OctoPrint-Nozzle-Filament-Validator

This plugin validates slicer profile, nozzle size (for each extruder), build plate, and filament type (for each
extruder) before starting a print.
It uses the slicer config present in the gcode to work, it is not a replacement for checking yourself but can help to
prevent simple
mistakes from occurring

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/archive/master.zip


## Needed plugins

- [Spool Manager](https://plugins.octoprint.org/plugins/SpoolManager/) - This plugin will
  automatically set the filament type for the spool if you have it installed and have set
  the filament type for the spool.

## Configuration

Make sure the printer model is set in the printer profile. This is used to determine whether gcode has been sliced for
your printer.
(if you get a message saying the printer model is wrong, you can copy the printer model from the error message if you
know you sliced the gcode correctly and paste it into the printer profile).

Go to plugin settings and set your nozzle size for each extruder (or extruder 1 if you have a single tool head machine,
and build plate.

Filament type should be set automatically if you have spool manager installed and have set
the filament type for the spool.
If you do not have spool manager installed, filament type will not be checked.

If using a plugin that runs a .gcode file such as the continuous print queue plugin, You can skip gcode validation for that file by adding
```; skip_validation``` anywhere in the gcode file (This works on all .gcode files so be careful when using it). 

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

## Coming Soon

-  Add the ability to scan the gcode before a print to verify the settings
-  Add the ability to auto scan new files for compatability when they are uploaded and remove them if they are not
compatible
-  Add the ability to scan all files and remove ones that aren't compatible

