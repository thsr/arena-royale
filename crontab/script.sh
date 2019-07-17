#!/bin/bash

echo "$(date): executed script" >> /var/log/cron.log 2>&1
curl -X POST http://pythonflask:80/backup