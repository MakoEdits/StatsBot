#!/usr/bin/env python

# Main bot module

import irc.bot
import requests
import json
import re

import Fetcher


class TwitchBot(irc.bot.SingleServerIRCBot):
	def __init__(self, username, client_id, auth, channel, config):
		SERVER = "irc.chat.twitch.tv"
		PORT = 6667

		self.channel = channel
		self.config = config
		self.client_id = client_id
		self.channel_name = f"{channel['channel']}"
		# String which the user enters to call function
		self.operator_list = config[0]
		self.season_list = config[1]
		self.rank_list = config[2]
		self.platform_list = config[3]
		# Settings unique to channel
		self.bot_prefix = self.channel["bot_prefix"]
		self.prefix_len = len(self.bot_prefix)
		self.text_coloured = channel["text_coloured"]
		self.stats_string = channel["stats_string"]
		self.mains_string = channel["mains_string"]
		self.op_string = channel["op_string"]
		self.season_string = channel["season_string"]
		self.clearance = channel["clearance"]

		headers = {
			"Client-ID": client_id,
			"Accept": "application/vnd.twitchtv.v5+json"
		}
		# Connect and generate bot
		url = f"https://api.twitch.tv/kraken/users?login={username}"
		r = requests.get(url, headers=headers).json()
		self.channel_name_id = r["users"][0]["_id"]

		irc.bot.SingleServerIRCBot.__init__(
			self, [(SERVER, PORT, auth)],
			username, username
		)


	def on_welcome(self, connection, info):
		print(f"Stats Bot active in #{self.channel_name}")

		connection.cap("REQ", ":twitch.tv/membership")
		connection.cap("REQ", ":twitch.tv/tags")
		connection.cap("REQ", ":twitch.tv/commands")
		connection.join(f"#{self.channel_name}")
		self.connection = connection


	# Direct message towards relevant method
	def on_pubmsg(self, connection, info):
		msg = info.arguments[0]
		# Check for prefix
		if msg[:self.prefix_len] != self.bot_prefix:
			return
		# Sanitise
		if re.sub("[a-zA-Z0-9-_.!?# ]", "", msg[self.prefix_len:]) != "":
			return
		# Split input into list of words
		splitted = info.arguments[0].split(" ")
		self.caller = info.source.nick
		# Assigns currently set functions to keywords
		# Allowing them to be called by passing user input
		function_list = {
			f"{self.bot_prefix}statsbot": self.help,
			f"{self.bot_prefix}{self.stats_string}": self.stats,
			f"{self.bot_prefix}{self.op_string}": self.op,
			f"{self.bot_prefix}{self.mains_string}": self.mains,
			f"{self.bot_prefix}{self.season_string}": self.season,
			f"{self.bot_prefix}statsbot_update": self.update,
			f"{self.bot_prefix}statsbot_reset": self.reset,
			f"{self.bot_prefix}statsbot_resync": self.resync,
			f"{self.bot_prefix}statsbot_clearance": self.change_clearance
		}

		command = splitted[0].lower()

		if command in function_list.keys():
			function = function_list.get(command, lambda: None)
			function(splitted)


	# Returns list of commands in chat
	def help(self, splitted):
		out_message = (
			"For info on current commands and documentation, "
			+ "visit github/makoedits/statsbot"
		)
		
		# Send message to target channel
		self.send_message(out_message)


	# Test input values and return short results, long results and message format
	def search(self, splitted):
		try:
			platform = splitted[1].lower()
		except IndexError:
			return None

		try:
			target_player = splitted[2].lower()
		except IndexError:
			platform = "pc"
			target_player = splitted[1].lower()

		# Allow users to use more common names for platforms
		if platform not in ["uplay", "pc", "psn", "ps4", "xbl", "xbox"]:
			return None

		platform = self.platform_list[platform]

		# Allow xbox usernames with spaces
		if platform == "xbl" and len(splitted) > 3:
			target_player = "%20".join(splitted[2:])

		# Initial request to obtain p_id which is necesary for aditional data requests
		search_url = ("https://r6tab.com/api/search.php?platform="
			+ f"{platform}&search={target_player}")

		search_r = requests.get(search_url).json()

		# If player doesnt exist return else return info
		if search_r["totalresults"] > 0:
			player_id = search_r["results"][0]["p_id"]
			#ID data request for aditional information on player
			id_url = f"https://r6tab.com/api/player.php?p_id={player_id}"
			id_r = requests.get(id_url).json()
			# Formatting response
			results = search_r["results"][0]

			return [results, id_r]

		else:
			# User feedback
			out_message = "Player does not exist"
			self.send_message(out_message)

			return None


	# Return K/D and W/L of specified operator
	def op(self, splitted):
		op_arg = self.op_search(splitted[1])

		# If given operator doesn't exist, return
		if op_arg == None:
			return

		# Remove the operator from the argument to work with search function
		del splitted[1]
		results = self.search(splitted)
		if results == None:
			return

		s_results, l_results = results[0], results[1]
		operators = json.loads(l_results["operators"])
		win = operators[0][op_arg]
		loss = operators[1][op_arg]

		# Format results
		player_name  = s_results["p_name"]
		player_operator = self.operator_list[f"{op_arg}"]
		player_op_kd  = round(
			operators[2][f"{op_arg}"]/operators[3][f"{op_arg}"], 2
		)

		if win == 0 or loss == 0:
			player_op_wl = "N/A"
		else:
			player_op_wl = f"{round(win/(win+loss)*100, 2)}%"

		# Format response
		out_message = (
			f"{player_name}"
			+ f" | {player_operator}"
			+ f" | K/D: {player_op_kd}"
			+ f" | W/L: {player_op_wl}"
		)

		# Send message to target channel
		self.send_message(out_message)


	# Search through list of operators then return relevant key
	def op_search(self, op_arg):
		for key, op in self.operator_list.items():
			if op.lower() == op_arg.lower():
				return key
		return None


	# Returns operators by highest playtime and their K/D
	def mains(self, splitted):
		# Get request
		results = self.search(splitted)
		if results == None:
			return

		s_results, l_results = results[0], results[1]

		# Retrieve top attacker and defender
		a_top = l_results["favattacker"]
		d_top = l_results["favdefender"]
		operators = json.loads(l_results["operators"])

		# Format results
		player_name = s_results["p_name"]
		player_a = self.operator_list[f"{a_top}"]
		player_a_kd = round(
			operators[2][f"{a_top}"]/operators[3][f"{a_top}"], 2
		)
		player_d = self.operator_list[f"{d_top}"]
		player_d_kd = round(
			operators[2][f"{d_top}"]/operators[3][f"{d_top}"], 2
		)

		# Format response
		out_message = (
			f"{player_name}"
			+ f" | Attack main: {player_a}"
			+ f" K/D: {player_a_kd}"
			+ f" | Defend main: {player_d}"
			+ f" K/D: {player_d_kd}"
		)

		# Send message to target channel
		self.send_message(out_message)



	# Returns players current season rank and overalls stats
	def stats(self, splitted):
		# Get request
		results = self.search(splitted)
		if results == None:
			return

		s_results, l_results = results[0], results[1]

		# Win/Loss retrieval
		win = l_results["data"][3]
		loss = l_results["data"][4]
		# Format results
		player_name = s_results["p_name"]
		player_kd = int(s_results["kd"])/100

		if win == 0 or loss == 0:
			player_wl = "N/A"
		else:
			player_wl = f"{round(win/(win+loss)*100, 2)}%"

		player_current_mmr = s_results["p_currentmmr"]
		player_current_rank = self.rank_list[s_results["p_currentrank"]]
		player_level = s_results["p_level"]

		# Format response
		out_message = (
			f"{player_name}"
			+ f" | K/D: {player_kd}"
			+ f" | W/L: {player_wl}"
			+ f" | MMR: {player_current_mmr}"
			+ f" | Rank: {player_current_rank}"
			+ f" | Level: {player_level}"
		)

		# Send message to target channel
		self.send_message(out_message)


	# Returns players rank and mmr for specified season
	def season(self, splitted):
		if len(splitted) < 3:
			return

		season, del_two = self.season_search(splitted[1], splitted[2])
		if season == None:
			return

		# Remove the season from the argument to work with search function
		if del_two:
			del splitted[2]
		del splitted[1]

		results = self.search(splitted)
		if results == None:
			return

		s_results, l_results = results[0], results[1]

		# Retrieve MMR and Rank
		if season == len(self.season_list)-1:
			rank_mmr = [s_results["p_currentrank"], s_results["p_currentmmr"]]
		else:
			rank_mmr = l_results[f"season{season}"].split(":")

		# Format results
		player_name = s_results["p_name"]
		season_name = self.season_list[season].title()
		player_s_mmr = rank_mmr[1]
		player_s_rank = self.rank_list[int(rank_mmr[0])]

		# Format response
		out_message = (
			f"{player_name}"
			+ f" | {season_name} ( {season} )"
			+ f" | MMR: {player_s_mmr}"
			+ f" | Rank: {player_s_rank}"
		)

		# Send message to target channel
		self.send_message(out_message)


	# Test if the user passed a number or season name then return season number
	def season_search(self, season, seasonPlus):
		try:
			season = int(season)
			if season in range(6, len(self.season_list)):
				return season, False
			else:
				return None, None
		except ValueError:
			# Accounts for season names that are multiple words
			s_name_1 = season.lower()
			s_name_2 = seasonPlus.lower()
			if s_name_1 in self.season_list:
				return self.season_list.index(f"{s_name_1}"), False
			elif f"{s_name_1} {s_name_2}" in self.season_list:
				return self.season_list.index(f"{s_name_1} {s_name_2}"), True
			else:
				return None, None


	# Updates database
	def update(self, splitted):
		splitted = [x.lower() for x in splitted]
		if not self.check_clearance():
			return

		updatables = [
			"text_coloured", "stats_string", "mains_string", 
			"op_string", "season_string"
		]

		update_type = splitted[1]
		update = splitted[2]

		if update_type in updatables and len(splitted) == 3:
			if update_type == "text_coloured":
				if update not in ["true", "false"]:
					return
				update = True if update == "true" else False

			Fetcher.update(
				self.channel_name, update_type, update
			)

			self.update_settings(update_type, update)

			out_message = f"Updated {update_type} to {update}"

			# Send message to target channel
			self.send_message(out_message)


	# Updates setting
	def update_settings(self, update_type, update):
		if update_type == "text_coloured":
			self.text_coloured = update
		elif update_type == "stats_string":
			self.stats_string = update
		elif update_type == "mains_string":
			self.mains_string = update
		elif update_type == "op_string":
			self.op_string = update
		elif update_type == "season_string":
			self.season_string = update
		else:
			print("Received bad update")


	# Alter clearance
	def change_clearance(self, splitted):
		# Only channel owner can change clearance
		if not self.caller == self.channel_name:
			return

		splitted = [x.lower() for x in splitted]

		operation = splitted[1]
		if operation not in ["add", "remove"]:
			return

		update = splitted[2]
		if update == self.channel_name:
			return

		# Alter database with update and return new version of clearance
		self.clearance = Fetcher.clearance(
			self.channel_name, operation, update
		)

		out_message = "Updated clearance"

		# Send message to target channel
		self.send_message(out_message)


	# Directs to re_action with type reset
	def reset(self, splitted):
		self.re_action(splitted, "reset")


	# Directs to re_action with type resync
	def resync(self, splitted):
		self.re_action(splitted, "resync")


	# Sets the object variables based on returned values
	def re_action(self, splitted, re_type):
		if not self.check_clearance():
			return

		if re_type == "resync":
			settings = Fetcher.fetch(self.channel_name, "channel")
			self.clearance = [settings["clearance"]]
			out_message = f"Synced settings with database"

		elif re_type == "reset":
			settings = Fetcher.fetch(self.channel_name, "default")
			self.clearance = [self.channel_name]
			out_message = f"Reset settings to default"

		self.bot_prefix = settings["bot_prefix"]
		self.stats_string = settings["stats_string"]
		self.mains_string = settings["mains_string"]
		self.op_string = settings["op_string"]
		self.season_string = settings["season_string"]
		self.text_coloured = settings["text_coloured"]
		
		# Send message to target channel
		self.send_message(out_message)


	# Checks if user calling important commands have access
	def check_clearance(self):
		if self.caller not in self.clearance:
			if "moderators" in self.clearance:
				url = f"https://tmi.twitch.tv/group/user/{self.channel_name}/chatters"
				mod_list = requests.get(url).json()["chatters"]["moderators"]

				if self.caller not in mod_list:
					return False
			else:
				return False
		return True


	# Sends twitch message to channel
	def send_message(self, message):
		out_message = "/me " if self.text_coloured else ""
		out_message += f"{message}"
		self.connection.privmsg(f"#{self.channel_name}", out_message)