import os
import re


def parse_gcode(file_path):
    # Regular expression patterns to extract nozzle diameter and filament alert_type
    nozzle_pattern = re.compile(r'; nozzle_diameter = ((?:\d+\.\d+,?)+)')
    filament_pattern = re.compile(r'; filament_type = (.+)')

    # Number of lines to read from the end of the file
    num_lines = 1000

    with open(file_path, 'r') as file:
        # Move the file pointer to the end
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        # Track the position in the file
        pos = file_size - 1
        newline_count = 0
        # Read the file backwards until we find the last 100 lines or reach the beginning of the file
        while pos > 0 and newline_count < num_lines:
            file.seek(pos)
            char = file.read(1)
            if char == '\n':
                newline_count += 1
                if newline_count == num_lines:
                    break
            pos -= 1
        # Read the last 100 lines
        lines = file.readlines()

        # Extract nozzle diameter and filament alert_type from the collected lines
        gcode_content = ''.join(lines)
        nozzle_match = nozzle_pattern.search(gcode_content)
        filament_match = filament_pattern.search(gcode_content)
        nozzle_size = None
        filament_type = None
        if nozzle_match:
            nozzle_size = nozzle_match.group(1).strip().split(',')
        if filament_match:
            filament_type = filament_match.group(1).strip().split(';')

    return {"nozzle_size": nozzle_size, "filament_type": filament_type}


class validator:
    def __init__(self, nozzle, build_plate, extruders, spool_manager, printer, logger, plugin_manager, identifier):
        self.nozzle = nozzle
        self.build_plate = build_plate
        self._spool_manager = spool_manager
        self.extruders = extruders
        self._printer = printer
        self._logger = logger
        self._plugin_manager = plugin_manager
        self._identifier = identifier

    def send_alert(self, message, alert_type="popup"):
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def check_print(self, file_path):
        nozzle_passed = True
        filament_passed = True
        build_plate_passed = True
        # Retrieve the loaded filament alert_type from spool manager
        try:
            loaded_filaments = self._spool_manager.get_loaded_filaments()
        except Exception as e:
            self.send_alert(f"Error retrieving loaded filament: {e}", "error")
            return
        # Parse the GCODE file to extract the nozzle size and filament alert_type
        gcode_info = parse_gcode(file_path)

        self._logger.info(f"Loaded filaments: {loaded_filaments}")
        self._logger.info(f"GCODE info: {gcode_info}")
        self._logger.info(f"Number of extruders: {self.extruders.get_number_of_extruders()}")

        if len(gcode_info["nozzle_size"]) > self.extruders.get_number_of_extruders():
            self.send_alert("number of nozzles is longer than the number of extruders", "error")
            self._printer.cancel_print()

            return
        elif len(gcode_info["nozzle_size"]) < self.extruders.get_number_of_extruders():
            self.send_alert("number of nozzles is shorter than the number of extruders. Press RESUME to continue",
                            "info")
            self._printer.pause_print()

        if len(gcode_info["filament_type"]) > len(loaded_filaments) or len(
                gcode_info["nozzle_size"]) > self.extruders.get_number_of_extruders():
            self.send_alert("loaded filaments is shorter than the number specified in the gcode", "error")
            self._printer.cancel_print()
            return
        elif len(gcode_info["filament_type"]) < self.extruders.get_number_of_extruders():
            self.send_alert(
                "loaded filaments is longer than the number specified in the gcode. Press RESUME to continue",
                "info")
            self._printer.pause_print()
        try:
            for i in range(len(gcode_info["nozzle_size"])):
                loaded_filament = loaded_filaments[i] if loaded_filaments is not None else None

                # Check if the loaded filament matches the filament alert_type in the GCODE
                if gcode_info["filament_type"][i] is None and filament_passed:
                    self.send_alert("No filament alert_type found in GCODE, error checking won't be performed", "info")
                    filament_passed = False

                elif loaded_filament is None and filament_passed:
                    self.send_alert("No filament loaded, error checking won't be performed", "info")
                    filament_passed = False

                elif loaded_filament == -1 and filament_passed:
                    self.send_alert("Spool Manager plugin is not installed. Filament alert_type will not be checked.",
                                    "info")
                    filament_passed = False

                elif loaded_filament == -2 and filament_passed:
                    self.send_alert("Error retrieving loaded filament, filament error checking won't be performed",
                                    "info")
                    filament_passed = False

                if (gcode_info["filament_type"][i].lower() != str(loaded_filament).lower() and gcode_info[
                    "filament_type"][i] is not
                        None and filament_passed is not False):
                    self.send_alert(f"Print aborted: Incorrect filament type on extruder {i+1}", "error")
                    self._printer.cancel_print()
                    return

                # Check if the loaded nozzle size matches the nozzle size in the GCODE
                if gcode_info["nozzle_size"][i] is None and nozzle_passed:
                    self.send_alert("No nozzle size found in GCODE, error checking won't be performed", "info")
                    nozzle_passed = False

                elif self.extruders.get_nozzle_size_for_extruder(i + 1) is None and nozzle_passed:
                    self.send_alert(f"No nozzle selected for extruder {i+1}, error checking won't be performed", "info")
                    nozzle_passed = False

                if (float(gcode_info["nozzle_size"][i]) != float(self.extruders.get_nozzle_size_for_extruder(i + 1)) and
                        gcode_info["nozzle_size"][i] is
                        not None and nozzle_passed is not False):
                    self._logger.error(f"Print aborted: Incorrect nozzle size on extruder {i + 1}")
                    self.send_alert(f"Print aborted: Incorrect nozzle size on extruder {i + 1}", "error")
                    self._printer.cancel_print()
                    return

                # Check if the build plate is compatible with the loaded filament
                if gcode_info["filament_type"][i] is not None:
                    if not self.build_plate.is_filament_compatible_with_build_plate(gcode_info["filament_type"][i]):
                        self._logger.error("Print aborted: Incompatible build plate")
                        self.send_alert(f"Print aborted: Incompatible build plate, current plate doesn't support "
                                        f"{gcode_info['filament_type'][i]}",
                                        "error")
                        self._printer.cancel_print()
                        return

            if nozzle_passed and filament_passed and build_plate_passed:
                self.send_alert("Print passed nozzle and filament check", "success")
                self._logger.info("Print passed nozzle and filament check...")

        except IndexError:
            self.send_alert("list of nozzles is shorter than the number of extruders", "error")
            self._printer.cancel_print()
            return

        except Exception as e:
            self.send_alert(f"Error: {e}", "error")
            return
