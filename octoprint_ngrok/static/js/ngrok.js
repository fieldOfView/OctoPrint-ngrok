$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.tunnelName = ko.observable('');

        self.requestData = function() {
            OctoPrint.plugins.ngrok.get()
                .done(function(response) {
                    self.tunnelName(response.tunnel);
                });
        };

        self.onAfterBinding = self.onServerReconnect = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "ngrok") return;
            if (!data.hasOwnProperty("tunnel")) return;

            self.tunnelName(data.tunnel);
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: NgrokViewModel,
        elements: ["#navbar_plugin_ngrok", "#settings_plugin_ngrok"],
        dependencies: ["settingsViewModel"]
    });
});
