# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.settings import settings

import flask

from pyngrok import ngrok
from pyngrok.conf import PyngrokConfig

try:
	import urllib.parse as encode_lib # Python 3
except ImportError:
	import urllib as encode_lib # Python 2

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
		self._restart_ngrok = True

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			token="",
			region="us",
			auth_name="",
			auth_pass=""
		)

	def get_settings_restricted_paths(self):
		return dict(
			admin=[
				['token'], ['auth_name'], ['auth_pass']
			]
		)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		if "token" in data or "region" in data:
			self._restart_ngrok = True

		self._ngrok_connect()


	##~~ StartupPlugin mixin

	def on_startup(self, host, port):
		self._port = port

		# prefer port from discovery plugin if available, in case of a reverse proxy
		public_port = settings().get(["plugins", "discovery", "publicPort"])
		if public_port:
			self._port = public_port

	def on_after_startup(self):
		self._ngrok_connect()

	##~~ ShutdownPlugin mixin

	def on_shutdown(self):
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
			custom_bindings=False,
			template='ngrok_settings.jinja2'
		)]


	##~~ SimpleApiPlugin mixin

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
		except pyngrok.exception.PyngrokNgrokError:
			pass
		self._tunnel_url = ""
		self._plugin_manager.send_plugin_message(self._identifier, dict(tunnel=self._tunnel_url))

	def _ngrok_connect(self):
		if not self._settings.get(["token"]) or not self._settings.get(["auth_name"]) or not self._settings.get(["auth_pass"]):
			self._logger.warning("Ngrok is not fully configured")
			return

		self._ngrok_disconnect()

		pyngrok_config = PyngrokConfig()

		if self._restart_ngrok:
			self._logger.info("Setting ngrok auth token & region...")
			ngrok.kill()  # Make sure no previous token is used

			pyngrok_config.auth_token = self._settings.get(["token"])
			pyngrok_config.region = self._settings.get(["region"])

			self._restart_ngrok = False

		auth_string = "%s:%s" % (
			encode_lib.quote(self._settings.get(["auth_name"])),
			encode_lib.quote(self._settings.get(["auth_pass"]))
		)
		
		self._logger.info("Opening ngrok tunnel...")
		options = {"bind_tls":True, "auth":auth_string}

		try:
			tunnel_url = ngrok.connect(port=self._port, options=options, pyngrok_config=pyngrok_config)
		except pyngrok.exception.PyngrokNgrokError:
			self._logger.error("Could not connect with the provided API key")
			return

		if tunnel_url:
			self._tunnel_url = tunnel_url.partition("://")[2]
			self._logger.info("ngrok tunnel: %s" % self._tunnel_url)
			self._plugin_manager.send_plugin_message(self._identifier, dict(tunnel=self._tunnel_url))


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Ngrok Tunnel"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = NgrokPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

