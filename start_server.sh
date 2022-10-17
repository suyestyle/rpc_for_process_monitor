#!/bin/bash
export PATH="/usr/local/python3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin:/root/bin"
cd /opt/soft/rpc_for_monitor && flock --wait 5 -x state/rpc_server_flock.lock -c "./py37env/bin/python rpc.py --role server --client 192.168.1.100 --port 9300 --server 192.168.1.100"
