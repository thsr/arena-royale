echo "$(date): executed script" >> /var/log/cron.log 2>&1
curl http://pythonflask:5000/g