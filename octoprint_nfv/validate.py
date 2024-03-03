import os
import re


def parse_gcode(file_path):
    # Regular expression patterns to extract nozzle diameter and filament alert_type
    nozzle_pattern = re.compile(r'; nozzle_diameter = ((?:\d+\.\d+,?)+)')
    filament_pattern = re.compile(r'; filament_type = (.+)')
    used_filament_pattern = re.compile(r'; filament used \[mm] = (.+)')
    printer_model = re.compile(r'; printer_model = (.+)')

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
        filament_used_match = used_filament_pattern.search(gcode_content)
        printer_model_match = printer_model.search(gcode_content)
        nozzle_size = None
        filament_type = None
        filament_used = None
        printer_model = None
        if nozzle_match:
            nozzle_size = nozzle_match.group(1).strip().split(',')
        if filament_match:
            filament_type = filament_match.group(1).strip().split(';')
        if filament_used_match:
            filament_used = filament_used_match.group(1).strip("").split(',')
        if printer_model_match:
            printer_model = printer_model_match.group(1).strip()

    return {
        "nozzle_size": nozzle_size, "filament_type": filament_type, "filament_used": filament_used,
        "printer_model": printer_model}


def ends_with_mmu(string):
    match_1 = re.match(r".*mmu[23](s)?$", string)
    match_2 = re.match(r".*mmu[23](s)?is$", string)
    return bool(match_1 or match_2)


def match_ends_with_mmu(string):
    match = re.match(r"^(.*?)(mmu[23](s)?)(is)?$", string)
    if match:
        return match.group(1)
    else:
        return None


def remove_mmu_from_end(text):
    if bool(re.match(r".*mmu[23](s)?$|^mmu[23](s)?$", text)):
        return re.sub(r'mmu[23](s)?$', '', text)
    else:
        return re.sub(r'mmu[23](s)?is$', 'is', text)


def remove_is_from_end(text):
    return re.sub(r'is$', '', text, count=1)


