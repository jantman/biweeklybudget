.. _docker:

Docker
======

Biweeklybudget is also distributed as a `docker image <https://hub.docker.com/r/jantman/biweeklybudget/>`_,
to make it easier to run without installing as many :ref:`Requirements <_getting_started.requirements>`.

You can pull the latest version of the image with ``docker pull jantman/biweeklybudget:latest``, or
a specific release version ``X.Y.Z`` with ``docker pull jantman/biweeklybudget:X.Y.Z``.

The only dependencies for a Docker installation are:

* MySQL, which can be run via Docker (`MariaDB <https://hub.docker.com/_/mariadb/>`_ recommended) or local on the host
* Vault, if you wish to use the OFX downloading feature, which can also be run `via Docker <https://hub.docker.com/_/vault/>`_

**Important Note:** If you run MySQL and/or Vault in containers, please make sure that their data
is backed up and will not be removed.

The `image <https://hub.docker.com/r/jantman/biweeklybudget/>`_ runs with the `tini <https://github.com/krallin/tini>`_ init
wrapper and uses `gunicorn <http://gunicorn.org/>`_ under Python 3.6 to serve the web UI, exposed on port 80. Note that,
while it runs with 4 worker threads, there is no HTTP proxy in front of Gunicorn and this image is intended for local network
use by a single user/client.

For ease of running, the image defaults the ``SETTINGS_MODULE`` environment variable to
``biweeklybudget.settings_example``. This allows leveraging the environment variable
:ref:`configuration <_getting_started.configuration>` overrides so that you need only
specify configuration options that you want to override from
`settings_example.py <https://github.com/jantman/biweeklybudget/blob/master/biweeklybudget/settings_example.py>`_.

For ease of running, it's highly recommended that you put your configuration in a Docker-readable
environment variables file.

Environment Variable File
-------------------------

In the following examples, we reference the following environment variable file.
It will override settings from `settings_example.py <https://github.com/jantman/biweeklybudget/blob/master/biweeklybudget/settings_example.py>`_
as needed; specifically, we need to override the database connection string,
pay period start date and reconcile begin date. In the examples below, we would
save this as ``biweeklybudget.env``:

```
DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DBNAME?charset=utf8mb4
PAY_PERIOD_START_DATE=2017-03-28
RECONCILE_BEGIN_DATE=2017-02-15
```

Containerized MySQL Example
---------------------------

This assumes that you already have a MySQL database container running with the
container name "mysql" and exposing port 3306, and that we want the biweeklybudget
web UI served on host port 8080:

In our ``biweeklybudget.env``, we would specify the database connection string for the "mysql" container:

```
DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@mysql:3306/DBNAME?charset=utf8mb4
```

And then run biweeklybudget:

```
docker run --name biweeklybudget --env-file biweeklybudget.env \
  -p 8080:80 --link mysql jantman/biweeklybudget:latest
```

Host-Local MySQL Example
------------------------

It is also possible to use a MySQL server on the physical (Docker) host system. To do so,
you'll need to know the host system's IP address. On Linux when using the default "bridge"
Docker networking mode, this will coorespond to a ``docker0`` interface on the host system.
The Docker documentation on `adding entries to the Container's hosts file <https://docs.docker.com/engine/reference/commandline/run/#add-entries-to-container-hosts-file---add-host>`_
provides a helpful snippet for this (on my systems, this results in ``172.17.0.1``):

```
ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1
```

In our ``biweeklybudget.env``, we would specify the database connection string that uses the "dockerhost" hosts file entry, created by the ``--add-host`` option:

```
# "dockerhost" is added to /etc/hosts via the `--add-host` docker run option
DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@dockerhost:3306/DBNAME?charset=utf8mb4
```

So using that, we could run biweeklybudget listening on port 8080 and using our host's MySQL server (on port 3306):

```
docker run --name biweeklybudget --env-file biweeklybudget.env \
  --add-host="dockerhost:$(ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1)" \
  -p 8080:80 jantman/biweeklybudget:latest
```

You may need to adjust those commands depending on your operating system, Docker networking mode, and MySQL server.

Settings Module Example
-----------------------

If you need to provide biweeklybudget with more complicated configuration, this is
still possible via a Python settings module. The easiest way to inject one into the
Docker image is to `mount <https://docs.docker.com/engine/reference/commandline/run/#mount-volume--v---read-only>`_
a python module directly into the biweeklybudget package directory. Assuming you have
a custom settings module on your local machine at ``/opt/biweeklybudget-settings.py``, you would
run the container as shown below to mount the custom settings module into the container and use it.
Note that this example assumes using MySQL in another container; adjust as necessary if you are using
MySQL running on the Docker host:

```
docker run --name biweeklybudget -e SETTINGS_MODULE=biweeklybudget.mysettings \
  -v /opt/biweeklybudget-settings.py:/app/lib/python3.6/site-packages/biweeklybudget/mysettings.py \
  -p 8080:80 --link mysql jantman/biweeklybudget:latest
```

Note on Locales
---------------

biweeklybudget uses Python's `locale <https://docs.python.org/3.6/library/locale.html>`_ module
to format currency. This requires an appropriate locale installed on the system. The docker image
distributed for this package only includes the ``en_US.UTF-8`` locale. If you need a different one,
please cut a pull request against ``docker_build.py``.
