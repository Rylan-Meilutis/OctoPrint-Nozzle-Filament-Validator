/**
 *  This file contains the JavaScript code for the build_plate plugin. It also contains the event handlers for the build
 *  plate buttons.
 * @param response the response from the server
 */
function activate_build_plate_buttons(response) {

    $("#build-plate-list").empty();
    $.each(response.build_plates, function (index, plate) {
        $("#build-plate-list").append($("<option>", {
            value: plate.id,
            text: plate.name
        }));
    });

    // Function to update the name and compatible filaments when the edit button is checked
    $("#edit-build-plate-checkbox").change(function () {
            if (this.checked) {
                const selectedBuildPlateId = $("#build-plate-list").val();
                // Fetch the current build plate data
                OctoPrint.simpleApiCommand(PLUGIN_ID, "get_build_plate", {"buildPlateId": selectedBuildPlateId})
                    .done(function (response) {
                        let filaments = [];
                        if (response.filaments) {
                            filaments = response.filaments.split(",");
                        }

                        // Disable the dropdown while in editing mode
                        $("#build-plate-list").prop('disabled', true);
                        $("#select-build-plate-button").prop('disabled', true);
                        $("#remove-build-plate-button").prop('disabled', true);

                        // Update the input fields with the current values
                        $("#build-plate-input").val(response.name);
                        $("#add-build-plate-button").text("Update Build Plate");
                        $("#add-build-plate-title").text("Update Build Plate:");
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
                    });
            } else {
                // Clear the input fields and uncheck all checkboxes
                $("#build-plate-input").val("");
                $("#add-build-plate-button").text("Add Build Plate");
                $("#add-build-plate-title").text("Add New Build Plate:");
                // Enable the dropdown when not in editing mode
                $("#build-plate-list").prop('disabled', false);
                $("#select-build-plate-button").prop('disabled', false);
                $("#remove-build-plate-button").prop('disabled', false);
                $("input[type='checkbox'][name='filament-checkbox']").prop('checked', false);
            }
        }
    );


// Function to confirm before removing a build_plate
    /**
     * Confirm before removing a build_plate
     * @param buildPlateID the build_plate ID
     * @param buildPlateName the build_plate name
     */
    function confirmRemoveBuildPlate(buildPlateID, buildPlateName) {
        if (confirm("Are you sure you want to remove build plate " + buildPlateName + "?")) {
            removeBuildPlate(buildPlateID);
        }
    }

// Function to remove a build_plate
    /**
     * Remove a build_plate
     * @param buildPlateID the build_plate ID
     */
    function removeBuildPlate(buildPlateID) {

        OctoPrint.simpleApiCommand(PLUGIN_ID, "remove_build_plate", {"buildPlateId": buildPlateID})
            .done(function (response) {
                displayData();
            });
    }

// Event handler for adding a build_plate
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

        OctoPrint.simpleApiCommand(PLUGIN_ID, "add_build_plate", {
            "name": buildPlateName,
            "compatibleFilaments": compatibleFilaments,
            "id": id
        }).done(function (response) {
            displayData();
        });
    });

// Event handler for selecting the current sized build_plate
    $("#select-build-plate-button").click(function () {
        const selectedBuildPlateId = $("#build-plate-list").val();
        OctoPrint.simpleApiCommand(PLUGIN_ID, "select_build_plate", {"buildPlateId": selectedBuildPlateId}).done(function (response) {
            displayData();
        });
    });

// Event handler for removing a build_plate
    $("#remove-build-plate-button").click(function () {
        const selectedBuildPlateId = $("#build-plate-list").val();
        const selectedBuildPlateName = $("#build-plate-list option:selected").text();
        confirmRemoveBuildPlate(selectedBuildPlateId, selectedBuildPlateName);
    });

    $("#compatible-filaments-checkboxes").empty(); // Clear existing checkboxes

    const checkboxContainer = $("<div>").addClass("checkbox-container"); // Create a container for checkboxes

    response.filaments.forEach(function (filament) {
        const checkbox = $("<input>").attr("type", "checkbox").attr("id", "filament-" + filament).attr("name", "filament-checkbox").val(filament);
        const label = $("<label>").attr("for", "filament-" + filament).text(filament);
        const div = $("<div>").append(checkbox, label);
        checkboxContainer.append(div); // Append each checkbox to the container
    });

    $("#compatible-filaments-checkboxes").append(checkboxContainer); // Append the container to the main container
}