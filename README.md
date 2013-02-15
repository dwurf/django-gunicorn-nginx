django-gunicorn-nginx
=====================

Fabric deploy scripts to install django, gunicorn and nginx on a bare metal Linux box

Windows
-------
If you're trying to run this on windows, you need to:
 o Download pycrypto (v2.6) from 
    http://www.voidspace.org.uk/python/modules.shtml#pycrypto
 o Download pywin32 from http://sourceforge.net/projects/pywin32/files/
 o Install both libraries
 o Open a command prompt and run the following

    mkdir C:\tmp\fabric
    cd c:\tmp\fabric
    virtualenv --system-site-packages .
    Scripts\activate.bat
    pip install fabric cuisine fabtools

 o Now place this fabfile in C:\tmp\fabric. 
 o You can now do the following in a command prompt to run the fabfile

    cd c:\tmp\fabric
    Scripts\activate.bat
    fab help

Reference: https://techknowhow.library.emory.edu/blogs/sturnbu/2011/01/26/installing-fabric-windows 

Linux
-----
1. Install dependencies

    sudo apt-get install python-virtualenv python2.7-dev build-essential

2. Set up virtualenv:

    mkdir -p /tmp/fabric && cd /tmp/fabric
    virtualenv .
    . bin/activate
    pip install fabric cuisine fabtools

3. Install fabfile to /tmp/fabric

4. Run

    . bin/activate
    fab help

