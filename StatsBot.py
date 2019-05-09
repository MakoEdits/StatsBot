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
        print("Connecting to " + server + " on port " + str(port))
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, auth)], username, username)


    def on_welcome(self, c, e):
        print("Stats Bot active in " + str(self.channel))
        c.cap("REQ", ":twitch.tv/membership")
        c.cap("REQ", ":twitch.tv/tags")
        c.cap("REQ", ":twitch.tv/commands")
        c.join(self.channel)


    def on_pubmsg(self, c, e):
        #Sanitize inputs, allows bot prefix
        if re.sub("[a-zA-Z0-9-_. ]", "", e.arguments[0][len(botPrefix):]) != "":
            return
        #Split input into list of words
        splitted = e.arguments[0].split(" ")
        #Assigns currently set functions to keywords
        #Allowing them to be called by passing user input
        functionList = {botPrefix + statsString:  (lambda: self.stats(c, splitted)),
                        botPrefix + opString:     (lambda: self.op(c, splitted)),
                        botPrefix + mainsString:  (lambda: self.mains(c, splitted)),
                        botPrefix + seasonString: (lambda: self.season(c, splitted))}

        if splitted[0].lower() in [*functionList]:
            functionList[splitted[0].lower()]()


    def search(self, c, splitted):
        try:
            platform = splitted[1].lower()
        except IndexError:
            return None
        try:
            targetPlayer = splitted[2].lower()
        except IndexError:
            platform = "pc"
            targetPlayer = splitted[1].lower()
        #Allows for people to use more common names for platforms
        if platform not in ["uplay", "pc", "psn", "ps4", "xbl", "xbox"]:
            return None
        platform = platformList[platform]
        #Xbox name appending
        if platform == "xbl" and len(splitted) > 3:
            targetPlayer = "%20".join(splitted[2:])
        #Initial request for id
        searchUrl = "https://r6tab.com/api/search.php?platform=" + str(platform) + "&search=" + str(targetPlayer)
        searchR = requests.get(searchUrl).json()
        #/me command
        if textColoured:
            outMessage = "/me "
        else:
            outMessage = ""
        #If player doesnt exist return else return info
        if searchR["totalresults"] > 0:
            #ID data request for aditional information on player
            idUrl = "https://r6tab.com/api/player.php?p_id=" + str(searchR["results"][0]["p_id"])
            idR = requests.get(idUrl).json()
            #Formatting response
            results = searchR["results"][0]
            return [results, idR, outMessage]
        else:
            #User feedback
            outMessage += "Player does not exist"
            c.privmsg(self.channel, outMessage)
            return None


    def opSearch(self, opArg):
        #Search through list of operators then return relevant key
        for key, op in operatorList.items():
            if op.lower() == opArg.lower():
                return key
        return None


    #Retusn K/D and W/L of specified operator
    def op(self, c, splitted):
        opArg = self.opSearch(splitted[1])
        #If given operator doesn't exist, return
        if opArg == None:
            return
        #Remove the operator from the argument to work with search function
        del splitted[1]
        results = self.search(c, splitted)
        if results == None:
            return
        sResults, lResults, outMessage = results[0], results[1], results[2]
        operators = json.loads(lResults["operators"])
        win = operators[0][opArg]
        loss = operators[1][opArg]
        #Format results
        player_name     = str(sResults["p_name"])
        player_operator = str(operatorList[str(opArg)])
        player_opKD     = str(round(operators[2][opArg]/operators[3][opArg], 2))
        if win == 0 or loss == 0:
            player_opWL = str("N/A")
        else:
            player_opWL = str(round(win/(win+loss)*100, 2)) + "%"
        #Format response
        outMessage += str(player_name +
            " | " + player_operator +
            " | K/D: " + player_opKD +
            " | W/L: " + player_opWL)
        #Send message to target channel
        c.privmsg(self.channel, outMessage)


    #Returns operators by highest playtime and their K/D
    def mains(self, c, splitted):
        #Get request
        results = self.search(c, splitted)
        if results == None:
            return
        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Retrieve top attacker and defender
        aTop = lResults["favattacker"]
        dTop = lResults["favdefender"]
        operators = json.loads(lResults["operators"])
        #Format results
        player_name = str(sResults["p_name"])
        player_a    = str(operatorList[str(aTop)])
        player_aKD  = str(round(operators[2][aTop]/operators[3][aTop], 2))
        player_d    = str(operatorList[str(dTop)])
        player_dKD  = str(round(operators[2][dTop]/operators[3][dTop], 2))
        #Format response
        outMessage += str(player_name +
            " | Attack main: " + player_a +
            " K/D: " + player_aKD +
            " | Defend main: " + player_d +
            " K/D: " + player_dKD)
        #Send message to target channel
        c.privmsg(self.channel, outMessage) 

    #Returns players seasonal rank and overalls stats
    def stats(self, c, splitted):
        #Get request
        results = self.search(c, splitted)
        if results == None:
            return
        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Win/Loss retrieval
        win = lResults["data"][3]
        loss = lResults["data"][4]
        #Format results
        player_name        = str(sResults["p_name"])
        player_kd          = str(int(sResults["kd"])/100)
        if win == 0 or loss == 0:
            player_wl      = str("N/A")
        else:
            player_wl      = str(round(win/(win+loss)*100, 2)) + "%"
        player_currentmmr  = str(sResults["p_currentmmr"])
        player_currentrank = str(rankList[sResults["p_currentrank"]])
        player_level       = str(sResults["p_level"])
        #Format response
        outMessage += str(player_name + 
            " | K/D: "   + player_kd + 
            " | W/L: "   + player_wl +
            " | MMR: "   + player_currentmmr + 
            " | Rank: "  + player_currentrank +
            " | Level: " + player_level)
        #Send message to target channel
        c.privmsg(self.channel, outMessage)


    #Returns players rank and mmr for specified season
    def season(self, c, splitted):
        season = splitted[1]
        if int(season) in range(1, 13):
            if int(season) <= 6:
                outMessage += "Records before season 6 do no exist"
                c.privmsg(self.channel, outMessage)
                return
        else:
            return
        #Remove the operator from the argument to work with search function
        del splitted[1]
        results = self.search(c, splitted)
        if results == None:
            return
        sResults, lResults, outMessage = results[0], results[1], results[2]
        #Retrieve MMR and Rank
        rank_mmr = lResults["season" + season].split(":")
        #Format results
        player_name   = str(sResults["p_name"])
        player_s_mmr = str(rank_mmr[1])
        player_s_rank  = str(rankList[int(rank_mmr[0])])
        #Format response
        outMessage += str(player_name +
            " | Season " + season +
            " | MMR: " + player_s_mmr +
            " | Rank: " + player_s_rank)
        #Send message to target channel
        c.privmsg(self.channel, outMessage)


