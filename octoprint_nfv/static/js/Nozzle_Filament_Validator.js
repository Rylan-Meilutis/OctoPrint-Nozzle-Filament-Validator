$(function () {
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

    // Function to update the name and compatible filaments when the edit button is checked
    $("#edit-build-plate-checkbox").change(function () {
            if (this.checked) {
                const selectedBuildPlateId = $("#build-plate-list").val();
                // Fetch the current build plate data
                $.ajax({
                    url: API_BASEURL + "plugin/" + PLUGIN_ID,
                    type: "POST",
                    contentType: "application/json; charset=UTF-8",
                    dataType: "json",
                    data: JSON.stringify({
                        "command": "get_build_plate",
                        "buildPlateId": selectedBuildPlateId
                    }),
                    success: function (response) {
                        let filaments = [];
                        if (response.filaments) {
                            filaments = response.filaments.split(",");
                        }
                        // Update the input fields with the current values
                        $("#build-plate-input").val(response.name);
                        // Check the compatible filaments checkboxes
                        $("input[type='checkbox'][name='filament-checkbox']").prop('checked', false); // Uncheck all checkboxes first
                        if (filaments) {
                            filaments.forEach(function (filament) {
                                const cleanedFilament = String(filament).replace(/[\[\]]/g, ""); // Remove square brackets
                                $("input[type='checkbox'][name='filament-checkbox'][value=" + cleanedFilament.trim() + "]").prop('checked', true);
                            });
                        } else {
                            console.error("Compatible filaments is invalid:", filaments);
                        }
                    },
                    error: function (xhr, status, error) {
                        console.error("Error fetching build plate data:", error);
                    }
                });
            }
        }
    );

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

// Event handler for refreshing the filament alert_type
    $("#refresh-filament-button").click(function () {
        displayData();
    });
// Initial display of added nozzles, filament alert_type, and current nozzle size
    displayData();

// Function to confirm before removing a build_plate
    function confirmRemoveBuildPlate(buildPlateID, buildPlateName) {
        if (confirm("Are you sure you want to remove build plate " + buildPlateName + "?")) {
            removeBuildPlate(buildPlateID);
        }
    }

// Function to remove a nozzle
    function removeBuildPlate(buildPlateID) {
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "remove_build_plate",
                "buildPlateId": buildPlateID
            }),
            success: function (response) {
                displayData();
            },
            error: function (xhr, status, error) {
                console.error("Error removing build plate:", error);
            }
        });
    }

// Event handler for adding a nozzle
    $("#add-build-plate-button").click(function () {
        const buildPlateName = $("#build-plate-input").val();
        let compatibleFilaments = "";

        // Iterate over the checkboxes and concatenate checked filament names
        $("input[type='checkbox'][name='filament-checkbox']:checked").each(function () {
            compatibleFilaments += $(this).val() + ",";
        });
        compatibleFilaments = compatibleFilaments.replace(/,\s*$/, "");


        // Remove trailing comma
        let id = $("#build-plate-list").val();
        const isEditChecked = $("#edit-build-plate-checkbox").prop("checked");


        // Update id based on the value of the edit checkbox
        if (!isEditChecked) {
            id = "null";
        }

        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "add_build_plate",
                "name": buildPlateName,
                "compatibleFilaments": compatibleFilaments,
                "id": id
            }),
            success: function (response) {
                displayData();
            },
            error: function (xhr, status, error) {
                console.error("Error adding build plate: " + buildPlateName, error);
            }
        });
    });

// Event handler for selecting the current sized build_plate
    $("#select-build-plate-button").click(function () {
        const selectedBuildPlateId = $("#build-plate-list").val();
        $.ajax({
            url: API_BASEURL + "plugin/" + PLUGIN_ID,
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            dataType: "json",
            data: JSON.stringify({
                "command": "select_build_plate",
                "buildPlateId": selectedBuildPlateId
            }),

            success: function (response) {
                displayData()
                // Optionally, perform any UI update after selecting the nozzle
            },
            error: function (xhr, status, error) {
                console.error("Error selecting build plate: " + selectedBuildPlateId, error);
            }
        });
    });

// Event handler for removing a build_plate
    $("#remove-build-plate-button").click(function () {
        const selectedBuildPlateId = $("#build-plate-list").val();
        const selectedBuildPlateName = $("#build-plate-list option:selected").text();
        confirmRemoveBuildPlate(selectedBuildPlateId, selectedBuildPlateName);
    });


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
                case "info":
                    theme = "info";
                    break;
                case "tmp_error":
                    theme = "danger";
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
                    hide: data.type === 'info' || data.type === 'tmp_error',
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

})
;
