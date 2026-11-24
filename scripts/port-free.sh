#!/bin/sh
# Before starting a POC server: if the port is taken, say which program and which folder holds it, and how to free it.
# The POC and the DPH project both use ports 8100 and 3100, so only one of them can run at a time.
port="$1"
pid=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1)
[ -z "$pid" ] && exit 0
dir=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
case "$dir" in
  */DPH*) who="the DPH project" ;;
  */POC*) who="the POC itself (already running)" ;;
  *) who="another program" ;;
esac
echo ""
echo "Port $port is already in use by $who."
echo "  Process: $pid  $(ps -o command= -p "$pid" | cut -c1-90)"
echo "  Folder:  ${dir:-unknown}"
echo ""
echo "Stop it first (press Ctrl+C in its terminal, or run: kill $pid), then start the POC again."
echo ""
exit 1
