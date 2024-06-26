/**
 * This file contains the JavaScript functions for the extruders tab. It also contains the event handlers for the
 * extruder buttons.
 * @param response The response from the server
 */
function activate_extruder_buttons(response) {
    // Remove any existing event handlers for selecting the nozzle
    $("[id^='select-nozzle-button-']").off('click');

    // Event handler for selecting the current sized nozzle
    $("[id^='select-nozzle-button-']").click(function () {
        const extruderPosition = $(this).attr("id").split("-").pop(); // Get the extruder position from button ID
        const selectedNozzleId = $(`#nozzle-dropdown-${extruderPosition}`).val();
        const selectedNozzleSize = $(`#nozzle-dropdown-${extruderPosition} option:selected`).text(); // Get the selected nozzle size
        OctoPrint.simpleApiCommand(PLUGIN_ID, "update_extruder", {
            "nozzleId": selectedNozzleId,
            "extruderPosition": extruderPosition
        }).done(function (response) {
            // Update the current nozzle size for the current extruder
            $(`#current-nozzle-${extruderPosition}`).text(selectedNozzleSize); // Update the current nozzle size displayed on the page
            displayData();
        });
    });
}
