mac_setup:
	brew install rabbitmq  # admin: http://localhost:15672
	sudo chmod +w /etc/paths
	sudo echo /usr/local/sbin >> /etc/paths

rabbitmq_settings:
	rabbitmqctl add_user remote
	rabbitmqctl set_permissions -p / remote ".*" ".*" ".*"

#
# to start "worker" and "scheduler" parallel use "make run -j"
#

run: worker scheduler

worker:
	mkdir -p logs
	venv/bin/celery -A notify worker --loglevel=info --logfile=logs/worker.log

scheduler:
	mkdir -p logs
	venv/bin/celery -A notify beat --logfile=logs/scheduler.log
