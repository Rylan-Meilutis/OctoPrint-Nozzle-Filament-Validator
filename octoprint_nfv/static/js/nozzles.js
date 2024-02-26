$(function () {

// Function to confirm before removing a nozzle
    function confirmRemoveNozzle(nozzleId, nozzleSize) {
        if (confirm("Are you sure you want to remove nozzle size " + nozzleSize + "?")) {
            removeNozzle(nozzleId);
        }
    }

// Function to remove a nozzle
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

// Event handler for selecting the current sized nozzle
    $("#select-nozzle-button").click(function () {
        const selectedNozzleId = $("#nozzles-list").val();
        OctoPrint.simpleApiCommand(PLUGIN_ID, "selectNozzle", {"nozzleId": selectedNozzleId}).done(function (response) {
            displayData();
        });
    });

// Event handler for removing a nozzle
    $("#remove-nozzle-button").click(function () {
        const selectedNozzleId = $("#nozzles-list").val();
        const selectedNozzleSize = $("#nozzles-list option:selected").text();
        confirmRemoveNozzle(selectedNozzleId, selectedNozzleSize);
    });

});