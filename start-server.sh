#!/bin/bash

INSTDIR="/home/pzuser/pzserver/";
cd "${INSTDIR}";
## Backup previous server files before starting server
tar -zcvpf /home/pzuser/Zomboid/backups/"`date +%Y%m%d-%H%M%S`"_startup_serverWorldSave.tgz /home/pzuser/Zomboid/Saves/Multiplayer/servertest/
if "${INSTDIR}/jre64/bin/java" -version > /dev/null 2>&1; then
	echo "64-bit java detected"
	export PATH="${INSTDIR}/jre64/bin:$PATH"
	export LD_LIBRARY_PATH="${INSTDIR}/linux64:${INSTDIR}/natives:${INSTDIR}:${INSTDIR}/jre64/lib/amd64:${LD_LIBRARY_PATH}"
	JSIG="libjsig.so"
	LD_PRELOAD="${LD_PRELOAD}:${JSIG}" ./ProjectZomboid64 "$@"
elif "${INSTDIR}/jre/bin/java" -client -version > /dev/null 2>&1; then
	echo "32-bit java detected"
	export PATH="${INSTDIR}/jre/bin:$PATH"
	export LD_LIBRARY_PATH="${INSTDIR}/linux32:${INSTDIR}/natives:${INSTDIR}:${INSTDIR}/jre/lib/i386:${LD_LIBRARY_PATH}"
	JSIG="libjsig.so"
	LD_PRELOAD="${LD_PRELOAD}:${JSIG}" ./ProjectZomboid32 "$@"
else
	echo "couldn't determine 32/64 bit of java"
fi
exit 0

#
# EOF
#
###############################################################################

