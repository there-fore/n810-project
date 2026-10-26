#!/bin/sh
# Start Mote on the N810's screen as `user`, from an SSH session as root.
# Usage: sh /tmp/run-mote.sh [test] [secs]
cd /tmp
exec su user -c "DISPLAY=:0 python2.5 -u /tmp/mote.py $*"