class validator:
    def __init__(self, nozzle, build_plate, extruders, spool_manager, printer, logger, plugin_manager, identifier,
                 printer_profile_manager):
        self.nozzle = nozzle
        self.build_plate = build_plate
        self._spool_manager = spool_manager
        self.extruders = extruders
        self._printer = printer
        self._logger = logger
        self._plugin_manager = plugin_manager
        self._identifier = identifier
        self._printer_profile_manager = printer_profile_manager

    def get_printer_model(self):
        return self._printer_profile_manager.get_current_or_default()['model']

    def send_alert(self, message, alert_type="popup"):
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def check_print(self, file_path):
        if not os.path.exists(file_path):
            self.send_alert(f"File {file_path} not found, no checks will be performed. Press RESUME to continue "
                            f"anyways", "error")
            self._printer.pause_print()
            return
        nozzle_passed = True
        filament_passed = True
        mmu_single_mode = False
        gcode_info = parse_gcode(file_path)
        printer_model = gcode_info["printer_model"]

        if printer_model is None:
            self.send_alert("No printer model found in GCODE, printer model checking won't be performed", "info")

        elif (printer_model is not None and printer_model.lower() != self.get_printer_model().lower() and printer_model
              != ""):
            if self.get_printer_model().lower().endswith("is"):
                if not printer_model.lower().endswith("is"):
                    self.send_alert(f"Printing with non InputShaping profile on a printer that supports input shaping",
                                    "info")

            if remove_is_from_end(self.get_printer_model().lower()) != printer_model.lower():
                self.send_alert(f"Print aborted: Incorrect printer model, {printer_model} found in gcode but "
                                f"{self.get_printer_model()} is set.", "error")
                self._printer.cancel_print()
                return

        # Retrieve the loaded filament alert_type from spool manager
        try:
            loaded_filaments = self._spool_manager.get_loaded_filaments()
        except Exception as e:
            self.send_alert(f"Error retrieving loaded filament: {e}", "error")
            return
        # Parse the GCODE file to extract the nozzle size and filament alert_type

        nozzles = gcode_info["nozzle_size"]
        filament_types = gcode_info["filament_type"]
        filament_used = gcode_info["filament_used"]

        if (ends_with_mmu(printer_model.lower()) and len(nozzles) == 1 and len(filament_types) == 1 and len(
                filament_used) == 1):
            mmu_single_mode = True
            self.send_alert(
                "MMU single mode detected, skipping filament checks, please make sure you pick the tool with the "
                "correct filament", "info")

        if len(nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(f"Number of nozzles ({len(nozzles)}) in the gcode is longer than the number of extruders "
                            f"on your machine ({self.extruders.get_number_of_extruders()})", "error")
            self._printer.cancel_print()

            return
        elif len(nozzles) < self.extruders.get_number_of_extruders() and not mmu_single_mode:
            self.send_alert(
                f"Print paused: Number of nozzles in gcode ({len(nozzles)}) is shorter than the number of extruders("
                f"{self.extruders.get_number_of_extruders()}). Press RESUME to continue", "info")
            self._printer.pause_print()

        if len(filament_types) > len(loaded_filaments) or len(
                nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(
                f"Loaded filaments ({len(loaded_filaments)}) is shorter than the number specified in the gcode "
                f"({len(filament_types)})", "error")
            self._printer.cancel_print()
            return
        elif len(filament_types) < self.extruders.get_number_of_extruders() and not mmu_single_mode:
            self.send_alert(
                f" Print paused: loaded filaments ({len(loaded_filaments)}) is longer than the number specified in "
                f"the gcode ({len(filament_types)}). Press RESUME to continue", "info")
            self._printer.pause_print()

        try:
            for i in range(len(nozzles)):
                if filament_used[i] is not None:
                    # if no filament was used, assume the tool isn't used and skip the check
                    if float(filament_used[i]) == 0:
                        continue

                loaded_filament = loaded_filaments[i] if loaded_filaments is not None else None

                # Check if the loaded filament matches the filament alert_type in the GCODE
                if filament_types[i] is None and filament_passed and not mmu_single_mode:
                    self.send_alert("No filament alert_type found in GCODE, error checking won't be performed", "info")
                    filament_passed = False

                elif loaded_filament is None and filament_passed and not mmu_single_mode:
                    self.send_alert("No filament loaded, error checking won't be performed", "info")
                    filament_passed = False

                elif loaded_filament == -1 and filament_passed and not mmu_single_mode:
                    self.send_alert("Spool Manager plugin is not installed. Filament alert_type will not be checked.",
                                    "info")
                    filament_passed = False

                elif loaded_filament == -2 and filament_passed and not mmu_single_mode:
                    self.send_alert("Error retrieving loaded filament, filament error checking won't be performed",
                                    "info")
                    filament_passed = False
                if filament_passed and not mmu_single_mode:
                    if (filament_types[i].lower() != str(loaded_filament).lower() and gcode_info[
                        "filament_type"][i] is not
                            None):
                        self.send_alert(f"Print aborted: Incorrect filament type on extruder {i + 1}. expected "
                                        f"{filament_types[i]}, but {loaded_filament} is currently loaded", "error")
                        self._printer.cancel_print()
                        return

                # Check if the loaded nozzle size matches the nozzle size in the GCODE
                if nozzles[i] is None and nozzle_passed:
                    self.send_alert("No nozzle size found in GCODE, error checking won't be performed", "info")
                    nozzle_passed = False

                elif self.extruders.get_nozzle_size_for_extruder(i + 1) is None and nozzle_passed:
                    self.send_alert(f"No nozzle selected for extruder {i + 1}, error checking won't be performed",
                                    "info")
                    nozzle_passed = False

                if nozzle_passed:
                    if (float(nozzles[i]) != float(self.extruders.get_nozzle_size_for_extruder(i + 1)) and
                            nozzles[i] is
                            not None):
                        self.send_alert(f"Print aborted: Incorrect nozzle size on extruder {i + 1}. expected "
                                        f"{nozzles[i]}mm nozzle, but"
                                        f" {self.extruders.get_nozzle_size_for_extruder(i + 1)}mm nozzle is currently "
                                        f"installed", "error")
                        self._printer.cancel_print()
                        return

                # Check if the build plate is compatible with the loaded filament
                if filament_types[i] is not None:
                    if not self.build_plate.is_filament_compatible_with_build_plate(filament_types[i]):
                        self._logger.error("Print aborted: Incompatible build plate")
                        self.send_alert(f"Print aborted: Incompatible build plate, current plate doesn't support "
                                        f"{gcode_info['filament_type'][i]}",
                                        "error")
                        self._printer.cancel_print()
                        return

            if nozzle_passed and filament_passed:
                self.send_alert("Print passed nozzle and filament check", "success")
                self._logger.info("Print passed nozzle and filament check...")
            else:
                out_str = ""
                data = {
                    "nozzle_passed": nozzle_passed, "filament_passed": filament_passed
                }
                for key, value in data.items():
                    if not value:
                        out_str += f"{key}, "
                out_str = out_str[:-2]
                self.send_alert(f"Not all checks passed, the following checks failed: {out_str}.\nPlease check your "
                                f"config and press resume to continue.", "info")
                self._printer.pause_print()

        except Exception as e:
            self.send_alert(f"An error occurred while running checks, please report this error on github. \n"
                            f"Error: \"{e}\" \n please check your config and press resume to continue.",
                            "error")
            self._printer.pause_print()
            return
