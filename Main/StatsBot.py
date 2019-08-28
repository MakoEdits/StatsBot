#!/usr/bin/env python

import irc.bot
import requests
import json
import re


class TwitchBot(irc.bot.SingleServerIRCBot):
	def __init__(self, username, client_id, auth, channel, config):
		SERVER = "irc.chat.twitch.tv"
		PORT = 6667

		self.channel = channel
		self.config = config

		self.client_id = client_id
		self.channel_name = f"#{channel['channel']}"
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
		self.main_string = channel["main_string"]
		self.op_string = channel["op_string"]
		self.season_string = channel["season_string"]

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
		print(f"Stats Bot active in {self.channel_name}")

		connection.cap("REQ", ":twitch.tv/membership")
		connection.cap("REQ", ":twitch.tv/tags")
		connection.cap("REQ", ":twitch.tv/commands")
		connection.join(self.channel_name)


	# Direct message towards relevant method
	def on_pubmsg(self, connection, info):
		msg = info.arguments[0]
		# Check for prefix
		if msg[:self.prefix_len] != self.bot_prefix:
			return
		# Sanitise
		if re.sub("[a-zA-Z0-9-_. ]", "", msg[self.prefix_len:]) != "":
			return
		# Split input into list of words
		splitted = info.arguments[0].split(" ")

		# Assigns currently set functions to keywords
		# Allowing them to be called by passing user input
		function_list = {f"{self.bot_prefix}statsbot": self.help,
						f"{self.bot_prefix}{self.stats_string}": self.stats,
						f"{self.bot_prefix}{self.op_string}": self.op,
						f"{self.bot_prefix}{self.main_string}": self.mains,
						f"{self.bot_prefix}{self.season_string}": self.season}

		command = splitted[0].lower()

		if command in [*function_list]:
			function = function_list.get(command, lambda:None)
			function(connection, splitted)


	# Returns list of commands in chat
	def help(self, connection, splitted):
		# /me command
		out_message = "/me " if self.text_coloured else ""

		out_message += ("Current StatsBot commands are: "
		+ "!stats [p] [t] # "
		+ "!op [o] [p] [t] # "
		+ "!mains [p] [t] # "
		+ "!season [s] [p] [t] # "
		+ "p: platform, t: target player, o: operator, s: season")

		connection.privmsg(self.channel_name, out_message)


	# Test input values and return short results, long results and message format
	def search(self, connection, splitted):
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

		# /me command
		out_message = "/me " if self.text_coloured else ""
		# If player doesnt exist return else return info
		if search_r["total_results"] > 0:
			player_id = search_r["results"][0]["p_id"]
			#ID data request for aditional information on player
			id_url = f"https://r6tab.com/api/player.php?p_id={player_id}"
			id_r = requests.get(id_url).json()
			# Formatting response
			results = search_r["results"][0]

			return [results, id_r, out_message]

		else:
			# User feedback
			out_message += "Player does not exist"
			connection.privmsg(self.channel_name, out_message)

			return None



	# Return K/D and W/L of specified operator
	def op(self, connection, splitted):
		op_arg = self.op_search(splitted[1])

		# If given operator doesn"t exist, return
		if op_arg == None:
			return

		# Remove the operator from the argument to work with search function
		del splitted[1]
		results = self.search(connection, splitted)
		if results == None:
			return

		s_results, l_results, out_message = results[0], results[1], results[2]
		operators = json.load(l_results["operators"])
		win = operators[0][op_arg]
		loss = operators[1][op_arg]

		# Format results
		player_name  = s_results["p_name"]
		player_operator = self.operator_list[str(op_arg)]
		player_op_kd  = round(operators[2][op_arg]/operators[3][op_arg], 2)

		if win == 0 or loss == 0:
			player_op_wl = "N/A"
		else:
			player_op_wl = f"{round(win/(win+loss)*100, 2)}%"

		# Format response
		out_message += (player_name
			+ " | " + player_operator
			+ " | K/D: " + player_op_kd
			+ " | W/L: " + player_op_wl)

		# Send message to target channel
		connection.privmsg(self.channel_name, out_message)


	# Search through list of operators then return relevant key
	def op_search(self, op_arg):
		for key, op in self.operator_list.items():
			if op.lower() == op_arg.lower():
				return key
		return None



	# Returns operators by highest playtime and their K/D
	def mains(self, connection, splitted):
		# Get request
		results = self.search(connection, splitted)
		if results == None:
			return

		s_results, l_results, out_message = results[0], results[1], results[2]

		# Retrieve top attacker and defender
		a_top = l_results["favattacker"]
		d_top = l_results["favdefender"]
		operators = json.load(l_results["operators"])

		# Format results
		player_name = s_results["p_name"]
		player_a = self.operator_list[str(a_top)]
		player_a_kd = round(operators[2][a_top]/operators[3][a_top], 2)
		player_d = self.operator_list[str(d_top)]
		player_d_kd = round(operators[2][d_top]/operators[3][d_top], 2)

		# Format response
		out_message += (player_name
			+ " | Attack main: " + player_a
			+ " K/D: " + player_a_kd
			+ " | Defend main: " + player_d
			+ " K/D: " + player_d_kd)

		# Send message to target channel
		connection.privmsg(self.channel_name, out_message) 



	# Returns players current season rank and overalls stats
	def stats(self, connection, splitted):
		# Get request
		results = self.search(connection, splitted)
		if results == None:
			return

		s_results, l_results, out_message = results[0], results[1], results[2]

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
		out_message += (player_name
			+ " | K/D: " + player_kd
			+ " | W/L: " + player_wl
			+ " | MMR: " + player_current_mmr
			+ " | Rank: " + player_current_rank
			+ " | Level: " + player_level)

		# Send message to target channel
		connection.privmsg(self.channel_name, out_message)


	# Returns players rank and mmr for specified season
	def season(self, connection, splitted):
		season, del_two = self.seasonSearch(splitted[1], splitted[2])
		if season == None:
			return

		# Remove the season from the argument to work with search function
		if del_two:
			del splitted[2]
		del splitted[1]

		results = self.search(connection, splitted)
		if results == None:
			return

		s_results, l_results, out_message = results[0], results[1], results[2]
		# Retrieve MMR and Rank
		if season == len(self.season_list)-1:
			rank_mmr = [s_results["p_currentrank"], s_results["p_currentmmr"]]
		else:
			rank_mmr = l_results["season" + str(season)].split(":")

		# Format results
		player_name = s_results["p_name"]
		season_name = self.season_list[season].title()
		player_s_mmr = rank_mmr[1]
		player_s_rank = self.rank_list[int(rank_mmr[0])]

		# Format response
		out_message += (player_name
			+ f" | {season__name} ( {season} )"
			+ " | MMR: " + player_s_mmr
			+ " | Rank: " + player_s_rank)

		# Send message to target channel
		connection.privmsg(self.channel_name, out_message)


	# Test if the user passed a number or season name then return season number
	def seasonSearch(self, season, seasonPlus):
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