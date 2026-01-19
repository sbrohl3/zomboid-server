#!/usr/bin/python3

## Standard imports
import os
import json
import queue
import time as t
import psutil as ps
import schedule as s
import datetime as dt
import subprocess as sp
import threading as th
from signal import signal, SIGINT

## import custom class for scraping mods list
from zomboidSoup import zomboidSoup

################################################################################
#  Created by https://steamcommunity.com/id/Mr_Pink47/
#  Discord: pink9
#
#  Version - 1.10.0 (09/23/2024)
#  © 2024 - Open Source - Free to share and modify
#
# To use this program, first install all Python3 dependencies:
#
#     python3 -m pip install -r requirements.txt
#        (I recommend using a venv for this; Python>=3.10 )
#
# Then ensure you have this rcon client installed into your Linux server
#
#      https://github.com/gorcon/rcon-cli/releases
#
#      *Extract this rcon archive to /usr/bin on your Linux server
#
# Then run this script with Python3 like so:
#
#           python3 /path/to/script/zomboid_server_manager.py
#
# Add to Crontab (Must be added to use reboot_counter): 
#           @reboot /usr/bin/python3 /path/to/script/zomboid_server_manager.py
#
#
# NOTE: zomboidSoup.py must be in the same folder as zomboid_server_manager.py
################################################################################

