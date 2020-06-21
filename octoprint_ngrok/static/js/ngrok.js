$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.tunnelName = ko.observable('');

        self.closeTunnel = function() {
            OctoPrint.simpleApiCommand("ngrok", "close", {});
        }

        self.connectTunnel = function() {
            self.settings.saveData();
            OctoPrint.simpleApiCommand("ngrok", "connect", {});
        }

        self.showTunnelSettings = function() {
            self.settings.show('#settings_plugin_ngrok');
        }

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

            if (data.hasOwnProperty("tunnel")) {
                self.tunnelName(data.tunnel);
            }
            else if (data.hasOwnProperty("error")) {
                new PNotify({
                    title: gettext("Failed to create tunnel"),
                    text: data.error.replace(/(?:\\r\\n|\\r|\\n)/g, "<br />"),
                    type: "error",
                    hide: false
                });
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: NgrokViewModel,
        elements: ["#navbar_plugin_ngrok", "#settings_plugin_ngrok"],
        dependencies: ["settingsViewModel"]
    });
});
