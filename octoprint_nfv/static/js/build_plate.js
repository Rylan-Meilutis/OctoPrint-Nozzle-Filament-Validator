$(function () {


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
            } else {
                // Clear the input fields and uncheck all checkboxes
                $("#build-plate-input").val("");
                $("input[type='checkbox'][name='filament-checkbox']").prop('checked', false);
            }
        }
    );


// Function to confirm before removing a build_plate
    function confirmRemoveBuildPlate(buildPlateID, buildPlateName) {
        if (confirm("Are you sure you want to remove build plate " + buildPlateName + "?")) {
            removeBuildPlate(buildPlateID);
        }
    }

// Function to remove a build_plate
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
});