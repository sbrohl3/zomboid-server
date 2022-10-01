#!/usr/bin/bash

## Start Server
nohup /home/pzuser/pzserver/./start-server.sh&
sleep 5m
## While server running execute rcon commands to restart the server and create a backup
printf "Rcon Script Now Managing Server Restart Sequence!\n"
while true
do
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server will restart in 4 hours\""
  sleep 3h
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server will restart in 1 hour\""
  sleep 55m
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server will restart in 5 minutes\""
  sleep 4m
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server will restart in 1 minute\""
  sleep 55
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server preparing for restart...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Restart Imminent. Please disconnect from the server.\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Saving state & backing up world dictionary...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "servermsg \"Server preparing for restart...\""
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "save"
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "save"
  sleep 1
  rcon -a 127.0.0.1:27015 -p <INSERT RCON PASSWORD HERE> "quit"
  sleep 1m
  # Backing up server to tar.gz
  printf "Backing up Server!\n"
  tar -zcvpf /home/pzuser/Zomboid/backups/"`date +%Y%m%d-%H%M%S`"_restart_serverWorldSave.tgz /home/pzuser/Zomboid/Saves/Multiplayer/servertest/
  sleep 10
  nohup /home/pzuser/pzserver/./server-start.sh&
  sleep 5m
done
