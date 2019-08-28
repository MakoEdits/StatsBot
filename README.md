## StatsBot
Twitch chat bot which returns Rainbow Six player stats

TODO: setup.py, runtime database updates, channel settings change, error checks

## Installation
Run setup.py to install relevant packages (todo)

Link database (mongodb) to bot launcher using python 3.6 or later connection string

[Database format](https://github.com/MakoEdits/StatsBot/Examples/Database.png)

Or launch single StatsBot.py instance passing relevant args:

[Args format](https://github.com/MakoEdits/StatsBot/Examples/Args.png)


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