class ZomboidServerController():
    ''' A zomboid server controller class '''
    
    def __init__(self) -> None:
        ''' Constructor for Zomboid Server Cotnroller Variables '''
        try:
            if os.path.exists("server_config.json"):
                with open("server_config.json", "r") as config:
                    config_data = json.load(config)
                
                ## Reboot counter - Tracks when to restart the host pc 
                ###########################################################
                self.reboot_counter         = 0 # - Don't Modify
                self.reboot_counter_enabled = config_data["server_config"]["reboot_enabled"]
                self.reboot_threshold       = config_data["server_config"]["reboot_threshold"]
                ###########################################################

                ## Flags for managing state of the server - Don't Modify
                ###########################################################
                self.one_hour_flag = False
                self.restart_flag  = False
                self.start_flag    = False
                ###########################################################

                ## A list storing current jobs active on the server
                ###########################################################
                self.jobs = []
                ###########################################################

                ## Current Datetime - Don't Modify
                ###########################################################
                self.current_time = dt.datetime
                ###########################################################
                
                ## Path to start-server script
                ###########################################################
                self.start_server_cmd = config_data["server_config"]["start_server_command"]
                ###########################################################
                
                ## Zomboid Soup Paths
                ###########################################################
                self.server_ini = config_data["server_config"]["server_ini_path"] # Specify path to server.init
                self.mod_csv    = config_data["server_config"]["mod_csv_path"] # specify path where to save mod_updateList.csv
                ###########################################################

                ## Define backup folder path and world dictionary location
                ###########################################################
                self.backup_path = config_data["server_config"]["backup_folder_path"] ## Location of server backups
                self.world_path  = config_data["server_config"]["world_dict_path"]
                ###########################################################

                ## Server Shell and binary process names
                ###########################################################
                self.server_shell_process_name  = config_data["server_config"]["server_shell_process_name"]
                self.server_binary_process_name = config_data["server_config"]["server_binary_process_name"]
                ###########################################################

                ## Rcon Config 
                ##########################################################
                self.server_local_ip  = config_data["server_config"]["rcon_local_ip"]
                self.local_rcon_port  = config_data["server_config"]["rcon_local_port"]
                self.rcon_password    = config_data["server_config"]["rcon_password"]
                #########################################################

                ## Rcon Command - Don't Modify
                #########################################################        
                self.rcon_conn_string = rf"rcon --address {self.server_local_ip}:{self.local_rcon_port} --password {self.rcon_password} "
                #########################################################
            
            else:
                print("Unable to read server_config.json.\nPlease re-download the repo and ensure it's in the same directory as zomboid_server_manager.py")
                exit(1)

        except Exception as error:
            print(f"ERROR: Could not initialize server configuration.\n{error}")
            exit(1)

    def backupWorld(self, server_status) -> None:
        ''' A method to backup the Zomboid server '''
        # Back up server to tar.gz
        print(f"{self.current_time.now()} -- Backing up Server!\n")
        backup_server_cmd = f"tar -zcpf {self.backup_path}/\"`date +%Y%m%d-%H%M%S`\"_{server_status}_serverWorldSave.tgz --absolute-names {self.world_path}"
        sp.call(backup_server_cmd, shell=True)
        t.sleep(10)

    def coldStart(self) -> None:
        ''' A method for starting the server for the first boot '''
        
        ## Track number of times user presses Ctrl+C (Sigint)
        self.sigint_count = 0

        def handler(signal_received, frame):
            ''' A handler for killing the program with Ctrl+C '''
            # Handle user shutdown
            print(f'\n{self.current_time.now()} -- CTRL-C detected. Exiting gracefully. Please wait...\n')
            if self.sigint_count >= 1:
               print(f"{self.current_time.now()} -- CTRL-C received twice; forcing immediate server shutdown!\n")
               exit(0)
            self.sigint_count += 1
            self.serverMessenger("quit")
            exit(0)
       
        ## When Ctrl+C detected, called stopServer()
        signal(SIGINT, handler)

        ## Start a new server instance
        ## and kill any previous instances
        self.stopServer()
        self.startServer()

    def rebootHost(self) -> None:
        ''' A method to reboot the host PC after the server has rebooted x number of times '''
        print(f"\n####ZOMBOID SERVER HAS RESTARTED {self.reboot_counter} TIMES.\n####Initiating a reboot of the host PC...\n")
        result = sp.run(["uname", "-a"], capture_output=True)
        result = result.stdout.strip().decode()
        ## Check if server is hosted in a WSL instance or not
        if "Microsoft" in result:
            sp.call(["/mnt/c/WINDOWS/system32/shutdown.exe", "/r"])
            sp.call(["/mnt/c/WINDOWS/system32/shutdown.exe", "/f"])
        else:
            ## In case of Linux, run reboot with --force
            sp.call("reboot --force")
    
    def runScheduler(self):
        ''' Method to keep the scheduler running '''
        while True:
           # Checks whether a scheduled task
            # is pending to run or not
            s.run_pending()
            t.sleep(1)

    def scheduleTasks(self) -> None:
        ## Set schedules for restarting the server, and checking modlist status
        one_hour        = s.every(3).hours.do(zsc.serverMessenger, "1h")
        restart         = s.every(4).hours.do(zsc.serverMessenger, "restart")
        update_check    = s.every(30).minutes.do(zsc.serverMessenger, "modUpdateCheck")

        ## Store jobs so they can be cancelled later
        self.jobs.extend([one_hour, restart, update_check])

    def serverMessenger(self, cmd_flag) -> None:
        ''' A method for controlling the Zomboid Server and sending messages via RCON '''
        ## Send messages to the server
        def sendMessage(rcon_command):
            ''' A helper method to perform a subprocess (system) call to send an rcon message to the zomboid server instance '''
            sp.call(self.rcon_conn_string + rcon_command, shell=True)
        
        try:
            if cmd_flag in ["1h", "4h"]:
                print(f"{self.current_time.now()} -- {cmd_flag} sent. Sending {cmd_flag} before restart warning.")
                try:
                    sendMessage(f"\"servermsg \\\"Server will restart in {cmd_flag.replace("h","")} hour(s)\\\"\"")
                    if cmd_flag == "1h":
                        self.one_hour_flag = True
                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
            
            if cmd_flag == "restart":
                print(f"\n{self.current_time.now()} -- {cmd_flag} sent. Restarting server.\n")
                try:
                    if self.reboot_counter == self.reboot_threshold:
                        self.backupWorld("restart")
                        self.stopServer()
                        self.rebootHost()
                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")
                try:
                    sendMessage("\"servermsg \\\"Server will restart in 5 minutes...\\\"\"")
                    self.restart_flag = True
                    t.sleep(300)
                    sendMessage("\"servermsg \\\"Server will restart in 1 minutes...\\\"\"")
                    t.sleep(60)
                    sendMessage("\"servermsg \\\"Server preparing for restart...\\\"\"")
                    t.sleep(1)
                    sendMessage("\"servermsg \\\"Restart imminent! Please disconnect from the server!\\\"\"")
                    t.sleep(1)
                    sendMessage("\"servermsg \\\"Saving Server State and backing up World Dictionary.\\\"\"")
                    t.sleep(1)
                    sendMessage("\"servermsg \\\"Server is preparing to restart.\\\"\"")
                    t.sleep(1)
                    sendMessage("\"save\"")
                    t.sleep(1)
                    self.backupWorld(cmd_flag)
                    t.sleep(5)
                    sendMessage("\"quit\"")

                except Exception as error:
                    print(f"{self.current_time.now()} -- ERROR: {error}")

                ## Stop & Restart the server
                t.sleep(5)
                self.stopServer()
                t.sleep(10)
                self.startServer()

                if self.reboot_counter_enabled:
                    self.reboot_counter += 1 
                    print(f"#### ZOMBOID SERVER HAS RESTARTED: {self.reboot_counter} times\n#### PC will restart on reboot #: {self.reboot_threshold}")
                else:
                    print("Reboot counter disabled. Manual reboot is required for the host PC.")
        
            if cmd_flag == "quit":
                print(f"\n{self.current_time.now()} -- {cmd_flag} sent. Shutting down server.")
                try:
                    ## Issue a final deathnote to the server and save the map
                    sendMessage("\"servermsg \\\"Server is shutting down.\\\"\"")
                    sendMessage("\"save\"")

                    ## Sleep 5 seconds to allow the final save to take place prior to backing up the server
                    t.sleep(5)

                    ## Backup the world before shutting down the server 
                    self.backupWorld(cmd_flag)

                    ## Send a quit message to shutdown the Zomboid server connection
                    sendMessage("\"quit\"")

                    ## Wait 5 seconds for "quit" command to finish
                    t.sleep(5)

                    ## Call the final stop function to kill the server
                    self.stopServer()

                except Exception as error:
                    print(f"\n{self.current_time.now()} -- ERROR: {error}")
            
            if cmd_flag == "modUpdateCheck":
                if self.one_hour_flag or self.restart_flag:
                    print("Server preparing to restart. Cancelling mod update check.\n")
                    return
                
                ## Instantiate ZomboidSoup class to variable
                zs = zomboidSoup(self.server_ini, self.mod_csv)

                ## Queue to grab the state of current server mods
                response_queue = queue.Queue()

                def modUpdateThread(arg, response_queue):
                    ''' A helper method for creating threads for the updating the zomboid server modlist '''
                    ## Thread zomboidSoup instance for faster results and better interoperability with other scripts
                    thread = th.Thread(target=zs.scrapeSteamWorkshop,args=(arg ,response_queue,), daemon=True)
                    thread.start()

                if os.path.exists(self.mod_csv) and not self.start_flag:
                    ## Check if the current modsList.csv has updated
                    modUpdateThread("--check", response_queue)
                    result = response_queue.get()

                    if result == 0:
                        print(f"{self.current_time.now()} -- Mods are in sync. Nothing else to do.\n")
                        return

                    elif result == 1:
                        print(f"{self.current_time.now()} -- Mods out of sync. Preparing to restart server!\n")
                        try:
                            sendMessage("\"servermsg \\\"One or more mods have updated and the server must restart.\\\"\"")
                        except Exception as error:
                            print(f"{self.current_time.now()} -- ERROR: {error}\n")
                        self.serverMessenger("restart")
                        return
                    else:
                        print(f"{self.current_time.now()} -- Error with synchronizing mods. Skipping sync.\n")
                
                elif not os.path.exists(self.mod_csv) or self.start_flag:
                    ## Mods are updated on server start, so only write updates to modList
                    print(f"{self.current_time.now()} -- Server started; updating modlist CSV.")
                    modUpdateThread("--write", response_queue)
                    self.start_flag = False
                    return

        except Exception as error:
            print(f"{self.current_time.now()} -- ERROR {error}")

    def startServer(self):
        ''' A method for starting a zomboid server instance '''
        ## Start the Zomboid server
        print(f"{self.current_time.now()} -- Starting first server instance via script!\n")
        print('#### Server instance started! Press CTRL-C to safely shutdown, backup, and exit the server. ####\n')
        
        ## Backup the world before starting the server
        self.backupWorld("start")

        ## This line starts the server using the command assigned from config.json
        ## The command is printed to the terminal to verify it's been passed correctly
        sp.call(self.start_server_cmd, shell=True)
        print(f"{self.current_time.now()} -- Now running server-start.sh script...\nCommand: {self.start_server_cmd}")
        
        ## A flag to manage server state
        self.start_flag = True 
        
        ## Update modList.csv
        self.serverMessenger("modUpdateCheck") 
        
        ## Sleep 5 minutes to allow the server to finish loading, then send server message
        t.sleep(300)
        
        ## Send 4h restart warning to the server
        self.serverMessenger("4h")

        ## Schedule tasks to run after the server has started
        self.scheduleTasks()

    def stopServer(self):
        ''' A method for stopping instances of a zomboid server '''
        ## Reset all server state flags
        self.one_hour_flag = False
        self.restart_flag  = False
        self.start_flag    = False

        ## Clear the jobs list
        for job in self.jobs:
            s.cancel_job(job)
        self.jobs.clear() 
        
        ## stop server process
        print(f"{self.current_time.now()} -- Cleaning up previous server instance (if any exist)...\n")
        for proc in ps.process_iter():
            # check whether the process name matches
            if proc.name() in [self.server_shell_process_name,self.server_binary_process_name]:
                proc.kill()
        t.sleep(5)

if __name__ == "__main__":    
    print(r" ____          _         _    _   ___                        __  __                              ")
    print(r"|_  /___ _ __ | |__  ___(_)__| | / __| ___ _ ___ _____ _ _  |  \/  |__ _ _ _  __ _ __ _ ___ _ _  ")
    print(r" / // _ \ '  \| '_ \/ _ \ / _` | \__ \/ -_) '_\ V / -_) '_| | |\/| / _` | ' \/ _` / _` / -_) '_| ")
    print(r"/___\___/_|_|_|_.__/\___/_\__,_| |___/\___|_|  \_/\___|_|   |_|  |_\__,_|_||_\__,_\__, \___|_|   ")
    print(r"                                                                                  |___/          ")
    print("=================================================================================================")
    version = "Version - 1.9 (01/04/2024)\nCreated by https://steamcommunity.com/id/Mr_Pink47/\nDiscord: pink9\n© 2024 - Open Source - Free to share and modify"
    print(version)
    print("=================================================================================================")           
    
    ## Init the server controller obj
    zsc = ZomboidServerController()
    
    ## Call a server cold start
    zsc.coldStart()

    ## Start the job scheduler
    zsc.runScheduler()









