#!/usr/bin/env python

import pymongo
import pathlib
import os


# Updates given string
def update(channel, update_type, update):
	col = get_collection()
	current_channel = col.find({"channel": channel})[0]

	new_values = {"$set": {update_type: update}}

	col.update_one({"channel": channel}, new_values)


# Alters clearance
def clearance(channel, operation, update):
	col = get_collection()
	current_channel = col.find({"channel": channel})[0]

	clearance = current_channel["clearance"]

	if operation == "add":
		combined = list(set(clearance + [update]))
	elif operation == "remove":
		del clearance[clearance.index(update)]
		combined = clearance

	new_values = {"$set": {"clearance": combined}}

	col.update_one({"channel": channel}, new_values)

	return combined


# Returns values based off of database
def fetch(channel, fetch_type):
	col = get_collection()
	if fetch_type == "default":
		target_channel = "default"
	elif fetch_type == "channel":
		target_channel = channel
	else:
		return

	current_channel = col.find({"channel": target_channel})[0]

	if target_channel == "default":
		default_update(channel, col, current_channel)

	return current_channel


# Updates all values to default
def default_update(channel, col, current_channel):
	update_channel = col.find({"channel": channel})[0]

	update_list = [
		"stats_string", "mains_string",
		"op_string", "season_string", "text_coloured"
	]

	for setting in update_list:
		new_values = {"$set": {setting: current_channel[setting]}}
		col.update_one({"channel": channel}, new_values)

	new_values = {"$set": {"clearance": [channel]}}
	col.update_one({"channel": channel}, new_values)


# Creates client instance from mongodb key stored in txt 2 directories above
def get_collection():
	path = os.path.abspath(os.path.join("..", os.pardir))
	with open(path+"\\MongoPath.txt", "r") as mongo_path:
		client = pymongo.MongoClient(mongo_path.read())

	return client.Main.Channels