/**
 * Display the nozzles data and activate the buttons
 * @param response The response from the server
 */
function activate_nozzle_buttons(response) {

    // Function to confirm before removing a nozzle
    /**
     * Confirm before removing a nozzle
     * @param nozzleId The nozzle ID
     * @param nozzleSize The nozzle size
     */
    function confirmRemoveNozzle(nozzleId, nozzleSize) {
        if (confirm("Are you sure you want to remove nozzle size " + nozzleSize + "?")) {
            removeNozzle(nozzleId);
        }
    }

    // Function to remove a nozzle
    /**
     * Remove a nozzle
     * @param nozzleId The nozzle ID
     */
    function removeNozzle(nozzleId) {
        OctoPrint.simpleApiCommand(PLUGIN_ID, "removeNozzle", {"nozzleId": nozzleId}).done(function (response) {
            displayData();
        });
    }

    // Event handler for adding a nozzle
    $("#add-nozzle-button").click(function () {
        const nozzleSize = $("#nozzle-size-input").val();
        OctoPrint.simpleApiCommand(PLUGIN_ID, "addNozzle", {"size": nozzleSize}).done(function (response) {
            displayData();
        });
    });

    // Event handler for removing a nozzle
    $("#remove-nozzle-button").click(function () {
        const selectedNozzleId = $("#nozzles-list").val();
        const selectedNozzleSize = $("#nozzles-list option:selected").text();
        confirmRemoveNozzle(selectedNozzleId, selectedNozzleSize);
    });

    $("#nozzles-list").empty();
    $.each(response.nozzles, function (index, nozzle) {
        $("#nozzles-list").append($("<option>", {value: nozzle.id, text: nozzle.size}));
    });

}