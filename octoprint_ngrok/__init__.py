# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin

import flask
import base64
import zlib

from pyngrok import ngrok
from pyngrok.conf import PyngrokConfig
from pyngrok.exception import PyngrokNgrokError

class NgrokPlugin(octoprint.plugin.SettingsPlugin,
				  octoprint.plugin.StartupPlugin,
				  octoprint.plugin.ShutdownPlugin,
				  octoprint.plugin.SimpleApiPlugin,
				  octoprint.plugin.AssetPlugin,
				  octoprint.plugin.TemplatePlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._port = 0
		self._tunnel_url = ""
		self._ngrok_started = False
		self._restart_ngrok = True


	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			token="",
			region="us",
			subdomain="",
			auth_name="",
			auth_pass="",
			auto_connect=True,
			trust_basic_authentication=False,
		)

	def get_settings_restricted_paths(self):
		return dict(
			admin=[
				['token'], ['auth_name'], ['auth_pass']
			]
		)

	def get_settings_version(self):
		return 1

	def on_settings_migrate(self, target, current):
		if current is None or current < 1:
			self._settings.set(["auth_pass"], self._obfuscate(self._settings.get(["auth_pass"])))

	def get_settings_preprocessors(self):
		return (
			dict(auth_pass=lambda x: self._deobfuscate(x)),  # getter preprocessors
			dict(auth_pass=lambda x: self._obfuscate(x))     # setter preprocessors
		)

	def on_settings_load(self):
		data = octoprint.plugin.SettingsPlugin.on_settings_load(self)

		if "trust_basic_authentication" in data:
			data["trust_basic_authentication"] = self._settings.global_get_boolean(["accessControl", "trustBasicAuthentication"])

		if "auth_pass" in data:
			data["auth_pass"] = self._deobfuscate(data["auth_pass"])

		return data

	def on_settings_save(self, data):
		if "auth_pass" in data:
			data["auth_pass"] = self._obfuscate(data["auth_pass"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		if "trust_basic_authentication" in data:
			self._settings.global_set_boolean(["accessControl", "trustBasicAuthentication"], data["trust_basic_authentication"])
			if data["trust_basic_authentication"]:
				self._settings.global_set_boolean(["accessControl", "checkBasicAuthenticationPassword "], True)

		if "token" in data or "region" in data:
			self._restart_ngrok = True

		if self._settings.getBoolean(["auto_connect"]):
			self._ngrok_connect()


	##~~ StartupPlugin mixin

	def on_startup(self, host, port):
		self._port = port

		# prefer port from discovery plugin if available, in case of a reverse proxy
		public_port = self._settings.global_get_int(["plugins", "discovery", "publicPort"])
		if public_port:
			self._port = public_port

	def on_after_startup(self):
		if self._settings.getBoolean(["auto_connect"]):
			self._ngrok_connect()


	##~~ ShutdownPlugin mixin

	def on_shutdown(self):
		if self._ngrok_started:
			self._ngrok_disconnect()
			ngrok.kill()


	#~~ AssetPlugin

	def get_assets(self):
		return dict(
			clientjs=["clientjs/ngrok.js"],
			js=["js/ngrok.js"]
		)


	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [dict(
			type='settings',
			custom_bindings=True,
			template='ngrok_settings.jinja2'
		), dict(
			type='navbar',
			custom_bindings=True,
			template='ngrok_navbar.jinja2',
			classes=["dropdown"]
		)]


	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(
			connect=[],
			close=[]
		)

	def on_api_command(self, command, data):
		if command == "connect":
			self._logger.info("(Re-)connecting to ngrok tunnel")
			self._ngrok_connect()

		elif command == "close":
			self._logger.info("Closing connection with ngrok")
			if self._ngrok_started:
				self._ngrok_disconnect()
			ngrok.kill()
			self._ngrok_started = False
			self._restart_ngrok = True

	def on_api_get(self, request):
		return flask.jsonify(tunnel=self._tunnel_url)


	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			ngrok=dict(
				displayName="Ngrok Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="fieldOfView",
				repo="OctoPrint-ngrok",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/fieldOfView/OctoPrint-ngrok/archive/{target_version}.zip"
			)
		)


	##~~ Ngrok logic

	def _ngrok_disconnect(self):
		self._logger.info("Closing any open ngrok tunnels")
		try:
			for tunnel in ngrok.get_tunnels():
				self._logger.info("Closing tunnel %s" % tunnel.public_url)
				ngrok.disconnect(tunnel.public_url)
		except PyngrokNgrokError:
			pass
		self._tunnel_url = ""
		self._plugin_manager.send_plugin_message(self._identifier, dict(tunnel=self._tunnel_url))

	def _ngrok_connect(self):
		if self._ngrok_started:
			self._ngrok_disconnect()

		if not self._settings.get(["token"]):
			self._logger.warning("Ngrok auth token is not configured")
			self._plugin_manager.send_plugin_message(self._identifier, dict(error="The auth token is not configured. An auth token is required to create a secure tunnel."))

			self._restart_ngrok = True

			return

		if not (self._settings.get(["auth_name"]) and self._settings.get(["auth_pass"])):
			self._logger.warning("Basic Auth is not configured")
			self._plugin_manager.send_plugin_message(self._identifier, dict(error="The username and password are not configured. Authentication is required to create a secure tunnel."))

			return

		pyngrok_config = PyngrokConfig()
		pyngrok_config.log_event_callback = self.on_ngrok_log_event

		if self._restart_ngrok:
			self._logger.info("Setting ngrok auth token & region...")
			if self._ngrok_started:
				ngrok.kill()  # Make sure no previous token is used

			pyngrok_config.auth_token = self._settings.get(["token"])
			pyngrok_config.region = self._settings.get(["region"])

			# Resettimg the _restart_ngrok flag is postponed until we know the restart was succesful
			# because otherwise the token and region may not "take".

		self._logger.info("Opening ngrok tunnel...")
		options = dict(
			bind_tls=True,
			inspect=False,
			auth="%s:%s" % (
				self._settings.get(["auth_name"]),
				self._settings.get(["auth_pass"])
			)
		)

		if self._settings.get(["subdomain"]):
			options["subdomain"] = self._settings.get(["subdomain"])

		try:
			tunnel_url = ngrok.connect(port=self._port, options=options, pyngrok_config=pyngrok_config)
			self._ngrok_started = True
		except PyngrokNgrokError:
			self._logger.error("Could not connect with the provided API key")
			return

		if tunnel_url:
			self._tunnel_url = tunnel_url.partition("://")[2]
			self._logger.info("ngrok tunnel: %s" % self._tunnel_url)
			self._plugin_manager.send_plugin_message(self._identifier, dict(tunnel=self._tunnel_url))

			self._restart_ngrok = False

	def on_ngrok_log_event(self, log):
		if log.lvl == "WARNING" and log.msg=="failed to start tunnel":
			self._plugin_manager.send_plugin_message(self._identifier, dict(error=log.err))
		elif log.lvl == "ERROR" and log.msg=="failed to auth":
			self._plugin_manager.send_plugin_message(self._identifier, dict(error=log.err))
		elif log.lvl == "ERROR" and log.msg=="failed to reconnect session" and "server misbehaving" in log.err:
			self._plugin_manager.send_plugin_message(self._identifier, dict(error="The ngrok tunnel server could not be reached"))


	##~~ Utility handlers
	def _obfuscate(self, x):
		return octoprint.util.to_native_str(base64.b64encode(zlib.compress(octoprint.util.to_bytes(x))))

	def _deobfuscate(self, x):
		return octoprint.util.to_native_str(zlib.decompress(base64.b64decode(octoprint.util.to_bytes(x))))


__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2020 Aldo Hoeben / fieldOfView - Released under terms of the AGPLv3 License"

__plugin_name__ = "Ngrok Tunnel"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = NgrokPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

