function setRefreshButtons() {
    // Event delegation for refreshing the filament type
    $('#extruder-tabs').on('click', '[id^="refresh-filament-button"]', function () {
        displayData();
    });
}