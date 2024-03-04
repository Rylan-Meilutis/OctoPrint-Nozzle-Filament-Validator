function setRefreshButtons() {
    // Remove any existing event handlers for the button
    $('#extruder-tabs').off('click', '[id^="refresh-filament-button"]');

    // Event delegation for refreshing the filament type
    $('#extruder-tabs').on('click', '[id^="refresh-filament-button"]', function () {
        displayData();
    });
}