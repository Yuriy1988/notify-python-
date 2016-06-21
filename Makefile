PYTHON=python3.5

QUEUE_USERNAME=xopay_rabbit
QUEUE_PASSWORD=5lf01xiOFwyMLvQrkzz7
QUEUE_VIRTUAL_HOST=/xopay


# ========== Linux ==========


# ----- Install -----

install_python35_repo:
	sudo add-apt-repository ppa:fkrull/deadsnakes
	sudo apt-get update

install_mongodb_repo:
	sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
	echo "deb http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb.list
	sudo apt-get update

install:
	sudo apt-get install -y $(PYTHON) $(PYTHON)-dev python3-pip python3-wheel python-virtualenv
	sudo apt-get install -y rabbitmq-server
	sudo apt-get install -y mongodb-org


# ----- Queue -----

queue_create:
	sudo rabbitmqctl add_vhost $(QUEUE_VIRTUAL_HOST)
	sudo rabbitmqctl add_user $(QUEUE_USERNAME) $(QUEUE_PASSWORD)
	sudo rabbitmqctl set_permissions -p $(QUEUE_VIRTUAL_HOST) $(QUEUE_USERNAME) ".*" ".*" ".*"

queue_remove:
	sudo rabbitmqctl delete_user $(QUEUE_USERNAME)
	sudo rabbitmqctl delete_vhost $(QUEUE_VIRTUAL_HOST)


# ----- Virtualenv -----

venv_init:
	if [ ! -d "venv" ]; then virtualenv --no-site-packages -p $(PYTHON) venv; fi;
	bash -c "source venv/bin/activate && pip install --upgrade wheel && pip install -r requirements.txt"


# ----- Setup -----

setup: install venv_init


# ----- Update -----

update: venv_init


# ----- Demo Server -----

setup_demo:
	fab setenv:demo setup

deploy:
	fab setenv:demo update


# ----- Run Server -----

runserver:
	./app.py --debug

# ========== MacOS ==========


# ----- Install -----

mac_install:
	brew install rabbitmq  # admin: http://localhost:15672
	sudo chmod +w /etc/paths
	sudo echo /usr/local/sbin >> /etc/paths


rabbitmq_settings:
	rabbitmqctl add_vhost $(QUEUE_VIRTUAL_HOST)
	rabbitmqctl add_user $(QUEUE_USERNAME) $(QUEUE_PASSWORD)
	rabbitmqctl set_permissions -p $(QUEUE_VIRTUAL_HOST) $(QUEUE_USERNAME) ".*" ".*" ".*"

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
