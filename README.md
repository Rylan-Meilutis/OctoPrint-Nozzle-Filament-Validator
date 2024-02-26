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
filament type should be set automatically if you have spool manager installed and have set the filament type for the 
spool.
When you go to print it will check if the gcode settings match the settings you have set.
