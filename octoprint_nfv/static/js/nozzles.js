$(function () {

// Function to confirm before removing a nozzle
    function confirmRemoveNozzle(nozzleId, nozzleSize) {
        if (confirm("Are you sure you want to remove nozzle size " + nozzleSize + "?")) {
            removeNozzle(nozzleId);
        }
    }

// Function to remove a nozzle
    function removeNozzle(nozzleId) {
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "removeNozzle",
                "nozzleId": nozzleId
            }),
            success: function (response) {
                displayData();
            },
            error: function (xhr, status, error) {
                console.error("Error removing nozzle:", error);
            }
        });
    }

// Event handler for adding a nozzle
    $("#add-nozzle-button").click(function () {
        const nozzleSize = $("#nozzle-size-input").val();
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "addNozzle",
                "size": nozzleSize
            }),
            success: function (response) {
                displayData();
            },
            error: function (xhr, status, error) {
                console.error("Error adding nozzle: " + nozzleSize, error);
            }
        });
    });

// Event handler for selecting the current sized nozzle
    $("#select-nozzle-button").click(function () {
        const selectedNozzleId = $("#nozzles-list").val();
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "selectNozzle",
                "nozzleId": selectedNozzleId
            }),

            success: function (response) {
                displayData()
                // Optionally, perform any UI update after selecting the nozzle
            },
            error: function (xhr, status, error) {
                console.error("Error selecting nozzle: " + selectedNozzleId, error);
            }
        });
    });

// Event handler for removing a nozzle
    $("#remove-nozzle-button").click(function () {
        const selectedNozzleId = $("#nozzles-list").val();
        const selectedNozzleSize = $("#nozzles-list option:selected").text();
        confirmRemoveNozzle(selectedNozzleId, selectedNozzleSize);
    });

});