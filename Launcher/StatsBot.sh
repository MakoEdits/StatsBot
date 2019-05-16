#!/bin/bash
users=()
userText=()
for i in "${!users[@]}"; do
	py "StatsBot.py" "${users[$i]}" "${userText[$i]}" &
done