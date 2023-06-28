#!/usr/bin/python3

## Standard imports
import os
import queue
import time as t
import psutil as ps
import schedule as s
import datetime as dt
import subprocess as sp
import threading as th
from signal import signal, SIGINT

## import custom class for scraping mods list
from zomboid_soup import zomboid_Soup

################################################################################
#  Created by https://steamcommunity.com/id/Mr_Pink47/
#  Discord: pink9
#
#  Version - 1.0 (06/18/2023)
#  © 2023 - Open Source - Free to share and modify
#
# To use this program, first install all Python3 dependencies:
#
#     python3 -m pip install -r requirements.txt
#
# Then ensure you have this rcon client installed into your Linux server
#
#      https://github.com/gorcon/rcon-cli/releases
#
#      *Extract this rcon archive to /usr/bin on your Linux server
#
# Then run this script with Python3 like so:
#
#           python3 zomboid_server_manager.py
#
# Add to Crontab (Must be added to use reboot_counter): 
#           @reboot /usr/bin/python3 zomboid_server_manager.py
#
#
# NOTE: zomboid_soup.py must be in the same folder as zomboid_server_manager.py
################################################################################

class zomboidServerController():
    ''' A zomboid server controller class '''
    
    def __init__(self):
        ''' Constructor for Zomboid Server Cotnroller Variables '''
        ## Reboot counter - Tracks when to restart the host pc 
        ###########################################################
        self.reboot_counter         = 0
        self.reboot_counter_enabled = False
        ###########################################################

        ## A flag for managing state of the server
        ###########################################################
        self.one_hour_flag = False
        self.restart_flag  = False
        self.start_flag    = False
        ###########################################################

        ## Current Datetime
        ###########################################################
        self.current_time = dt.datetime
        ###########################################################
        
        ## Zomboid Soup Paths
        ###########################################################
        self.server_ini = "/home/user/Zomboid/Server/servertest.ini" # Specify path to server.init
        self.mod_csv    = "/home/user/Zomboid/Server/zomboid_mod_updateList.csv" # specify path where to save mod_updateList.csv
        ###########################################################

        ## Assign server World Dictionary backup path to variable
        ###########################################################
        self.backup_path  = "/home/user/Zomboid/Saves/Multiplayer/servertest/"
        ###########################################################

        ## Server Shell and binary process names -- DO NOT MODDIFY
        ###########################################################
        self.server_shell_process_name  = "start-server.sh"
        self.server_binary_process_name = "ProjectZomboid64"
        ###########################################################

        ## Rcon Config
        ##########################################################
        self.server_local_ip  = "127.0.0.1"
        self.local_rcon_port  = 27015
        self.rcon_password    = "rcon_password"
        #########################################################

        ## Rcon Command -- DO NOT MODIFY
        #########################################################        
        self.rcon_command = "" ## Variable to hold Rcon command
        self.rcon_message = rf"rcon --address {self.server_local_ip}:{self.local_rcon_port} --password {self.rcon_password} "
        #########################################################

    def coldStart(self):
        ''' A method for starting the server for the first boot '''

        def handler(signal_received, frame):
            ''' A handler for killing the program with Ctrl+C '''
            # Handle any cleanup here
            print('\nCTRL-C detected. Exiting gracefully. Please wait...')
            self.serverMessenger("quit")
            exit(0)
       
       ## When Ctrl+C detected, called stopServer()
        signal(SIGINT, handler)

        ## Start a new server instance
        ## and kill any previous instances
        self.stopServer()
        self.startServer()

        ## Set schedules for restarting the server, and checking modlist status
        s.every(3).hours.do(zsc.serverMessenger, "1h")
        s.every(4).hours.do(zsc.serverMessenger, "restart")
        s.every(30).minutes.do(zsc.serverMessenger, "modUpdateCheck")

        while True:
            # Checks whether a scheduled task
            # is pending to run or not
            s.run_pending()
            t.sleep(1)

    def backupWorld(self, server_status):
        ''' A method to backup the Zomboid server '''
        # Back up server to tar.gz
        print(f"{self.current_time.now()} -- Backing up Server!\n")
        backup_server_cmd = f"tar -zcpf /home/pzuser/Zomboid/backups/\"`date +%Y%m%d-%H%M%S`\"_{server_status}_serverWorldSave.tgz --absolute-names {self.backup_path}"
        sp.call(backup_server_cmd, shell=True)
        t.sleep(10)

    def rebootHost(self):
        ''' A method to reboot the host PC after the server has rebooted three times '''
        print(f"ZOMBOID SERVER HAS RESTARTED {self.reboot_counter} TIMES.\nInitiating a reboot of the host PC...")
        result = sp.run(["uname", "-a"], capture_output=True)
        result = result.stdout.strip().decode()
        ## Check if server is hosted in a WSL instance or not
        if "Microsoft" in result:
            sp.call("shutdown.exe -f")
        else:
            sp.call("reboot --force")
        
    def stopServer(self):
        ''' A method for stopping instances of a zomboid server '''
        ## Reset all server state flags
        self.one_hour_flag = False
        self.restart_flag  = False
        self.start_flag    = False
        
        ## stop server process
        print(f"{self.current_time.now()} -- Cleaning up previous server instance (if any exist)...\n")
        for proc in ps.process_iter():
            # check whether the process name matches
            if proc.name() in [self.server_shell_process_name,self.server_binary_process_name]:
                proc.kill()
        t.sleep(5)

    def startServer(self):
        ''' A method for starting a zomboid server instance '''
        ## Start server
        print(f"{self.current_time.now()} -- Starting first server instance via script!\n")
        print('=== Server Running. Press CTRL-C to safely shutdown, backup, and exit the server. ===\n')
        self.backupWorld("start")
        start_server_cmd = "nohup /home/pzuser/pzserver/./start-server.sh >/dev/null 2>&1 &"
        sp.call(start_server_cmd, shell=True)
        self.start_flag = True ## A flag to manage server state
        self.serverMessenger("modUpdateCheck") ## Update modList.csv
        t.sleep(300)
        self.serverMessenger("4h")

    def serverMessenger(self, cmd_flag):
        ''' A method for controlling the Zomboid Server and sending messages via RCON '''
        ## Send messages to the server
        def sendMessage():
            ''' A helper method to perform a subprocess (system) call to send an rcon message to the zomboid server instance '''
            sp.call(self.rcon_message + self.rcon_command, shell=True)
        
        try:
            if cmd_flag   == "4h":
                print(f"{self.current_time.now()} -- {cmd_flag} sent. Sending 4 hours before restart warning.")
                try:
                    self.rcon_command = "\"servermsg \\\"Server will restart in 4 hours\\\"\""
                    sendMessage()
                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
            
            if cmd_flag == "1h":
                print(f"\n{self.current_time.now()} -- {cmd_flag} sent. Sending 1h before restart warning.")
                try:
                    self.rcon_command = "\"servermsg \\\"Server will restart in 1 hour\\\"\""
                    sendMessage()
                    self.one_hour_flag = True
                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
            
            if cmd_flag == "restart":
                print(f"\n{self.current_time.now()} -- {cmd_flag} sent. Restarting server.")
                try:
                    if self.reboot_counter >= 3:
                        self.reboot_counter = 0
                        self.backupWorld()
                        self.stopServer()
                        self.rebootHost()
                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
                try:
                    self.rcon_command = "\"servermsg \\\"Server will restart in 5 minutes...\\\"\""
                    sendMessage()
                    self.restart_flag = True
                    t.sleep(300)
                    self.rcon_command = "\"servermsg \\\"Server will restart in 1 minutes...\\\"\""
                    sendMessage()
                    t.sleep(60)
                    self.rcon_command = "\"servermsg \\\"Server preparing for restart...\\\"\""
                    sendMessage()
                    t.sleep(1)
                    self.rcon_command = "\"servermsg \\\"Restart imminent! Please disconnect from the server!\\\"\""
                    sendMessage()
                    t.sleep(1)
                    self.rcon_command = "\"servermsg \\\"Saving Server State and backing up World Dictionary.\\\"\""
                    sendMessage()
                    t.sleep(1)
                    self.rcon_command = "\"servermsg \\\"Server is preparing to restart.\\\"\""
                    sendMessage()
                    t.sleep(1)
                    self.rcon_command = "\"save\""
                    sendMessage()
                    t.sleep(1)
                    self.backupWorld(cmd_flag)
                    t.sleep(5)
                    self.rcon_command = "\"quit\""
                    sendMessage()

                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
                t.sleep(5)
                self.stopServer()
                t.sleep(10)
                self.startServer()
                if self.reboot_counter_enabled:
                    self.reboot_counter += 1 
                else:
                    print("Reboot counter disabled. Manual reboot is required for the host PC.")
        
            if cmd_flag == "quit":
                print(f"\n{self.current_time.now()} -- {cmd_flag} sent. Shutting down server.")
                try:
                    self.rcon_command = "\"servermsg \\\"Server is shutting down.\\\"\""
                    sendMessage()
                    self.rcon_command = "\"save\""
                    sendMessage()
                    t.sleep(5)
                    self.backupWorld(cmd_flag)
                    self.rcon_command = "\"quit\""
                    sendMessage()
                    t.sleep(5)
                    self.stopServer()
                except Exception as error:
                    print(f"\n{self.current_time.now()} -- ERROR: {error}")
            
            if cmd_flag == "modUpdateCheck":
                if self.one_hour_flag and self.restart_flag:
                    print("Server preapring to restart. Cancelling mod update check.\n")
                    return
                
                ## Instantiate ZomboidSoup class to variable
                zs = zomboid_Soup()

                ## Initialize paths to server.ini and mod.csv in Zomboid_soup class
                zs.server_ini = self.server_ini
                zs.mod_csv    = self.mod_csv

                ## Queue to grab the state of current server mods
                data_queue = queue.Queue()

                def modUpdateThread(arg, data_queue):
                    ''' A helper method for creating threads for the updating the zomboid server modlist '''
                    ## Thread zomboid_Soup instance for faster results and better interoperability with other scripts
                    thread = th.Thread(target=zs.scrapeSteamWorkshop,args=(arg ,data_queue,), daemon=True)
                    thread.start()
                    thread.join()

                if  os.path.exists(self.mod_csv) and not self.start_flag:
                    ## Check if the current modsList.csv has updated
                    modUpdateThread("--check", data_queue)
                    result = data_queue.get()

                    if result == 0:
                        print(f"\n{self.current_time.now()} -- Mods are in Sync. Nothing else to do.")
                        return

                    elif result == 1:
                        print("\nMods out of sync. Preparing to restart server!")
                        try:
                            self.rcon_command = "\"servermsg \\\"One or more mods have updated and the server must restart.\\\"\""
                            sendMessage()
                        except Exception as error:
                            print(f"{self.current_time.now()} --\nERROR: {error}")
                        modUpdateThread("--write", data_queue)
                        self.serverMessenger("restart")
                        return
                
                elif not os.path.exists(self.mod_csv) or self.start_flag:
                    ## Mods are updated on server start, so only write updates to modList
                    modUpdateThread("--write", data_queue)
                    self.start_flag = False
                    return

        except Exception as error:
            print(f"{self.current_time.now()} -- {error}")

if __name__ == "__main__":    
    print(" ____          _         _    _   ___                        __  __                              ")
    print("|_  /___ _ __ | |__  ___(_)__| | / __| ___ _ ___ _____ _ _  |  \/  |__ _ _ _  __ _ __ _ ___ _ _  ")
    print(" / // _ \ '  \| '_ \/ _ \ / _` | \__ \/ -_) '_\ V / -_) '_| | |\/| / _` | ' \/ _` / _` / -_) '_| ")
    print("/___\___/_|_|_|_.__/\___/_\__,_| |___/\___|_|  \_/\___|_|   |_|  |_\__,_|_||_\__,_\__, \___|_|   ")
    print("                                                                                  |___/          ")
    print("=================================================================================================")
    version = "Version - 1.0 (06/18/2023)\nCreated by https://steamcommunity.com/id/Mr_Pink47/\nDiscord: pink9\n© 2023 - Open Source - Free to share and modify"
    print(version)
    print("=================================================================================================")           
    ## Create an instance of the zomboid server conroller class
    zsc = zomboidServerController()
    zsc.coldStart()









