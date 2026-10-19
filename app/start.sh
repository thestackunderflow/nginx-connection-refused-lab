#!/usr/bin/env bash
# Start Tomcat, optionally bound to one address (BIND_ADDR) and after a delay (START_DELAY).
set -e
cd /usr/local/tomcat
if [ -n "${BIND_ADDR:-}" ]; then
  sed -i "s|<Connector port=\"8080\"|<Connector address=\"$BIND_ADDR\" port=\"8080\"|" conf/server.xml
fi
grep -o '<Connector [^>]*port="8080"[^>]*' conf/server.xml | head -1 | tr -s ' \n' ' ' > /tmp/connector.txt
if [ "${START_DELAY:-0}" != "0" ]; then echo "start.sh: waiting ${START_DELAY}s before Tomcat starts"; sleep "$START_DELAY"; fi
exec catalina.sh run
