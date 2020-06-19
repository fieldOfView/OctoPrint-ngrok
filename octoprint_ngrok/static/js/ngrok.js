$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.tunnelName = ko.observable('');

        self.tunnelName.subscribe(function(host_name) {
            $("#settings_plugin_ngrok_tunnel_address").val(host_name);
            var host_url = (host_name != '') ? 'https://' + host_name : '';
            $("#settings_plugin_ngrok_tunnel_visit").attr('href', host_url);
        });

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
        elements: ["#navbar_plugin_ngrok"],
        dependencies: ["settingsViewModel"]
    });
});
