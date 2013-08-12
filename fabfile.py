r"""
fabfile for installing Django/nginx/gunicorn onto a fresh Linux server
"""

from fabric.api import local, settings, abort, cd
from fabric import operations
from fabric.contrib.console import confirm
from fabric.contrib.files import sed
from cuisine import run, sudo
from cuisine import select_package, package_ensure
from cuisine import command_check, command_ensure
from cuisine import user_ensure, user_remove
from cuisine import group_ensure, group_user_ensure
from cuisine import dir_ensure, dir_attribs, dir_remove, dir_exists
from cuisine import file_ensure, file_attribs, file_exists
from cuisine import file_link, file_is_link
from cuisine import mode_sudo
from cuisine import upstart_ensure
from cuisine import python_package_ensure_pip
from fabtools import require
import os

def help():
    print """Usage:

fab install_django - fab will prompt you for a connection string 
                     (user@hostname.com). It will then SSH to that box and 
                     install django, nginx and gunicorn. DANGER: Only do 
                     this on a clean install!

fab uninstall_django - fab will prompt you for a connection string 
                       (user@hostname.com). It will then SSH to that box and 
                       attempt to uninstall the previously installed django.
                       Note: all directories created by the installer will be
                       destroyed!
"""

def install_django():
    installer = InstallDjango()
    #installer.user_name = r'ec2_user'

    installer.run()

def uninstall_django():
    installer = UninstallDjango()

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

class InstallerBase(object):
    def __init__(self):
        self.user_name = 'django'
        self.group_name = 'django'

        self.www_dir = r'/var/www/django'
        self.repo_dir = r'/var/repo/django-chinook'
        self.repo_django_root = r'/'
        self.django_requirements_txt = r'local-requirements.txt'
        self.virtualenv_dir = r'/var/venv/django'
        self.repo_url = r'https://bitbucket.org/xeoscript/django-chinook.git'

        self.vcs = 'git'

        # required by fabric, a dependency of this particular django install
        self.install_packages = ['python-dev', 'build-essential'] 

        self.util = UtilClass()


class InstallDjango(InstallerBase):

    def run(self):
        """
        Do a complete install
        """
        #self.upgrade_system()
        self.install_prereqs()
        self.create_user()
        self.checkout_project()
        self.create_virtualenv()
        self.create_symlink()
        self.install_nginx()
        self.install_gunicorn()
        self.run_tests()

    def run_virtualenv(self, command):
        with cd(self.virtualenv_dir):
            sudo('. bin/activate && ' + command,
                user=self.user_name)

    def upgrade_system(self):
        if self.util.get_package_manager() == 'apt':
            sudo(r'apt-get -q update && apt-get -qy upgrade')
        elif self.util.get_package_manager() == 'yum':
            # TODO: untested
            sudo(r'yum update && yum upgrade')

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

        for pkg in self.install_packages:
            package_ensure(pkg)

    def create_user(self):
        user_ensure(self.user_name)
        group_ensure(self.group_name)
        group_user_ensure(self.user_name, self.group_name)

    def checkout_project(self):
        with mode_sudo():
            dir_ensure(self.repo_dir, 
                owner=self.user_name,
                group=self.group_name,
                recursive=True,
                )
        with cd(self.repo_dir):
            sudo(r'chown %s:%s .' % (self.user_name, self.group_name))
            sudo(r'ls -d * > /dev/null 2>&1 || %s clone -q %s .' 
                    % (self.vcs, self.repo_url), 
                user=self.user_name)

    def create_virtualenv(self):
        with mode_sudo():
            dir_ensure(self.virtualenv_dir,
                owner=self.user_name,
                group=self.group_name,
                recursive=True,
                )
            with cd(self.virtualenv_dir):
                run('[[ -f bin/activate ]] || virtualenv .',
                    user=self.user_name)
                python_package_ensure_pip(r=os.sep.join((
                    self.repo_dir,
                    self.repo_django_root,
                    self.django_requirements_txt
                )))

    def create_symlink(self):
        (basedir, symlink_location) = self.www_dir.rsplit('/', 1)
        with mode_sudo():
            dir_ensure(basedir,
                recursive=True,
                )
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
        self.run_virtualenv('pip -q install gunicorn')

        with mode_sudo():
            dir_ensure('/var/log/gunicorn/',
                owner=self.user_name,
                group=self.group_name,
                )

        if self.util.get_package_manager() == 'apt':
            operations.put(
                'gunicorn.conf', 
                '/etc/init/', 
                use_sudo=True, mode=644)
            with mode_sudo():
                file_attribs('/etc/init/gunicorn.conf',
                    mode=700,
                    owner='root',
                    group='root',
                    )
                with settings(warn_only=True):
                    sed('/etc/init/gunicorn.conf', 
                        '\{virtualenv\}', 
                        self.virtualenv_dir,
                        use_sudo = True,
                        )

        operations.put(
            'gunicorn-launcher.sh', 
            self.virtualenv_dir + '/bin/', 
            use_sudo=True, mode=750)
        with mode_sudo():
            file_attribs(self.virtualenv_dir + '/bin/gunicorn-launcher.sh',
                mode=700,
                owner=self.user_name,
                group=self.group_name,
                )
            with settings(warn_only=True):
                sed(self.virtualenv_dir + '/bin/gunicorn-launcher.sh', 
                    '\{virtualenv\}', 
                    self.virtualenv_dir,
                    use_sudo = True,
                    )
                sed(self.virtualenv_dir + '/bin/gunicorn-launcher.sh', 
                    '\{project\}', 
                    self.www_dir,
                    use_sudo = True,
                    )


        # install gevent. This is non-critical and might fail so we go to
        # warn-only mode 
        with settings(warn_only=True):
            package_ensure('libevent-dev')
            self.run_virtualenv('pip -q install gevent')
        
        #   # TODO: add -k gevent to gunicorn launcher script

        # TODO
        upstart_ensure('gunicorn')

    def run_tests(self):
        # TODO
        pass

class UninstallDjango(InstallerBase):
    def run(self):
        """
        Remove all files and directories
        """
        self.uninstall_gunicorn()
        self.remove_symlink()
        self.remove_project()
        self.remove_user()

    def uninstall_gunicorn(self):
        with mode_sudo():
            with settings(warn_only=True):
                dir_remove('/var/log/gunicorn', recursive = True)
                if (self.virtualenv_dir and 
                    file_exists(self.virtualenv_dir + '/bin/activate')
                    ):
                    dir_remove(self.virtualenv_dir, recursive = True)
                if self.util.get_package_manager() == 'apt':
                    dir_remove('/etc/init/gunicorn.conf') 

    def remove_symlink(self):
        (basedir, symlink_location) = self.www_dir.rsplit('/', 1)
        with settings(warn_only=True):
            if file_is_link(self.www_dir):
                with mode_sudo():
                    dir_remove(self.www_dir, recursive = True)

    def remove_project(self):
        with settings(warn_only=True):
            if dir_exists('%s/.%s' % (self.repo_dir, self.vcs)):
                with mode_sudo():
                    dir_remove(self.repo_dir, recursive=True,)

    def remove_user(self):
        with settings(warn_only=True):
            user_remove(self.user_name, rmhome = True)
            #group_remove(self.user_name)
            # Group_remove not in the cuisine version currently in pip

