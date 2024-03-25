import logging
import os
import re
from typing import Any, Union

from octoprint_nfv.constants import alert_types


def parse_gcode(file_path: str) -> dict[str, Any]:
    """
    Parse the GCODE file to extract the nozzle diameter and filament type
    :param file_path: the path to the GCODE file
    :return: a dictionary containing the nozzle diameter and filament type
    """
    # Regular expression patterns to extract nozzle diameter and filament alert_type
    nozzle_pattern = re.compile(r'; nozzle_diameter = ((?:\d+\.\d+,?)+)')
    filament_pattern = re.compile(r'; filament_type = (.+)')
    used_filament_pattern = re.compile(r'; filament used \[mm] = (.+)')
    printer_model_pattern = re.compile(r'; printer_model = (.+)')
    skip_validation_pattern = re.compile(r'; skip_validation(.*)')

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
        printer_model_match = printer_model_pattern.search(gcode_content)
        skip_validation_match = skip_validation_pattern.search(gcode_content)
        nozzle_size = None
        filament_type = None
        filament_used = None
        printer_model = None
        skip_validation = False
        if nozzle_match:
            nozzle_size = nozzle_match.group(1).strip().split(',')
        if filament_match:
            filament_type = filament_match.group(1).strip().split(';')
        if filament_used_match:
            filament_used = filament_used_match.group(1).strip("").split(',')
        if printer_model_match:
            printer_model = printer_model_match.group(1).strip()
        if skip_validation_match:
            skip_validation = True

    return {
        "nozzle_size": nozzle_size, "filament_type": filament_type, "filament_used": filament_used,
        "printer_model": printer_model, "skip_validation": skip_validation}


def ends_with_mmu(string: str) -> bool:
    """
    Check if the string ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    :param string: the string to check
    :return: if the string ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    """
    match_1 = re.match(r".*mmu[23](s)?$", string)
    match_2 = re.match(r".*mmu[23](s)?is$", string)
    return bool(match_1 or match_2)


def match_ends_with_mmu(string: str) -> Union[str, None]:
    """
    Match the string that ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    :param string: the string to match
    :return: the matched string
    """
    match = re.match(r"^(.*?)(mmu[23](s)?)(is)?$", string)
    if match:
        return match.group(1)
    else:
        return None


def remove_mmu_from_end(text: str) -> str:
    """
    Remove mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis from the end of the string
    :param text: the string to remove mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis from
    :return: the string with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis removed
    """
    if bool(re.match(r".*mmu[23](s)?$|^mmu[23](s)?$", text)):
        return re.sub(r'mmu[23](s)?$', '', text)
    else:
        return re.sub(r'mmu[23](s)?is$', 'is', text)


def remove_is_from_end(text: str) -> str:
    """
    Remove is from the end of the string
    :param text: the text to remove is from
    :return: the text with is removed
    """
    return re.sub(r'is$', '', text, count=1)


