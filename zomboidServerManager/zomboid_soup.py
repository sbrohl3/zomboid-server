#!/usr/bin/python3

import datetime as dt
import numpy as np
import pandas as pd
import requests
import logging
from bs4 import BeautifulSoup
import sys

## Created by https://steamcommunity.com/id/Mr_Pink47/
## NOTE Version - 1.5 (10/03/2022)
## © 2022 - Open Source - Free to share and modify

## README: This script is best used with a Linux x64 Zomboid Server
## This script currently opens a Zomboid servertest.ini file to search for steam workshop mod IDs and then uses them to search the steam workshop using Beautiful Soup to retrieve the mod's last updated timestamp
## The workshop IDs and their "last updated" timestamps are appended to a list which are then exported to a CSV file

class zomboid_Soup():
    ''' A class to scrape the steam workshop for Zomboid mod updates to help determine when a server should restart/shutdown '''

    def __init__(self):
        ''' Constructor to declare variables used by the Zomboid Soup Scraping Class'''
        self.modlist_timestamps = []
        self.server_ini = ""
        self.mod_csv =""
        self.URL = "https://steamcommunity.com/sharedfiles/filedetails/?id="
        self.workshop_ids_column = pd.DataFrame()

    def checkAndCompare(self, data_queue):
        ''' A method to check and compare the mod list'''
        logging.info(f"Checking if anything has changed...")
        current_mod_list = pd.read_csv(self.mod_csv)

        ## Fix weird issue with NaN's interpreted as strings in some cases
        self.workshop_ids_column['updated_timestamp'] = self.workshop_ids_column['updated_timestamp'].replace('NaN', np.nan)
        current_mod_list['updated_timestamp'] = current_mod_list['updated_timestamp'].replace('NaN', np.nan)

        ## Enable logging.DEBUG to view DataFrame output
        # logging.debug("From File:")
        # logging.debug(current_mod_list['updated_timestamp'])
        # logging.debug("From Workshop")
        # logging.debug(self.workshop_ids_column['updated_timestamp'])

        compare_cols = current_mod_list['updated_timestamp'].equals(self.workshop_ids_column['updated_timestamp'])
        logging.info(f"Local mods are currently up to date: {compare_cols}")

        ## If mods are in sync between local and workshop, return True, else return False
        if compare_cols:
            print("Exit 0") ## Bash script uses this print statement to interpret status. DO NOT REMOVE!
            data_queue.put(0)
        else:
            print("Exit 1") ## This one too!
            data_queue.put(1)

    def openServerConfig(self):
        ''' A method to open servertest.ini config files and return the workshop mod ID list as a Panadas DataFrame column '''
        ## Open servertest.ini file to check for WorkshopItem IDs
        logging.info(f"\nReading Mods from {self.server_ini}....")
        try:
            with open(f"{self.server_ini}") as config:
                lines = config.readlines()
                for line in lines:
                    if "WorkshopItems=" in line and "#" not in line:
                        mods_list = line.strip().replace("WorkshopItems=","").split(";")
                        break
            ## Create a new data frame enumerated with workshop IDs from servertest.ini
            self.workshop_ids_column = pd.DataFrame({'workshop_id':mods_list})
            return self.workshop_ids_column
        except Exception as error:
            print(f"Error: {error}\n")

    def scrapeSteamWorkshop(self, arg, data_queue):
        ''' A method to check whether Steam workshop mods have been updated or not'''
        try:
            if arg == "--write" or arg == "--check":
                self.openServerConfig()
                ## Iterate over workshop item IDs and begin scraping the Steam Workship for timestamps of when mods were last updated
                logging.info("Scraping Steam Workshop....")
                for id in self.workshop_ids_column["workshop_id"]:
                    mod_url = self.URL+str(id)
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
                            self.modlist_timestamps.append(np.nan)
                        else:
                            modified_timestamp = mod_last_updated_timestamp[0].strip().replace("@","").replace("  ", " ")
                            self.modlist_timestamps.append(modified_timestamp)
                    except:
                        self.modlist_timestamps.append(np.nan)
                
                ## Merge timestamps and mods into one dataframe
                self.workshop_ids_column.insert(1,"updated_timestamp", self.modlist_timestamps, True)
                #print(sys.argv[1])
                if arg.lower() == "--write":
                    self.writeToCSV()
                elif arg.lower() == "--check":
                    self.checkAndCompare(data_queue)
            elif arg.lower() == "-h" or arg.lower() == "--help":
                print("Proper Usage:\n\tpython3 zomboid_soup.py --check\n\tpython3 zomboid_soup.py --write\
                    \n\n\t--write:\n\t\tReads your server.ini file for workshop mod IDs and then creates a CSV file to use as reference while scraping the Steam workshop for mod updates.\
                    \n\t\tIf --check returns False, you can use --write to update your mod list upon a server restart.\
                    \n\t--check:\n\t\tCrawls the Steam workshop to check if mods are updated by comparing them against the CSV file created by --write.\
                    \n\t\tReturns True to stdout if the last updated timestamps crawled from Steam matches the CSV. Returns False if not.\
                    \n\n\t© 2023 - Free to share and distribute\n\t\t Created by:  Pink9\n\t\t Version: 1.0")
                return
            else:
                print("Invalid argument provided. Specify either --write or --check after the script name to get started, or use -h or --help for proper usage of this script.")
                return
        except Exception as e:
            print(e)
            print("No argument provided. Specify either --write or --check after the script name to get started, or use -h or --help for proper usage of this script.")
            return

    def writeToCSV(self):
        ''' Write mod ID and mod last update timestamp to CSV '''
        self.workshop_ids_column.to_csv(self.mod_csv, index=False)
        logging.info("Done.\n")

# Configure the logging system
logging.basicConfig(level = logging.INFO) ## To re-enable logging remove logging.disable() i.e, level = logging.INFO



