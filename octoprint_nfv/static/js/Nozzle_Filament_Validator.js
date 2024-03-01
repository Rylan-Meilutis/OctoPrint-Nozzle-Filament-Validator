const PLUGIN_ID = "Nozzle_Filament_Validator";
let activeTabId = "";

function sleep(time) {
    return new Promise(resolve => setTimeout(resolve, time));
}

// Function to fetch and display general information
function displayGeneralInfo(response) {
    let currentBuildPlate = response.currentBuildPlate || "No build plate selected";
    let currentBuildPlateFilaments = String(response.currentBuildPlateFilaments) || "";
    currentBuildPlateFilaments = currentBuildPlateFilaments.replace(/,/g, ", ");
    let numberOfExtruders = response.number_of_extruders || 0;

    $("#current-build-plate").text(currentBuildPlate);
    $("#current-build-plate-filaments").text(currentBuildPlateFilaments);
    $("#number-of-extruders").text(numberOfExtruders);
}

// Function to create extruder tabs
function createExtruderTabs(extrudersArray, response) {
    $('#extruder-tabs').empty();
    $('#myTabs').empty();

    $('#myTabs').append(`
        <li class="nav-item">
            <a class="nav-link active" data-toggle="tab" href="#general-info-tab">General</a>
        </li>
    `);

    $('#extruder-tabs').append(`
        <div id="general-info-tab" class="tab-pane show active">
            <!-- General information will be displayed here -->
            <strong>Current Build Plate: </strong><span id="current-build-plate"></span><br>
            <strong>Supported Materials: </strong><span id="current-build-plate-filaments"></span><br><hr>
            
            <div class="form-group">
                <strong>Nozzle Settings</strong>
                <label for="nozzle-size-input">Add New Nozzle Size:</label>
                <input type="number" class="form-control" id="nozzle-size-input" placeholder="Enter nozzle size" step="0.2">
                <button id="add-nozzle-button" class="btn btn-primary">Add Nozzle</button>
            </div>

            <div class="form-group">
                <label for="nozzles-list">Select Nozzle:</label>
                <select id="nozzles-list" class="form-control"></select>

                <button id="remove-nozzle-button" class="btn btn-danger">Remove Nozzle</button>
            </div>
            <hr>
            <div class="form-group">
                <strong>Build Plate Settings</strong>
                 <label for="build-plate-list">Select Current Build Plate:</label>
                 <select id="build-plate-list" class="form-control"></select>
                 <button id="select-build-plate-button" class="btn btn-success">Select Build Plate</button>
            </div>
            
            <!-- Button to remove selected build plate -->
            <div class="form-group">
                <button id="remove-build-plate-button" class="btn btn-danger">Remove Build Plate</button>
            </div>
            
            <!-- Input for adding a new build plate -->
            <div class="form-group">
                <label for="build-plate-input">Add New Build Plate:</label>
                <input type="text" class="form-control" id="build-plate-input" placeholder="Enter build plate name">
                <!-- add edit button to edit the currently selected build_plate and add a grid of checkboxes for the compatible
                filaments -->
                <label for="compatible-filaments-checkboxes">Check supported materials:</label>
                <div id="compatible-filaments-checkboxes">
                    <!-- Dynamic checkboxes will be added here -->
                </div>
                <div class="form-check">
                    <br>
                    <hr>
                    <input class="form-check-input" type="checkbox" id="edit-build-plate-checkbox">
                    <label class="form-check-label" for="edit-build-plate-checkbox">Edit Selected Build Plate</label>
                </div>
                <button id="add-build-plate-button" class="btn btn-primary">Add Build Plate</button>
            </div>
        </div>
    `);

    extrudersArray.forEach(function (extruder) {
        let extruderPosition = extruder.extruderPosition || "Position Not Available";
        let extruderNozzleSize = extruder.nozzleSize || "Nozzle size not available";
        let extruderFilamentType = extruder.filamentType || "Filament type not available";

        $('#myTabs').append(`
            <li class="nav-item">
                <a class="nav-link" data-toggle="tab" href="#extruder-${extruderPosition}">Extruder ${extruderPosition}</a>
            </li>
        `);

        let nozzleDropdownDisabled = (response.isMultiExtruder === "False" && extruderPosition !== 1) ? "disabled" : "";
        $('#extruder-tabs').append(`
            <div class="tab-pane" id="extruder-${extruderPosition}">
                <div>
                    <strong>Filament Type: </strong><span>${extruderFilamentType}</span>&nbsp;&nbsp;
                    <button id="refresh-filament-button" class="btn btn-info">Refresh</button>
                    <hr>
                    <strong>Nozzle Size: </strong><span>${extruderNozzleSize}</span>
                    <br>
                    <label for="nozzle-dropdown-${extruderPosition}">Select Nozzle:</label>
                    <select id="nozzle-dropdown-${extruderPosition}" class="form-control" ${nozzleDropdownDisabled}>
                    </select>
                    <button id="select-nozzle-button-${extruderPosition}" class="btn btn-success">Select Nozzle</button>   
                </div>
            </div>
        `);

        // Populate nozzle dropdown options
        let nozzles = response.nozzles || []; // Assuming nozzles are available in response
        let nozzleDropdown = $(`#nozzle-dropdown-${extruderPosition}`);
        nozzleDropdown.empty(); // Clear existing options
        nozzles.forEach(function (nozzle) {
            nozzleDropdown.append($('<option>', {
                value: nozzle.id,
                text: nozzle.size
            }));
        });

    });

    //check if activeTabId is empty, if not set all tabs in the class="tab-content" id="extruder-tabs" to inactive and then the tab with
    //the id of activeTabId to active
    if (activeTabId !== "") {
        $('#extruder-tabs').children().removeClass('active');
        $(`#${activeTabId}`).addClass('active');

    }

    // Event listener for the tab show event to update the activeTabId variable
    $('a[data-toggle="tab"]').on('show.bs.tab', function (e) {
        let data = e.target.getAttribute("href").slice(1);
        //check if data isn't blank and is a child of the extruder-tabs div
        if (data !== "" && $(`#${data}`).parent().attr('id') === "extruder-tabs") {
            activeTabId = data;
        }

    });


}

