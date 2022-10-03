
import datetime as dt
import pandas as pd
import requests
import logging
from bs4 import BeautifulSoup

## Created by https://steamcommunity.com/id/Mr_Pink47/
## NOTE Version - 0.5 (10/03/2022)
## 	© 2022 - Open Source - Free to share and modify

## README: This script is best used with a Linux x64 Zomboid Server
## This script currently opens a Zomboid servertest.ini file to serch for steam workshop mod IDs and then uses them to search the steam workshop using Beautiful Soup to retrieve the mod's last updated timestamp
## The workshop IDs and their "last updated" timestamps are appended to a list which are then exported to a CSV file

## The idea for later develipment is that this CSV file can be loaded upon a server start and then as the server is running this script can run and scrape again the latest "last update" timestamp for each mod and compaare it to the one in the list
## and then if there are discrepencies in the timestamps the server can be restarted to initiate an update of all mods

# Configure the logging system
logging.basicConfig(level = logging.INFO)
logging.disable()
 
class zomboid_Soup():
    ''' A class to scrape the steam workshop for Zomboid mod updates to help determine when a server should restart/shutdown '''

    def __init__(self):
        ''' Constructor to declare variables used by the Zomboid Soup Scraping Class'''
        self.workshop_ids_column = pd.DataFrame()

    def openServerConfig(self):
        ''' A method to open servertest.ini config files and return the workshop mod ID list as a Panadas DataFrame column '''
        ## Open servertest.ini file to check for WorkshopItem IDs
        with open("servertest.ini") as config:
            lines = config.readlines()
            for line in lines:
                if "Workshop" in line:
                    mods_list = line.strip().replace("WorkshopItems=","").split(";")
                    break
        ## Create a new data frame enumerated with workshop IDs from servertest.ini
        self.workshop_ids_column = pd.DataFrame({'workshop_id':mods_list})
        return self.workshop_ids_column

    def scrapeSteamWorkshop(self):
        ''' A method to check whether Steam workshop mods have been updated or not'''
        self.openServerConfig()
        ## Define the URL workshop IDs can be paired with for lookup
        URL = "https://steamcommunity.com/sharedfiles/filedetails/?id="

        ## Create an empty list for scraped timestamps
        modlist_timestamps = []

        ## Iterate over workshop item IDs and begin scraping the Steam Workship for timestamps of when mods were last updated
        for id in self.workshop_ids_column["workshop_id"]:
            mod_url = URL+str(id)
            #logging.debug(mod_url)
            r = requests.get(mod_url)

            soup = BeautifulSoup(r.content, 'html5lib')

            timestamp_list=[] 

            try:
                table = soup.find('div', attrs = {'class':'detailsStatsContainerRight'}) 

                for i, timestamp in enumerate(table):
                    if timestamp.string.strip() == "":
                        pass
                    elif i == 5:
                        timestamp_list.append(timestamp.string.strip())

                mod_last_updated_timestamp = timestamp_list
                if mod_last_updated_timestamp == []:
                    modlist_timestamps.append("N/A")
                else:
                    modified_timestamp = mod_last_updated_timestamp[0].strip().replace("@","").replace("  ", " ")
                    modlist_timestamps.append(modified_timestamp)
            except:
                modlist_timestamps.append("N/A")

        #logging.info(len(modlist_timestamps))
        #logging.info(workshop_ids_column)

        self.workshop_ids_column.insert(1,"updated_timestamp", modlist_timestamps, True)
        logging.info(self.workshop_ids_column)
        self.workshop_ids_column.to_csv("zomboid_mod_updateList.csv", index=False)

zs = zomboid_Soup()
zs.scrapeSteamWorkshop()