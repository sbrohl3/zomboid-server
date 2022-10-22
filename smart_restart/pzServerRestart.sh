#!/usr/bin/bash

## Project Zomboid  Rcon Server Controller
## Created Nov 12th 2021 by Pink#4317
## Version 1.5

## Config
server_local_ip=127.0.0.1
local_rcon_port=27015
rcon_password=password
three_hour_flag="False"

## Kill previous server instance(s) before starting for the first time
printf "Cleaning up previous server instance (if any exist)!\n"
pkill ./ProjectZomboid64 -f
pkill start-server.sh -f
sleep 5

## Start server
printf "Starting first server instance via script!\n"
#nohup /home/pzuser/pzserver/./start-server.sh&
#sleep 1m

## Initialize varialbe to act as a timer
timer=`date +%s`

## Script start time
start_timer=`date +%s`

## Set timer for when to check if any mods changed
mod_check_time=$(expr $start_timer + 12) #00


function rcon_controller () {
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Server will restart in 5 minutes\""
    sleep 4m
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password"servermsg \"Server will restart in 1 minute\""
    sleep 55
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Server preparing for restart...\""
    sleep 1
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Restart Imminent. Please disconnect from the server.\""
    sleep 1
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Saving state & backing up world dictionary...\""
    sleep 1
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password"servermsg \"Server preparing for restart...\""
    sleep 1
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "save"
    sleep 1
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "quit"
    sleep 5
}


## While server running execute rcon commands to restart the server and create a backup
printf "Rcon Client will now manage server restart sequence!\n"
printf "The server will restart in 4 hours!\n"
rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Server will restart in 4 hours\""
while true
do
  ## For debugging purposes
  #echo $timer
  #echo $(expr $timer + 10) #800)
  #echo $(expr $timer + 14) #400)

  ## 3 Hour timer warning
  if (( $timer >= $(expr $start_timer + 10) )) &&  [[ $three_hour_flag == "False" ]]; then
    echo "Server will restart in 1 Hours."
    rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"Server will restart in 1 hour\""
    three_hour_flag="True"
  fi;

  ## 4 Hour timer warning, shutdown, backup, and restart
  if (( $timer >= $(expr $start_timer + 14) )) && [[ $three_hour_flag == "True" ]]; then
    echo "Server has been up for 4 hours. Time to restart."
    rcon_controller

    # Backing up server to tar.gz
    printf "Backing up Server!\n"
    tar -zcpf /home/pzuser/Zomboid/backups/"`date +%Y%m%d-%H%M%S`"_restart_serverWorldSave.tgz /home/pzuser/Zomboid/Saves/Multiplayer/servertest/
    sleep 10

    ## Kill previous server instances
    printf "Killing previous server instance!\n"
    pkill ./ProjectZomboid64 -f
    pkill start-server.sh -f
    sleep 10

    ## Start server instance
    printf "Starting new server instance!\n"
    #nohup /home/pzuser/pzserver/./start-server.sh&
    sleep 1

    three_hour_flag="False"
  fi;

  ## Run zomboid_soup script to determine if the server needs to restart on mod update
  if (( $timer >= $mod_check_time )); then
    printf "Python is running in the background...\n"
    python3 zomboid_soup.py "--check"
    mod_status=$?
    echo $mod_status 
    if (( ${mod_status} == 0 )); then
      printf "Everything is up to date...\n"
    elif (( ${mod_status} == 1 )); then
      printf "One or more server mods is out of sync. Preparing to reboot the server...\n"
      rcon -a $server_local_ip:$local_rcon_port -p $rcon_password "servermsg \"One or more mods has been updated. The server must restart!\""
      rcon_controller
    fi;
    mod_check_time=$(expr $(date +%s) + 12) #00
  fi;
 timer=`date +%s`
done;