// Function to fetch extruder information
function fetchExtruderInfo(numberOfExtruders) {
    let promises = [];

    for (let i = 0; i < numberOfExtruders; i++) {
        let promise = new Promise((resolve, reject) => {
            OctoPrint.simpleApiCommand(PLUGIN_ID, "get_extruder_info", {"extruderId": i + 1})
                .done(function (response) {
                    resolve(response);
                }).fail(function (xhr, status, error) {
                reject(error);
            });
        });
        promises.push(promise);
    }

    return Promise.all(promises);
}

// Main function to display data
function displayData() {
    OctoPrint.simpleApiGet(PLUGIN_ID).done(function (response) {
        fetchExtruderInfo(response.number_of_extruders)
            .then((responses) => {
                let extruderArray = responses;
                extruderArray.sort((a, b) => (a.extruderPosition > b.extruderPosition) ? 1 : -1);
                createExtruderTabs(extruderArray, response);
                displayGeneralInfo(response);
                activate_nozzle_buttons(response);
                activate_build_plate_buttons(response);
                activate_extruder_buttons(response);
                setRefreshButtons();

            }).catch((error) => {
            console.error("Error fetching extruder info:", error);
        });
    });
}

$(function () {
// Bind the plugin message handler to the global scope
    function messageHandler() {

        this.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "Nozzle_Filament_Validator") {
                return;
            }
            if (data.type === "reload") {
                displayData();
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
                    hide: data.type === 'info' || data.type === 'tmp_error' || data.type === 'tmp_danger' || data.type === 'success',
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

    // $(document).ready(function () {
    // Initial display of data
    sleep(500).then(() => {
        displayData();
    });
    // });
});