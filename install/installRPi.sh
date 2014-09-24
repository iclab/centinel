#!/bin/bash
#
# installRPi.sh: install centinel on Raspbian

sudo apt-get install python-pip python-m2crypto
sudo pip install --upgrade centinel-dev

# write out a centinel test script to cron.hourly
sudo echo "#!/bin/bash" > /etc/cron.hourly/centinel
sudo echo "# cron job for centinel" >> /etc/cron.hourly/centinel
sudo echo "/usr/local/bin/centinel-dev" >> /etc/cron.hourly/centinel
sudo echo "/usr/local/bin/centinel-dev --sync" >> /etc/cron.hourly/centinel
sudo chmod +x /etc/cron.hourly/centinel
