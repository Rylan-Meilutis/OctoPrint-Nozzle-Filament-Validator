import logging
import math
import os
import re
import threading
import time
from typing import Any, Union, Dict, List, Tuple

from octoprint_nfv.constants import alert_types


class filament_timeout:
    """
    Class to handle the filament timeout states
    """
    ok = "ok"
    waiting = "waiting"
    cancel = "cancel"


def parse_gcode(file_path: str) -> Dict[str, Any]:
    """
    Parse the GCODE file to extract the nozzle diameter and filament type
    :param file_path: the path to the GCODE file
    :return: a dictionary containing the nozzle diameter and filament type
    """
    # Regular expression patterns to extract nozzle diameter and filament alert_type
    nozzle_pattern = re.compile(r'^;\s*nozzle_diameter\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    filament_pattern = re.compile(r'^;\s*filament_type\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    used_filament_pattern = re.compile(r'^;\s*filament used \[mm]\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    printer_model_pattern = re.compile(r'^;\s*printer_model\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    skip_validation_pattern = re.compile(r'^;\s*skip_validation\s*$', re.MULTILINE | re.IGNORECASE)
    filament_notes_pattern = re.compile(r'^;\s*filament_notes\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)
    single_extruder_multi_material_pattern = re.compile(
        r'^;\s*single_extruder_multi_material\s*=\s*(.+)$', re.MULTILINE | re.IGNORECASE)

    # Number of lines to read from the end of the file
    num_lines = 1000

    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
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
        # Ensure short files are read from byte zero. Without this seek, the
        # first character of a file with fewer than ``num_lines`` lines was
        # omitted.
        file.seek(max(pos, 0))
        lines = file.readlines()

        # Extract nozzle diameter and filament alert_type from the collected lines
        gcode_content = ''.join(lines)
        nozzle_match = nozzle_pattern.search(gcode_content)
        filament_match = filament_pattern.search(gcode_content)
        filament_used_match = used_filament_pattern.search(gcode_content)
        printer_model_match = printer_model_pattern.search(gcode_content)
        skip_validation_match = skip_validation_pattern.search(gcode_content)
        filament_notes_match = filament_notes_pattern.search(gcode_content)
        single_extruder_multi_material_match = single_extruder_multi_material_pattern.search(gcode_content)
        nozzle_size = None
        filament_type = None
        filament_used = None
        printer_model = None
        filament_notes = None
        single_extruder_multi_material = None
        skip_validation = False
        if nozzle_match:
            nozzle_size = nozzle_match.group(1).replace(" ", "").strip().split(',')
        if filament_match:
            filament_type = filament_match.group(1).strip().split(';')
        if filament_used_match:
            filament_used = filament_used_match.group(1).replace(" ", "").strip().split(',')
        if printer_model_match:
            printer_model = printer_model_match.group(1).strip()
        if skip_validation_match:
            skip_validation = True
        if filament_notes_match:
            filament_notes = filament_notes_match.group(1).strip().split(';')
        if single_extruder_multi_material_match:
            data = single_extruder_multi_material_match.group(1).replace(" ", "").strip()
            if data == "1":
                single_extruder_multi_material = True
            else:
                single_extruder_multi_material = False

    return {
        "nozzle_size": nozzle_size, "filament_type": filament_type, "filament_used": filament_used,
        "printer_model": printer_model, "skip_validation": skip_validation, "filament_notes": filament_notes,
        "single_extruder_multi_material": single_extruder_multi_material}


def ends_with_mmu(string: str) -> bool:
    """
    Check if the string ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    :param string: the string to check
    :return: if the string ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    """
    match_1 = re.match(r".*mmu[23](s)?$", string)
    match_2 = re.match(r".*mmu[23](s)?is$", string)
    match_3 = re.match(r".*ismmu[23](s)?$", string)
    return bool(match_1 or match_2 or match_3)


def match_ends_with_mmu(string: str) -> Union[str, None]:
    """
    Match the string that ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
    :param string: the string to match
    :return: the matched string
    """
    match = re.match(r"^(.*?)(is)?(mmu[23](s)?)(is)?$", string)
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
    elif bool(re.match(r".*mmu[23](s)?is$|^mmu[23](s)?is$", text)):
        return re.sub(r'mmu[23](s)?is$', 'is', text)
    elif bool(re.match(r".*ismmu[23](s)?$|^ismmu[23](s)?$", text)):
        return re.sub(r'ismmu[23](s)?$', 'is', text)
    else:
        return text


def remove_is_from_end(text: str) -> str:
    """
    Remove 'is' from the end of the string unless it is followed by 'mmu', a number, and optionally 's'
    :param text: the text to remove 'is' from
    :return: the text with 'is' removed
    """
    if bool(re.search(r"ismmu[23](s)?", text)):
        return re.sub(r'is(?=mmu[23](s)?)', '', text)
    elif bool(re.search(r"is$", text)):
        return re.sub(r'is$', '', text)
    else:
        return text


class validator:
    """
    Class to validate the GCODE file before printing
    """

    def __init__(self, nozzle: Any, build_plate: Any,
                 extruders: Any, spool_manager: Any, filament: Any, printer: Any,
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
        self._filament = filament
        self.filament_wait_status = "ok"
        self.paused = False
        self._prompt_lock = threading.RLock()
        self._active_prompt = None
        self._prompt_deadline = None
        self.last_check_cacheable = False
        self._validation_was_overridden = False
        # Keys are zero-based slicer/logical tools and values are zero-based
        # physical tools. Identity is the safe default when RME is absent.
        self._tool_mapping = {}

    def set_tool_mapping(self, mapping: Dict[int, int]) -> None:
        """Set the confirmed logical-to-physical mapping for the next checks."""
        normalized = {int(logical): int(physical) for logical, physical in mapping.items()}
        if any(logical < 0 or physical < 0 for logical, physical in normalized.items()):
            raise ValueError("Tool mapping indices must be non-negative")
        self._tool_mapping = normalized

    def physical_tool(self, logical_tool: int) -> int:
        """Resolve a slicer tool to the physical tool configured by RME."""
        logical_tool = int(logical_tool)
        return self._tool_mapping.get(logical_tool, logical_tool)

    def _tool_description(self, logical_tool: int) -> str:
        physical = self.physical_tool(logical_tool)
        if physical == logical_tool:
            return f"extruder {logical_tool + 1}"
        return f"logical extruder {logical_tool + 1} (physical tool {physical + 1})"

    def pause_print(self) -> None:
        """
        Pause the print
        """
        if not self.paused:
            self._printer.pause_print()
            self.paused = True

    def update_filament_wait_status(self, state: str) -> None:
        """
        Update the filament wait status
        :param state:
        :return:
        """
        self.filament_wait_status = state
        if state != filament_timeout.waiting:
            self.clear_active_prompt()

    def set_active_prompt(self, prompt_type: str, message: str, timeout: int) -> Dict[str, Any]:
        timeout = max(0, int(timeout))
        with self._prompt_lock:
            self._active_prompt = {"type": prompt_type, "msg": message}
            self._prompt_deadline = time.monotonic() + timeout
            return dict(self._active_prompt, timeout=timeout)

    def clear_active_prompt(self) -> None:
        with self._prompt_lock:
            self._active_prompt = None
            self._prompt_deadline = None

    def get_active_prompt(self) -> Union[Dict[str, Any], None]:
        with self._prompt_lock:
            if self._active_prompt is None or self._prompt_deadline is None:
                return None
            remaining = max(0, math.ceil(self._prompt_deadline - time.monotonic()))
            if remaining <= 0:
                return None
            return dict(self._active_prompt, timeout=remaining)

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

    def prompt_validation_override(self, message: str) -> bool:
        """Wait for an explicit continue/cancel decision, defaulting to cancel on timeout."""
        timeout = max(0, int(self._filament.get_timeout()))
        self.update_filament_wait_status(filament_timeout.waiting)
        prompt = self.set_active_prompt(alert_types.validation_prompt, message, timeout)
        self._plugin_manager.send_plugin_message(self._identifier, prompt)

        deadline = time.monotonic() + timeout
        while self.filament_wait_status == filament_timeout.waiting and time.monotonic() < deadline:
            time.sleep(0.1)

        if self.filament_wait_status == filament_timeout.ok:
            self._validation_was_overridden = True
            self.send_alert("Validation warning acknowledged; continuing at the user's request.", alert_types.info)
            return True

        if self.filament_wait_status == filament_timeout.waiting:
            self.update_filament_wait_status(filament_timeout.cancel)
            self.send_alert("Validation prompt timed out; the print was blocked.", alert_types.error)
        return False

    def check_print(self, file_path: str) -> bool:
        """
        Validate a GCODE file and return whether it is safe to start.
        :param file_path: The path to the GCODE file
        """
        self.paused = False
        self.last_check_cacheable = False
        self._validation_was_overridden = False
        if not file_path or not os.path.isfile(file_path):
            return self.prompt_validation_override(
                f"The GCODE file {file_path!r} could not be read, so it could not be validated.")

        nozzle_passed = True
        filament_passed = True
        spool_passed = True
        try:
            gcode_info = parse_gcode(file_path)
        except (OSError, UnicodeError) as error:
            return self.prompt_validation_override(f"The GCODE could not be parsed: {error}")
        printer_model = gcode_info["printer_model"]
        skip_validation = gcode_info["skip_validation"]
        semm = gcode_info["single_extruder_multi_material"]

        if semm is None:
            semm = False

        if skip_validation:
            self._logger.warning("GCODE validation explicitly skipped by file directive")
            self.last_check_cacheable = True
            return True

        nozzles = gcode_info["nozzle_size"]
        filament_types = gcode_info["filament_type"]
        filament_used = gcode_info["filament_used"]

        missing_fields = [name for name, value in (
            ("nozzle_diameter", nozzles),
            ("filament_type", filament_types),
            ("filament used [mm]", filament_used),
            ("printer_model", printer_model),
        ) if not value]
        if missing_fields:
            return self.prompt_validation_override(
                "Required slicer metadata is missing: " + ", ".join(missing_fields))

        if not (len(nozzles) == len(filament_types) == len(filament_used)):
            return self.prompt_validation_override(
                "Nozzle, filament type, and filament usage metadata have different tool counts.")

        try:
            [float(value) for value in nozzles]
            [float(value) for value in filament_used]
        except (TypeError, ValueError):
            return self.prompt_validation_override(
                "Nozzle diameter or filament usage metadata contains a malformed numeric value.")

        if not self.check_printer_model(printer_model):
            return self.prompt_validation_override("The printer model in the GCODE does not match this printer.")

        mmu_pass, mmu_single_mode = self.check_mmu(printer_model, nozzles, filament_types, filament_used)

        if not mmu_pass:
            return self.prompt_validation_override("The GCODE tool count is incompatible with this printer.")

        for i in range(len(nozzles)):
            if filament_used[i] is not None:
                # if no filament was used, assume the tool isn't used and skip the check
                if float(filament_used[i]) == 0:
                    continue
            else:  # if the filament used is None, assume the tool isn't used and skip the check for that tool
                continue

            spool_pass, spool_passed = self.check_spool_id(i, gcode_info, spool_passed)
            if not spool_pass:
                return False

        check_filament_types = self._filament.get_enable_filament_type_checking()
        if check_filament_types:
            try:
                loaded_filaments = self._spool_manager.get_loaded_filaments()
            except Exception as e:
                return self.prompt_validation_override(f"Loaded filament information could not be retrieved: {e}")
        else:
            loaded_filaments = [-1] * len(filament_types)

        # SpoolManager uses sentinel values when it is unavailable. Normalize
        # those values to one entry per tool so the validator can safely skip
        # filament comparison while still checking nozzle and build plate.
        if isinstance(loaded_filaments, int):
            loaded_filaments = [loaded_filaments] * len(filament_types)
        elif loaded_filaments is None:
            loaded_filaments = [None] * len(filament_types)

        if check_filament_types and not self.check_num_filaments(loaded_filaments, filament_types, filament_used):
            return self.prompt_validation_override("There are fewer loaded filaments than the GCODE requires.")

        if not self.check_num_extruders(nozzles, semm):
            return self.prompt_validation_override("The configured extruder count does not match the GCODE.")

        try:
            # Check if the loaded filament matches the filament alert_type in the GCODE
            for i in range(len(nozzles)):
                if filament_used[i] is not None:
                    # if no filament was used, assume the tool isn't used and skip the check
                    if float(filament_used[i]) == 0:
                        continue

                if check_filament_types:
                    filament_passed, filament_pass = self.check_filament_type(
                        i, loaded_filaments, filament_types, gcode_info, filament_passed, mmu_single_mode)
                    if not filament_pass:
                        return self.prompt_validation_override(
                            f"The loaded filament type does not match the GCODE on extruder {i + 1}.")

                nozzle_passed, nozzle_pass = self.check_nozzle(i, nozzles, nozzle_passed)
                if not nozzle_pass:
                    return self.prompt_validation_override(
                        f"The installed nozzle does not match the GCODE on extruder {i + 1}.")

                if not self.check_build_plate(i, filament_types, gcode_info):
                    return self.prompt_validation_override(
                        f"The selected build plate is incompatible with extruder {i + 1}'s filament.")

            # Check if the print passed all checks
            if nozzle_passed and filament_passed and spool_passed:
                self.last_check_cacheable = not self._validation_was_overridden
                self.send_alert("Print passed nozzle and filament check", alert_types.success)
                self._logger.info("Print passed nozzle and filament check...")
                return True

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
                return self.prompt_validation_override("One or more validation checks did not pass.")

        # If an error occurred while running checks, pause the print
        except Exception as e:
            return self.prompt_validation_override(f"An unexpected validation error occurred: {e}")

    def check_printer_model(self, printer_model: str = None) -> bool:
        """
        Check if the printer model in the GCODE matches the printer model set in OctoPrint if it isn't the same,
        cancel the print
        :param printer_model: the printer model in the GCODE
        :return: true if the printer model passes the check
        """
        if printer_model is None or printer_model == "":
            self.send_alert("No printer model found in GCODE, printer model checking won't be performed",
                            alert_types.info)
            return True

        elif self.get_printer_model() is None or self.get_printer_model() == "":
            self.send_alert("No printer model set in OctoPrint, printer model checking won't be performed",
                            alert_types.info)
            return True

        elif (printer_model is not None and printer_model.lower() != self.get_printer_model().lower() and printer_model
              != ""):
            if remove_mmu_from_end(self.get_printer_model().lower()).endswith("is"):
                if not remove_mmu_from_end(printer_model.lower()).endswith("is"):
                    self.send_alert(
                        f"Printing with non InputShaping profile on a printer that supports input shaping",
                        alert_types.info)

            if remove_is_from_end(self.get_printer_model().lower()) != printer_model.lower():
                self.send_alert(f"Validation warning: Incorrect printer model, {printer_model} found in gcode but "
                                f"{self.get_printer_model()} is set.", alert_types.error)
                return False
        return True

    def check_mmu(self, printer_model: str = None, nozzles: List[str] = None, filament_types: List[str] = None,
                  filament_used: List[str] = None) -> Tuple[bool, bool]:
        """
        Check if using an mmu and handle it accordingly
        :param printer_model: the printer model from the GCODE
        :param nozzles: the nozzles from the GCODE
        :param filament_types: the filament types from the GCODE
        :param filament_used: the filament used from the GCODE
        :return: True if the check passed, False if it didn't
        """
        mmu_single_mode = False
        # Check if the printer model ends with mmu3 or mmu3s or mmu2 or mmu2s or mmu3is or mmu3sis or mmu2is or mmu2sis
        if (printer_model and ends_with_mmu(printer_model.lower()) and len(nozzles) == 1
                and len(filament_types) == 1 and len(
                filament_used) == 1):
            mmu_single_mode = True
            self.send_alert(
                "MMU single mode detected, skipping filament checks, please make sure you pick a tool with "
                f"{filament_types[0]} filament", alert_types.info)
        # Check if the number of nozzles in the GCODE is longer than the number of extruders on the printer
        if len(nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(f"Number of nozzles ({len(nozzles)}) in the gcode is longer than the number of extruders "
                            f"on your machine ({self.extruders.get_number_of_extruders()})", alert_types.error)
            return False, mmu_single_mode

        return True, mmu_single_mode

    def check_num_filaments(self, loaded_filaments: List[str], filament_types: List[str],
                            filament_used: List[str], ) -> bool:
        """
        Check the number of filaments in the GCODE

        :param loaded_filaments: The loaded filaments from the spool manager
        :param filament_types: the filament types from the GCODE
        :param filament_used: the filament used from the GCODE
        :return: true if the check passed
        """
        # Check if the number of filament types in the GCODE is longer than the number of extruders on the printer
        loaded_fil_length = len(loaded_filaments)
        needed_fil_length = len(filament_types)

        for i in range(len(filament_types)):
            if filament_used[i] is not None:
                # if no filament was used, assume the tool isn't used and skip the check
                if float(filament_used[i]) == 0:
                    needed_fil_length -= 1

        if needed_fil_length > loaded_fil_length:
            self.send_alert(
                f"Loaded filaments ({loaded_fil_length}) is shorter than the number specified in the gcode "
                f"({len(filament_types)})", alert_types.error)
            return False

        return True

    def check_num_extruders(self, nozzles: List[str], semm) -> bool:
        """
        Check the number of extruders in the GCODE
        :param semm: Single Extruder Multi Material
        :param nozzles: the nozzles from the GCODE
        :return: true if the check passed
        """
        if len(nozzles) > self.extruders.get_number_of_extruders():
            self.send_alert(
                f"Number of extruders in gcode ({len(nozzles)}) is Larger than the number specified in the "
                f"config ({self.extruders.get_number_of_extruders()})", alert_types.error)
            return False
        elif len(nozzles) < self.extruders.get_number_of_extruders():
            if not semm:
                self.send_alert(
                    f"Number of extruders in gcode ({len(nozzles)}) is shorter than the number specified in the "
                    f"config ({self.extruders.get_number_of_extruders()}). Print blocked.", alert_types.error)
                return False

        return True

    def check_filament_type(self, index: int, loaded_filaments: List[str], filament_types: List[str],
                            gcode_info: Dict[str, Any], filament_passed: bool, mmu_single_mode: bool) -> Tuple[bool, bool]:
        """
        Check the filament type
        :param index: the index of the extruder
        :param loaded_filaments: the loaded filaments from the spool manager
        :param filament_types: the filament types from the GCODE
        :param gcode_info: the GCODE info
        :param filament_passed: the state of filament_passed
        :param mmu_single_mode: whether the printer is in mmu single mode
        :return: (filament_passed, check_passed) the value filament passed and true if the check passed
        """
        physical_index = self.physical_tool(index)
        loaded_filament = (
            loaded_filaments[physical_index]
            if loaded_filaments is not None and physical_index < len(loaded_filaments)
            else None
        )

        # Check if the loaded filament matches the filament alert_type in the GCODE
        if filament_types[index] is None and filament_passed and not mmu_single_mode:
            self.send_alert("No filament alert_type found in GCODE, error checking won't be performed",
                            alert_types.info)
            filament_passed = False

        # Check if the loaded filament is None and filament_passed is True and mmu_single_mode is False
        elif loaded_filament is None and filament_passed and not mmu_single_mode:
            self.send_alert("No filament loaded, error checking won't be performed", alert_types.info)
            return filament_passed, True

        # Check if the loaded filament is -1 and filament_passed is True and mmu_single_mode is False
        elif loaded_filament == -1 and filament_passed and not mmu_single_mode:
            self.send_alert("Spool Manager plugin is not installed. Filament alert_type will not be checked.",
                            alert_types.info)
            return filament_passed, True

        # Check if the loaded filament is -2 and filament_passed is True and mmu_single_mode is False
        elif loaded_filament == -2 and filament_passed and not mmu_single_mode:
            self.send_alert("Error retrieving loaded filament, filament error checking won't be performed",
                            alert_types.info)
            return filament_passed, True

        # Check if the loaded filament is -3 and filament_passed is True and mmu_single_mode is False
        if filament_passed and not mmu_single_mode:
            if (filament_types[index].lower() != str(loaded_filament).lower() and gcode_info[
                "filament_type"][index] is not
                    None):
                self.send_alert(f"Validation warning: Incorrect filament type on {self._tool_description(index)}. expected "
                                f"{filament_types[index]}, but {loaded_filament} is currently loaded",
                                alert_types.error)
                return filament_passed, False

        return filament_passed, True

    def check_nozzle(self, index: int, nozzles: List[str], nozzle_passed: bool) -> Tuple[bool, bool]:
        """
        Check the nozzle size
        :param index: index of the extruder
        :param nozzles: list of nozzles from the GCODE
        :param nozzle_passed: current state of nozzle_passed
        :return: (nozzle_passed, check_passed) the value of nozzle_passed and true if the check passed
        """

        # NFV's database uses one-based physical extruder positions while GCODE
        # metadata and the RME mapping use zero-based logical indices.
        physical_position = self.physical_tool(index) + 1

        # Check if the loaded nozzle size matches the nozzle size in the GCODE
        if nozzles[index] is None and nozzle_passed:
            self.send_alert("No nozzle size found in GCODE, error checking won't be performed",
                            alert_types.info)
            nozzle_passed = False

        # Check if the nozzle size is None and nozzle_passed is True
        elif self.extruders.get_nozzle_size_for_extruder(physical_position) is None and nozzle_passed:
            self.send_alert(f"No nozzle selected for {self._tool_description(index)}, error checking won't be performed",
                            alert_types.info)
            nozzle_passed = False

        # Check if the nozzle size is not None and nozzle_passed is True
        if nozzle_passed:
            if (float(nozzles[index]) != float(self.extruders.get_nozzle_size_for_extruder(physical_position)) and
                    nozzles[index] is
                    not None):
                self.send_alert(f"Validation warning: Incorrect nozzle size on {self._tool_description(index)}. expected "
                                f"{nozzles[index]}mm nozzle, but"
                                f" {self.extruders.get_nozzle_size_for_extruder(physical_position)}mm nozzle is currently "
                                f"installed", alert_types.error)
                return nozzle_passed, False
        return nozzle_passed, True

    def check_build_plate(self, index: int, filament_types: List[str], gcode_info: Dict[str, Any]) -> bool:
        """
        Check if the build plate is compatible with the loaded filament
        :param index: index of the extruder
        :param filament_types: filament types from the GCODE
        :param gcode_info: gcodes info
        :return: true if the check passed
        """
        # Check if the build plate is compatible with the loaded filament
        if filament_types[index] is not None:
            if not self.build_plate.is_filament_compatible_with_build_plate(filament_types[index]):
                self._logger.warning("Validation warning: Incompatible build plate")
                self.send_alert(f"Validation warning: Incompatible build plate, current plate doesn't support "
                                f"{gcode_info['filament_type'][index]}",
                                alert_types.error)
                return False
        return True

    def check_spool_id(self, index: int, gcode_info: Dict[str, Any], passed: bool) -> Tuple[bool, bool]:
        """
        Check the spool id, if it is invalid, wait for input from the frontend
        :param index: index of the extruder
        :param gcode_info: info from the GCODE
        :passed: the current state of passed
        :return: true if the check passed
        """

        if not self._filament.get_enable_spool_checking():
            return True, True

        timeout = self._filament.get_timeout()
        self.update_filament_wait_status(filament_timeout.ok)
        # parse the existing spool id from the gcode
        filament_notes = gcode_info.get("filament_notes")
        if not filament_notes or index >= len(filament_notes):
            override = self.prompt_validation_override(
                f"Filament/spool name metadata is missing for extruder {index + 1}.")
            return override, override

        raw_data = filament_notes[index]

        match = re.search(r"\[\s*sm_name\s*=\s*([^]]*\S)]", raw_data)

        physical_index = self.physical_tool(index)
        selected_names = self._spool_manager.get_names()
        current_fil_id = selected_names[physical_index] if physical_index < len(selected_names) else None

        if match:
            spool_id = str(match.group(1))
            if current_fil_id is None:
                self._validation_was_overridden = True
                self.update_filament_wait_status(filament_timeout.waiting)
                message = f"{spool_id}, {physical_index}, None Selected, {self._filament.get_timeout()}"
                prompt = self.set_active_prompt(alert_types.switch_spools, message, timeout)
                self._plugin_manager.send_plugin_message(self._identifier, prompt)

            elif str(current_fil_id) != spool_id:
                self._validation_was_overridden = True
                self.update_filament_wait_status(filament_timeout.waiting)
                message = f"{spool_id}, {physical_index}, {current_fil_id}, {self._filament.get_timeout()}"
                prompt = self.set_active_prompt(alert_types.switch_spools, message, timeout)
                self._plugin_manager.send_plugin_message(self._identifier, prompt)

            while self.filament_wait_status == filament_timeout.waiting:
                if timeout == 0:
                    self.send_alert("Timeout reached, print cancelling", alert_types.error)
                    return False, False
                timeout -= 1
                time.sleep(1)
        else:
            self.send_alert(f"Spool name not found in GCODE for extruder {index + 1}. Print blocked.",
                            alert_types.error)
            passed = False
        if self.filament_wait_status == filament_timeout.cancel:
            self.send_alert("Cancelling print", alert_types.error)
            return False, False

        return True, passed
