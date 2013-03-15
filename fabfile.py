import os
from fabric.api import task, run, env, settings, cd
from fabtools.vagrant import ssh_config, _settings_dict
import fabtools
from fabtools import require
from fabric.contrib import files


@task
def vagrant(name=''):
    config = ssh_config(name)
    extra_args = _settings_dict(config)
    env.update(extra_args)
    env['user'] = 'root'

    env['mysql_user'] = 'root'
    env['mysql_password'] = os.environ.get('MYSQL_PASSWORD', 'password')
    env['redmine_version'] = 'trunk'
    # env['redmine_version'] = 'http://rubyforge.org/frs/download.php/76771/redmine-2.2.3.tar.gz'


def _add_user(*args, **kwargs):
    require.user(*args, **kwargs)
    if 'name' not in kwargs:
        user = args[0]
    else:
        user = kwargs['name']

    if not fabtools.files.is_file('/home/%s/.ssh/authorized_keys' % user):
        run('mkdir -p /home/%s/.ssh/' % user)
        run('cp /root/.ssh/authorized_keys /home/%s/.ssh/' % user)
        run('chown %(user)s:%(user)s /home/%(user)s/.ssh/ -R' % {'user': user})


@task
def upgrade():
    fabtools.deb.update_index()
    fabtools.deb.upgrade()


@task
def install():
    env['redmine_version'] = env.get('redmine_version', 'http://rubyforge.org/frs/download.php/76771/redmine-2.2.3.tar.gz')
    require.deb.packages(['sudo'])

    fabtools.require.system.locale('fr_FR.UTF-8')

    fabtools.deb.update_index()

    env['mysql_user'] = 'root'
    env['mysql_password'] = os.environ.get('MYSQL_PASSWORD', 'password')
    fabtools.deb.preseed_package('mysql-server', {
        'mysql-server/root_password': ('password', env['mysql_password']),
        'mysql-server/root_password_again': ('password', env['mysql_password']),
    })

    require.deb.packages([
        'build-essential',
        'devscripts',
        'locales',
        'apache2',
        'mysql-server',
        'mysql-client',
        'vim',
        'mc',
        'curl',
        'wget',
        'ruby1.8',
        'ruby1.8-dev',
        'supervisor',
        'python-pip',
        'python-dev',
        'subversion',
        'libxslt1-dev',
        'libxml2-dev',
        'libmysqld-dev',
        'libmagick++-dev',
        'libsqlite3-dev'
    ])

    require.deb.nopackages([
        'rubygems',
        'rubygems1.8'
    ])

    _add_user(
        name='redmine',
        password=None,
        shell='/bin/bash'
    )
    require.mysql.user('redmine', 'password')
    require.mysql.database('redmine', owner='redmine')

    with settings(user='redmine'):
        run('mkdir -p ~/gem')
        require.file(
            '/home/redmine/ruby-env',
            contents="""\
export GEM_HOME=~/gem
export RUBYLIB=~/lib
export PATH=~/bin:$GEM_HOME/bin:$PATH
export RAILS_ENV=production
"""
        )
        files.append('/home/redmine/.profile', 'source ~/ruby-env')
        run('wget http://production.cf.rubygems.org/rubygems/rubygems-2.0.3.tgz')
        run('tar xzf rubygems-2.0.3.tgz')
        run('cd rubygems-2.0.3; ruby setup.rb --prefix=~ --no-format-executable')
        run('rm -rf rubygems*')
        run('gem install bundler')
        if env['redmine_version'] == 'trunk':
            run('svn co http://svn.redmine.org/redmine/trunk redmine-trunk')
            run('mv redmine-trunk redmine')
        else:
            run('wget %s' % env['redmine_version'])
            run('tar xzf redmine-*')
            run('mv redmine-* redmine')

        with cd('/home/redmine/redmine/'):
            require.file(
                '/home/redmine/redmine/config/database.yml',
                """\
production:
    adapter: mysql2
    database: redmine
    host: localhost
    socket: /var/run/mysqld/mysqld.sock
    username: redmine
    password: password
    encoding: utf8
    reconnect: true

test:
    adapter: sqlite3
    database: db/redmine.db
"""
            )
            require.file(
                '/home/redmine/redmine/config/thin.conf',
                """\
daemonize: false
chdir: /home/redmine/redmine
pid: tmp/pids/thin.pid
log: log/thin.log
prefix: /
environment: production
"""
            )
            run('chmod 0600 config/database.yml')
            files.append('/home/redmine/redmine/Gemfile', 'gem "thin"')
            run('bundle install --without sqlite postgresql')
            run('rake generate_secret_token')
            run('rake db:migrate')
            run('rake redmine:load_default_data REDMINE_LANG=en')

    require.file(
        '/etc/supervisor/conf.d/redmine.conf',
        """\
[program:redmine]
process_name=%(program_name)s_%(process_num)02d
directory=/home/redmine/redmine/
user=redmine
numprocs=2
autostart=true
autorestart=true
startsecs=10
redirect_stderr=true
stdout_logfile=/var/log/supervisor/redmine-thin.log
command=/home/redmine/gem/bin/thin -C config/thin.conf -p 30%(process_num)02d start
environment=GEM_HOME='/home/redmine/gem',RUBYLIB='/home/redmine/lib',RAILS_ENV='production'
"""
    )
    run('supervisorctl reload')

    run('a2dissite default')
    require.file(
        '/etc/apache2/sites-available/redmine.conf',
        """\
<VirtualHost *:80>
    ServerName redmine.example.com

    Redirect / https://redmine.example.com/
</VirtualHost>
<VirtualHost *:443>
    ServerName redmine.example.com

    DocumentRoot /home/redmine/redmine/public/

    SSLEngine On
    SSLCertificateFile /etc/ssl/localcerts/apache.pem
    SSLCertificateKeyFile /etc/ssl/localcerts/apache.key

    <Proxy *>
        Order allow,deny
        Allow from all
    </Proxy>

    ProxyPreserveHost On
    ProxyTimeout 30

    <Proxy balancer://redmine_app>
        BalancerMember http://localhost:3000 max=1
        BalancerMember http://localhost:3001 max=1
        ProxySet maxattempts=3
        Allow from all
    </Proxy>

    RewriteEngine On
    RewriteCond %{LA-U:REQUEST_FILENAME} !-f
    RewriteRule ^(.*) balancer://redmine_app/$1 [P,L]

    RequestHeader set X_FORWARDED_PROTO 'https'
</VirtualHost>
""")
    run('a2ensite redmine.conf')
    run('a2enmod proxy')
    run('a2enmod proxy_http')
    run('a2enmod rewrite')
    run('a2enmod headers')
    run('a2enmod ssl')
    run('a2enmod proxy_balancer')

    if not fabtools.files.is_file('/etc/ssl/localcerts/apache.key'):
        require.file(
            '/tmp/openssl.cnf',
            """\
[ req ]
prompt = no
distinguished_name = req_distinguished_name

[ req_distinguished_name ]
C = FR
ST = French
L = Pars
O = Example
OU = Org Unit Name
CN = Common Name
emailAddress = contact@example.com
"""
        )
        run('mkdir -p /etc/ssl/localcerts')
        run('openssl req -config /tmp/openssl.cnf -new -x509 -days 365 -nodes -out /etc/ssl/localcerts/apache.pem -keyout /etc/ssl/localcerts/apache.key')
        run('rm /tmp/openssl.cnf')

    run('pip install mercurial')

    run('/etc/init.d/apache2 force-reload')
