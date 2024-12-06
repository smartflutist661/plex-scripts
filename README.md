# plex-scripts

Requirements are defined in `requirements.txt`. Requires Python 3.10 or higher.

All scripts with a CLI accept `--help/-h` to display possible arguments.

Most scripts in this repository require a Plex auth token;
see Plex's [help page](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) to acquire one.
They accept either `--local`, if running on the Plex host, or `--host`, if running remotely.
This may be a local IP, remote IP, or hostname.

Some also require a Tautulli API key, which can be found on Tautulli's settings page.
