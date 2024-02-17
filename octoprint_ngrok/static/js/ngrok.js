$(function() {

    function NgrokViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.loginState = parameters[1];
        self.access = parameters[2];

        self.tunnelName = ko.observable('');

        self.tokenIsEmpty = ko.observable(false);
        self.nameIsEmpty = ko.observable(false);
        self.passIsEmpty = ko.observable(false);

        self._notification = undefined;


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

        self.addAllowedDomain = function() {
            if(self.settings.settings.plugins.ngrok.oauth_allow_domains().indexOf($("#settings_plugin_ngrok_oauth_allow_domains").val()) < 0) {
                self.settings.settings.plugins.ngrok.oauth_allow_domains.push($("#settings_plugin_ngrok_oauth_allow_domains").val());
                $("#settings_plugin_ngrok_oauth_allow_domains").val('');
            }
        }

        self.addAllowedEmail = function() {
            if(self.settings.settings.plugins.ngrok.oauth_allow_emails().indexOf($("#settings_plugin_ngrok_oauth_allow_emails").val()) < 0) {
                self.settings.settings.plugins.ngrok.oauth_allow_emails.push($("#settings_plugin_ngrok_oauth_allow_emails").val());
                $("#settings_plugin_ngrok_oauth_allow_emails").val('');
            }
        }

        self.removeAllowedDomain = function(data) {
            self.settings.settings.plugins.ngrok.oauth_allow_domains.remove(data);
        }

        self.removeAllowedEmail = function(data) {
            self.settings.settings.plugins.ngrok.oauth_allow_emails.remove(data);
        }

        self.connectTunnel = function() {
            self.settings.saveData();
            OctoPrint.simpleApiCommand("ngrok", "connect", {});
        }

        self.showTunnelSettings = function() {
            if (!self.loginState.hasPermission(self.access.permissions.SETTINGS)) {
                return;
            }
            self.settings.show("#settings_plugin_ngrok");
        }

        self.requestData = function() {
            OctoPrint.plugins.ngrok.get()
                .done(function(response) {
                    self.tunnelName(response.tunnel);
                    if(response.tunnel !== '') {
                        $('#ngrok_qrcode').empty().qrcode({size: 180, text: "https://" + response.tunnel});
                    }
                });
        };


        self.onAfterBinding = self.onServerReconnect = function() {
            self.tokenIsEmpty(self.settings.settings.plugins.ngrok.token() == "");
            self.nameIsEmpty(self.settings.settings.plugins.ngrok.auth_name() == "");
            self.passIsEmpty(self.settings.settings.plugins.ngrok.auth_pass() == "");
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "ngrok") return;

            if (data.hasOwnProperty("tunnel")) {
                self.tunnelName(data.tunnel);
                if(data.tunnel !== '') {
                    $('#ngrok_qrcode').empty().qrcode({size: 180, text: "https://" + data.tunnel});
                }
                if (
                    self._notification !== undefined &&
                    self._notification.state == "open" &&
                    self._notification.options.type == "error"
                ) {
                    self._notification.remove();
                }
            }
            else if (data.hasOwnProperty("error")) {
                if (
                    self._notification !== undefined &&
                    self._notification.state == "open"
                ) {
                    self._notification.remove();
                }
                self._notification = new PNotify({
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
        dependencies: ["settingsViewModel", "loginStateViewModel", "accessViewModel"]
    });
});
