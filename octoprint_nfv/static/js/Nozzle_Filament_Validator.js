const PLUGIN_ID = "Nozzle_Filament_Validator";

// Function to fetch and display added nozzles, filament alert_type, and current nozzle size
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

            $("#build-plate-list").empty();
            $.each(response.build_plates, function (index, plate) {
                $("#build-plate-list").append($("<option>", {
                    value: plate.id,
                    text: plate.name
                }));
            });

            let filament = response.filament_type;
            if (filament === "" || filament === null || filament === undefined || filament === " ") {
                filament = "No filament selected";
            } else if (filament === "None") {
                filament = "No filament selected";
            } else if (filament === -1) {
                filament = "Spool manager is not installed, please install it to to enable filament error checking";
            } else if (filament === -2) {
                filament = "An error occurred while fetching the filament alert_type, please try again";
            }
            // Update current filament alert_type
            $("#current-filament").text(filament);

            let currentNozzle = response.currentNozzle
            if (currentNozzle === "") {
                currentNozzle = "No nozzle selected";
            } else if (currentNozzle === "None") {
                currentNozzle = "No nozzle selected";
            }
            // Update current nozzle size
            $("#current-nozzle").text(currentNozzle);

            let currentBuildPlate = response.currentBuildPlate
            let currentBuildPlateFilaments = response.currentBuildPlateFilaments
            if (currentBuildPlate === "") {
                currentBuildPlate = "No build plate selected";
                currentBuildPlateFilaments = "";
            } else if (currentBuildPlate === "None") {
                currentBuildPlate = "No build plate selected";
                currentBuildPlateFilaments = "";
            } else if (currentBuildPlate === undefined || currentBuildPlate === null) {
                currentBuildPlate = "No build plate selected";
                currentBuildPlateFilaments = "";
            }

            // Replace the commas with a comma and a space
            if (currentBuildPlateFilaments !== "") {
                currentBuildPlateFilaments = String(currentBuildPlateFilaments).replace(/,/g, ", ");
            }
            // Update current build_plate_name
            $("#current-build-plate").text(currentBuildPlate);
            $("#current-build-plate-filaments").text(currentBuildPlateFilaments);

            $("#compatible-filaments-checkboxes").empty(); // Clear existing checkboxes

            const checkboxContainer = $("<div>").addClass("checkbox-container"); // Create a container for checkboxes

            response.filaments.forEach(function (filament) {
                const checkbox = $("<input>").attr("type", "checkbox").attr("id", "filament-" + filament).attr("name", "filament-checkbox").val(filament);
                const label = $("<label>").attr("for", "filament-" + filament).text(filament);
                const div = $("<div>").append(checkbox, label);
                checkboxContainer.append(div); // Append each checkbox to the container
            });

            $("#compatible-filaments-checkboxes").append(checkboxContainer); // Append the container to the main container

        },
        error: function (xhr, status, error) {
            console.error("Error fetching data:", error);
        }
    });
}


$(function () {
// Initial display of added nozzles, filament alert_type, and current nozzle size
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
                    theme = 'error';
                    break;
                case "danger":
                    theme = 'danger';
                    break;
                case "info":
                    theme = "info";
                    break;
                case "tmp_error":
                    theme = "error";
                    break;
                case "tmp_danger":
                    theme = "danger";
                    break;
                case "success":
                    theme = "success";
                    break;
                default:
                    theme = "info";
                    break;
            }

            if (data.msg !== "") {
                new PNotify({
                    title: 'Nozzle Filament Validator',
                    text: data.msg,
                    type: theme,
                    hide: data.type === 'info' || data.type === 'tmp_error' || data.type === 'tmp_danger' || data.type === 'success' ,
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
