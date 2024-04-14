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

import postprocessor


# the following code is an example of how the app's structure could look like, feel free to change it as you see fit


class modes:
    STAND_ALONE = "stand-alone"
    POST_PROCESSOR = "post-processor"


MODE = modes.STAND_ALONE


def main() -> None:
    if MODE == modes.POST_PROCESSOR:
        json_data = post_processor_mode()
        postprocessor.main(sys.argv[1], json_data=postprocessor.parse_json_data(json_data))

    elif MODE == modes.STAND_ALONE:
        stand_alone_mode()


def stand_alone_mode() -> None:
    # show interface to edit the json data and add/remove extruders
    json_data = json.load(open(sys.argv[1], 'r'))
    # the app

    # save the file and return the data
    with open(sys.argv[1], 'w') as file:
        json.dump(json_data, file)


def post_processor_mode() -> dict[str, None]:
    # show interface to change and confirm the json data based on the length of the gcode data
    json_data = json.load(open(sys.argv[1], 'r'))
    # the app

    # save the file and return the data
    with open(sys.argv[1], 'w') as file:
        json.dump(json_data, file)
    return json_data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        MODE = modes.POST_PROCESSOR
    main()
