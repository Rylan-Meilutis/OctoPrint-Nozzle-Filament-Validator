const PLUGIN_ID = "Nozzle_Filament_Validator";
let activeTabId = "";

/**
 * Function to sleep for a given time in ms
 * @param time the time to sleep in ms
 * @returns {Promise<unknown>}
 */
function sleep(time) {
    return new Promise(resolve => setTimeout(resolve, time));
}

// Function to fetch and display general information
/**
 * Function to display general information
 * @param response The response object
 */
function displayGeneralInfo(response) {
    let currentBuildPlate = response.currentBuildPlate || "No build plate selected";
    let currentBuildPlateFilaments = String(response.currentBuildPlateFilaments) || "";
    currentBuildPlateFilaments = currentBuildPlateFilaments.replace(/,/g, ", ");
    let numberOfExtruders = response.number_of_extruders || 0;

    $("#current-build-plate").text(currentBuildPlate);
    $("#current-build-plate-filaments").text(currentBuildPlateFilaments);
    $("#number-of-extruders").text(numberOfExtruders);
}

/**
 * Function to update the state of the filament spool check
 * @param state The state to update to
 */
function updateWaitState(state) {
    OctoPrint.simpleApiCommand(PLUGIN_ID, "updateWaitState", {"state": state}).done(function (response) {
        displayData();
    });
}

// Function to create extruder tabs
/**
 * Function to create extruder tabs
 * @param extrudersArray The array of extruders
 * @param response The response object
 */
