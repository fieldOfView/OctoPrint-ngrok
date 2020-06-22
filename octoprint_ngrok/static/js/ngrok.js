$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.tunnelName = ko.observable('');

        self.tokenIsEmpty = ko.observable(false);
        self.nameIsEmpty = ko.observable(false);
        self.passIsEmpty = ko.observable(false);

        $("#settings_plugin_ngrok_token").change(function(){
            self.tokenIsEmpty(this.value == "");
        });
        $("#settings_plugin_ngrok_auth_name").change(function(){
            self.nameIsEmpty(this.value == "");
        });
        $("#settings_plugin_ngrok_auth_pass").change(function(){
            self.passIsEmpty(this.value == "");
        });


        self.closeTunnel = function() {
            OctoPrint.simpleApiCommand("ngrok", "close", {});
        }

        self.connectTunnel = function() {
            self.settings.saveData();
            OctoPrint.simpleApiCommand("ngrok", "connect", {});
        }

        self.showTunnelSettings = function() {
            self.settings.show("#settings_plugin_ngrok");
        }

        self.requestData = function() {
            OctoPrint.plugins.ngrok.get()
                .done(function(response) {
                    self.tunnelName(response.tunnel);
                });
        };


        self.onAfterBinding = self.onServerReconnect = function() {
            console.log(self.settings)
            self.tokenIsEmpty(self.settings.settings.plugins.ngrok.token() == "");
            self.nameIsEmpty(self.settings.settings.plugins.ngrok.auth_name() == "");
            self.passIsEmpty(self.settings.settings.plugins.ngrok.auth_pass() == "");

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
