# -*- test-case-name: twisted.scripts.test.test_tap2deb -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import os
import sys
import shutil
import subprocess
from email.utils import formatdate as now

from twisted.python import usage
from twisted.python.filepath import FilePath


class MyOptions(usage.Options):
    optFlags = [["unsigned", "u"]]
    optParameters = [["tapfile", "t", "twistd.tap"],
                  ["maintainer", "m", "", "The maintainer's name and email in a specific format: "
                   "'John Doe <johndoe@example.com>'"],
                  ["protocol", "p", ""],
                  ["description", "e", ""],
                  ["long_description", "l", ""],
                  ["set-version", "V", "1.0"],
                  ["debfile", "d", None],
                  ["type", "y", "tap", "type of configuration: 'tap', 'xml, 'source' or 'python' for .tac files"]]

    compData = usage.Completions(
        optActions={
            "type": usage.CompleteList(["tap", "xml", "source", "python"]),
            "debfile": usage.CompleteFiles("*.deb")}
        )

    def postOptions(self):
        if not self["maintainer"]:
            raise usage.UsageError("maintainer must be specified.")


type_dict = {
    'tap': 'file',
    'python': 'python',
    'source': 'source',
    'xml': 'xml',
}



def run(options=None):
    try:
        config = MyOptions()
        config.parseOptions(options)
    except usage.error as ue:
        sys.exit("%s: %s" % (sys.argv[0], ue))

    tap_file = config['tapfile']
    base_tap_file = os.path.basename(config['tapfile'])
    protocol = (config['protocol'] or os.path.splitext(base_tap_file)[0])
    deb_file = config['debfile'] or 'twisted-' + protocol
    version = config['set-version']
    maintainer = config['maintainer']
    description = config['description'] or ('A Twisted-based server for %(protocol)s' %
                                            vars())
    long_description = config['long_description'] or 'Automatically created by tap2deb'
    twistd_option = type_dict[config['type']]
    date = now()
    directory = deb_file + '-' + version
    python_version = '%s.%s' % sys.version_info[:2]
    buildDir = FilePath('.build').child(directory)

    if buildDir.exists():
        buildDir.remove()

    debianDir = buildDir.child('debian')
    debianDir.child('source').makedirs()
    shutil.copy(tap_file, buildDir.path)

    debianDir.child('README.Debian').setContent(
    '''This package was auto-generated by tap2deb\n''')

    debianDir.child('conffiles').setContent(
    '''\
/etc/init.d/%(deb_file)s
/etc/default/%(deb_file)s
/etc/%(base_tap_file)s
''' % vars())

    debianDir.child('default').setContent(
    '''\
pidfile=/var/run/%(deb_file)s.pid
rundir=/var/lib/%(deb_file)s/
file=/etc/%(tap_file)s
logfile=/var/log/%(deb_file)s.log
 ''' % vars())

    debianDir.child('init.d').setContent(
    '''\
#!/bin/sh

PATH=/sbin:/bin:/usr/sbin:/usr/bin

pidfile=/var/run/%(deb_file)s.pid \
rundir=/var/lib/%(deb_file)s/ \
file=/etc/%(tap_file)s \
logfile=/var/log/%(deb_file)s.log

[ -r /etc/default/%(deb_file)s ] && . /etc/default/%(deb_file)s

test -x /usr/bin/twistd%(python_version)s || exit 0
test -r $file || exit 0
test -r /usr/share/%(deb_file)s/package-installed || exit 0


case "$1" in
    start)
        echo -n "Starting %(deb_file)s: twistd"
        start-stop-daemon --start --quiet --exec /usr/bin/twistd%(python_version)s -- \
                          --pidfile=$pidfile \
                          --rundir=$rundir \
                          --%(twistd_option)s=$file \
                          --logfile=$logfile
        echo "."	
    ;;

    stop)
        echo -n "Stopping %(deb_file)s: twistd"
        start-stop-daemon --stop --quiet  \
            --pidfile $pidfile
        echo "."	
    ;;

    restart)
        $0 stop
        $0 start
    ;;

    force-reload)
        $0 restart
    ;;

    *)
        echo "Usage: /etc/init.d/%(deb_file)s {start|stop|restart|force-reload}" >&2
        exit 1
    ;;
esac

exit 0
''' % vars())

    debianDir.child('init.d').chmod(0755)

    debianDir.child('postinst').setContent(
    '''\
#!/bin/sh
update-rc.d %(deb_file)s defaults >/dev/null
invoke-rc.d %(deb_file)s start
''' % vars())

    debianDir.child('prerm').setContent(
    '''\
#!/bin/sh
invoke-rc.d %(deb_file)s stop
''' % vars())

    debianDir.child('postrm').setContent(
    '''\
#!/bin/sh
if [ "$1" = purge ]; then
        update-rc.d %(deb_file)s remove >/dev/null
fi
''' % vars())

    debianDir.child('changelog').setContent(
    '''\
%(deb_file)s (%(version)s) unstable; urgency=low

  * Created by tap2deb

 -- %(maintainer)s  %(date)s

''' % vars())

    debianDir.child('control').setContent(
    '''\
Source: %(deb_file)s
Section: net
Priority: extra
Maintainer: %(maintainer)s
Build-Depends-Indep: debhelper
Standards-Version: 3.5.6

Package: %(deb_file)s
Architecture: all
Depends: python%(python_version)s-twisted
Description: %(description)s
 %(long_description)s
''' % vars())

    debianDir.child('compat').setContent(
    '''\
7
''' % vars())

    debianDir.child('copyright').setContent(
    '''\
This package was auto-debianized by %(maintainer)s on
%(date)s

It was auto-generated by tap2deb

Upstream Author(s): 
Moshe Zadka <moshez@twistedmatrix.com> -- tap2deb author

Copyright:

Insert copyright here.
''' % vars())

    debianDir.child('dirs').setContent(
    '''\
etc/init.d
etc/default
var/lib/%(deb_file)s
usr/share/doc/%(deb_file)s
usr/share/%(deb_file)s
''' % vars())

    debianDir.child('source').child('format').setContent(
    '''\
3.0 (native)
''' % vars())

    debianDir.child('rules').setContent(
    '''\
#!/usr/bin/make -f

export DH_COMPAT=1

build: build-stamp
build-stamp:
	dh_testdir
	touch build-stamp

clean:
	dh_testdir
	dh_testroot
	rm -f build-stamp install-stamp
	dh_clean

install: install-stamp
install-stamp: build-stamp
	dh_testdir
	dh_testroot
	dh_clean -k
	dh_installdirs

	# Add here commands to install the package into debian/tmp.
	cp %(base_tap_file)s debian/tmp/etc/
	cp debian/init.d debian/tmp/etc/init.d/%(deb_file)s
	cp debian/default debian/tmp/etc/default/%(deb_file)s
	cp debian/copyright debian/tmp/usr/share/doc/%(deb_file)s/
	cp debian/README.Debian debian/tmp/usr/share/doc/%(deb_file)s/
	touch debian/tmp/usr/share/%(deb_file)s/package-installed
	touch install-stamp

binary-arch: build install

binary-indep: build install
	dh_testdir
	dh_testroot
	dh_strip
	dh_compress
	dh_installchangelogs
	dh_fixperms
	dh_installdeb
	dh_shlibdeps
	dh_gencontrol
	dh_md5sums
	dh_builddeb

source diff:                                                                  
	@echo >&2 'source and diff are obsolete - use dpkg-source -b'; false

binary: binary-indep binary-arch
.PHONY: build clean binary-indep binary-arch binary install
''' % vars())

    debianDir.child('rules').chmod(0755)
    os.chdir(buildDir.path)

    args = ["dpkg-buildpackage", "-rfakeroot"]
    if config['unsigned']:
        args = args + ['-uc', '-us']

    # Build deb
    job = subprocess.Popen(args, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    stdout, _ = job.communicate()

