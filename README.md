About:
	Python Translator between a Slack Channel and Cleverbot.com's API
	using Redis for Conversation Retention and Cleverbot.io's API as a backup.


Requirments:

   * Slack Token [ https://my.slack.com/services/new/bot )

    - The username you set when creating your token is NOT the slack_bot_user in the config.py!

   * Cleverbot API [ https://www.cleverbot.com/api/ ]


Optional Configuration:

   * cleverbot.io API [ https://cleverbot.io/keys ]

    - Suggested as a fallback in the event your cleverbot.com API has issues.

   * Redis Server


Install //Ubuntu || Assuming you are logged in as root

        apt-get install redis-server python git

        pip install redis slackclient

        adduser cleverme

        su cleverme

        cd ~/

        git clone https://github.com/ixof/cleverme.git

        cd cleverme

        cp config.py.dist config.py

        nano config.py


Running //Testing

        python cleverme.py

        	###CTRL+C when you are done testing###


Running //Ubunut Start (headless)

        nohup python /home/cleverme/cleverme/cleverme.py &


Running //Ubuntu Install

        crontab -e

        	###add to the bottom of the crontab file the following line:###

        @reboot nohup python /home/cleverme/cleverme/cleverme.py &

        	###CLTR+X, press Y, then press Enter###


Install #Note: You will need to edit config.py with the necessary information.

Install #Note: For more redis support, check out https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-redis-on-ubuntu-16-04