function createExtruderTabs(extrudersArray, response) {
    $('#extruder-tabs').empty();
    $('#myTabs').empty();

    $('#myTabs').append(`
        <li class="nav-item active" id="#general-info-tab">
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
                <label id="add-build-plate-title" for="build-plate-input">Add New Build Plate:</label>
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
            
            <hr>
            <!-- Checkbox to set check_spool_id -->
            <div class="form-group">
                <input type="checkbox" id="check-spool-id-checkbox" ${response.check_spool_id === "True" ? 'checked' : ''}>
                <label for="check-spool-id-checkbox">Check Spool ID</label>
            </div>
            <!-- Input field to set check_spool_id_timeout -->
            <div class="form-group">
                <label for="check-spool-id-timeout-input">Check Spool ID Timeout</label>
                <input type="number" id="check-spool-id-timeout-input" placeholder="Enter timeout" step="1" value="${response.check_spool_id_timeout}">
                <p>The timeout determins how long it takes with no action until the print is aborted if the spool id in 
                the gcode doesn't match the id in Spool Manager (default 300 seconds)</p>
            </div>
            
            <hr>
            <!-- help info -->
            <div>
            <p>For help and usage info, visit <a href="https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/blob/main/README.md" target="_blank">this</a> page</p>
            <p>For help, setup, and usage info for the post-procesor, visit <a href="https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/blob/main/Postprocesor/README.md" target="_blank">this</a> page</p>
            </div>
        </div>
    `);

    extrudersArray.forEach(function (extruder) {
        let extruderPosition = extruder.extruderPosition || "Position Not Available";
        let extruderNozzleSize = extruder.nozzleSize || "Nozzle size not available";
        let extruderFilamentType = extruder.filamentType || "Filament type not available";
        let extruderFilamentName = extruder.spoolName || "Filament DB ID not available";
        let check_spool_id = response.check_spool_id >= "True" || false;

        $('#myTabs').append(`
            <li class="nav-item" id="#extruder-${extruderPosition}">
                <a class="nav-link" data-toggle="tab" href="#extruder-${extruderPosition}">Extruder ${extruderPosition}</a>
            </li>
        `);

        let nozzleDropdownDisabled = (response.isMultiExtruder === "False" && extruderPosition !== 1) ? "disabled" : "";
        $('#extruder-tabs').append(`
            <div class="tab-pane" id="extruder-${extruderPosition}">
                <div>
                    <strong>Filament Type: </strong><span>${extruderFilamentType}</span><br>
                    <strong>Spool Name: </strong><span>${extruderFilamentName}</span>&nbsp;&nbsp;
                    <button id="refresh-filament-button" class="btn btn-info">Refresh</button>
                    ${check_spool_id && extruderFilamentName !== "Filament DB ID not available" ? '<p>To setup this spool in your slicer, you need to add the following line into ' +
            'the notes setting of your filament <code>[sm_name = ' + extruderFilamentName + ']</code><br>(Note: you cannot have brackets [] in the name of your filament.)</p>' : ''}
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
        $('#myTabs').children().removeClass('active');
        $(`#${activeTabId}`).addClass('active');
        $('#myTabs li[id="#' + activeTabId + '"]').addClass('active');

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
/**
 * Fetches extruder information for the given number of extruders
 * @param numberOfExtruders The number of extruders to fetch information for
 * @returns {Promise<Awaited<Promise>[]>}
 */
function fetchExtruderInfo(numberOfExtruders) {
    let promises = [];

    for (let i = 0; i < numberOfExtruders; i++) {
        let promise = new Promise((resolve, reject) => {
            OctoPrint.simpleApiCommand(PLUGIN_ID, "get_extruder_info", {"extruderId": i + 1})
                .done(function (response) {
                    resolve(response);
                }).fail(function (error) {
                new PNotify({
                    title: 'Extruder Error',
                    text: 'Failed to fetch extruder information for extruder ' + (i + 1) + '.',
                    type: 'error',
                    hide: false
                })
            });
        });
        promises.push(promise);
    }
    return Promise.all(promises);
}

// Main function to display data
/**
 * Function to update the display window with the latest data
 */
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
    /**
     * this function is called when the plugin receives a message from the server
     */
    function messageHandler() {
        /**
         * This function is called when the plugin receives a message from the server
         * @param plugin The plugin that sent the message
         * @param data The data sent by the plugin
         */
        this.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "Nozzle_Filament_Validator") {
                return;
            }
            if (data.type === "reload") {
                displayData();
                return;
            }

            if (data.type === "switch_spools") {
                get_spools().then((raw_spool_data) => {
                    let raw_data = data.msg.split(",");
                    let desiredName = raw_data[0];

                    // remove leading and trailing whitespace
                    while (desiredName[0] === " ") {
                        desiredName = desiredName.substring(1);
                    }
                    while (desiredName[desiredName.length - 1] === " ") {
                        desiredName = desiredName.substring(0, desiredName.length - 1);
                    }

                    let extruderPos = raw_data[1].replace(" ", "");
                    let currentName = raw_data[2].replace(" ", "");
                    let timeout = raw_data[3].replace(" ", "");

                    if (raw_spool_data === undefined || raw_spool_data.length === 0) {
                        alert("No spools found in Spool Manager. Please add a spool to Spool Manager before continuing.");
                        updateWaitState("cancel")
                        return;
                    }

                    let spool = raw_spool_data.find(sp => sp.displayName === desiredName);
                    let desiredDbId = undefined;

                    if (spool) {
                        desiredDbId = spool.databaseId;
                    }

                    if (desiredDbId === undefined) {
                        new PNotify({
                            title: 'Spool Mismatch Detected',
                            text: 'The spool specified in the gcode (name: ' + desiredName + ') does not match the spool ' +
                                'loaded in Spool Manager (name: ' + currentName + '). The desired spool was not found. Which of the following is true?',
                            icon: 'fas fa-question-circle',
                            hide: false,
                            closer: false,
                            sticker: false,
                            destroy: true,
                            buttons: {closer: false, sticker: false},
                            confirm: {
                                confirm: true,
                                buttons: [{
                                    text: 'The incorrect spool is loaded',
                                    addClass: "button",
                                    click: notice => {
                                        updateWaitState("cancel");
                                        notice.update({
                                            title: 'Incorrect spool loaded',
                                            text: 'leaving the spool and canceling the print',
                                            icon: true,
                                            closer: true,
                                            sticker: false,
                                            type: 'info',
                                            buttons: {closer: true, sticker: false},
                                            hide: true,
                                        });
                                        notice.get().find(".button").remove();
                                    },
                                },
                                    {
                                        text: 'The incorrect spool is loaded but I want to continue anyway.',
                                        addClass: "button",
                                        click: notice => {
                                            updateWaitState("ok");
                                            notice.update({
                                                title: 'Ignoring spool',
                                                text: 'Ignoring the spool and continuing the print',
                                                icon: true,
                                                closer: true,
                                                sticker: false,
                                                type: 'info',
                                                buttons: {closer: true, sticker: false},
                                                hide: true,
                                            });
                                            notice.get().find(".button").remove();

                                        }
                                    }
                                ]
                            }, before_close: function (notice) {
                                updateWaitState("cancel")
                            },
                            // Close the notification after 5000 milliseconds (5 seconds)
                            autoClose: $(timeout) ? timeout * 1000 : 5000

                        });
                        return;
                    }

                    new PNotify({
                        title: 'Spool Mismatch Detected',
                        text: 'The spool specified in the gcode (name: ' + desiredName + ') does not match the spool ' +
                            'loaded in Spool Manager (name: ' + currentName + '). Which of the following is true?',
                        icon: 'fas fa-question-circle',
                        hide: false,
                        closer: false,
                        sticker: false,
                        destroy: true,
                        buttons: {closer: false, sticker: false},
                        confirm: {
                            confirm: true,
                            buttons: [{
                                text: 'The correct spool is loaded',
                                primary: true,
                                addClass: "button",
                                click: notice => {
                                    updateSpool(desiredDbId, extruderPos);
                                    updateWaitState("ok");
                                    notice.update({
                                        title: 'Correct spool loaded',
                                        text: 'Changing the spool and continuing',
                                        icon: true,
                                        closer: true,
                                        sticker: false,
                                        type: 'info',
                                        buttons: {closer: true, sticker: false},
                                        hide: true,
                                    });
                                    notice.get().find(".button").remove();
                                }
                            },
                                {
                                    text: 'The incorrect spool is loaded',
                                    addClass: "button",
                                    click: notice => {
                                        updateWaitState("cancel");
                                        notice.update({
                                            title: 'Incorrect spool loaded',
                                            text: 'leaving the spool and canceling the print',
                                            icon: true,
                                            closer: true,
                                            sticker: false,
                                            type: 'info',
                                            buttons: {closer: true, sticker: false},
                                            hide: true,
                                        });
                                        notice.get().find(".button").remove();
                                    },
                                },
                                {
                                    text: 'The incorrect spool is loaded but I want to continue anyway.',
                                    addClass: "button",
                                    click: notice => {
                                        updateWaitState("ok");
                                        notice.update({
                                            title: 'Ignoring spool',
                                            text: 'Ignoring the spool and continuing the print',
                                            icon: true,
                                            closer: true,
                                            sticker: false,
                                            type: 'info',
                                            buttons: {closer: true, sticker: false},
                                            hide: true,
                                        });
                                        notice.get().find(".button").remove();
                                    }
                                }
                            ]
                        }, before_close: function (notice) {
                            updateWaitState("cancel")
                        },
                        // Close the notification after 5000 milliseconds (5 seconds)
                        autoClose: $(timeout) ? timeout * 1000 : 5000
                    });

                }).catch((error) => {
                    console.log("Error fetching spools:", error);
                });
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


    // Add the plugin message handler to the list of OctoPrint view models
    OCTOPRINT_VIEWMODELS.push({
        construct: messageHandler,
        additionalNames: ["messageHandler"],
        dependencies: ["loginStateViewModel", "appearanceViewModel"],
        elements: [""]
    });

    // Initial display of data
    sleep(500).then(() => {
        displayData();
    });
});