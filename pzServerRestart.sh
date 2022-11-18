#!/usr/bin/bash

## Project Zomboid  Rcon Server Controller
## Created Nov 12th 2021 by Pink#4317
## Version 1.5

## Kill previous server instance(s) before starting for the first time
printf "Cleaning up previous server instance (if any exist)!\n"
pkill ./ProjectZomboid64 -f
pkill start-server.sh -f
sleep 5

## Start server
printf "Starting first server instance via script!\n"
nohup /home/pzuser/pzserver/./start-server.sh&
sleep 1m

## While server running execute rcon commands to restart the server and create a backup
printf "Rcon Client will now manage server restart sequence!\n"
while true
do
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server will restart in 4 hours\""
  sleep 3h
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server will restart in 1 hour\""
  sleep 55m
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server will restart in 5 minutes\""
  sleep 4m
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server will restart in 1 minute\""
  sleep 55
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server preparing for restart...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Restart Imminent. Please disconnect from the server.\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Saving state & backing up world dictionary...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p yourpassword "servermsg \"Server preparing for restart...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p yourpassword "save"
  sleep 1
  rcon -a 127.0.0.1:27015 -p yourpassword "quit"
  sleep 5

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
  nohup /home/pzuser/pzserver/./start-server.sh&
  sleep 5m

done
