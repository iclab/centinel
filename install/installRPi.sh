#!/bin/bash
#
# installRPi.sh: install centinel on Raspbian

sudo apt-get install python-pip python-m2crypto
sudo pip uninstall centinel
sudo pip install --upgrade centinel-dev

# write out a centinel test script to cron.hourly
sudo rm -f /etc/cron.hourly/centinel
echo "#!/bin/bash"                                > centinel-hourly-run
echo "# cron job for centinel"                   >> centinel-hourly-run
echo 'sleepTime=$(($RANDOM % $(expr 60 \* 15)))' >> centinel-hourly-run
echo 'sleep $sleepTime'                          >> centinel-hourly-run
echo "/usr/local/bin/centinel-dev --sync"        >> centinel-hourly-run
echo "/usr/local/bin/centinel-dev"               >> centinel-hourly-run
echo "/usr/local/bin/centinel-dev --sync"        >> centinel-hourly-run
sudo mv centinel-hourly-run /etc/cron.hourly/centinel
sudo chmod +x /etc/cron.hourly/centinel

# write out a centinel autoupdate script
sudo rm -f /etc/cron.daily/centinel-autoupdate
echo "#!/bin/bash"                              > centinel-autoupdate-script
echo "# cron job for centinel autoupdate"      >> centinel-autoupdate-script
echo "sudo pip install --upgrade centinel-dev" >> centinel-autoupdate-script
sudo mv centinel-autoupdate-script /etc/cron.daily/centinel-autoupdate
sudo chmod +x /etc/cron.daily/centinel-autoupdate
