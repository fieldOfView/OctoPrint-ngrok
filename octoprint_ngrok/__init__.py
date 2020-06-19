# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin
from octoprint.settings import settings

import flask

from pyngrok import ngrok
from pyngrok.conf import PyngrokConfig
from pyngrok.exception import PyngrokNgrokError

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
		self._ngrok_started = False
		self._restart_ngrok = True

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			token="",
			region="us",
			subdomain="",
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
		except PyngrokNgrokError:
			pass
		self._tunnel_url = ""
		self._plugin_manager.send_plugin_message(self._identifier, dict(tunnel=self._tunnel_url))

	def _ngrok_connect(self):
		if not self._settings.get(["token"]) or not self._settings.get(["auth_name"]) or not self._settings.get(["auth_pass"]):
			self._logger.warning("Ngrok is not fully configured")
			return

		if self._ngrok_started:
			self._ngrok_disconnect()

		pyngrok_config = PyngrokConfig()

		if self._restart_ngrok:
			self._logger.info("Setting ngrok auth token & region...")
			if self._ngrok_started:
				ngrok.kill()  # Make sure no previous token is used

			pyngrok_config.auth_token = self._settings.get(["token"])
			pyngrok_config.region = self._settings.get(["region"])

			self._restart_ngrok = False

		auth_string = "%s:%s" % (
			encode_lib.quote(self._settings.get(["auth_name"])),
			encode_lib.quote(self._settings.get(["auth_pass"]))
		)
		
		self._logger.info("Opening ngrok tunnel...")
		options = dict(
			bind_tls=True,
			auth=auth_string
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

