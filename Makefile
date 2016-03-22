mac_setup:
	brew install rabbitmq  # http://localhost:15672
	sudo chmod +w /etc/paths
	sudo echo /usr/local/sbin >> /etc/paths
	# pip3 install celery  # should be installed globally for accessing from shell.



#
# to start "worker" and "scheduler" parallel use "make run -j"
#

run: worker scheduler

worker:
	venv/bin/celery -A tasks worker --loglevel=info

scheduler:
	venv/bin/celery -A tasks beat