#Prefix for the bot, don't use something stupid like only numbers
botPrefix = "!"
#Customisable commands, dont use spaces anywhere, keep lowercase
statsString = "stats"
mainsString = "mains"
opString = "op"
seasonString = "season"
#If bot uses /me or not
textColoured = False

#Fill values
targetChannel = ""
clientID = ""
auth = ""

#Returns rank name based on R6Tab number based format
rankList = ["Unranked", #0
            "Copper IV", "Copper III", "Copper II", "Copper I", #1-4
            "Bronze IV", "Bronze III", "Bronze II", "Bronze I", #5-8
            "Silver IV", "Silver III", "Silver II", "Silver I", #9-12
            "Gold IV", "Gold III", "Gold II", "Gold I", #13-16
            "Platinum III", "Platinum II", "Platinum I", #17-19
            "Diamond"] #20

#Returns corrected platform name
platformList = {"uplay": "uplay", "pc": "uplay", 
                "psn": "psn", "ps4": "psn", 
                "xbl": "xbl", "xbox": "xbl"}

#Dictionary based on R6Tab api formatting
operatorList = {"2:1": "Smoke",     "2:2": "Castle",   "2:3": "Doc",        "2:4": "Glaz", 
                "2:5": "Blitz",     "2:6": "Buck",     "2:7": "Blackbeard", "2:8": "Capitao", 
                "2:9": "Hibana",    "2:A": "Jackal",   "2:B": "Ying",       "2:C": "Ela", 
                "2:D": "Dokkaebi",  "2:F": "Maestro",  "3:1": "Mute",       "3:2": "Ash",
                "3:3": "Rook",      "3:4": "Fuze",     "3:5": "IQ",         "3:6": "Frost", 
                "3:7": "Valkyrie",  "3:8": "Caveira",  "3:9": "Echo",       "3:A": "Mira",
                "3:B": "Lesion",    "3:C": "Zofia",    "3:D": "Vigil",      "3:E": "Lion",
                "3:F": "Alibi",     "4:1": "Sledge",   "4:2": "Pulse",      "4:3": "Twitch",
                "4:4": "Kapkan",    "4:5": "Jager",    "4:E": "Finka",      "5:1": "Thatcher",
                "5:2": "Thermite",  "5:3": "Montagne", "5:4": "Tachanka",   "5:5": "Bandit",
                "2:11": "Nomad",    "3:11": "Kaid",    "3:10": "Clash",     "2:10": "Maverick",
                "2:12": "Gridlock", "3:12": "Mozzie"}

bot = TwitchBot(str(targetChannel), str(clientID), str(auth), str(targetChannel))
bot.start()
