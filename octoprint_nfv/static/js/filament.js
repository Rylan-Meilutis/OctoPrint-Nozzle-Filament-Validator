/**
 * Display the filament data for the selected extruder and activate the buttons
 */
function setRefreshButtons() {
    // Remove any existing event handlers for the button
    $('#extruder-tabs').off('click', '[id^="refresh-filament-button"]');

    // Event delegation for refreshing the filament type
    $('#extruder-tabs').on('click', '[id^="refresh-filament-button"]', function () {
        displayData();
    });
    $('#check-spool-id-checkbox').change(function () {
        update_check_spool_id(this.checked);
    });
    $('#check-spool-id-timeout-input').change(function () {
        update_check_spool_id_timeout(this.value);
    });
}

/**
 * Display the filament data for the selected extruder and activate the buttons
 * @param isChecked update the check spool id checkbox
 */
function update_check_spool_id(isChecked) {
    OctoPrint.simpleApiCommand(PLUGIN_ID, "update_check_spool_id", {
        "checkSpoolId": isChecked ? 1 : 0
    }).done(function (response) {
        displayData();
    });
}

/**
 * Update the timeout for the spool id check
 * @param timeout Timeout in seconds
 */
function update_check_spool_id_timeout(timeout) {
    OctoPrint.simpleApiCommand(PLUGIN_ID, "update_check_spool_id_timeout", {
        "timeout": timeout
    }).done(function (response) {
        displayData();
    });
}

/**
 * Display the filament data for the selected extruder and activate the buttons
 * @param dbID Database ID of the spool
 * @param extruderPos Extruder position to select
 */
function updateSpool(dbID, extruderPos) {
    let payload = {databaseId: dbID, toolIndex: extruderPos, commitCurrentSpoolValues: true};
    $.ajax({
        url: self.location.href.substring(0, self.location.href.lastIndexOf('/')) + "/plugin/SpoolManager/selectSpool",
        dataType: "json",
        contentType: "application/json; charset=UTF-8",
        data: JSON.stringify(payload),
        type: "PUT"
    }).done(function (data) {
        displayData();
    }).fail(function (data) {
        new PNotify({
            title: 'SpoolManager Error',
            text: 'Failed to select spool:' + data.responseText,
            type: 'error',
            hide: false,
            closer: true,
            sticker: false,
            buttons: {closer: true, sticker: false}

        })
        updateWaitState("cancel");
    });
}

