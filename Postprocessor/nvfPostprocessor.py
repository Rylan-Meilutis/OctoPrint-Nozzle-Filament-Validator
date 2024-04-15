# This will be a graphical app allowing the user to easily modify the json file used as input to the postprocessor. I
# will handle the compilation into an executable using auto-py-to-exe or similar. Feel free to use a different
# language if you want such as rust, c++, c, electron, etc. The app should have the following features: gets the path
# to the json file using a file dialog, displays the entries in the in a user-friendly format, allows the user to
# modify them and saves the changes as they type, allows the user to add new entries, allows the user to delete entries.
# The app should also work in 2 modes, stand-alone mode, where the user can edit the json file, and postprocessor
# mode, where it allows editing of the current extruders and the names of the spools that should be used.
# You will be able to tell the difference based on the number of system arguments if there are none (len(sys.argv)
# < 1) or the data isn't a path, then you are in stand-alone mode. If there is an argument, and it is a path,
# then you are in postprocessor mode. If the app is closed without saving, it should ask the user if they want to save.

from __future__ import annotations

import json
import sys

import requests

import postprocessor


# the following code is an example of how the app's structure could look like, feel free to change it as you see fit


class modes:
    STAND_ALONE = "stand-alone"
    POST_PROCESSOR = "post-processor"


MODE = modes.STAND_ALONE
# Settings schema should include all settings you with to include (light mode, dark mode, etc.) and the url of the
# octoprint server.
# The url stuff should be in place already including the ability to check if the url is correct and get the loaded
# filament spools.
# The load and save settings are also already implemented
SETTINGS_PATH = "nvfsettings.json"


def main() -> None:
    """
    Main function
    :return:
    """
    if MODE == modes.POST_PROCESSOR:
        json_data = post_processor_mode()
        postprocessor.main(sys.argv[1], json_data=postprocessor.parse_json_data(json_data))

    elif MODE == modes.STAND_ALONE:
        stand_alone_mode()


def stand_alone_mode() -> None:
    """
    Stand alone mode
    :return:
    """

    # show interface to edit the json data and add/remove extruders
    json_data = json.load(open(sys.argv[1], 'r'))
    settings = load_settings()
    # the app

    # save the file and return the data
    with open(sys.argv[1], 'w') as file:
        json.dump(json_data, file)


def post_processor_mode() -> dict[str, None]:
    """
    Post processor mode
    :return:
    """
    # show interface to change and confirm the json data based on the length of the gcode data
    json_data = json.load(open(sys.argv[1], 'r'))

    settings = load_settings()

    # the app

    # save the file and return the data
    with open(sys.argv[1], 'w') as file:
        json.dump(json_data, file)
    return json_data


def save_settings(json_data: dict[str, None]) -> None:
    """
    Save the settings to the json file
    :param json_data: the json data
    :return:
    """
    with open(SETTINGS_PATH, 'w') as file:
        json.dump(json_data, file)


def load_settings() -> dict[str, None]:
    """
    Load the settings from the json file
    :return: the json data or an empty dictionary if the file does not exist
    """
    try:
        return json.load(open(SETTINGS_PATH, 'r'))
    except FileNotFoundError:
        return {}


def check_octoprint_settings(url: str) -> bool | str:
    """
    Check the octoprint settings
    :param url: the base octoprint url
    :return: True if the settings are correct, the error message otherwise
    """
    try:
        requests.get(url=url)
    except requests.exceptions.ConnectionError as e:
        return f"Could not connect to the octoprint server: \"{e}\""

    return True


def get_loaded_spools(url: str) -> list[str] | None:
    """
    Get the loaded spools from octoprint
    :param url: the base octoprint url
    :return: a list of the loaded spools name or None if there was an error
    """
    # get the spools from the database
    # return the spools
    api_path = ("/plugin/SpoolManager/loadSpoolsByQuery?selectedPageSize=100000&from=0&to=100000&sortColumn"
                "=displayName&sortOrder=desc&filterName=&materialFilter=all&vendorFilter=all&colorFilter=all")
    try:
        json_data = requests.get(url + api_path).json()
    except requests.exceptions.ConnectionError:
        return None
    except json.JSONDecodeError:
        return None
    # remove all except loaded spools
    json_data = json_data["selectedSpools"]
    # create a list where each element is the name of a spool, the spools are in order of the extruders in the json
    # response
    spool_data = [spool["displayName"] for spool in json_data]
    # the app
    return spool_data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        MODE = modes.POST_PROCESSOR
    main()