class validator:
    """
    Class to validate the GCODE file before printing
    """

    def __init__(self, nozzle: Any, build_plate: Any,
                 extruders: Any, spool_manager: Any, printer: Any,
                 logger: logging.Logger, plugin_manager: Any, identifier: str, printer_profile_manager: Any) -> None:
        self.nozzle = nozzle
        self.build_plate = build_plate
        self._spool_manager = spool_manager
        self.extruders = extruders
        self._printer = printer
        self._logger = logger
        self._plugin_manager = plugin_manager
        self._identifier = identifier
        self._printer_profile_manager = printer_profile_manager

    def get_printer_model(self) -> str:
        """
        Get the current printer model
        :return: the current printer model
        """
        return self._printer_profile_manager.get_current_or_default()['model']

    def send_alert(self, message: str, alert_type: str = alert_types.popup) -> None:
        """
        Send an alert to the frontend
        :param message: the message to send
        :param alert_type: what type of alert to send
        """
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def check_print(self, file_path: str) -> None:
        """
        Checks the print before starting, will pause the print if certain checks fail and cancel the print if critical
        checks fail.
        :param file_path: The path to the GCODE file
        """
        if not os.path.exists(file_path):
            self.send_alert(f"File {file_path} not found, no checks will be performed. Press RESUME to continue "
                            f"anyways", alert_types.error)
            self._printer.pause_print()
            return

        nozzle_passed = True
        filament_passed = True
        mmu_single_mode = False
        gcode_info = parse_gcode(file_path)
        printer_model = gcode_info["printer_model"]
        skip_validation = gcode_info["skip_validation"]

        if skip_validation:
            return

        if printer_model is None:
            self.send_alert("No printer model found in GCODE, printer model checking won't be performed",
                            alert_types.info)

        elif (printer_model is not None and printer_model.lower() != self.get_printer_model().lower() and printer_model
              != ""):
            if self.get_printer_model().lower().endswith("is"):
                if not printer_model.lower().endswith("is"):
                    self.send_alert(f"Printing with non InputShaping profile on a printer that supports input shaping",
                                    alert_types.info)

            if remove_is_from_end(self.get_printer_model().lower()) != printer_model.lower():
                self.send_alert(f"Print aborted: Incorrect printer model, {printer_model} found in gcode but "
                                f"{self.get_printer_model()} is set.", alert_types.error)
                self._printer.cancel_print()
                return

        # Retrieve the loaded filament alert_type from spool manager
        try:
            loaded_filaments = self._spool_manager.get_loaded_filaments()
        except Exception as e:
            self.send_alert(f"Error retrieving loaded filament: {e}", alert_types.error)
            return
        # Parse the GCODE file to extract the nozzle size and filament alert_type

        nozzles = gcode_info["nozzle_size"]
        filament_types = gcode_info["filament_type"]
        filament_used = gcode_info["filament_used"]

        # Check if the printer model ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
        if (ends_with_mmu(printer_model.lower()) and len(nozzles) == 1 and len(filament_types) == 1 and len(
                filament_used) == 1):
            mmu_single_mode = True
            self.send_alert(
                "MMU single mode detected, skipping filament checks, please make sure you pick a tool with "
                f"{filament_types[0]} filament", alert_types.info)
        # Check if the number of nozzles in the GCODE is longer than the number of extruders on the printer
        if len(nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(f"Number of nozzles ({len(nozzles)}) in the gcode is longer than the number of extruders "
                            f"on your machine ({self.extruders.get_number_of_extruders()})", alert_types.error)
            self._printer.cancel_print()
            return

        # Check if the number of nozzles in the GCODE is shorter than the number of extruders on the printer
        elif len(nozzles) < self.extruders.get_number_of_extruders() and not mmu_single_mode:
            self.send_alert(
                f"Print paused: Number of nozzles in gcode ({len(nozzles)}) is shorter than the number of extruders("
                f"{self.extruders.get_number_of_extruders()}). Press RESUME to continue", alert_types.info)
            self._printer.pause_print()

        # Check if the number of filament alert_types in the GCODE is longer than the number of extruders on the printer
        if len(filament_types) > len(loaded_filaments) or len(
                nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(
                f"Loaded filaments ({len(loaded_filaments)}) is shorter than the number specified in the gcode "
                f"({len(filament_types)})", alert_types.error)
            self._printer.cancel_print()
            return

        # Check if the number of filament alert_types in the GCODE is shorter than the number of extruders on the
        # printer
        elif len(filament_types) < self.extruders.get_number_of_extruders() and not mmu_single_mode:
            self.send_alert(
                f" Print paused: loaded filaments ({len(loaded_filaments)}) is longer than the number specified in "
                f"the gcode ({len(filament_types)}). Press RESUME to continue", alert_types.info)
            self._printer.pause_print()

        try:
            # Check if the loaded filament matches the filament alert_type in the GCODE
            for i in range(len(nozzles)):
                if filament_used[i] is not None:
                    # if no filament was used, assume the tool isn't used and skip the check
                    if float(filament_used[i]) == 0:
                        continue

                loaded_filament = loaded_filaments[i] if loaded_filaments is not None else None

                # Check if the loaded filament matches the filament alert_type in the GCODE
                if filament_types[i] is None and filament_passed and not mmu_single_mode:
                    self.send_alert("No filament alert_type found in GCODE, error checking won't be performed",
                                    alert_types.info)
                    filament_passed = False

                # Check if the loaded filament is None and filament_passed is True and mmu_single_mode is False
                elif loaded_filament is None and filament_passed and not mmu_single_mode:
                    self.send_alert("No filament loaded, error checking won't be performed", alert_types.info)
                    filament_passed = False

                # Check if the loaded filament is -1 and filament_passed is True and mmu_single_mode is False
                elif loaded_filament == -1 and filament_passed and not mmu_single_mode:
                    self.send_alert("Spool Manager plugin is not installed. Filament alert_type will not be checked.",
                                    alert_types.info)
                    filament_passed = False

                # Check if the loaded filament is -2 and filament_passed is True and mmu_single_mode is False
                elif loaded_filament == -2 and filament_passed and not mmu_single_mode:
                    self.send_alert("Error retrieving loaded filament, filament error checking won't be performed",
                                    alert_types.info)
                    filament_passed = False

                # Check if the loaded filament is -3 and filament_passed is True and mmu_single_mode is False
                if filament_passed and not mmu_single_mode:
                    if (filament_types[i].lower() != str(loaded_filament).lower() and gcode_info[
                        "filament_type"][i] is not
                            None):
                        self.send_alert(f"Print aborted: Incorrect filament type on extruder {i + 1}. expected "
                                        f"{filament_types[i]}, but {loaded_filament} is currently loaded",
                                        alert_types.error)
                        self._printer.cancel_print()
                        return

                # Check if the loaded nozzle size matches the nozzle size in the GCODE
                if nozzles[i] is None and nozzle_passed:
                    self.send_alert("No nozzle size found in GCODE, error checking won't be performed",
                                    alert_types.info)
                    nozzle_passed = False

                # Check if the nozzle size is None and nozzle_passed is True
                elif self.extruders.get_nozzle_size_for_extruder(i + 1) is None and nozzle_passed:
                    self.send_alert(f"No nozzle selected for extruder {i + 1}, error checking won't be performed",
                                    alert_types.info)
                    nozzle_passed = False

                # Check if the nozzle size is not None and nozzle_passed is True
                if nozzle_passed:
                    if (float(nozzles[i]) != float(self.extruders.get_nozzle_size_for_extruder(i + 1)) and
                            nozzles[i] is
                            not None):
                        self.send_alert(f"Print aborted: Incorrect nozzle size on extruder {i + 1}. expected "
                                        f"{nozzles[i]}mm nozzle, but"
                                        f" {self.extruders.get_nozzle_size_for_extruder(i + 1)}mm nozzle is currently "
                                        f"installed", alert_types.error)
                        self._printer.cancel_print()
                        return

                # Check if the build plate is compatible with the loaded filament
                if filament_types[i] is not None:
                    if not self.build_plate.is_filament_compatible_with_build_plate(filament_types[i]):
                        self._logger.error("Print aborted: Incompatible build plate")
                        self.send_alert(f"Print aborted: Incompatible build plate, current plate doesn't support "
                                        f"{gcode_info['filament_type'][i]}",
                                        alert_types.error)
                        self._printer.cancel_print()
                        return
            # Check if the print passed all checks
            if nozzle_passed and filament_passed:
                self.send_alert("Print passed nozzle and filament check", alert_types.success)
                self._logger.info("Print passed nozzle and filament check...")

            # If the print didn't pass all checks, pause the print
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
                                f"config and press resume to continue.", alert_types.info)
                self._printer.pause_print()

        # If an error occurred while running checks, pause the print
        except Exception as e:
            self.send_alert(f"An error occurred while running checks, please report this error on github. \n"
                            f"Error: \"{e}\" \n please check your config and press resume to continue.",
                            alert_types.error)
            self._printer.pause_print()
            return
