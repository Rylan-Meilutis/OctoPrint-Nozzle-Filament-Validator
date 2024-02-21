$(function () {
    const PLUGIN_ID = "Nozzle_Filament_Validator";

    // Function to fetch and display added nozzles, filament type, and current nozzle size
    function displayData() {
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "GET",
            dataType: "json",
            success: function (response) {
                // Display the list of added nozzles
                $("#nozzles-list").empty();
                $.each(response.nozzles, function (index, nozzle) {
                    $("#nozzles-list").append($("<option>", {value: nozzle.id, text: nozzle.size}));
                });

                // Update current filament type
                $("#current-filament").text(response.filament_type);

                // Update current nozzle size
                $("#current-nozzle").text(response.currentNozzle);
            },
            error: function (xhr, status, error) {
                console.error("Error fetching data:", error);
            }
        });
    }

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

    // Event handler for refreshing the filament type
    $("#refresh-filament-button").click(function () {
        displayData();
    });
    // Initial display of added nozzles, filament type, and current nozzle size
    displayData();


    // Bind the plugin message handler to the global scope
    function messageHandler() {

        this.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "Nozzle_Filament_Validator") {
                return;
            }

            let theme;
            switch (data.type) {
                case "popup":
                    theme = "info";
                    break;
                case "error":
                    theme = 'danger';
                    break;
                default:
                    theme = "info";
                    break;
            }

            if (data.msg !== "") {
                new PNotify({
                    title: 'Continuous Print',
                    text: data.msg,
                    type: theme,
                    hide: (theme !== 'danger'),
                    buttons: {closer: true, sticker: false}
                });
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: messageHandler,
        additionalNames: ["messageHandler"],
        dependencies: ["loginStateViewModel", "appearanceViewModel"],
        elements: [""]
    });

});
