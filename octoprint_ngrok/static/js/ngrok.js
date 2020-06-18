$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.tunnelHost = ko.observable('');

        self.requestData = function() {
            OctoPrint.plugins.ngrok.get()
                .done(function(response) {
                    self.tunnelHost(response.tunnel);
                });
        };

        self.onAfterBinding = self.onServerReconnect = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "ngrok") return;
            if (!data.hasOwnProperty("tunnel")) return;

            self.tunnelHost(data.tunnel);
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: NgrokViewModel,
        elements: ["#navbar_plugin_ngrok"]
    });
});
