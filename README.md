## StatsBot
Twitch chat bot which returns Rainbow Six player stats

If you would like me to host the bot under my own bot contact me @ Twitter.com/Mako_Edits

<hr>

## Requires

Python 3.6 not 3.7 or 2.x  https://www.python.org/downloads/release/python-367/

Python packages: IRC and Requests

<i> In CMD type "py -m pip install irc" or "python -m pip install irc" same for requests </i>

<hr>

In the file:

**Fill targetChannel with your channel name**

**Fill clientID with the client ID you retrieve by registering a new application at https://dev.twitch.tv/console**

<i>(copy settings shown if you are unfamiliar)</i>

**Fill auth with auth string you get from https://twitchapps.com/tmi/ (include "oauth:" in string)**

![ClientID](https://i.imgur.com/k368tq7.png)

<hr>

Launch the bot either through IDLE, Python's IDE by opening the StatsBot.py and pressing F5

Or double click on StatsBot.py

**Or use Launcher shell script. Specify list of target channels aswell as if they want coloured text (True, False) then launch script

<hr>

## Usage
Current commands:

!stats [platform] [target player]

!mains [platform] [target player]

!op [target operator] [platform] [target player]

!season [season number or season name] [platform] [target player] (only works for season 6 and more)

!statsbot

![Example](https://i.imgur.com/cIHZay1.png)

Friendly to alternate platform names such as pc, ps4, xbox

Now defaults to pc if no platform given

Command string and prefix is customisable by editing the relevant strings

<hr>

Uses R6Tab's API

https://r6tab.com

https://twitter.com/tabwire

https://github.com/Tabwire/R6Tab-API

## Affiliation
The R6Tab API and the usage of this bot is in no way shape or form affiliated with Ubisoft and its partners. Any "Rainbow Six: Siege" name, logos and/or images are registered trademarks of Ubisoft.
