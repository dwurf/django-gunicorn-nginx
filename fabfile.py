r"""
fabfile for installing Django/nginx/gunicorn onto a fresh Linux server
"""

from fabric.api import local, settings, abort, run, cd, sudo
from fabric.contrib.console import confirm
from cuisine import select_package, package_ensure
from cuisine import command_check, command_ensure
from cuisine import user_ensure, group_ensure, group_user_ensure
from cuisine import dir_ensure, dir_attribs 
from cuisine import file_link
from cuisine import mode_sudo
from fabtools import require
import os

def help():
    print """Usage:

fab install_django - fab will prompt you for a connection string 
                     (user@hostname.com). It will then SSH to that box and 
                     install django, nginx and gunicorn. DANGER: Only do 
                     this on a clean install!
"""

def install_django():
    installer = InstallDjango()
    #installer.user_name = r'ec2_user'

    installer.run()


## =========
class UtilClass(object):
    def __init__(self):
        self.distro = run(r'lsb_release -si')

    def get_package_manager(self):
        # TODO: test on a wider variety of platforms
        if self.distro in ('Ubuntu', 'Debian'):
            return 'apt'
        elif self.distro in ('Fedora'):
            return 'yum'
        else:
            raise EnvironmentError('Unknown distribution')

class InstallDjango(object):
    def __init__(self):
        self.user_name = 'django'
        self.group_name = 'django'

        self.www_dir = r'/var/www/django'
        self.repo_dir = r'/var/repo/django_project'
        self.repo_django_root = r'/'
        self.virtualenv_dir = r'/var/venv/django'
        self.repo_url = r'https://github.com/django/djangoproject.com'

        self.vcs = 'git'

        self.util = UtilClass()

    def run(self):
        """
        Do a complete install
        """
        self.install_prereqs()
        self.create_user()
        self.checkout_project()
        self.create_virtualenv()
        self.create_symlink()
        self.install_nginx()
        self.install_gunicorn()
        self.run_tests()

    def install_prereqs(self):
        select_package(self.util.get_package_manager())

        vcs_to_pkg = {
            'git': 'git',
            'hg': 'mercurial',
        }
        package_ensure(vcs_to_pkg[self.vcs])

        command_ensure('python2.7')

        if not command_check('virtualenv'):
            package_ensure('python-virtualenv')

    def create_user(self):
        user_ensure(self.user_name)
        group_ensure(self.group_name)
        group_user_ensure(self.user_name, self.group_name)

    def checkout_project(self):
        # TODO: raise bug
        # workaround for bug: dir_ensure doesn't use mkdir -p
        sudo('mkdir -p "%s"' % self.repo_dir)
        with mode_sudo():
            dir_ensure(self.repo_dir, 
                owner=self.user_name,
                group=self.group_name)
        with cd(self.repo_dir):
            sudo(r'chown %s:%s .' % (self.user_name, self.group_name))
            sudo(r'ls -d * > /dev/null 2>&1 || %s clone -q %s .' 
                    % (self.vcs, self.repo_url), 
                user=self.user_name)

    def create_virtualenv(self):
        # workaround for bug: dir_ensure doesn't use mkdir -p
        sudo('mkdir -p "%s"' % self.virtualenv_dir)
        with mode_sudo():
            dir_ensure(self.virtualenv_dir,
                owner=self.user_name,
                group=self.group_name)
        with cd(self.virtualenv_dir):
            # TODO: don't re-virtualenv if not necessary
            sudo(r'virtualenv .', user=self.user_name)
            # TODO: install all requirements.txt
            #sudo(r'pip install -r %s', user=self.user_name)

    def create_symlink(self):
        (basedir, symlink_location) = self.www_dir.rsplit(os.sep, 1)
        # workaround for bug: dir_ensure doesn't use mkdir -p
        sudo('mkdir -p "%s"' % basedir)
        with cd(basedir):
            with mode_sudo():
                file_link(
                    os.sep.join((
                        self.repo_dir, 
                        self.repo_django_root
                    )),
                    symlink_location)

    def install_nginx(self):
        require.nginx.proxied_site('example.com',
            docroot=self.www_dir,
            proxy_url='http://localhost:8000')

    def install_gunicorn(self):
        # TODO pip install, runner script, gevent
        pass

    def run_tests(self):
        # TODO
        pass

