#!/usr/bin/env python

import pymongo
from threading import Thread
import pathlib
import os

import StatsBot


def main():
	print("Accessing database")
	path = os.path.abspath(os.path.join("..", os.pardir))
	with open(path+"\\MongoPath.txt", "r") as mongo_path:
		client = pymongo.MongoClient(mongo_path.read())
	db = client.Main
	config = get_config(db)
	bot_list = get_bots(db)
	channel_list = get_channels(db)

	bot_directory = {}
	for bot in bot_list:
		bot_directory[bot_list[bot]["name"]] = []

	for channel in channel_list:
		bot_directory[channel_list[channel]["bot"]] += [channel]

	print("Launching bots")

	for bot in bot_directory:
		channels = bot_directory[bot]
		for channel in channels:
			current_channel = channel_list[channel]
			current_bot = bot_list[bot]

			new_bot = StatsBot.TwitchBot(
				str(current_bot["name"]),
				str(current_bot["client_id"]),
				str(current_bot["auth"]),
				current_channel,
				config
			)

			new_thread = Thread(target=lambda: new_bot.start())
			new_thread.start()


def get_bots(db):
	bots = db.Bots

	bot_list = {}
	db_list = bots.find()
	bot_count = bots.count_documents({})

	for x in range(bot_count):
		bot_list[db_list[x]["name"]] = db_list[x]

	return bot_list


def get_channels(db):
	channels = db.Channels

	channel_list = {}
	db_list = channels.find({"channel": {"$ne": "default"}})
	channel_count  = channels.count_documents({"channel": {"$ne": "default"}})

	for x in range(channel_count):
		channel_list[db_list[x]["channel"]] = db_list[x]

	return channel_list


def get_config(db):
	config = db.Config

	old_operator_list = config.find({"name": "operator_list"})[0]
	cleanup(old_operator_list)
	operator_list = {}
	for key in old_operator_list:
		operator_list[key.replace("-",":")] = old_operator_list[key]

	season_list = config.find({"name":"season_list"})[0]["seasons"]
	rank_list = config.find({"name": "rank_list"})[0]["ranks"]
	platform_list = config.find({"name": "platform_list"})[0]
	cleanup(platform_list)

	return operator_list, season_list, rank_list, platform_list


def cleanup(input_list):
	cleanup_list = ["_id", "name"]
	for key in cleanup_list:
		del input_list[key]


if __name__ == "__main__":
	main()