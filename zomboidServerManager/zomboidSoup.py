#!/usr/bin/python3

import sys
import logging
import requests
import numpy as np
import pandas as pd
import queue
import datetime as dt
from bs4 import BeautifulSoup

## Created by https://steamcommunity.com/id/Mr_Pink47/
## NOTE Version - 1.8 (12/20/2023)
## © 2024 - Open Source - Free to share and modify

## README: This script is best used with a Linux x64 Zomboid Server
## This script currently opens a Zomboid servertest.ini file to search for steam workshop mod IDs and then uses them to search the steam workshop using Beautiful Soup to retrieve the mod's last updated timestamp
## The workshop IDs and their "last updated" timestamps are appended to a list which are then exported to a CSV file

## If you run into issues running this program, be sure to intstall html5lib
## python3 -m pip install html5lib

class zomboidSoup():
    ''' A class to scrape the steam workshop for Zomboid mod updates to help determine when a server should restart/shutdown '''

    def __init__(self, server_ini, mod_csv) -> None:
        ''' Constructor to declare variables used by the Zomboid Soup Scraping Class'''
        self.modlist_timestamps     = []
        self.server_ini             = server_ini
        self.mod_csv                = mod_csv
        self.workshop_URL           = "https://steamcommunity.com/sharedfiles/filedetails/?id="
        self.workshop_ids_column    = pd.DataFrame()

    def checkAndCompare(self, data_queue) -> queue.Queue:
        ''' A method to check and compare the mod list'''
        logging.info("Checking if anything has changed...")
        try:
            current_mod_list = pd.read_csv(self.mod_csv)
        except Exception as e:
            logging.info(f"ERROR - Could not read mod_csv\n{e}")

        ## Fix weird issue with NaN's interpreted as strings in some cases
        try:
            self.workshop_ids_column['updated_timestamp']   = self.workshop_ids_column['updated_timestamp'].replace('NaN', np.nan)
            current_mod_list['updated_timestamp']           = current_mod_list['updated_timestamp'].replace('NaN', np.nan)
        except Exception as e:
            print(f"ERROR - Could not convert timestamps\n{e}")

        ## Enable logging.DEBUG to view DataFrame output
        # logging.debug("From File:")
        # logging.debug(current_mod_list['updated_timestamp'])
        # logging.debug("From Workshop")
        # logging.debug(self.workshop_ids_column['updated_timestamp'])

        try:
            compare_cols = current_mod_list['updated_timestamp'].equals(self.workshop_ids_column['updated_timestamp'])
            logging.info(f"Local mods are currently up to date: {compare_cols}")
        except Exception as e:
            logging.info(f"ERROR - Could not compare current mod_list to updated_timestamp dataframe\n{e}")

        ## If mods are in sync between local and workshop, return True, else return False
        if compare_cols:
            return data_queue.put(0)
            
        else:
            return data_queue.put(1)

    def openServerConfig(self) -> pd.DataFrame():
        ''' A method to open servertest.ini config files and return the workshop mod ID list as a Panadas DataFrame column '''
        ## Open servertest.ini file to check for WorkshopItem IDs
        logging.info(f"Reading Mods from {self.server_ini}....")
        try:
            with open(f"{self.server_ini}") as config:
                lines           = config.readlines()
                search_string   = "WorkshopItems="
                found_line      = next((line for line in lines if search_string in line and "#" not in line), None)                
                mods_list       = found_line.strip().replace("WorkshopItems=","").split(";")

            ## Create a new dataframe enumerated with workshop IDs from servertest.ini
            self.workshop_ids_column = pd.DataFrame({'workshop_id': mods_list})
            logging.info("Mods list loaded successfully.")
            return self.workshop_ids_column
        except Exception as error:
            logging.info(f"ERROR - Failed loading server config: {error}\n")

    def scrapeSteamWorkshop(self, arg, data_queue) -> None:
        ''' A method to check whether Steam workshop mods have been updated or not'''
        try:
            if arg.lower() in ["--write", "--check"]:
                if self.openServerConfig().empty:
                    logging.info("ERROR - Could not load mods from server configuration ini")
                    exit(1)

                ## Iterate over workshop item IDs and begin scraping the Steam Workship for timestamps of when mods were last updated
                logging.info("Scraping Steam Workshop....")

                ## Append Steam Workshop search URL to each modID in a new column
                self.workshop_ids_column["mod_urls"] = self.workshop_URL + self.workshop_ids_column["workshop_id"]
                
                for mod_url in self.workshop_ids_column["mod_urls"]:
                    raw_webpage         = requests.get(mod_url, timeout=5)
                    converted_webpage   = BeautifulSoup(raw_webpage.content, 'html5lib')

                    try:
                        ## Find the mod's latest update timestamp and isolate it from the rest of the HTML5 encoding, then append it the list of timestamps
                        mod_update_results  = converted_webpage.find('div', attrs = {'class':'detailsStatsContainerRight'})
                        isolated_timestamp  = mod_update_results.get_text().replace('\t', '').strip().split('\n')[2]
                        modified_timestamp  = isolated_timestamp.strip().replace("@","").replace("  ", " ")
                        self.modlist_timestamps.append(modified_timestamp)
                            
                    except Exception as error:
                        ## If the website results include no "last updated" timestamp or no longer exists then append NaN
                        self.modlist_timestamps.append(np.nan)

                ## Merge updated timestamps and workshopIDs into one dataframe
                self.workshop_ids_column.insert(1,"updated_timestamp", self.modlist_timestamps, True)

                if arg.lower() == "--write":
                    self.writeToCSV()
                elif arg.lower() == "--check":
                    self.checkAndCompare(data_queue)

            else:
                logging.info("Invalid argument provided. Specify either --write or --check after the script name to get started, or use -h or --help for proper usage of this script.")
        
        except Exception as e:
            logging.debug(f"ERROR - {e}")

    def writeToCSV(self) -> None:
        ''' Write mod ID and mod last update timestamp to CSV '''
        logging.info("Writing latest mod list to CSV file...")
        self.workshop_ids_column.to_csv(self.mod_csv, index=False)
        logging.info("Done.\n")

if __name__ == "__main__":
    # Configure the logging system
    logging.basicConfig(level = logging.INFO) ## To re-enable logging remove logging.disable() i.e, level = logging.INFO

    usage = ("Proper Usage:\n\tpython3 zomboid_soup.py --check\n\tpython3 zomboid_soup.py --write\
        \n\n\t--write:\n\t\tReads your server.ini file for workshop mod IDs and then creates a CSV file to use as reference while scraping the Steam workshop for mod updates.\
        \n\t\tIf --check returns False, you can use --write to update your mod list upon a server restart.\
        \n\t--check:\n\t\tCrawls the Steam workshop to check if mods are updated by comparing them against the CSV file created by --write.\
        \n\t\tReturns 0 to passed queue if the last updated timestamps crawled from Steam matches the CSV. Returns 1 if not.\
        \n\n\t© 2024 - Free to share and distribute\n\t\t Created by:  Pink9\n\t\t Version: 1.8")

    zs = zomboidSoup("../servertest.ini", "../mod_csv.csv")

    response_queue = queue.Queue()
    
    if 1 < len(sys.argv) <= 2:
        zs.scrapeSteamWorkshop(sys.argv[1], response_queue)
    else:
        print(f"missing or invalid argument(s). Please try again.\n{usage}")
        exit(1)

    logging.info(f"Response: {response_queue.get()}")
