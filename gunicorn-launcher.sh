#!/bin/bash

set -e

LOGFILE=/var/log/gunicorn/django.log
LOGDIR=$(dirname $LOGFILE)
test -d $LOGDIR || mkdir -p $LOGDIR

NUM_WORKERS=3
# user/group to run as
USER=django
GROUP=django
cd {project}
source {virtualenv}/bin/activate
exec {virtualenv}/bin/gunicorn_django -w $NUM_WORKERS \
    --user=$USER --group=$GROUP --log-level=debug \
    --log-file=$LOGFILE 2>>$LOGFILE
