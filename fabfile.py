import os
from datetime import datetime
from fabric.api import env, task, run, put, cd, puts, local, sudo
from fabric.contrib.files import append

__author__ = 'Kostel Serhii'


hosts = dict(
    local='127.0.0.1',
    demo='demoenv@xopay.digitaloutlooks.com',
)

path_to_deploy = [
    'currency',
    'message_queue',
    'notification',
    '*.py',
    'requirements.txt',
    'Makefile',
]

path_to_exclude = [
    '*.pyc',
    '__pycache__',
    'fabfile.py'
]

env.deploy_dir = '/var/www/xopay/notify'
env.log_dir = '/var/log/xopay'
env.supervisor_task = 'xopay-notify'
env.build_dir = 'dist'
env.colorize_errors = True
env.hosts = list(hosts.values())

env.notify_port = 7461


def create_config(config_file, template_file, **config_kwargs):
    with open(template_file) as tf, open(config_file, 'w') as cf:
        config_kwargs.update(env)
        config = tf.read().format(**config_kwargs)
        cf.write(config)
    tf.close()
    cf.close()


def deploy():
    build_name = 'xopay-notify-{timestamp}.tar.gz'.format(timestamp=datetime.now().strftime("%Y-%m-%d-%H.%M.%S"))
    build_path = os.path.join(env.build_dir, build_name)

    # create build
    local('mkdir -p {build_dir}'.format(**env))
    local('tar --create --gzip --same-permissions --verbose --file {build_path} {paths} {exclude}'.format(
        build_path=build_path,
        paths=' '.join(path_to_deploy),
        exclude=' '.join('--exclude="%s"' % ep for ep in path_to_exclude)
    ))

    # deploy
    run('mkdir -p {deploy_dir}'.format(**env))
    with cd(env.deploy_dir):
        run('rm -rf {paths}'.format(paths=' '.join(path_to_deploy)))
    put(build_path, env.deploy_dir)
    local('rm -r {build_dir}'.format(**env))

    # update
    with cd(env.deploy_dir):
        run('tar --extract --verbose --file {build_name}'.format(build_name=build_name))
        run('rm {build_name}'.format(build_name=build_name))


# ----- Set Environment -----

@task
def setenv(host_name='demo'):
    """
    Define fabric environment depending on the server host.
    Example: fab setenv:demo
    :param host_name: remote server host_name from hosts
    """
    if host_name not in hosts:
        puts('ERROR: Host name {host_name} not found!\nTry:{commands}'.format(
            host_name=host_name,
            commands=''.join('\n  fab setenv:host=%s -> (%s)' % hi for hi in hosts.items())
        ))
        return

    host_addr = hosts.get(host_name)
    puts('Set host: {host}'.format(host=host_addr))
    env.hosts = [host_addr]
    env.host_name = host_name


# ----- Push ssh key -----

def read_key_file(key_file):
    key_file = os.path.expanduser(key_file)
    if not key_file.endswith('pub'):
        raise RuntimeWarning('Trying to push non-public part of key pair')
    with open(key_file) as f:
        return f.read()


@task
def push_key(key_file='~/.ssh/id_rsa.pub'):
    key_text = read_key_file(key_file)
    append('~/.ssh/authorized_keys', key_text)


# ----- Install -----

def setup_supervisor():
    sudo('apt-get install -y supervisor')

    base_config_file = '/tmp/supervisord.conf'
    create_config(base_config_file, 'DEPLOY/supervisord.conf.templ')
    put(base_config_file, '/etc/supervisor/', use_sudo=True)
    local('rm {config}'.format(config=base_config_file))

    config_file = '/tmp/xopay-notify.conf'
    create_config(config_file, 'DEPLOY/xopay-notify.conf.supervisor.templ')

    put(config_file, '/etc/supervisor/conf.d/', use_sudo=True)
    local('rm {config}'.format(config=config_file))

    sudo('supervisorctl reread')
    sudo('supervisorctl update')


@task
def setup():
    # add current user to www-data group
    sudo('usermod -a -G www-data $USER')

    # create project structure
    base_deploy_dir = os.path.dirname(env.deploy_dir)
    sudo('mkdir -p {deploy_dir}'.format(**env))
    sudo('chown -R "{user}:www-data" {base_deploy_dir}'.format(user=env.user, base_deploy_dir=base_deploy_dir))
    sudo('chmod 2750 {base_deploy_dir}'.format(base_deploy_dir=base_deploy_dir))

    # create log structure
    sudo('mkdir -p {log_dir}'.format(**env))
    sudo('chown -R "{user}:www-data" {log_dir}'.format(**env))
    sudo('chmod 2770 {log_dir}'.format(**env))

    # deploy
    deploy()

    # setup
    with cd(env.deploy_dir):
        run('make setup')

    # supervisor
    setup_supervisor()

    # start
    start()


# ----- Update -----

@task
def update():
    deploy()
    with cd(env.deploy_dir):
        run('make update')
    restart()


# ----- Control supervisor -----

@task
def start():
    run('supervisorctl start {supervisor_task}'.format(**env))
    status()


@task
def stop():
    run('supervisorctl stop {supervisor_task}'.format(**env))
    status()


@task
def restart():
    run('supervisorctl restart {supervisor_task}'.format(**env))
    status()


@task
def status():
    run("supervisorctl status")
