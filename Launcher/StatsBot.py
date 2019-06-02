import os, irc.bot, requests, json, re

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, auth, channel):
        self.client_id = client_id
        self.channel = "#" + channel
        headers = {"Client-ID": client_id, "Accept": "application/vnd.twitchtv.v5+json"}
        url = "https://api.twitch.tv/kraken/users?login=" + channel
        r = requests.get(url, headers=headers).json()
        self.channel_id = r["users"][0]["_id"]
        server = "irc.chat.twitch.tv"
        port = 6667
        print(f"Connecting to {server} on port {port}")
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, auth)], username, username)

    def on_welcome(self, connection, info):
        print("Stats Bot active in " + str(self.channel))
        connection.cap("REQ", ":twitch.tv/membership")
        connection.cap("REQ", ":twitch.tv/tags")
        connection.cap("REQ", ":twitch.tv/commands")
        connection.join(self.channel)

    #Sanitize inputs, allows bot prefix
    def on_pubmsg(self, connection, info):
        msg = info.arguments[0]
        prefixLen = len(botPrefix)
        #Check for prefix
        if msg[:prefixLen] != botPrefix:
            return
        #Sanitise
        if re.sub("[a-zA-Z0-9-_. ]", "", msg[prefixLen:]) != "":
            return
        #Split input into list of words
        splitted = info.arguments[0].split(" ")
        #Assigns currently set functions to keywords
        #Allowing them to be called by passing user input
        functionList = {f"{botPrefix} statsbot":       self.help,
                        f"{botPrefix} {statsString}":  self.stats,
                        f"{botPrefix} {opString}":     self.op,
                        f"{botPrefix} {mainsString}":  self.mains,
                        f"{botPrefix} {seasonString}": self.season}

        command = splitted[0].lower()
        if command in [*functionList]:
            function = functionList.get(command, lambda:None)
            function(connection, splitted)


    #Returns list of commands in chat
    def help(self, connection, splitted):
        #/me command
        outMessage = "/me" if textColoured else ""
        outMessage += ("Current StatsBot commands are: " + 
        "!stats [p] [t] # " +
        "!op [o] [p] [t] # " +
        "!mains [p] [t] # " + 
        "!season [s] [p] [t] # " +
        "p: platform, t: target player, o: operator, s: season")
        connection.privmsg(self.channel, outMessage)



    #Test input values and return short results, long results and message format
    def search(self, connection, splitted):
        try:
            platform = splitted[1].lower()
        except IndexError:
            return None
        try:
            targetPlayer = splitted[2].lower()
        except IndexError:
            platform = "pc"
            targetPlayer = splitted[1].lower()

        #Allow users to use more common names for platforms
        if platform not in ["uplay", "pc", "psn", "ps4", "xbl", "xbox"]:
            return None
        with open("Lists/platformList.json", "r") as file:
            platformList = json.loads(file)
        platform = platformList[platform]
        #Allow xbox usernames with spaces
        if platform == "xbl" and len(splitted) > 3:
            targetPlayer = "%20".join(splitted[2:])

        #Initial request to obtain p_id which is necesary for aditional data requests
        searchUrl = f"https://r6tab.com/api/search.php?platform={platform}&search={targetPlayer}"
        searchR = requests.get(searchUrl).json()

        #/me command
        outMessage = "/me" if textColoured else ""
        #If player doesnt exist return else return info
        if searchR["totalresults"] > 0:
            player_id = searchR["results"][0]["p_id"]
            #ID data request for aditional information on player
            idUrl = f"https://r6tab.com/api/player.php?p_id={player_id}"
            idR = requests.get(idUrl).json()
            #Formatting response
            results = searchR["results"][0]
            return [results, idR, outMessage]
        else:
            #User feedback
            outMessage += "Player does not exist"
            connection.privmsg(self.channel, outMessage)
            return None



    #Return K/D and W/L of specified operator
    def op(self, connection, splitted):
        with open("Lists/operatorList.json", "r") as file:
            operatorList = json.loads(file)
        opArg = self.opSearch(splitted[1])
        #If given operator doesn"t exist, return
        if opArg == None:
            return
        #Remove the operator from the argument to work with search function
        del splitted[1]
        results = self.search(connection, splitted)
        if results == None:
            return

        sResults, lResults, outMessage = results[0], results[1], results[2]
        operators = json.loads(lResults["operators"])
        win = operators[0][opArg]
        loss = operators[1][opArg]

        #Format results
        player_name     = sResults["p_name"]
        player_operator = operatorList[str(opArg)]
        player_opKD     = round(operators[2][opArg]/operators[3][opArg], 2)
        player_opWL     = "N/A" if (win == 0 or loss == 0) else f"{round(win/(win+loss)*100, 2)}%"
        #Format response
        outMessage += f"{player_name} | {player_operator} | K/D: {player_opKD} | W/L: {player_opWL}"
        #Send message to target channel
        connection.privmsg(self.channel, outMessage)


    #Search through list of operators then return relevant key
    def opSearch(self, opArg):
        for key, op in operatorList.items():
            if op.lower() == opArg.lower():
                return key
        return None



    #Returns operators by highest playtime and their K/D
    def mains(self, connection, splitted):
        #Get request
        results = self.search(connection, splitted)
        if results == None:
            return
        with open("Lists/operatorList.json", "r") as file:
            operatorList = json.loads(file)

        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Retrieve top attacker and defender
        aTop = lResults["favattacker"]
        dTop = lResults["favdefender"]
        operators = json.loads(lResults["operators"])

        #Format results
        player_name = sResults["p_name"]
        player_a    = operatorList[str(aTop)]
        player_aKD  = round(operators[2][aTop]/operators[3][aTop], 2)
        player_d    = operatorList[str(dTop)]
        player_dKD  = round(operators[2][dTop]/operators[3][dTop], 2)
        #Format response
        outMessage += f"{player_name} | Attack main: {player_a} K/D: {player_aKD} | Defend main: {player_d} K/D: {player_dKD}"
        #Send message to target channel
        connection.privmsg(self.channel, outMessage) 



    #Returns players current season rank and overalls stats
    def stats(self, connection, splitted):
        #Get request
        results = self.search(connection, splitted)
        if results == None:
            return
        with open("Lists/rankList.json", "r") as file:
            rankList = json.loads(file)

        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Win/Loss retrieval
        win = lResults["data"][3]
        loss = lResults["data"][4]

        #Format results
        player_name        = sResults["p_name"]
        player_kd          = int(sResults["kd"])/100
        player_wl          = "N/A" if (win == 0 or loss == 0) else f"{round(win/(win+loss)*100, 2)}%"
        player_currentmmr  = sResults["p_currentmmr"]
        player_currentrank = rankList[sResults["p_currentrank"]]
        player_level       = sResults["p_level"]
        #Format response
        outMessage += f"{player_name} | K/D: {player_kd} | W/L: {player_wl} | MMR: {player_currentmmr} | Rank: {player_currentrank} | Level: {player_level}"
        #Send message to target channel
        connection.privmsg(self.channel, outMessage)



    #Returns players rank and mmr for specified season
    def season(self, connection, splitted):
        with open("Lists/seasonList.json", "r") as file:
            seasonList = json.loads(file)
        season, delTwo = self.seasonSearch(splitted[1], splitted[2], seasonList)
        if season == None:
            return
        #Remove the season from the argument to work with search function
        if delTwo:
            del splitted[2]
        del splitted[1]
        results = self.search(connection, splitted)
        if results == None:
            return
        with open("Lists/rankList.json", "r") as file:
            rankList = json.loads(file)

        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Retrieve MMR and Rank
        if season == len(seasonList)-1:
            rank_mmr = [sResults["p_currentrank"], sResults["p_currentmmr"]]
        else:
            rank_mmr = lResults["season" + str(season)].split(":")

        #Format results
        player_name    = sResults["p_name"]
        seasonName     = seasonList[season].title()
        player_s_mmr   = rank_mmr[1]
        player_s_rank  = rankList[int(rank_mmr[0])]
        #Format response
        outMessage += f"{player_name} | {seasonName} ( {season} ) | MMR: {player_s_mmr} | Rank: {player_s_rank}"
        #Send message to target channel
        connection.privmsg(self.channel, outMessage)


    #Test if the user passed a number or season name then return season number
    def seasonSearch(self, season, seasonPlus, seasonList):
        try:
            season = int(season)
            if season in range(6, len(seasonList)):
                return season, False
            else:
                return None, None
        except ValueError:
            #Accounts for season names that are multiple words
            if season.lower() in seasonList:
                return seasonList.index(str(season)), False
            elif (season.lower() + " " + seasonPlus.lower()) in seasonList:
                return seasonList.index(str(season + " " + seasonPlus)), True
            else:
                return None, None


#Prefix for the bot, don't use something stupid like only numbers
botPrefix = "!"
#Customisable commands, dont use spaces anywhere, keep lowercase
statsString = "stats"
mainsString = "mains"
opString = "op"
seasonString = "season"
#If bot uses /me or not
if sys.argv[2] == "True":
    textColoured = True
else:
    textColoured = False

#Fill values
targetChannel = sys.argv[1]
clientID = ""
auth = ""

try:
    bot = TwitchBot(str(targetChannel), str(clientID), str(auth), str(targetChannel))
    bot.start()
except Exception as e:
    print(str(e) + str(targetChannel))
    file = open("errorLogs.txt", "a")
    file.write(str(e) + str(targetChannel) + "\n")
    file.close()
