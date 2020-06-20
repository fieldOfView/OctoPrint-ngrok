# OctoPrint Ngrok Tunnel

This plugin creates a secure tunnel to access OctoPrint remotely. It provides a more secure alternative to using port forwarding to expose your OctoPrint instance to the internet, while giving full and secure access to the OctoPrint web interface and the OctoPrint API. The plugin uses secure tunnels provided by [ngrok](https://ngrok.com). These tunnels are encrypted via SSL and Basic Authentication to prevent snooping.

Each time OctoPrint is (re-)started, the tunnel is created at a new, randomly created subdomain of ngrok.io. If you sign up for a paid account at ngrok.com, you can configure the tunnel to use a fixed subdomain.

You can always find the address of the currently active ngrok tunnel by logging in to the [ngrok dashboard](https://dashboard.ngrok.com/status/tunnels).

## Setup

Install the plugin via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/fieldOfView/OctoPrint-ngrok/archive/master.zip

Sign up for a free or paid [ngrok account](https://dashboard.ngrok.com/signup).


## Configuration

The Ngrok Tunnel plugin can be configured via the OctoPrint settings panel.

The ngrok **auth token** is used to authenticate you on the ngrok service and can be found by logging in to the [ngrok dashboard](https://dashboard.ngrok.com/auth/your-authtoken).

The plugin recommends you to set up Basic Authentication on the tunnel in addition to the access control already set up on your OctoPrint instance. Any username and password combination can be chosen, but it is recommended to use a different username and password than your OctoPrint credentials, in order not to create a single point of failure.

