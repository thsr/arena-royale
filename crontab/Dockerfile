FROM ubuntu:18.04

RUN apt-get update && apt-get install -y cron  && apt-get install -y curl

# Add crontab file in the cron directory
COPY crontab /etc/cron.d/simple-cron

# Add shell script and grant execution rights
COPY script.sh /script.sh
RUN chmod +x /script.sh

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/simple-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log