$(function() {
    // Function to fetch and display added nozzles
    function displayNozzles() {
        $.ajax({
            url: API_BASEURL + "plugin/NozzleFilamentValidator/nozzles",
            type: "GET",
            dataType: "json",
            success: function(response) {
                // Display the list of added nozzles
                $("#nozzles-list").empty();
                $.each(response.nozzles, function(index, nozzle) {
                    $("#nozzles-list").append($("<option>", { value: nozzle.id, text: nozzle.size }));
                });
            },
            error: function(xhr, status, error) {
                console.error("Error fetching nozzles:", error);
            }
        });
    }

    // Event handler for adding a nozzle
    $("#add-nozzle-button").click(function() {
        var nozzleSize = parseFloat($("#nozzle-size-input").val());
        $.ajax({
            url: API_BASEURL + "plugin/NozzleFilamentValidator/nozzles",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ "size": nozzleSize }),
            success: function(response) {
                displayNozzles();
            },
            error: function(xhr, status, error) {
                console.error("Error adding nozzle:", error);
            }
        });
    });

    // Event handler for selecting the current sized nozzle
    $("#select-nozzle-button").click(function() {
        var selectedNozzleId = $("#nozzles-list").val();
        $.ajax({
            url: API_BASEURL + "plugin/NozzleFilamentValidator/current_nozzle",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ "nozzle_id": selectedNozzleId }),
            success: function(response) {
                // Optionally, perform any UI update after selecting the nozzle
            },
            error: function(xhr, status, error) {
                console.error("Error selecting nozzle:", error);
            }
        });
    });

    // Initial display of added nozzles
    displayNozzles();
});
