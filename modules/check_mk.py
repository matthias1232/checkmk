#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# This file is also read in by check_mk's web pages. In that case,
# the variable check_mk_web is set to True

import os, sys, socket, time, getopt, glob, re, stat, py_compile, urllib

# These variable will be substituted at 'make dist' time
check_mk_version  = '(inofficial)'

# Some things have to be done before option parsing and might
# want to output some verbose messages.
if __name__ == "__main__":
    opt_verbose      = '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]
    opt_debug        = '--debug' in sys.argv[1:]
else:
    opt_verbose = False
    opt_debug = False

# are we running OMD? If yes, honor local/ hierarchy
omd_root = os.getenv("OMD_ROOT", None)
if omd_root:
    local_share              = omd_root + "/local/share/check_mk"
    local_checks_dir         = local_share + "/checks"
    local_check_manpages_dir = local_share + "/checkman"
    local_agents_dir         = local_share + "/agents"
    local_web_dir            = local_share + "/web"
    local_pnp_templates_dir  = local_share + "/pnp-templates"
    local_pnp_rraconf_dir    = local_share + "/pnp-rraconf"
    local_doc_dir            = omd_root + "/local/share/doc/check_mk"
else:
    local_checks_dir         = None
    local_check_manpages_dir = None
    local_agents_dir         = None
    local_web_dir            = None
    local_pnp_templates_dir  = None
    local_pnp_rraconf_dir    = None
    local_doc_dir            = None



#   +----------------------------------------------------------------------+
#   |        ____       _   _                                              |
#   |       |  _ \ __ _| |_| |__  _ __   __ _ _ __ ___   ___  ___          |
#   |       | |_) / _` | __| '_ \| '_ \ / _` | '_ ` _ \ / _ \/ __|         |
#   |       |  __/ (_| | |_| | | | | | | (_| | | | | | |  __/\__ \         |
#   |       |_|   \__,_|\__|_| |_|_| |_|\__,_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Pathnames, directories   and  other  settings.  All  these  settings
# should be  overriden by  /usr/share/check_mk/modules/defaults, which
# is created by setup.sh. The user might override those values again
# in main.mk

default_config_dir                 = '/etc/check_mk'
check_mk_configdir                 = default_config_dir + "/conf.d"
checks_dir                         = '/usr/share/check_mk/checks'
agents_dir                         = '/usr/share/check_mk/agents'
check_manpages_dir                 = '/usr/share/doc/check_mk/checks'
modules_dir                        = '/usr/share/check_mk/modules'
var_dir                            = '/var/lib/check_mk'
autochecksdir                      = var_dir + '/autochecks'
snmpwalks_dir                      = var_dir + '/snmpwalks'
precompiled_hostchecks_dir         = var_dir + '/precompiled'
counters_directory                 = var_dir + '/counters'
tcp_cache_dir                      = var_dir + '/cache'
rrd_path                           = var_dir + '/rrd'
logwatch_dir                       = var_dir + '/logwatch'
nagios_objects_file                = var_dir + '/check_mk_objects.cfg'
nagios_command_pipe_path           = '/var/log/nagios/rw/nagios.cmd'
www_group                          = None # unset
nagios_startscript                 = '/etc/init.d/nagios'
nagios_binary                      = '/usr/sbin/nagios'
nagios_config_file                 = '/etc/nagios/nagios.cfg'
logwatch_notes_url                 = "/nagios/logwatch.php?host=%s&file=%s"

def verbose(t):
    if opt_verbose:
        sys.stderr.write(t)
        sys.stderr.flush()


# During setup a file called defaults is created in the modules
# directory.  In this file all directories are configured.  We need to
# read in this file first. It tells us where to look for our
# configuration file. In python argv[0] always contains the directory,
# even if the binary lies in the PATH and is called without
# '/'. This allows us to find our directory by taking everying up to
# the first '/'

# Allow to specify defaults file on command line (needed for OMD)
if len(sys.argv) >= 2 and sys.argv[1] == '--defaults':
    defaults_path = sys.argv[2]
    del sys.argv[1:3]
elif __name__ == "__main__":
    defaults_path = os.path.dirname(sys.argv[0]) + "/defaults"

if opt_debug:
    sys.stderr.write("Reading default settings from %s\n" % defaults_path)
try:
    execfile(defaults_path)
except Exception, e:
    sys.stderr.write(("ERROR: Cannot read installation settings of check_mk.\n%s\n\n"+
                      "During setup the file '%s'\n"+
                      "should have been created. Please make sure that that file\n"+
                      "exists, is readable and contains valid Python code.\n") %
                     (e, defaults_path))
    sys.exit(3)

# Now determine the location of the directory containing main.mk. It
# is searched for at several places:
#
# 1. if present - the option '-c' specifies the path to main.mk
# 2. in the default_config_dir (that path should be present in modules/defaults)


if __name__ == "__main__":
    try:
        i = sys.argv.index('-c')
        if i > 0 and i < len(sys.argv)-1:
            check_mk_configfile = sys.argv[i+1]
            parts = check_mk_configfile.split('/')
            if len(parts) > 1:
                check_mk_basedir = check_mk_configfile.rsplit('/',1)[0]
            else:
                check_mk_basedir = "." # no / contained in filename

            if not os.path.exists(check_mk_basedir):
                sys.stderr.write("Directory %s does not exist.\n" % check_mk_basedir)
                sys.exit(1)

            if not os.path.exists(check_mk_configfile):
                sys.stderr.write("Missing configuration file %s.\n" % check_mk_configfile)
                sys.exit(1)
        else:
            sys.stderr.write("Missing argument to option -c.\n")
            sys.exit(1)

    except ValueError:
        if not os.path.exists(default_config_dir + "/main.mk"):
            sys.stderr.write("Missing main configuration file %s/main.mk\n" % default_config_dir)
            sys.exit(4)
        check_mk_basedir = default_config_dir
        check_mk_configfile = check_mk_basedir + "/main.mk"

    except SystemExit, exitcode:
        sys.exit(exitcode)

else:
    check_mk_basedir = default_config_dir
    check_mk_configfile = default_config_dir + "/main.mk"



#   +----------------------------------------------------------------------+
#   |        ____       _     ____        __             _ _               |
#   |       / ___|  ___| |_  |  _ \  ___ / _| __ _ _   _| | |_ ___         |
#   |       \___ \ / _ \ __| | | | |/ _ \ |_ / _` | | | | | __/ __|        |
#   |        ___) |  __/ |_  | |_| |  __/  _| (_| | |_| | | |_\__ \        |
#   |       |____/ \___|\__| |____/ \___|_|  \__,_|\__,_|_|\__|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Before we read the configuration files we create default settings
# for all variables. The user can easily override them.

# define magic keys for use in host extraconf lists
PHYSICAL_HOSTS = [ '@physical' ] # all hosts but not clusters
CLUSTER_HOSTS  = [ '@cluster' ]  # all cluster hosts
ALL_HOSTS      = [ '@all' ]      # physical and cluster hosts
ALL_SERVICES   = [ "" ]          # optical replacement"
NEGATE         = '@negate'       # negation in boolean lists

# Basic Settings
agent_port                         = 6556
tcp_connect_timeout                = 5.0
do_rrd_update                      = False
aggr_summary_hostname              = "%s-s"
agent_min_version                  = 0 # warn, if plugin has not at least version
check_max_cachefile_age            = 0 # per default do not use cache files when checking
cluster_max_cachefile_age          = 90   # secs.
simulation_mode                    = False
perfdata_format                    = "pnp" # also possible: "standard"
debug_log                          = None
monitoring_host                    = "localhost" # your Nagios host
max_num_processes                  = 50

# SNMP communities
snmp_default_community             = 'public'
snmp_communities                   = []

# Inventory and inventory checks
inventory_check_interval           = None # Nagios intervals (4h = 240)
inventory_check_severity           = 1    # warning
inventory_max_cachefile_age        = 120  # secs.
always_cleanup_autochecks          = False

# Nagios templates and other settings concerning generation
# of Nagios configuration files. No need to change these values.
# Better adopt the content of the templates
host_template                      = 'check_mk_host'
cluster_template                   = 'check_mk_cluster'
pingonly_template                  = 'check_mk_pingonly'
active_service_template            = 'check_mk_active'
inventory_check_template           = 'check_mk_inventory'
passive_service_template           = 'check_mk_passive'
passive_service_template_perf      = 'check_mk_passive_perf'
summary_service_template           = 'check_mk_summarized'
service_dependency_template        = 'check_mk'
default_host_group                 = 'check_mk'
generate_hostconf                  = True
generate_dummy_commands            = True
dummy_check_commandline            = 'echo "ERROR - you did an active check on this service - please disable active checks" && exit 1'
nagios_illegal_chars               = '`~!$%^&*|\'"<>?,()='

# Data to be defined in main.mk
checks                               = []
check_parameters                     = []
legacy_checks                        = []
all_hosts                            = []
snmp_hosts                           = [ (['snmp'], ALL_HOSTS) ]
tcp_hosts                            = [ (['tcp'], ALL_HOSTS), (NEGATE, ['snmp'], ALL_HOSTS), (['!ping'], ALL_HOSTS) ]
bulkwalk_hosts                       = []
usewalk_hosts                        = []
ignored_checktypes                   = [] # exclude from inventory
ignored_services                     = [] # exclude from inventory
ignored_checks                       = [] # exclude from inventory
host_groups                          = []
service_groups                       = []
service_contactgroups                = []
service_notification_periods         = []
host_notification_periods            = []
host_contactgroups                   = []
parents                              = []
define_hostgroups                    = None
define_servicegroups                 = None
define_contactgroups                 = None
clusters                             = {}
clustered_services                   = []
clustered_services_of                = {} # new in 1.1.4
datasource_programs                  = []
service_aggregations                 = []
service_dependencies                 = []
non_aggregated_hosts                 = []
aggregate_check_mk                   = False
aggregation_output_format            = "multiline" # new in 1.1.6. Possible also: "multiline"
summary_host_groups                  = []
summary_service_groups               = [] # service groups for aggregated services
summary_service_contactgroups        = [] # service contact groups for aggregated services
summary_host_notification_periods    = []
summary_service_notification_periods = []
ipaddresses                          = {} # mapping from hostname to ipadress
only_hosts                           = None
extra_host_conf                      = {}
extra_summary_host_conf              = {}
extra_service_conf                   = {}
extra_summary_service_conf           = {}
extra_nagios_conf                    = ""
service_descriptions                 = {}
donation_hosts                       = []
donation_command                     = 'mail -r checkmk@yoursite.de  -s "Host donation %s" donatehosts@mathias-kettner.de' % check_mk_version
scanparent_hosts                     = [ ( ALL_HOSTS ) ]

# Settings for filesystem checks (df, df_vms, df_netapp and maybe others)
filesystem_default_levels          = (80, 90)
filesystem_levels                  = []
df_magicnumber_normsize            = 20 # Standard size if 20 GB
df_lowest_warning_level            = 50 # Never move warn level below 50% due to magic factor
df_lowest_critical_level           = 60 # Never move crit level below 60% due to magic factor

# This is obsolete stuff and should be moved to the check plugins some day
inventory_df_exclude_fs            = [ 'nfs', 'smbfs', 'cifs', 'iso9660' ]
inventory_df_exclude_mountpoints   = [ '/dev' ]
inventory_df_check_params          = 'filesystem_default_levels'

# global variables used to cache temporary values (not needed in check_mk_base)
ip_to_hostname_cache = None

# The following data structures will be filled by the various checks
# found in the checks/ directory.
check_info                         = {} # all known checks
precompile_params                  = {} # optional functions for parameter precompilation, look at df for an example
check_config_variables             = [] # variables (names) in checks/* needed for check itself
snmp_info                          = {} # whichs OIDs to fetch for which check (for tabular information)
snmp_info_single                   = {} # similar, but for single SNMP variables (MIB-Name BASE-OID List-of-Suffixes)
snmp_scan_functions                = {} # SNMP autodetection


# Now include the other modules. They contain everything that is needed
# at check time (and many of that is also needed at administration time).
try:
    for module in [ 'check_mk_base', 'snmp' ]:
        filename = modules_dir + "/" + module + ".py"
        execfile(filename)

except Exception, e:
    sys.stderr.write("Cannot read file %s: %s\n" % (filename, e))
    sys.exit(5)



#   +----------------------------------------------------------------------+
#   |     ____ _               _      _          _                         |
#   |    / ___| |__   ___  ___| | __ | |__   ___| |_ __   ___ _ __ ___     |
#   |   | |   | '_ \ / _ \/ __| |/ / | '_ \ / _ \ | '_ \ / _ \ '__/ __|    |
#   |   | |___| | | |  __/ (__|   <  | | | |  __/ | |_) |  __/ |  \__ \    |
#   |    \____|_| |_|\___|\___|_|\_\ |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                                             |_|                      |
#   |                                                                      |
#   | These functions are used by some checks at administration time.      |
#   +----------------------------------------------------------------------+

# The function no_inventory_possible is as stub function used for
# those checks that do not support inventory. It must be known before
# we read in all the checks
def no_inventory_possible(checkname, info):
    sys.stderr.write("Sorry. No inventory possible for check type %s.\n" % checkname)
    sys.exit(3)

def lookup_filesystem_levels(host, mountpoint):
    levels = service_extra_conf(host, mountpoint, filesystem_levels)
    # may return 0, 1 or more answers
    if len(levels) == 0:
        return filesystem_default_levels
    else:
        return levels[0]

def precompile_filesystem_levels(host, item, params):
    if  params is filesystem_default_levels:
        params = lookup_filesystem_levels(host, item)
    return params


#   +----------------------------------------------------------------------+
#   |       _                    _        _               _                |
#   |      | |    ___   __ _  __| |   ___| |__   ___  ___| | _____         |
#   |      | |   / _ \ / _` |/ _` |  / __| '_ \ / _ \/ __| |/ / __|        |
#   |      | |__| (_) | (_| | (_| | | (__| | | |  __/ (__|   <\__ \        |
#   |      |_____\___/ \__,_|\__,_|  \___|_| |_|\___|\___|_|\_\___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values. The user can override those variables in his configuration.
# Do not read in the checks if check_mk is called as module

if __name__ == "__main__":
    filelist = glob.glob(checks_dir + "/*")
    if local_checks_dir:
        filelist += glob.glob(local_checks_dir + "/*")
    for f in filelist: 
        if not f.endswith("~"): # ignore emacs-like backup files
            try:
                execfile(f)
            except Exception, e:
                sys.stderr.write("Error in plugin file %s: %s\n" % (f, e))
                if opt_debug:
                    raise
                sys.exit(5)


#   +----------------------------------------------------------------------+
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def have_perfdata(checkname):
    return check_info[checkname][2]

def output_check_info():
    print "Available check types:"
    print
    print "                      plugin   perf-  in- "
    print "Name                  type     data   vent.  service description"
    print "-------------------------------------------------------------------------"

    checks_sorted = check_info.items()
    checks_sorted.sort()
    for check_type, info in checks_sorted:
        try:
            func, itemstring, have_perfdata, invfunc = info
            if have_perfdata == 1:
                p = tty_green + tty_bold + "yes" + tty_normal
            else:
                p = "no"
            if invfunc == no_inventory_possible:
                i = "no"
            else:
                i = tty_blue + tty_bold + "yes" + tty_normal

            if check_uses_snmp(check_type):
                typename = tty_magenta + "snmp" + tty_normal
            else:
                typename = tty_yellow + "tcp " + tty_normal

            print (tty_bold + "%-19s" + tty_normal + "   %s     %-3s    %-3s    %s") % \
                  (check_type, typename, p, i, itemstring)
        except Exception, e:
            sys.stderr.write("ERROR in check_type %s: %s\n" % (check_type, e))



#   +----------------------------------------------------------------------+
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+

def strip_tags(host_or_list):
    if type(host_or_list) == list:
        return [ strip_tags(h) for h in host_or_list ]
    else:
        return host_or_list.split("|")[0]

def tags_of_host(hostname):
    return hosttags.get(hostname, [])

# Check if a host fullfills the requirements of a tags
# list. The host must have all tags in the list, except
# for those negated with '!'. Those the host must *not* have!
def hosttags_match_taglist(hosttags, required_tags):
    for tag in required_tags:
        if len(tag) > 0 and tag[0] == '!':
            negate = True
            tag = tag[1:]
        else:
            negate = False
        if (tag in hosttags) == negate:
            return False
    return True

#   +----------------------------------------------------------------------+
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   +----------------------------------------------------------------------+

# Checks if a host has service aggregations
def host_is_aggregated(hostname):
    if not service_aggregations:
        return False

    # host might by explicitely configured as not aggregated
    if in_binary_hostlist(hostname, non_aggregated_hosts):
        return False

    # convert into host_conf_list suitable for host_extra_conf()
    host_conf_list = [ entry[:-1] for entry in service_aggregations ]
    is_aggr = len(host_extra_conf(hostname, host_conf_list)) > 0
    return is_aggr

# Determines the aggretated service name for a given
# host and service description. Returns "" if the service
# is not aggregated
def aggregated_service_name(hostname, servicedesc):
    if not service_aggregations:
        return ""

    for entry in service_aggregations:
        if len(entry) == 3:
            aggrname, hostlist, pattern = entry
            tags = []
        elif len(entry) == 4:
            aggrname, tags, hostlist, pattern = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service_aggregations: must have 3 or 4 entries" % entry)

        if len(hostlist) == 1 and hostlist[0] == "":
            sys.stderr.write('WARNING: deprecated hostlist [ "" ] in service_aggregations. Please use all_hosts instead\n')

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
            if type(pattern) != str:
                raise MKGeneralException("Invalid entry '%r' in service_aggregations:\n "
                                         "service specification must be a string, not %s.\n" %
                                         (entry, pattern))
            matchobject = re.search(pattern, servicedesc)
            if matchobject:
                try:
                    item = matchobject.groups()[-1]
                    return aggrname % item
                except:
                    return aggrname
    return ""


#   +----------------------------------------------------------------------+
#   |                      ____  _   _ __  __ ____                         |
#   |                     / ___|| \ | |  \/  |  _ \                        |
#   |                     \___ \|  \| | |\/| | |_) |                       |
#   |                      ___) | |\  | |  | |  __/                        |
#   |                     |____/|_| \_|_|  |_|_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Returns command lines for snmpwalk and snmpget including
# options for authentication. This handles communities and
# authentication for SNMP V3. Also bulkwalk hosts
def snmp_get_command(hostname):
    return snmp_base_command('get', hostname)

def snmp_walk_command(hostname):
    return snmp_base_command('walk', hostname)

# Constructs the basic snmp commands for a host with all important information
# like the commandname, SNMP version and credentials.
# This function also changes snmpbulkwalk to snmpwalk for snmpv1.
def snmp_base_command(what, hostname):
    # if the credentials are a string, we use that as community,
    # if it is a four-tuple, we use it as V3 auth parameters:
    # (1) security level (-l)
    # (2) auth protocol (-a, e.g. 'md5')
    # (3) security name (-u)
    # (4) auth password (-A)
    # And if it is a six-tuple, it has the following additional arguments:
    # (5) privacy protocol (DES|AES) (-x)  
    # (6) privacy protocol pass phrase (-X) 

    credentials = snmp_credentials_of(hostname)
    if what == 'get':
        command = 'snmpget'
    else:
        command = 'snmpbulkwalk'

    # Handle V1 and V2C
    if type(credentials) == str:
        if is_bulkwalk_host(hostname):
            options = '-v2c'
        else:
            options = '-v1'
            if what == 'walk':
                command = 'snmpwalk'
        options += " -c '%s'" % credentials

        # Handle V3
    else:
        if len(credentials) == 6:
           options = "-v3 -l '%s' -a '%s' -u '%s' -A '%s' -x '%s' -X '%s'" % tuple(credentials)
        elif len(credentials) == 4:
           options = "-v3 -l '%s' -a '%s' -u '%s' -A '%s'" % tuple(credentials)
        else:
            raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be string, 4-tuple or 6-tuple" % (credentials, hostname))

    # Do not load *any* MIB files. This save lot's of CPU.
    options += " -m '' -M ''"
    return command + ' ' + options


# Determine SNMP community for a specific host.  It the host is found
# int the map snmp_communities, that community is returned. Otherwise
# the snmp_default_community is returned (wich is preset with
# "public", but can be overridden in main.mk
def snmp_credentials_of(hostname):
    communities = host_extra_conf(hostname, snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community

def check_uses_snmp(check_type):
    check_name = check_type.split(".")[0]
    return snmp_info.has_key(check_name) or snmp_info_single.has_key(check_name)

def is_snmp_host(hostname):
    return in_binary_hostlist(hostname, snmp_hosts)

def is_tcp_host(hostname):
    return in_binary_hostlist(hostname, tcp_hosts)

def is_ping_host(hostname):
    return not is_snmp_host(hostname) and not is_tcp_host(hostname)

def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return in_binary_hostlist(hostname, bulkwalk_hosts)
    else:
        return False

def is_usewalk_host(hostname):
    return in_binary_hostlist(hostname, usewalk_hosts)

def get_single_oid(hostname, ipaddress, oid):
    global g_single_oid_hostname
    global g_single_oid_cache

    if g_single_oid_hostname != hostname:
        g_single_oid_hostname = hostname
        g_single_oid_cache = {}

    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    if opt_use_snmp_walk or is_usewalk_host(hostname):
        walk = get_stored_snmpwalk(hostname, oid)
        if len(walk) == 1:
            return walk[0][1]
        else:
            return None

    command = snmp_get_command(hostname) + \
         " -On -OQ -Oe %s %s 2>/dev/null" % (ipaddress, oid)
    try:
        if opt_verbose:
            sys.stdout.write("Running '%s'\n" % command)

        snmp_process = os.popen(command, "r")
        line = snmp_process.readline().strip()
        item, value = line.split("=")
        value = value.strip()
        if opt_verbose:
            sys.stdout.write("SNMP answer: ==> [%s]\n" % value)
        if value.startswith('No more variables') or value.startswith('End of MIB') \
           or value.startswith('No Such Object available') or value.startswith('No Such Instance currently exists'):
            value = None

        # try to remove text, only keep number
        # value_num = value_text.split(" ")[0]
        # value_num = value_num.lstrip("+")
        # value_num = value_num.rstrip("%")
        # value = value_num
    except:
        value = None

    g_single_oid_cache[oid] = value
    return value

def snmp_scan(hostname, ipaddress):
    if opt_verbose:
        sys.stdout.write("Scanning host %s(%s) for SNMP checks..." % (hostname, ipaddress))
    sys_descr = get_single_oid(hostname, ipaddress, ".1.3.6.1.2.1.1.1.0")
    if sys_descr == None:
        print "no SNMP answer"
        return []

    found = []
    for checktype, detect_function in snmp_scan_functions.items():
        try:
            if detect_function(lambda oid: get_single_oid(hostname, ipaddress, oid)):
                found.append(checktype)
                if opt_verbose:
                    sys.stdout.write(tty_green + tty_bold + checktype + " " + tty_normal)
                    sys.stdout.flush()
        except:
            pass

    # Now try all checks not having a scan function
    for checktype in check_info.keys():
        datatype = checktype.split('.')[0]
        if datatype not in snmp_info:
            continue # no snmp check
        if checktype not in snmp_scan_functions:
            if opt_verbose:
                sys.stdout.write(tty_blue + tty_bold + checktype + tty_normal + " ")
                sys.stdout.flush()
            found.append(checktype)

    if opt_verbose:
        if found == []:
            sys.stdout.write("nothing detected.\n")
        else:
            sys.stdout.write("\n")
    return found


#   +----------------------------------------------------------------------+
#   |                    ____ _           _                                |
#   |                   / ___| |_   _ ___| |_ ___ _ __                     |
#   |                  | |   | | | | / __| __/ _ \ '__|                    |
#   |                  | |___| | |_| \__ \ ||  __/ |                       |
#   |                   \____|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# clusternames (keys into dictionary) might be tagged :-(
# names of nodes not!
def is_cluster(hostname):
    for tagged_hostname, nodes in clusters.items():
        if hostname == strip_tags(tagged_hostname):
            return True
    return False

# If host is node of a cluster, return name of that cluster
# (untagged). If not, return None. If a host belongt to
# more than one cluster, then a random cluster is choosen.
def cluster_of(hostname):
    for clustername, nodes in clusters.items():
        if hostname in nodes:
            return strip_tags(clustername)
    return None

# Determine wether a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    # 1. New style: explicitlely assigned services
    for cluster, conf in clustered_services_of.items():
        if hostname in nodes_of(cluster) and \
            in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
        cluster = cluster_of(hostname)
        if cluster:
            return cluster

    return hostname


#   +----------------------------------------------------------------------+
#   |          _   _           _       _               _                   |
#   |         | | | | ___  ___| |_ ___| |__   ___  ___| | _____            |
#   |         | |_| |/ _ \/ __| __/ __| '_ \ / _ \/ __| |/ / __|           |
#   |         |  _  | (_) \__ \ || (__| | | |  __/ (__|   <\__ \           |
#   |         |_| |_|\___/|___/\__\___|_| |_|\___|\___|_|\_\___/           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


# Returns check table for a specific host
# Format: ( checkname, item ) -> (params, description )
g_check_table_cache = {}
def get_check_table(hostname):
    # speed up multiple lookup of same host
    if hostname in g_check_table_cache:
        return g_check_table_cache[hostname]

    check_table = {}
    for entry in checks:
        if len(entry) == 4:
            hostlist, checkname, item, params = entry
            tags = []
        elif len(entry) == 5:
            tags, hostlist, checkname, item, params = entry
            if type(tags) != list:
                raise MKGeneralException("Invalid entry '%r' in check table. First entry must be list of host tags." %
                                         (entry, ))

        else:
            raise MKGeneralException("Invalid entry '%r' in check table. It has %d entries, but must have 4 or 5." %
                                     (entry, len(entry)))

        # hostinfo list might be:
        # 1. a plain hostname (string)
        # 2. a list of hostnames (list of strings)
        # Hostnames may be tagged. Tags are removed.
        # In autochecks there are always single untagged hostnames.
        # We optimize for that. But: hostlist might be tagged hostname!
        if type(hostlist) == str:
            if hostlist != hostname:
                continue # optimize most common case: hostname mismatch
            hostlist = [ strip_tags(hostlist) ]
        elif type(hostlist[0]) == str:
            hostlist = strip_tags(hostlist)
        elif hostlist != []:
            raise MKGeneralException("Invalid entry '%r' in check table. Must be single hostname or list of hostnames" % hostinfolist)

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
               in_extraconf_hostlist(hostlist, hostname):
            descr = service_description(checkname, item)
            deps  = service_deps(hostname, descr)
            check_table[(checkname, item)] = (params, descr, deps)

    # Remove dependencies to non-existing services
    all_descr = set([ descr for ((checkname, item), (params, descr, deps)) in check_table.items() ])
    for (checkname, item), (params, descr, deps) in check_table.items():
        deeps = deps[:]
        del deps[:]
        for d in deeps:
            if d in all_descr:
                deps.append(d)

    g_check_table_cache[hostname] = check_table
    return check_table


def get_sorted_check_table(hostname):
    # Convert from dictionary into simple tuple list. Then sort
    # it according to the service dependencies.
    unsorted = [ (checkname, item, params, descr, deps)
                 for ((checkname, item), (params, descr, deps))
                 in get_check_table(hostname).items() ]
    def cmp(a, b):
        if a[3] < b[3]:
            return -1
        else:
            return 1
    unsorted.sort(cmp)


    sorted = []
    while len(unsorted) > 0:
        unsorted_descrs = set([ entry[3] for entry in unsorted ])
        left = []
        at_least_one_hit = False
        for check in unsorted:
            deps_fullfilled = True
            for dep in check[4]: # deps
                if dep in unsorted_descrs:
                    deps_fullfilled = False
                    break
            if deps_fullfilled:
                sorted.append(check)
                at_least_one_hit = True
            else:
                left.append(check)
        if len(left) == 0:
            break
        if not at_least_one_hit:
            raise MKGeneralException("Cyclic service dependency of host %s. Problematic are: %s" %
                                     (hostname, ",".join(unsorted_descrs)))
        unsorted = left
    return sorted



# Determine, which program to call to get data. Should
# be None in most cases -> to TCP connect on port 6556
def get_datasource_program(hostname, ipaddress):
    programs = host_extra_conf(hostname, datasource_programs)
    if len(programs) == 0:
        return None
    else:
        return programs[0].replace("<IP>", ipaddress).replace("<HOST>", hostname)


def service_description(checkname, item):
    if checkname not in check_info:
        raise MKGeneralException("Unknown check type '%s'.\n"
                                 "Please use check_mk -L for a list of all check types.\n" % checkname)

    # use user-supplied service description, of available
    descr_format = service_descriptions.get(checkname)
    if not descr_format:
        descr_format = check_info[checkname][1]

    if type(item) == str:
        # Remove characters from item name that are banned by Nagios
        item_safe = "".join([ c for c in item if c not in nagios_illegal_chars ])
        if "%s" not in descr_format:
            descr_format += " %s"
        return descr_format % (item_safe,)
    if type(item) == int or type(item) == long:
        if "%s" not in descr_format:
            descr_format += " %s"
        return descr_format % (item,)
    else:
        return descr_format

#   +----------------------------------------------------------------------+
#   |    ____             __ _                     _               _       |
#   |   / ___|___  _ __  / _(_) __ _    ___  _   _| |_ _ __  _   _| |_     |
#   |  | |   / _ \| '_ \| |_| |/ _` |  / _ \| | | | __| '_ \| | | | __|    |
#   |  | |__| (_) | | | |  _| | (_| | | (_) | |_| | |_| |_) | |_| | |_     |
#   |   \____\___/|_| |_|_| |_|\__, |  \___/ \__,_|\__| .__/ \__,_|\__|    |
#   |                          |___/                  |_|                  |
#   +----------------------------------------------------------------------+

def output_conf_header(outfile):
    outfile.write("""#
# Created by Check_MK. Do not edit.
#

""")

def all_active_hosts():
    if only_hosts == None:
        return strip_tags(all_hosts)
    else:
        return [ hostname for hostname in strip_tags(all_hosts) \
                 if in_binary_hostlist(hostname, only_hosts) ]

def all_active_clusters():
    if only_hosts == None:
        return strip_tags(clusters.keys())
    else:
        return [ hostname for hostname in strip_tags(clusters.keys()) \
                 if in_binary_hostlist(hostname, only_hosts) ]

def hostgroups_of(hostname):
    return host_extra_conf(hostname, host_groups)

def summary_hostgroups_of(hostname):
    return host_extra_conf(hostname, summary_host_groups)

def host_contactgroups_of(hostlist):
    cgrs = []
    for host in hostlist:
        cgrs += host_extra_conf(host, host_contactgroups)
    return list(set(cgrs))

def host_contactgroups_nag(hostlist):
    cgrs = host_contactgroups_of(hostlist)
    if len(cgrs) > 0:
        return "    contact_groups +" + ",".join(cgrs) + "\n"
    else:
        return ""

def parents_of(hostname):
    par = host_extra_conf(hostname, parents)
    # Use only those parents which are defined and active in
    # all_hosts.
    used_parents = []
    for p in par:
        ps = p.split(",")
        for pss in ps:
            if pss in all_hosts_untagged:
                used_parents.append(pss)
    return used_parents

def extra_host_conf_of(hostname):
    return extra_conf_of(extra_host_conf, hostname, None)

def extra_summary_host_conf_of(hostname):
    return extra_conf_of(extra_summary_host_conf, hostname, None)

# Collect all extra configuration data for a service
def extra_service_conf_of(hostname, description):
    global contactgroups_to_define
    global servicegroups_to_define
    conf = ""

    # Contact groups
    sercgr = service_extra_conf(hostname, description, service_contactgroups)
    contactgroups_to_define.update(sercgr)
    if len(sercgr) > 0:
        conf += "  contact_groups\t\t+" + ",".join(sercgr) + "\n"

    sergr = service_extra_conf(hostname, description, service_groups)
    if len(sergr) > 0:
        conf += "  service_groups\t\t+" + ",".join(sergr) + "\n"
        if define_servicegroups:
            servicegroups_to_define.update(sergr)
    conf += extra_conf_of(extra_service_conf, hostname, description)
    return conf

def extra_summary_service_conf_of(hostname, description):
    return extra_conf_of(extra_summary_service_conf, hostname, description)

def extra_conf_of(confdict, hostname, service):
    result = ""
    for key, conflist in confdict.items():
        if service:
            values = service_extra_conf(hostname, service, conflist)
        else:
            values = host_extra_conf(hostname, conflist)
        if len(values) > 0:
            format = "  %-29s %s\n"
            result += format % (key, values[0])
    return result


# Return a list of services this services depends upon
def service_deps(hostname, servicedesc):
    deps = []
    for entry in service_dependencies:
        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags = []
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service dependencies: must have 3 or 4 entries" % entry)

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
            for pattern in patternlist:
                reg = compiled_regexes.get(pattern)
                if not reg:
                    reg = re.compile(pattern)
                    compiled_regexes[pattern] = reg
                matchobject = reg.search(servicedesc)
                if matchobject:
                    try:
                        item = matchobject.groups()[-1]
                        deps.append(depname % item)
                    except:
                        deps.append(depname)
    return deps


def host_extra_conf(hostname, conf):
    items = []
    if len(conf) == 1 and conf[0] == "":
        sys.stderr.write('WARNING: deprecated entry [ "" ] in host configuration list\n')

    for entry in conf:
        if len(entry) == 2:
            item, hostlist = entry
            tags = []
        elif len(entry) == 3:
            item, tags, hostlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in host configuration list: must have 2 or 3 entries" % (entry,))

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
            items.append(item)
    return items

def in_binary_hostlist(hostname, conf):
    # if we have just a list of strings just take it as list of (may be tagged) hostnames
    if len(conf) > 0 and type(conf[0]) == str:
        return hostname in strip_tags(conf)

    for entry in conf:
        try:
            # Negation via 'NEGATE'
            if entry[0] == NEGATE:
                entry = entry[1:]
                negate = True
            else:
                negate = False
            # entry should be one-tuple or two-tuple. Tuple's elements are
            # lists of strings. User might forget comma in one tuple. Then the
            # entry is the list itself.
            if type(entry) == list:
                hostlist = entry
                tags = []
            else:
                if len(entry) == 1: # 1-Tuple with list of hosts
                    hostlist = entry[0]
                    tags = []
                else:
                    tags, hostlist = entry

            if hosttags_match_taglist(tags_of_host(hostname), tags) and \
                   in_extraconf_hostlist(hostlist, hostname):
                return not negate

        except:
            MKGeneralException("Invalid entry '%r' in host configuration list: must be tupel with 1 or 2 entries" % (entry,))

    return False


# Compute list of service_groups or contact_groups of service
# conf is either service_groups or service_contactgroups
def service_extra_conf(hostname, service, conf):
    entries = []
    for entry in conf:
        if len(entry) == 3:
            item, hostlist, servlist = entry
            tags = []
        elif len(entry) == 4:
            item, tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service configuration list: must have 3 or 4 elements" % (entry,))

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname) and \
           in_extraconf_servicelist(servlist, service):
            entries.append(item)
    return entries



# Entries in list are (tagged) hostnames that must equal the
# (untagged) hostname. Expressions beginning with ! are negated: if
# they match, the item is excluded from the list. Also the three
# special tags '@all', '@clusters', '@physical' are allowed.
def in_extraconf_hostlist(hostlist, hostname):

    # Migration help: print error if old format appears in config file
    if len(hostlist) == 1 and hostlist[0] == "":
        raise MKGeneralException('Invalid emtpy entry [ "" ] in configuration')

    for hostentry in hostlist:
        if len(hostentry) == 0:
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            ic = is_cluster(hostname)
            if hostentry == '@cluster' and ic:
                return True
            elif hostentry == '@physical' and not ic:
                return True

        # Allow negation of hostentry with prefix '!'
        elif hostentry[0] == '!':
            hostentry = hostentry[1:]
            negate = True
        else:
            negate = False

        if hostname == strip_tags(hostentry):
            return not negate

    return False

def in_extraconf_servicelist(list, item):
    for pattern in list:
        # Allow negation of pattern with prefix '!'
        if len(pattern) > 0 and pattern[0] == '!':
            pattern = pattern[1:]
            negate = True
        else:
            negate = False

        reg = compiled_regexes.get(pattern)
        if not reg:
            reg = re.compile(pattern)
            compiled_regexes[pattern] = reg
        if reg.match(item):
            return not negate

    # no match in list -> negative answer
    return False


# NEW IMPLEMENTATION
def create_nagios_config(outfile = sys.stdout, hostnames = None):
    global hostgroups_to_define
    hostgroups_to_define = set([])
    global servicegroups_to_define
    servicegroups_to_define = set([])
    global contactgroups_to_define
    contactgroups_to_define = set([])
    global checknames_to_define
    checknames_to_define = set([])

    if host_notification_periods != []:
        raise MKGeneralException("host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead.")

    if summary_host_notification_periods != []:
        raise MKGeneralException("summary_host_notification_periods is not longer supported. Please use extra_summary_host_conf['notification_period'] instead.")

    if service_notification_periods != []:
        raise MKGeneralException("service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead.")

    if summary_service_notification_periods != []:
        raise MKGeneralException("summary_service_notification_periods is not longer supported. Please use extra_summary_service_conf['notification_period'] instead.")

    output_conf_header(outfile)
    if hostnames == None:
        hostnames = all_hosts_untagged + all_active_clusters()

    for hostname in hostnames:
        create_nagios_config_host(outfile, hostname)

    create_nagios_config_hostgroups(outfile)
    create_nagios_config_servicegroups(outfile)
    create_nagios_config_contactgroups(outfile)
    create_nagios_config_commands(outfile)

    if extra_nagios_conf:
        outfile.write("\n# extra_nagios_conf\n\n")
        outfile.write(extra_nagios_conf)



def create_nagios_config_host(outfile, hostname):
    outfile.write("\n# ----------------------------------------------------\n")
    outfile.write("# %s\n" % hostname)
    outfile.write("# ----------------------------------------------------\n")
    if generate_hostconf:
        create_nagios_hostdefs(outfile, hostname)
    create_nagios_servicedefs(outfile, hostname)

def create_nagios_hostdefs(outfile, hostname):
    is_clust = is_cluster(hostname)

    # Determine IP address. For cluster hosts this is optional.
    # A cluster might have or not have a service ip address.
    try:
        ip = lookup_ipaddress(hostname)
    except:
        if not is_cluster(hostname):
            raise MKGeneralException("Cannot determine ip address of %s. Please add to ipaddresses." % hostname)
        ip = None

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    alias = hostname
    outfile.write("\ndefine host {\n")
    outfile.write("  host_name\t\t\t%s\n" % hostname)
    outfile.write("  use\t\t\t\t%s\n" % (is_clust and cluster_template or host_template))
    outfile.write("  address\t\t\t%s\n" % (ip and ip or "0.0.0.0"))
    outfile.write("  _TAGS\t\t\t\t%s\n" % " ".join(tags_of_host(hostname)))

    # Host groups: If the host has no hostgroups it gets the default
    # hostgroup (Nagios requires each host to be member of at least on
    # group.
    hgs = hostgroups_of(hostname)
    hostgroups = ",".join(hgs)
    if len(hgs) == 0:
        hostgroups = default_host_group
        hostgroups_to_define.add(default_host_group)
    elif define_hostgroups:
        hostgroups_to_define.update(hgs)
    outfile.write("  host_groups\t\t\t+%s\n" % hostgroups)

    # Contact groups
    cgrs = host_contactgroups_of([hostname])
    if len(cgrs) > 0:
        outfile.write("  contact_groups\t\t+%s\n" % ",".join(cgrs))
        contactgroups_to_define.update(cgrs)

    # Parents for non-clusters
    if not is_clust:
        parents_list = parents_of(hostname)
        if len(parents_list) > 0:
            outfile.write("  parents\t\t\t%s\n" % (",".join(parents_list)))

    # Special handling of clusters
    if is_clust:
        nodes = nodes_of(hostname)
        for node in nodes:
            if node not in all_hosts_untagged:
                raise MKGeneralException("Node %s of cluster %s not in all_hosts." % (node, hostname))
        node_ips = [ lookup_ipaddress(h) for h in nodes ]
        alias = "cluster of %s" % ", ".join(nodes)
        outfile.write("  _NODEIPS\t\t\t%s\n" % " ".join(node_ips))
        outfile.write("  parents\t\t\t%s\n" % ",".join(nodes))

        # Host check uses (service-) IP address if available
        if ip:
            outfile.write("  check_command\t\t\tcheck-mk-ping\n")

    outfile.write("  alias\t\t\t\t%s\n" % alias)

    # Custom configuration last -> user may override all other values
    outfile.write(extra_host_conf_of(hostname))

    outfile.write("}\n")

    #   ____
    #  |___ \
    #   __) |
    #  / __/
    #  |_____|  2. summary hosts

    if host_is_aggregated(hostname):
        outfile.write("\ndefine host {\n")
        outfile.write("  host_name\t\t\t%s\n" % summary_hostname(hostname))
        outfile.write("  use\t\t\t\t%s-summary\n" % (is_clust and cluster_template or host_template))
        outfile.write("  alias\t\t\t\tSummary of %s\n" % alias)
        outfile.write("  address\t\t\t%s\n" % (ip and ip or "0.0.0.0"))
        outfile.write("  _TAGS\t\t\t\t%s\n" % " ".join(tags_of_host(hostname)))
        outfile.write("  __REALNAME\t\t\t%s\n" % hostname)
        outfile.write("  parents\t\t\t%s\n" % hostname)

        hgs = summary_hostgroups_of(hostname)
        hostgroups = ",".join(hgs)
        if len(hgs) == 0:
            hostgroups = default_host_group
            hostgroups_to_define.add(default_host_group)
        elif define_hostgroups:
            hostgroups_to_define.update(hgs)
        outfile.write("  host_groups\t\t\t+%s\n" % hostgroups)

        # host gets same contactgroups as real host
        if len(cgrs) > 0:
            outfile.write("  contact_groups\t\t+%s\n" % ",".join(cgrs))

        if is_clust:
            outfile.write("  _NODEIPS\t\t\t%s\n" % " ".join(node_ips))
        outfile.write("}\n")
    outfile.write("\n")

def create_nagios_servicedefs(outfile, hostname):
    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services

    host_checks = get_check_table(hostname).items()
    host_checks.sort() # Create deterministic order
    aggregated_services_conf = set([])
    do_aggregation = host_is_aggregated(hostname)
    have_at_least_one_service = False
    used_descriptions = {}
    for ((checkname, item), (params, description, deps)) in host_checks:
        # Make sure, the service description is unique on this host
        if description in used_descriptions:
            cn, it = used_descriptions[description]
            raise MKGeneralException(
                    "ERROR: Duplicate service description '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = %s, item = %r\n" % 
                    (description, hostname, cn, it, checkname, item))

        else:
            used_descriptions[description] = ( checkname, item )
        if have_perfdata(checkname):
            template = passive_service_template_perf
        else:
            template = passive_service_template

        # Hardcoded for logwatch check: Link to logwatch.php
        if checkname == "logwatch":
            logwatch = "  notes_url\t\t\t" + (logwatch_notes_url % (urllib.quote(hostname), urllib.quote(item))) + "\n"
        else:
            logwatch = "";

        # Services Dependencies
        for dep in deps:
            outfile.write("define servicedependency {\n"
                         "    use\t\t\t\t%s\n"
                         "    host_name\t\t\t%s\n"
                         "    service_description\t%s\n"
                         "    dependent_host_name\t%s\n"
                         "    dependent_service_description %s\n"
                         "}\n\n" % (service_dependency_template, hostname, dep, hostname, description))


        # Handle aggregated services. If this service belongs to an aggregation,
        # remember, that the aggregated service must be configured. We cannot
        # do this here, because each aggregated service must occur only once
        # in the configuration.
        if do_aggregation:
            asn = aggregated_service_name(hostname, description)
            if asn != "":
                aggregated_services_conf.add(asn)

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\t%s
%s%s  check_command\t\t\tcheck_mk-%s
}

""" % ( template, hostname, description, logwatch,
        extra_service_conf_of(hostname, description), checkname ))

        checknames_to_define.add(checkname)
        have_at_least_one_service = True


    # Now create definitions of the aggregated services for this host
    if do_aggregation and service_aggregations:
        outfile.write("\n# Aggregated services\n\n")

    aggr_descripts = aggregated_services_conf
    if aggregate_check_mk and host_is_aggregated(hostname) and have_at_least_one_service:
        aggr_descripts.add("Check_MK")

    # If a ping-only-host is aggregated, the summary host gets it's own
    # copy of the ping - as active check. We cannot aggregate the result
    # from the ping of the real host since no Check_MK is running during
    # the check.
    elif host_is_aggregated(hostname) and not have_at_least_one_service:
        outfile.write("""
define service {
  use\t\t\t\t%s
%s  host_name\t\t\t%s
}

""" % (pingonly_template, extra_service_conf_of(hostname, "PING"), summary_hostname(hostname)))

    for description in aggr_descripts:
        sergr = service_extra_conf(hostname, description, summary_service_groups)
        if len(sergr) > 0:
            sg = "  service_groups\t\t\t+" + ",".join(sergr) + "\n"
            if define_servicegroups:
                servicegroups_to_define.update(sergr)
        else:
            sg = ""

        sercgr = service_extra_conf(hostname, description, summary_service_contactgroups)
        contactgroups_to_define.update(sercgr)
        if len(sercgr) > 0:
            scg = "  contact_groups\t\t\t+" + ",".join(sercgr) + "\n"
        else:
            scg = ""

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s%s%s  service_description\t\t%s
}

""" % ( summary_service_template, summary_hostname(hostname), sg, scg,
extra_summary_service_conf_of(hostname, description), description  ))

    # Active check for check_mk
    if have_at_least_one_service:
        outfile.write("""
# Active checks

define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s  service_description\t\tCheck_MK
}
""" % (active_service_template, hostname, extra_service_conf_of(hostname, "Check_MK")))
        # Inventory checks - if user has configured them. Not for clusters.
        if inventory_check_interval and not is_cluster(hostname):
            outfile.write("""
define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  normal_check_interval\t\t%d
%s  service_description\t\tCheck_MK inventory
}

define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\tCheck_MK
  dependent_host_name\t\t%s
  dependent_service_description\tCheck_MK inventory
}
""" % (inventory_check_template, hostname, inventory_check_interval,
       extra_service_conf_of(hostname, "Check_MK inventory"),
       service_dependency_template, hostname, hostname))

    legchecks = host_extra_conf(hostname, legacy_checks)
    if len(legchecks) > 0:
        outfile.write("\n\n# Legacy checks\n")
    for command, description, has_perfdata in legchecks:
        if description in used_descriptions:
            cn, it = used_descriptions[description]
            raise MKGeneralException(
                    "ERROR: Duplicate service description (legacy check) '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = legacy(%s), item = None\n" % 
                    (description, hostname, cn, it, command))

        else:
            used_descriptions[description] = ( "legacy(" + command + ")", item )
        
        extraconf = extra_service_conf_of(hostname, description)
        if has_perfdata:
            template = "check_mk_perf,"
        else:
            template = ""
        outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t1
%s}
""" % (template, hostname, description, command, extraconf))

    # No check_mk service, no legacy service -> create PING service
    if not have_at_least_one_service and len(legchecks) == 0:
        outfile.write("""
define service {
  use\t\t\t\t%s
%s  host_name\t\t\t%s
}

""" % (pingonly_template, extra_service_conf_of(hostname, "PING"), hostname))


def create_nagios_config_hostgroups(outfile):
    if define_hostgroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Host groups (controlled by define_hostgroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        hgs = list(hostgroups_to_define)
        hgs.sort()
        for hg in hgs:
            try:
                alias = define_hostgroups[hg]
            except:
                alias = hg
            outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (hg, alias))

    # No creation of host groups but we need to define
    # default host group
    elif default_host_group in hostgroups_to_define:
	outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\tCheck_MK default hostgroup
}
""" % default_host_group)
	

def create_nagios_config_servicegroups(outfile):
    if define_servicegroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Service groups (controlled by define_servicegroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        sgs = list(servicegroups_to_define)
        sgs.sort()
        for sg in sgs:
            try:
                alias = define_servicegroups[sg]
            except:
                alias = sg
            outfile.write("""
define servicegroup {
  servicegroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (sg, alias))

def create_nagios_config_contactgroups(outfile):
    if define_contactgroups:
        cgs = list(contactgroups_to_define)
        cgs.sort()
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Contact groups (controlled by define_contactgroups)\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        for name in cgs:
            if type(define_contactgroups) == dict:
                alias = define_contactgroups.get(name, name)
            else:
                alias = name
            outfile.write("\ndefine contactgroup {\n"
                    "  contactgroup_name\t\t%s\n"
                    "  alias\t\t\t\t%s\n"
                    "}\n" % (name, alias))


def create_nagios_config_commands(outfile):
    if generate_dummy_commands:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Dummy check commands (controlled by generate_dummy_commands)\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        for checkname in checknames_to_define:
            outfile.write("""define command {
  command_name\t\t\tcheck_mk-%s
  command_line\t\t\t%s
}

""" % ( checkname, dummy_check_commandline ))

#   +----------------------------------------------------------------------+
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+


def inventorable_checktypes(what): # tcp, all
    checknames = [ k for k in check_info.keys()
                   if check_info[k][3] != no_inventory_possible
#                   and (k not in ignored_checktypes)
                   and (what == "all" or k not in snmp_info)
                 ]
    checknames.sort()
    return checknames

def checktype_ignored_for_host(host, checktype):
    if checktype in ignored_checktypes: 
        return True
    ignored = host_extra_conf(host, ignored_checks)
    for e in ignored:
        if checktype == e or (type(e) == list and checktype in e):
            return True
    return False

def do_snmp_scan(hostnamelist, check_only=False, include_state=False):
    if hostnamelist == []:
        hostnamelist = all_hosts_untagged

    result = []
    for hostname in hostnamelist:
        if not is_snmp_host(hostname):
            if opt_verbose:
                sys.stdout.write("Skipping %s, not an snmp host\n" % hostname)
            continue
        try:
            ipaddress = lookup_ipaddress(hostname)
        except:
            sys.stdout.write("Cannot resolve %s into IP address. Skipping.\n" % hostname)
            continue
        checknames = snmp_scan(hostname, ipaddress)
        for checkname in checknames:
            if opt_debug:
                sys.stdout.write("Trying inventory for %s on %s\n" % (checkname, hostname))
            result += make_inventory(checkname, [hostname], check_only, include_state)
    return result


def make_inventory(checkname, hostnamelist, check_only=False, include_state=False):
    try:
        inventory_function = check_info[checkname][3]
    except KeyError:
        sys.stderr.write("No such check type '%s'. Try check_mk -I list.\n" % checkname)
        sys.exit(1)

    is_snmp_check = check_uses_snmp(checkname)

    newchecks = []
    newitems = []   # used by inventory check to display unchecked items
    count_new = 0
    checked_hosts = []

    # if no hostnamelist is specified, we use all hosts
    if not hostnamelist or len(hostnamelist) == 0:
        global opt_use_cachefile
        opt_use_cachefile = True
        hostnamelist = all_hosts_untagged

    try:
        for host in hostnamelist:

            # Skip SNMP checks on non-SNMP hosts
            if is_snmp_check and not is_snmp_host(host): 
                continue

            # Skip TCP checks on non-TCP hosts
            if not is_snmp_check and not is_tcp_host(host):
                continue

            # Skip checktypes which are generally ignored for this host
            if checktype_ignored_for_host(host, checkname):
                continue

            if is_cluster(host):
                sys.stderr.write("%s is a cluster host and cannot be inventorized.\n" % host)
                continue

            # host is either hostname or "hostname/ipaddress"
            s = host.split("/")
            hostname = s[0]
            if len(s) == 2:
                ipaddress = s[1]
            else:
                # try to resolve name into ip address
                if not opt_no_tcp:
                    try:
                        ipaddress = lookup_ipaddress(hostname)
                    except:
                        sys.stderr.write("Cannot resolve %s into IP address.\n" % hostname)
                        continue
                else:
                    ipaddress = None # not needed, not TCP used

            # Make hostname available as global variable in inventory functions
            # (used e.g. by ps-inventory)
            global g_hostname
            g_hostname = hostname

            # On --no-tcp option skip hosts without cache file
            if opt_no_tcp:
                if opt_no_cache:
                    sys.stderr.write("You allowed me neither TCP nor cache. Bailing out.\n")
                    sys.exit(4)

                cachefile = tcp_cache_dir + "/" + hostname
                if not os.path.exists(cachefile):
                    if opt_verbose:
                        sys.stderr.write("No cachefile %s. Skipping this host.\n" % cachefile)
                    continue

            checked_hosts.append(hostname)

            checkname_base = checkname.split('.')[0]    # make e.g. 'lsi' from 'lsi.arrays'
            try:
                info = get_realhost_info(hostname, ipaddress, checkname_base, inventory_max_cachefile_age)
            except MKAgentError, e:
                if check_only and str(e):
                    raise
		elif str(e):
		    sys.stderr.write("Host '%s': %s\n" % (hostname, str(e)))
                continue
            except MKSNMPError, e:
                if check_only and str(e):
                    raise
		elif str(e):
                    sys.stderr.write("Host '%s': %s\n" % (hostname, str(e)))
                continue
            except Exception, e:
                if check_only or opt_debug:
                    raise
                sys.stderr.write("Cannot get information from host '%s': %s\n" % (hostname, e))
                continue

            if info == None: # No data for this check type
                continue
            try:
                inventory = inventory_function(checkname, info) # inventory is a list of pairs (item, current_value)
                if inventory == None: # tolerate if function does no explicit return
                    inventory = []
            except Exception, e:
                if opt_debug:
                    raise
                sys.stderr.write("%s: Invalid output from agent or invalid configuration: %s\n" % (hostname, e))
                continue

            if not isinstance(inventory, list):
                sys.stderr.write("%s: Check %s returned invalid inventory data: %s\n" %
                                                    (hostname, checkname, repr(inventory)))
                continue

            for entry in inventory:
                state_type = "new" # assume new, change later if wrong
                if len(entry) == 2: # comment is now obsolete
                    item, paramstring = entry
                else:
                    item, comment, paramstring = entry

                description = service_description(checkname, item)

                # Find logical host this check belongs to. The service might belong to a cluster.
                hn = host_of_clustered_service(hostname, description)

                # Now compare with already known checks for this host (from
                # previous inventory or explicit checks). Also drop services
                # the user wants to ignore via 'ignored_services'.
                checktable = get_check_table(hn)
                checked_items = [ i for ( (cn, i), (par, descr, deps) ) \
                                  in checktable.items() if cn == checkname ]
                if item in checked_items:
                    if include_state:
                        state_type = "old"
                    else:
                        continue # we have that already

                if service_ignored(hn, description):
                    if include_state:
                        if state_type == "old":
                            state_type = "obsolete"
                        else:
                            state_type = "ignored"
                    else:
                        continue # user does not want this item to be checked

                newcheck = '  ("%s", "%s", %r, %s),' % (hn, checkname, item, paramstring)
                newcheck += "\n"
                if newcheck not in newchecks: # avoid duplicates if inventory outputs item twice
                    newchecks.append(newcheck)
                    if include_state:
                        newitems.append( (hn, checkname, item, paramstring, state_type) )
                    else:
                        newitems.append( (hn, checkname, item) )
                    count_new += 1


    except KeyboardInterrupt:
        sys.stderr.write('<Interrupted>\n')

    if not check_only:
        if newchecks != []:
            filename = autochecksdir + "/" + checkname + "-" + time.strftime("%Y-%m-%d_%H.%M.%S")
            while os.path.exists(filename + ".mk"): # in case of more than one file per second and checktype...
                filename += ".x"
            filename += ".mk"
            if not os.path.exists(autochecksdir):
                os.makedirs(autochecksdir)
            file(filename, "w").write('# %s\n[\n%s]\n' % (filename, ''.join(newchecks)))
            sys.stdout.write('%-30s ' % (tty_blue + checkname + tty_normal))
            sys.stdout.write('%s%d new checks%s\n' % (tty_bold + tty_green, count_new, tty_normal))

    return newitems


def check_inventory(hostname):
    newchecks = []
    newitems = []
    total_count = 0
    only_snmp = is_snmp_host(hostname)
    check_table = get_check_table(hostname)
    hosts_checktypes = set([ ct for (ct, item), params in check_table.items() ])
    try:
        for ct in inventorable_checktypes("all"):
            if only_snmp and not check_uses_snmp(ct):
                continue # No TCP checks on SNMP-only hosts
            elif check_uses_snmp(ct) and ct not in hosts_checktypes:
                continue # Do not look for new SNMP services (why?)
            new = make_inventory(ct, [hostname], True)
            newitems += new
            count = len(new)
            if count > 0:
                newchecks.append((ct, count))
                total_count += count
        if total_count > 0:
            info = ", ".join([ "%s:%d" % (ct, count) for ct,count in newchecks ])
            statustext = { 0 : "OK", 1: "WARNING", 2:"CRITICAL" }.get(inventory_check_severity, "UNKNOWN")
            sys.stdout.write("%s - %d unchecked services (%s)\n" % (statustext, total_count, info))
            # Put detailed list into long pluging output
            for hostname, checkname, item in newitems:
                sys.stdout.write("%s: %s\n" % (checkname, service_description(checkname, item)))
            sys.exit(inventory_check_severity)
        else:
            sys.stdout.write("OK - no unchecked services found\n")
            sys.exit(0)
    except SystemExit, e:
        raise e
    except Exception, e:
        if opt_debug:
            raise
        sys.stdout.write("UNKNOWN - %s\n" % (e,))
        sys.exit(3)


def service_ignored(hostname, service_description):
    return in_boolean_serviceconf_list(hostname, service_description, ignored_services)

def in_boolean_serviceconf_list(hostname, service_description, conflist):
    for entry in conflist:
        if entry[0] == NEGATE: # this entry is logically negated
            negate = True
            entry = entry[1:]
        else:
            negate = False

        if len(entry) == 2:
            hostlist, servlist = entry
            tags = []
        elif len(entry) == 3:
            tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in configuration: must have 2 or 3 elements" % (entry,))

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname) and \
           in_extraconf_servicelist(servlist, service_description):
            if opt_verbose:
                print "Ignoring service '%s' on host %s." % (service_description, hostname)
            return not negate
    return False # no match. Do not ignore


# Remove all autochecks of certain types of a certain host
def remove_autochecks_of(hostname, checktypes):
    for fn in glob.glob(autochecksdir + "/*.mk"):
        if opt_debug:
            sys.stdout.write("Scanning %s...\n" % fn)
        lines = []
        count = 0
        for line in file(fn):
            if line.lstrip().startswith('("'):
                count += 1
                splitted = line.split('"')
                if splitted[1] != hostname or splitted[3] not in checktypes:
                    lines.append(line)
        if len(lines) == 0:
            if opt_verbose:
                sys.stdout.write("Deleting %s.\n" % fn)
            os.remove(fn)
        elif count > len(lines):
            if opt_verbose:
                sys.stdout.write("Removing %d checks from %s.\n" % (count - len(lines), fn))
            f = file(fn, "w+")
            f.write("[\n")
            for line in lines:
                f.write(line)
            f.write("]\n")

def remove_all_autochecks():
    for f in glob.glob(autochecksdir + '/*.mk'):
        if opt_verbose:
            sys.stdout.write("Deleting %s.\n" % f)
        os.remove(f)

def reread_autochecks():
    global checks
    checks = checks[len(autochecks):]
    read_all_autochecks()
    checks = autochecks + checks

#   +----------------------------------------------------------------------+
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+

def find_check_plugin(checktype):
    if local_checks_dir and os.path.exists(local_checks_dir + "/" + checktype):
        return local_checks_dir + "/" + checktype
    filename = checks_dir + "/" + checktype
    if os.path.exists(filename):
        return filename

def get_precompiled_check_table(hostname):
    host_checks = get_sorted_check_table(hostname)
    precomp_table = []
    for checktype, item, params, description, deps in host_checks:
        aggr_name = aggregated_service_name(hostname, description)
        # some checks need precompilation of parameters
        precomp_func = precompile_params.get(checktype)
        if precomp_func:
            params = precomp_func(hostname, item, params)
        precomp_table.append((checktype, item, params, description, aggr_name)) # deps not needed while checking
    return precomp_table

def precompile_hostchecks():
    if not os.path.exists(precompiled_hostchecks_dir):
        os.makedirs(precompiled_hostchecks_dir)
    for host in all_active_hosts() + all_active_clusters():
        try:
            precompile_hostcheck(host)
        except Exception, e:
            sys.stderr.write("Error precompiling checks for host %s: %s\n" % (host, e))
            sys.exit(5)

# read python file and strip comments
def stripped_python_file(filename):
    a = ""
    for line in file(filename):
        l = line.strip()
        if l == "" or l[0] != '#':
            a += line # not stripped line because of indentation!
    return a

def precompile_hostcheck(hostname):
    if opt_verbose:
        sys.stderr.write("%s%s%-16s%s:" % (tty_bold, tty_blue, hostname, tty_normal))

    try:
        os.remove(compiled_filename)
        os.remove(source_filename)
    except:
        pass

    compiled_filename = precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    output = file(source_filename, "w")
    output.write("#!/usr/bin/python\n")
    output.write(stripped_python_file(modules_dir + "/check_mk_base.py"))

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v is supported
opt_verbose = '-v' in sys.argv
opt_debug   = False

# make sure these names are defined (even if never needed)
no_inventory_possible = None
precompile_filesystem_levels = None
filesystem_default_levels = None
""")

    # Compile in all neccessary global variables
    output.write("\n# Global variables\n")
    for var in [ 'check_mk_version', 'agent_port', 'tcp_connect_timeout', 'agent_min_version',
                 'perfdata_format', 'aggregation_output_format',
                 'aggr_summary_hostname', 'nagios_command_pipe_path',
                 'var_dir', 'counters_directory', 'tcp_cache_dir',
                 'snmpwalks_dir',
                 'check_mk_basedir', 'df_magicnumber_normsize',
                 'df_lowest_warning_level', 'df_lowest_critical_level', 'nagios_user',
                 'www_group', 'cluster_max_cachefile_age', 'check_max_cachefile_age',
                 'simulation_mode', 'aggregate_check_mk', 'debug_log',
                 ]:
        output.write("%s = %r\n" % (var, globals()[var]))

    # check table, enriched with addition precompiled information.
    check_table = get_precompiled_check_table(hostname)
    output.write("\n# Checks for %s\n\n" % hostname)
    output.write("def get_sorted_check_table(hostname):\n    return %r\n\n" % check_table)

    # Do we need to load the SNMP module? This is the case, if the host
    # has at least one SNMP based check. Also collect the needed check
    # types.
    need_snmp_module = False
    needed_types = set([])
    for checktype, item, param, descr, aggr in check_table:
        needed_types.add(checktype.split(".")[0])
        if check_uses_snmp(checktype):
            need_snmp_module = True

    if need_snmp_module:
        output.write(stripped_python_file(modules_dir + "/snmp.py"))

    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table
    filenames = set([])
    for checktype in needed_types:
        path = find_check_plugin(checktype)
        if not path:
            raise MKGeneralException("Cannot find plugin for check type %s (missing file %s/%s)\n" % \
                                     (checktype, checks_dir, checktype))
        filenames.add(path)

    output.write("check_info = {}\n" +
                 "precompile_params = {}\n" +
                 "check_config_variables = []\n" +
                 "snmp_info = {}\n" +
                 "snmp_info_single = {}\n" +
                 "snmp_scan_functions = {}\n")


    for filename in filenames:
        output.write("# %s\n" % filename)
        output.write(stripped_python_file(filename))
        output.write("\n\n")
        if opt_verbose:
            sys.stderr.write(" %s%s%s" % (tty_green, filename.split('/')[-1], tty_normal))

    # direct update of RRD databases by check_mk
    if do_rrd_update:
        output.write("do_rrd_update = True\n" +
                     "import rrdtool\n" +
                     "rrd_path = %r\n" % rrd_path)
    else:
        output.write("do_rrd_update = False\n")

    # handling of clusters
    if is_cluster(hostname):
        output.write("clusters = { %r : %r }\n" %
                     (hostname, nodes_of(hostname)))
        output.write("def is_cluster(hostname):\n    return True\n\n")
    else:
        output.write("clusters = {}\ndef is_cluster(hostname):\n    return False\n\n")

    # snmp hosts
    output.write("def is_snmp_host(hostname):\n   return %r\n\n" % is_snmp_host(hostname))
    output.write("def is_tcp_host(hostname):\n   return %r\n\n" % is_tcp_host(hostname))
    output.write("def snmp_get_command(hostname):\n   return %r\n\n" % snmp_get_command(hostname))
    output.write("def snmp_walk_command(hostname):\n   return %r\n\n" % snmp_walk_command(hostname))
    output.write("def is_usewalk_host(hostname):\n   return %r\n\n" % is_usewalk_host(hostname))

    # IP addresses
    needed_ipaddresses = {}
    nodes = []
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            ipa = lookup_ipaddress(node)
            needed_ipaddresses[node] = ipa
            nodes.append( (node, ipa) )
        ipaddress = None
    else:
        ipaddress = lookup_ipaddress(hostname) # might throw exception
        needed_ipaddresses[hostname] = ipaddress
        nodes = [ (hostname, ipaddress) ]

    output.write("ipaddresses = %r\n\n" % needed_ipaddresses)

    # datasource programs. Is this host relevant?
    # ACHTUNG: HIER GIBT ES BEI CLUSTERN EIN PROBLEM!! WIR MUESSEN DIE NODES
    # NEHMEN!!!!!

    dsprogs = {}
    for node, ipa in nodes:
        program = get_datasource_program(node, ipa)
        dsprogs[node] = program
    output.write("def get_datasource_program(hostname, ipaddress):\n" +
                 "    return %r[hostname]\n\n" % dsprogs)

    # aggregation
    output.write("def host_is_aggregated(hostname):\n    return %r\n\n" % host_is_aggregated(hostname))

    # Parameters for checks: Default values are defined in checks/*. The
    # variables might be overridden by the user in main.mk. We need
    # to set the actual values of those variables here. Otherwise the users'
    # settings would get lost. But we only need to set those variables that
    # influence the check itself - not those needed during inventory.
    for var in check_config_variables:
        output.write("%s = %r\n" % (var, eval(var)))

    # perform actual check
    output.write("do_check(%r, %r)\n" % (hostname, ipaddress))
    output.close()

    # compile python
    py_compile.compile(source_filename, compiled_filename, compiled_filename, True)
    os.chmod(compiled_filename, 0755)

    if opt_verbose:
        sys.stderr.write(" ==> %s.\n" % compiled_filename)


#   +----------------------------------------------------------------------+
#   |                  __  __                         _                    |
#   |                 |  \/  | __ _ _ __  _   _  __ _| |                   |
#   |                 | |\/| |/ _` | '_ \| | | |/ _` | |                   |
#   |                 | |  | | (_| | | | | |_| | (_| | |                   |
#   |                 |_|  |_|\__,_|_| |_|\__,_|\__,_|_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

opt_nowiki = False

def get_tty_size():
    import termios,struct,fcntl
    try:
        ws = struct.pack("HHHH", 0, 0, 0, 0)
        ws = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns, x, y = struct.unpack("HHHH", ws)
        if lines > 0 and columns > 0:
            return lines, columns
    except:
        pass
    return (24, 80)


def all_manuals():
    entries = dict([(fn, check_manpages_dir + "/" + fn) for fn in os.listdir(check_manpages_dir)])
    if local_check_manpages_dir and os.path.exists(local_check_manpages_dir):
        entries.update(dict([(fn, local_check_manpages_dir + "/" + fn) for fn in os.listdir(local_check_manpages_dir)]))
    return entries

def list_all_manuals():
    table = []
    for filename, path in all_manuals().items():
        if filename.endswith("~"):
            continue
        
        try:
            for line in file(path):
                if line.startswith("title:"):
                    table.append((filename, line.split(":", 1)[1].strip()))
        except:
            pass

    table.sort()
    print_table(['Check type', 'Title'], [tty_bold, tty_normal], table)

def show_check_manual(checkname):
    bg_color = 4
    fg_color = 7
    bold_color = tty_white + tty_bold
    normal_color = tty_normal + tty(fg_color, bg_color)
    title_color_left = tty(0,7,1)
    title_color_right = tty(0,7)
    subheader_color = tty(fg_color, bg_color, 1)
    header_color_left = tty(0,2)
    header_color_right = tty(7,2,1)
    parameters_color = tty(6,4,1)
    examples_color = tty(6,4,1)

    filename = all_manuals().get(checkname)
    if not filename:
        sys.stdout.write("No manpage for %s. Sorry." % checkname)
        return

    sections = {}
    current_section = []
    current_variable = None
    sections['header'] = current_section
    lineno = 0
    empty_line_count = 0

    try:
        for line in file(filename):
            lineno += 1
            if line.startswith(' ') and line.strip() != "": # continuation line
                empty_line_count = 0
                if current_variable:
                    name, curval = current_section[-1]
                    if curval.strip() == "":
                        current_section[-1] = (name, line.rstrip()[1:])
                    else:
                        current_section[-1] = (name, curval + "\n" + line.rstrip()[1:])
                else:
                    raise Exception
                continue

            line = line.strip()
            if line == "":
                empty_line_count += 1
                if empty_line_count == 1 and current_variable:
                    name, curval = current_section[-1]
                    current_section[-1] = (name, curval + "\n<br>\n")
                continue
            empty_line_count = 0

            if line[0] == '[' and line[-1] == ']':
                section_header = line[1:-1]
                current_section = []
                sections[section_header] = current_section
            else:
                current_variable, restofline = line.split(':', 1)
                current_section.append((current_variable, restofline.lstrip()))
    except Exception, e:
        sys.stderr.write("Syntax error in %s line %d (%s).\n" % (filename, lineno, e))
        sys.exit(1)

    # Output
    height, width = get_tty_size()
    if os.path.exists("/usr/bin/less") and not opt_nowiki:
        output = os.popen("/usr/bin/less -S -R -Q -u -L", "w")
    else:
        output = sys.stdout

    if opt_nowiki:
        print "TI:Check manual page of %s" % checkname
        print "DT:%s" % (time.strftime("%Y-%m-%d"))
        print "SA:checks"

        def markup(line, ignored=None):
            return line.replace("{", "<b>").replace("}", "</b>")

        def print_sectionheader(line, ignored):
            print "H1:" + line

        def print_subheader(line):
            print "H2:" + line

        def print_line(line, attr=None, no_markup = False):
            if no_markup:
                print line
            else:
                print markup(line)

        def print_splitline(attr1, left, attr2, right):
            print "<b style=\"width: 300px;\">%s</b> %s\n" % (left, right)

        def empty_line():
            print

        def print_textbody(text):
            print markup(text)

        def print_splitwrap(attr1, left, attr2, text):
            if '(' in left:
                name, typ = left.split('(', 1)
                name = name.strip()
                typ = typ.strip()[:-2]
            else:
                name = left
                typ = ""
            print "<tr><td class=tt>%s</td><td>%s</td><td>%s</td></tr>" % (name, typ, text)

    else:
        def markup(line, attr):
            return line.replace("{", bold_color).replace("}", tty_normal + attr)

        def print_sectionheader(left, right):
            print_splitline(title_color_left, "%-19s" % left, title_color_right, right)

        def print_subheader(line):
            empty_line()
            output.write(subheader_color + " " + tty_underline +
                         line.upper() +
                         normal_color +
                         (" " * (width - 1 - len(line))) +
                         tty_normal + "\n")

        def print_line(line, attr=normal_color, no_markup = False):
            if no_markup:
                text = line
                l = len(line)
            else:
                text = markup(line, attr)
                l = print_len(line)
            output.write(attr + " ")
            output.write(text)
            output.write(" " * (width - 2 - l))
            output.write(" " + tty_normal + "\n")

        def print_splitline(attr1, left, attr2, right):
            output.write(attr1 + " " + left)
            output.write(attr2)
            output.write(markup(right, attr2))
            output.write(" " * (width - 1 - len(left) - print_len(right)))
            output.write(tty_normal + "\n")

        def empty_line():
            print_line("", tty(7,4))

        def print_len(word):
            netto = word.replace("{", "").replace("}", "")
            netto = re.sub("\033[^m]+m", "", netto)
            return len(netto)

        def justify(line, width):
            need_spaces = float(width - print_len(line))
            spaces = float(line.count(' '))
            newline = ""
            x = 0.0
            s = 0.0
            words = line.split()
            newline = words[0]
            for word in words[1:]:
                newline += ' '
                x += 1.0
                if s/x < need_spaces / spaces:
                    newline += ' '
                    s += 1
                newline += word
            return newline

        def fillup(line, width):
            printlen = print_len(line)
            if printlen < width:
                line += " " * (width - printlen)
            return line

        def wrap_text(text, width, attr=tty(7,4)):
            wrapped = []
            line = ""
            col = 0
            for word in text.split():
                if word == '<br>':
                    if line != "":
                        wrapped.append(fillup(line, width))
                        wrapped.append("")
                        line = ""
                        col = 0
                else:
                    netto = print_len(word)
                    if line != "" and netto + col + 1 > width:
                        wrapped.append(justify(line, width))
                        col = 0
                        line = ""
                    if line != "":
                        line += ' '
                        col += 1
                    line += markup(word, attr)
                    col += netto
            if line != "":
                wrapped.append(fillup(line, width))

            # remove trailing empty lines
            while wrapped[-1].strip() == "":
                wrapped = wrapped[:-1]
            return wrapped

        def print_textbody(text, attr=tty(7,4)):
            wrapped = wrap_text(text, width - 2)
            for line in wrapped:
                print_line(line, attr)

        def print_splitwrap(attr1, left, attr2, text):
            wrapped = wrap_text(left + attr2 + text, width - 2)
            output.write(attr1 + " " + wrapped[0] + " " + tty_normal + "\n")
            for line in wrapped[1:]:
                output.write(attr2 + " " + line + " " + tty_normal + "\n")

    try:
        header = {}
        for key, value in sections['header']:
            header[key] = value.strip()

        print_sectionheader(checkname, header['title'])
        if opt_nowiki:
            sys.stderr.write("<tr><td class=tt>%s</td><td>[check_%s|%s]</td></tr>\n" % (checkname, checkname, header['title']))
        print_splitline(header_color_left, "Author:            ", header_color_right, header['author'])
        print_splitline(header_color_left, "License:           ", header_color_right, header['license'])
        distro = header['distribution']
        if distro == 'check_mk':
            distro = "official part of check_mk"
        print_splitline(header_color_left, "Distribution:      ", header_color_right, distro)
        ags = []
        for agent in header['agents'].split(","):
            agent = agent.strip()
            ags.append({ "vms" : "VMS", "linux":"Linux", "aix": "AIX", "solaris":"Solaris", "windows":"Windows", "snmp":"SNMP"}.get(agent, agent.upper()))
        print_splitline(header_color_left, "Supported Agents:  ", header_color_right, ", ".join(ags))
        if checkname in snmp_info_single:
            print_splitline(header_color_left, "Required MIB:      ", header_color_right, snmp_info_single[checkname][0])

        empty_line()
        print_textbody(header['description'])
        if 'item' in header:
            print_subheader("Item")
            print_textbody(header['item'])

        print_subheader("Check parameters")
        if sections.has_key('parameters'):
            if opt_nowiki:
                print "<table><th>Parameter</th><th>Type</th><th>Description</th></tr>"
            first = True
            for name, text in sections['parameters']:
                if not first:
                    empty_line()
                first = False
                print_splitwrap(parameters_color, name + ": ", normal_color, text)
            if opt_nowiki:
                print "</table>"
        else:
            print_line("None.")

        print_subheader("Performance data")
        if header.has_key('perfdata'):
            print_textbody(header['perfdata'])
        else:
            print_textbody("None.")

        print_subheader("Inventory")
        if header.has_key('inventory'):
            print_textbody(header['inventory'])
        else:
            print_textbody("No inventory supported.")

        print_subheader("Configuration variables")
        if sections.has_key('configuration'):
            if opt_nowiki:
                print "<table><th>Variable</th><th>Type</th><th>Description</th></tr>"
            first = True
            for name, text in sections['configuration']:
                if not first:
                    empty_line()
                first = False
                print_splitwrap(tty(2,4,1), name + ": ", tty_normal + tty(7,4), text)
            if opt_nowiki:
                print "</table>"
        else:
            print_line("None.")

        if header.has_key("examples"):
            print_subheader("Examples")
            lines = header['examples'].split('\n')
            if opt_nowiki:
                print "F+:main.mk"
            for line in lines:
                if line.lstrip().startswith('#'):
                    print_line(line)
                elif line != "<br>":
                    print_line(line, examples_color, True) # nomarkup
            if opt_nowiki:
                print "F-:"

        empty_line()
        output.flush()
        output.close()
    except Exception, e:
        print "Invalid check manpage %s: missing %s" % (filename, e)

#   +----------------------------------------------------------------------+
#   |                  ____             _                                  |
#   |                 | __ )  __ _  ___| | ___   _ _ __                    |
#   |                 |  _ \ / _` |/ __| |/ / | | | '_ \                   |
#   |                 | |_) | (_| | (__|   <| |_| | |_) |                  |
#   |                 |____/ \__,_|\___|_|\_\\__,_| .__/                   |
#   |                                             |_|                      |
#   +----------------------------------------------------------------------+

class fake_file:
    def __init__(self, content):
        self.content = content
        self.pointer = 0

    def size(self):
        return len(self.content)

    def read(self, size):
        new_end = self.pointer + size
        data = self.content[self.pointer:new_end]
        self.pointer = new_end
        return data

def do_backup(tarname):
    import tarfile
    if opt_verbose:
        sys.stderr.write("Creating backup file '%s'...\n" % tarname)
    tar = tarfile.open(tarname, "w:gz")


    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths:
        absdir = os.path.abspath(path)
        if os.path.exists(path):
            if opt_verbose:
                sys.stderr.write("  Adding %s (%s) " %  (descr, absdir))
            if is_dir:
                basedir = absdir
                filename = "."
                subtarname = name + ".tar"
                subdata = os.popen("tar cf - --dereference --force-local -C '%s' '%s'" % \
                                   (basedir, filename)).read()
            else:
                basedir = os.path.dirname(absdir)
                filename = os.path.basename(absdir)
                subtarname = canonical_name
                subdata = file(absdir).read()

            info = tarfile.TarInfo(subtarname)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = len(subdata)
            info.mode = 0644
            info.type = tarfile.REGTYPE
            info.name = subtarname
            if opt_verbose:
                sys.stderr.write("(%d bytes)...\n" % info.size)
            tar.addfile(info, fake_file(subdata))

    tar.close()
    if opt_verbose:
        sys.stderr.write("Successfully created backup.\n")


def do_restore(tarname):
    import tarfile, shutil

    if opt_verbose:
        sys.stderr.write("Restoring from '%s'...\n" % tarname)

    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths:
        absdir = os.path.abspath(path)
        if is_dir:
            basedir = absdir
            filename = "."
            if os.path.exists(absdir):
                if opt_verbose:
                    sys.stderr.write("  Deleting old contents of '%s'\n" % absdir)
                shutil.rmtree(absdir)
        else:
            basedir = os.path.dirname(absdir)
            filename = os.path.basename(absdir)
            canonical_path = basedir + "/" + canonical_name
            if os.path.exists(canonical_path):
                if opt_verbose:
                    sys.stderr.write("  Deleting old version of '%s'\n" % canonical_path)
                os.remove(canonical_path)

        if not os.path.exists(basedir):
            if opt_verbose:
                sys.stderr.write("  Creating directory %s\n" %  basedir)
            os.makedirs(basedir)

        if opt_verbose:
            sys.stderr.write("  Extracting %s (%s)\n" % (descr, absdir))
        if is_dir:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null "
                      "| tar xf - -C '%s' '%s' 2>/dev/null" % \
                      (tarname, name + ".tar", basedir, filename))
        else:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null > '%s' 2>/dev/null" %
                      (tarname, filename, canonical_path))

        if i_am_root():
            if owned_by_nagios:
                to_user = str(nagios_user)
            else:
                to_user = "root"
            if group_www and www_group != None:
                to_group = ":" + str(www_group)
                if opt_verbose:
                    sys.stderr.write("  Adding group write permissions\n")
                    os.system("chmod -R g+w '%s'" % absdir)
            else:
                to_group = ":root"
            if opt_verbose:
                sys.stderr.write("  Changing ownership to %s%s\n" % (to_user, to_group))
            os.system("chown -R '%s%s' '%s' 2>/dev/null" % (to_user, to_group, absdir))

    if opt_verbose:
        sys.stderr.write("Successfully restored backup.\n")


def do_flush(hosts):
    if len(hosts) == 0:
        hosts = all_active_hosts() + all_active_clusters()
    for host in hosts:
        sys.stdout.write("%-20s: " % host)
        sys.stdout.flush()
        flushed = False

        # counters
        try:
            os.remove(counters_directory + "/" + host)
            sys.stdout.write(tty_blue + " counters")
            sys.stdout.flush()
            flushed = True
        except:
            pass

        # cache files
        d = 0
        dir = tcp_cache_dir
        for f in os.listdir(dir):
            if f == host or f.startswith(host + "."):
                try:
                    os.remove(dir + "/" + f)
                    d += 1
                    flushed = True
                except:
                    pass
        if d == 1:
            sys.stdout.write(tty_green + " cache")
        elif d > 1:
            sys.stdout.write(tty_green + " cache(%d)" % d)
        sys.stdout.flush()

        # logfiles
        dir = logwatch_dir + "/" + host
        if os.path.exists(dir):
            d = 0
            for f in os.listdir(dir):
                if f not in [".", ".."]:
                    try:
                        os.remove(dir + "/" + f)
                        d += 1
                        flushed = True
                    except:
                        pass
            if d > 0:
                sys.stdout.write(tty_magenta + " logfiles(%d)" % d)
        if not flushed:
            sys.stdout.write("(nothing)")

        sys.stdout.write(tty_normal + "\n")


#   +----------------------------------------------------------------------+
#   |   __  __       _        __                  _   _                    |
#   |  |  \/  | __ _(_)_ __  / _|_   _ _ __   ___| |_(_) ___  _ __  ___    |
#   |  | |\/| |/ _` | | '_ \| |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|   |
#   |  | |  | | (_| | | | | |  _| |_| | | | | (__| |_| | (_) | | | \__ \   |
#   |  |_|  |_|\__,_|_|_| |_|_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Create a list of all hosts of a certain hostgroup. Needed only for
# option --list-hosts
def list_all_hosts(hostgroups):
    hostlist = []
    for hn in all_active_hosts() + all_active_clusters():
        if len(hostgroups) == 0:
            hostlist.append(hn)
        else:
            for hg in hostgroups_of(hn):
                if hg in hostgroups:
                    hostlist.append(hn)
                    break
    return hostlist

# Same for host tags, needed for --list-tag
def list_all_hosts_with_tags(tags):
    hosts = []
    for h in all_active_hosts() + all_active_clusters():
        if hosttags_match_taglist(tags_of_host(h), tags):
            hosts.append(h)
    return hosts


# Implementation of option -d
def output_plain_hostinfo(hostname):
    try:
        ipaddress = lookup_ipaddress(hostname)
        sys.stdout.write(get_agent_info(hostname, ipaddress, 0))
    except MKAgentError, e:
        sys.stderr.write("Problem contacting agent: %s\n" % (e,))
        sys.exit(3)
    except MKGeneralException, e:
        sys.stderr.write("General problem: %s\n" % (e,))
        sys.exit(3)
    except socket.gaierror, e:
        sys.stderr.write("Network error: %s\n" % e)
    except Exception, e:
        sys.stderr.write("Unexpected exception: %s\n" % (e,))
        sys.exit(3)

def do_snmpwalk(hostnames):
    if len(hostnames) == 0:
        sys.stderr.write("Please specify host names to walk on.\n")
        return
    if not os.path.exists(snmpwalks_dir):
        os.makedirs(snmpwalks_dir)
    for host in hostnames:
        try:
            do_snmpwalk_on(host, snmpwalks_dir + "/" + host)
        except Exception, e:
            sys.stderr.write("Error walking %s: %s\n" % (host, e))
            if opt_debug:
                raise

def do_snmpwalk_on(hostname, filename):
    if opt_verbose:
        sys.stdout.write("%s:\n" % hostname)
    ip = lookup_ipaddress(hostname)
    cmd = snmp_walk_command(hostname) + " -On -Ob -OQ %s " % ip
    if opt_debug:
        print 'Executing: %s' % cmd
    out = file(filename, "w")
    for oid in [ "", "1.3.6.1.4.1" ]: # SNMPv2-SMI::enterprises
        oids = []
        values = []
        if opt_verbose:
            sys.stdout.write("%s..." % (cmd + oid))
            sys.stdout.flush()
        count = 0
        f = os.popen(cmd + oid)
        while True:
            line = f.readline()
            if not line:
                break
            parts = line.strip().split("=", 1)
            if len(parts) != 2:
                continue
            oid, value = parts
            if value.strip().startswith('"'):
                while value[-1] != '"':
                    value += f.readline().strip()

            if oid.startswith("."):
                oid = oid[1:]
            oids.append(oid)
            values.append(value)
        for oid, value in zip(oids, values):
            out.write("%s %s\n" % (oid, value.strip()))
            count += 1
        if opt_verbose:
            sys.stdout.write("%d variables.\n" % count)

    out.close()
    if opt_verbose:
        sys.stdout.write("Successfully Wrote %s%s%s.\n" % (tty_bold, filename, tty_normal))

def show_paths():
    inst = 1
    conf = 2
    data = 3
    pipe = 4
    local = 5
    dir = 1
    fil = 2

    paths = [
        ( modules_dir,                 dir, inst, "Main components of check_mk"),
        ( checks_dir,                  dir, inst, "Checks"),
        ( agents_dir,                  dir, inst, "Agents for operating systems"),
        ( doc_dir,                     dir, inst, "Documentatoin files"),
        ( web_dir,                     dir, inst, "Check_MK's web pages"),
        ( check_manpages_dir,          dir, inst, "Check manpages (for check_mk -M)"),
        ( lib_dir,                     dir, inst, "Binary plugins (architecture specific)"),
        ( pnp_templates_dir,           dir, inst, "Templates for PNP4Nagios"),
        ( pnp_rraconf_dir,             dir, inst, "RRA configuration for PNP4Nagios"),
        ( nagios_startscript,          fil, inst, "Startscript for Nagios daemon"),
        ( nagios_binary,               fil, inst, "Path to Nagios executable"),

        ( default_config_dir,          dir, conf, "Directory that contains main.mk"),
        ( check_mk_configdir,          dir, conf, "Directory containing further *.mk files"),
        ( nagios_config_file,          fil, conf, "Main configuration file of Nagios"),
        ( nagios_conf_dir,             dir, conf, "Directory where Nagios reads all *.cfg files"),
        ( apache_config_dir,           dir, conf, "Directory where Apache reads all config files"),
        ( htpasswd_file,               fil, conf, "Users/Passwords for HTTP basic authentication"),

        ( var_dir,                     dir, data, "Base working directory for variable data"),
        ( autochecksdir,               dir, data, "Checks found by inventory"),
        ( precompiled_hostchecks_dir,  dir, data, "Precompiled host checks"),
        ( snmpwalks_dir,               dir, data, "Stored snmpwalks (output of --snmpwalk)"),
        ( counters_directory,          dir, data, "Current state of performance counters"),
        ( tcp_cache_dir,               dir, data, "Cached output from agents"),
        ( logwatch_dir,                dir, data, "Unacknowledged logfiles of logwatch extension"),
        ( nagios_objects_file,         fil, data, "File into which Nagios configuration is written"),
        ( rrd_path,                    dir, data, "Base directory of round robin databases"),
        ( nagios_status_file,          fil, data, "Path to Nagios status.dat"),

        ( nagios_command_pipe_path,    fil, pipe, "Nagios command pipe"),
        ( livestatus_unix_socket,      fil, pipe, "Socket of Check_MK's livestatus module"),
        ]

    if omd_root:
        paths += [
         ( local_checks_dir,           dir, local, "Locally installed checks"),
         ( local_check_manpages_dir,   dir, local, "Locally installed check man pages"),
         ( local_agents_dir,           dir, local, "Locally installed agents and plugins"),
         ( local_web_dir,              dir, local, "Locally installed Multisite addons"),
         ( local_pnp_templates_dir,    dir, local, "Locally installed PNP templates"),
         ( local_pnp_rraconf_dir,      dir, local, "Locally installed PNP RRA configuration"),
         ( local_doc_dir,              dir, local, "Locally installed documentation"),
        ]

    def show_paths(title, t):
        if t != inst:
            print
        print(tty_bold + title + tty_normal)
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == dir:
                    path += "/"
                print("  %-47s: %s%s%s" % (descr, tty_bold + tty_blue, path, tty_normal))

    for title, t in [
        ( "Files copied or created during installation", inst ),
        ( "Configuration files edited by you", conf ),
        ( "Data created by Nagios/Check_MK at runtime", data ),
        ( "Sockets and pipes", pipe ),
        ( "Locally installed addons", local ),
        ]:
        show_paths(title, t)

def dump_all_hosts(hostlist):
    if hostlist == []:
        hostlist = all_hosts_untagged + all_active_clusters()
    hostlist.sort()
    for hostname in hostlist:
        dump_host(hostname)

def dump_host(hostname):
    print
    if is_cluster(hostname):
        color = tty_bgmagenta
        add_txt = " (cluster of " + (",".join(nodes_of(hostname))) + ")"
    else:
        color = tty_bgblue
        add_txt = ""
    print "%s%s%s%-78s %s" % (color, tty_bold, tty_white, hostname + add_txt, tty_normal)

    tags = tags_of_host(hostname)
    print tty_yellow + "Tags:                   " + tty_normal + ", ".join(tags)
    if is_cluster(hostname):
        parents_list = nodes_of(hostname)
    else:
        parents_list = parents_of(hostname)
    if len(parents_list) > 0:
        print tty_yellow + "Parents:                " + tty_normal + ", ".join(parents_list)
    print tty_yellow + "Host groups:            " + tty_normal + ", ".join(hostgroups_of(hostname))
    print tty_yellow + "Contact groups:         " + tty_normal + ", ".join(host_contactgroups_of([hostname]))
    notperiod = (host_extra_conf(hostname, host_notification_periods) + [""])[0]
    print tty_yellow + "Notification:           " + tty_normal + notperiod
    agenttype = "TCP (port: %d)" % agent_port
    if is_snmp_host(hostname):
        credentials = snmp_credentials_of(hostname)
        if is_bulkwalk_host(hostname):
            bulk = "yes"
        else:
            bulk = "no"
        agenttype = "SNMP (community: '%s', bulk walk: %s)" % (credentials, bulk)
    print tty_yellow + "Type of agent:          " + tty_normal + agenttype
    is_aggregated = host_is_aggregated(hostname)
    if is_aggregated:
        print tty_yellow + "Is aggregated:          " + tty_normal + "yes"
        shn = summary_hostname(hostname)
        print tty_yellow + "Summary host:           " + tty_normal + shn
        print tty_yellow + "Summary host groups:    " + tty_normal + ", ".join(summary_hostgroups_of(hostname))
        print tty_yellow + "Summary contact groups: " + tty_normal + ", ".join(host_contactgroups_of([shn]))
        notperiod = (host_extra_conf(hostname, summary_host_notification_periods) + [""])[0]
        print tty_yellow + "Summary notification:   " + tty_normal + notperiod
    else:
        print tty_yellow + "Is aggregated:          " + tty_normal + "no"


    format_string = " %-15s %s%-10s %s%-17s %s%-14s%s %s%-16s%s"
    print tty_yellow + "Services:" + tty_normal
    check_items = get_sorted_check_table(hostname)
    # check_items.sort()
    headers = ["checktype", "item",    "params", "description", "groups", "summarized to", "groups"]
    colors =  [ tty_normal,  tty_blue, tty_normal, tty_green,     tty_normal, tty_red, tty_white ]
    if service_dependencies != []:
        headers.append("depends on")
        colors.append(tty_magenta)

    def if_aggr(a):
        if is_aggregated:
            return a
        else:
            return ""

    print_table(headers, colors, [ [
        checktype,
        item,
        params,
        description,
        ",".join(service_extra_conf(hostname, description, service_groups)),
        if_aggr(aggregated_service_name(hostname, description)),
        if_aggr(",".join(service_extra_conf(hostname, aggregated_service_name(hostname, description), summary_service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")

def print_table(headers, colors, rows, indent = ""):
    lengths = [ len(h) for h in headers ]
    for row in rows:
        lengths = [ max(len(str(c)), l) for c, l in zip(row, lengths) ]
    sumlen = sum(lengths) + len(headers)
    format = indent
    sep = ""
    for l,c in zip(lengths, colors):
        format += c + sep + "%-" + str(l) + "s" + tty_normal
        sep = " "

    first = True
    for row in [ headers ] + rows:
        print format % tuple(row[:len(headers)])
        if first:
            first = False
            print format % tuple([ "-" * l for l in lengths ])

def print_version():
    print """This is check_mk version %s
Copyright (C) 2009 Mathias Kettner

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; see the file COPYING.  If not, write to
    the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
    Boston, MA 02111-1307, USA.
""" % check_mk_version

def usage():
    print """WAYS TO CALL:
 check_mk [-n] [-v] [-p] HOST [IPADDRESS]  check all services on HOST
 check_mk [-u] -I [HOST ..]                inventory - find new services
 check_mk [-u] -II ...                     renew inventory, drop old services
 check_mk -u, --cleanup-autochecks         reorder autochecks files
 check_mk -N [HOSTS...]                    output Nagios configuration
 check_mk -C, --compile                    precompile host checks
 check_mk -U, --update                     precompile + create Nagios config
 check_mk -O, --reload                     precompile + config + Nagios reload
 check_mk -R, --restart                    precompile + config + Nagios restart
 check_mk -D, --dump [H1 H2 ..]            dump all or some hosts
 check_mk -d HOSTNAME|IPADDRESS            show raw information from agent
 check_mk --check-inventory HOSTNAME       check for items not yet checked
 check_mk --list-hosts [G1 G2 ...]         print list of hosts
 check_mk --list-tag TAG1 TAG2 ...         list hosts having certain tags
 check_mk -L, --list-checks                list all available check types
 check_mk -M, --man [CHECKTYPE]            show manpage for check CHECKTYPE
 check_mk --paths                          list all pathnames and directories
 check_mk -X, --check-config               check configuration for invalid vars
 check_mk --backup BACKUPFILE.tar.gz       make backup of configuration and data
 check_mk --restore BACKUPFILE.tar.gz      restore configuration and data
 check_mk --flush [HOST1 HOST2...]         flush all data of some or all hosts
 check_mk --donate                         Email data of configured hosts to MK
 check_mk --snmpwalk HOST1 HOST2 ...       Do snmpwalk on host
 check_mk --scan-parents [HOST1 HOST2...]  autoscan parents, create conf.d/parents.mk
 check_mk -P, --package COMMAND            do package operations
 check_mk -V, --version                    print version
 check_mk -h, --help                       print this help

OPTIONS:
  -v             show what's going on
  -p             also show performance data (use with -v)
  -n             do not submit results to Nagios, do not save counters
  -c FILE        read config file FILE instead of %s
  --cache        read info from cache file is present and fresh, use TCP
                 only, if cache file is absent or too old
  --no-cache     never use cached information
  --no-tcp       for -I: only use cache files. Skip hosts without
                 cache files.
  --fake-dns IP  fake IP addresses of all hosts to be IP. This
                 prevents DNS lookups.
  --usewalk      use snmpwalk stored with --snmpwalk
  --debug        never catch Python exceptions
  --procs N      start up to N processes in parallel during --scan-parents
  --checks A,..  restrict inventory to specified checks (tcp/snmp/check type)

NOTES:
  -I can be restricted to certain check types. Write '-I --checks df' if you
  just want to look for new filesystems. Use 'check_mk -L' for a list
  of all check types. Use 'tcp' for all TCP based checks and 'snmp' for
  all SNMP based checks.

  -II does the same as -I but deletes all existing checks of the
  specified types and hosts.

  -u, --cleanup-autochecks resorts all checks found by inventory
  into per-host files. It can be used as an options to -I or as
  a standalone operation.

  -N outputs the Nagios configuration. You may optionally add a list
  of hosts. In that case the configuration is generated only for
  that hosts (useful for debugging).

  -U redirects both the output of -S and -H to the file %s
  and also calls check_mk -C.

  -D, --dump dumps out the complete configuration and information
  about one, several or all hosts. It shows all services, hostgroups,
  contacts and other information about that host.

  -d does not work on clusters (such defined in main.mk) but only on
  real hosts.

  --check-inventory make check_mk behave as Nagios plugins that
  checks if an inventory would find new services for the host.

  --list-hosts called without argument lists all hosts. You may
  specify one or more host groups to restrict the output to hosts
  that are in at least one of those groups.

  --list-tag prints all hosts that have all of the specified tags
  at once.

  -M, --manpage shows documentation about a check type. If
  /usr/bin/less is available it is used as pager. Exit by pressing
  Q. Use -M without an argument to show a list of all manual pages.

  --backup saves all configuration and runtime data to a gzip
  compressed tar file. --restore *erases* the current configuration
  and data and replaces it with that from the backup file.

  --flush deletes all runtime data belonging to a host (not
  inventory data). This includes the state of performance counters,
  cached agent output,  and logfiles. Precompiled host checks
  are not deleted.

  -P, --package brings you into packager mode. Packages are
  used to ship inofficial extensions of Check_MK. Call without
  arguments for a help on packaging.

  --donate is for those who decided to help the Check_MK project
  by donating live host data. It tars the cached agent data of
  those host which are configured in main.mk:donation_hosts and sends
  them via email to donatehosts@mathias-kettner.de. The host data
  is then publicly available for others and can be used for setting
  up demo sites, implementing checks and so on.
  Do this only with test data from test hosts - not with productive
  data! By donating real-live host data you help others trying out
  Check_MK and developing checks by donating hosts. This is completely
  voluntary and turned off by default.

  --snmpwalk does a complete snmpwalk for the specifies hosts both
  on the standard MIB and the enterprises MIB and stores the
  result in the directory %s.

  --scan-parents uses traceroute in order to automatically detect
  hosts's parents. It creates the file conf.d/parents.mk which
  defines gateway hosts and parent declarations.

  Nagios can call check_mk without options and the hostname and its IP
  address as arguments. Much faster is using precompiled host checks,
  though.


""" % (check_mk_configfile,
       precompiled_hostchecks_dir,
       snmpwalks_dir,
       )


def do_create_config():
    out = file(nagios_objects_file, "w")
    sys.stdout.write("Generating Nagios configuration...")
    sys.stdout.flush()
    create_nagios_config(out)
    sys.stdout.write(tty_ok + "\n")

def do_output_nagios_conf(args):
    if len(args) == 0:
        args = None
    create_nagios_config(sys.stdout, args)

def do_precompile_hostchecks():
    sys.stdout.write("Precompiling host checks...")
    sys.stdout.flush()
    precompile_hostchecks()
    sys.stdout.write(tty_ok + "\n")


def do_update():
    try:
        do_create_config()
        do_precompile_hostchecks()
        sys.stdout.write(("Successfully created Nagios configuration file %s%s%s.\n\n" +
                         "Please make sure that file will be read by Nagios.\n" +
                         "You need to restart Nagios in order to activate " +
                         "the changes.\n") % (tty_green + tty_bold, nagios_objects_file, tty_normal))

    except Exception, e:
        sys.stderr.write("Configuration Error: %s\n" % e)
        if opt_debug:
            raise
        sys.exit(1)


def do_check_nagiosconfig():
    command = nagios_binary + " -v "  + nagios_config_file + " 2>&1"
    sys.stdout.write("Validating Nagios configuration...")
    if opt_verbose:
        sys.stderr.write("Running '%s'" % command)
    sys.stderr.flush()

    process = os.popen(command, "r")
    output = process.read()
    exit_status = process.close()
    if not exit_status:
        sys.stdout.write(tty_ok + "\n")
        return True
    else:
        sys.stdout.write("ERROR:\n")
        sys.stderr.write(output)
        return False


def do_restart_nagios(only_reload):
    action = only_reload and "load" or "start"
    sys.stdout.write("Re%sing Nagios..." % action)
    sys.stdout.flush()
    command = nagios_startscript + " re%s 2>&1" % action
    process = os.popen(command, "r")
    output = process.read()
    if process.close():
        sys.stdout.write("ERROR:\n")
        raise MKGeneralException("Cannot re%s Nagios" % action)
    else:
        sys.stdout.write(tty_ok + "\n")

def do_reload():
    do_restart(True)

def do_restart(only_reload = False):
    try:
        # Save current configuration
        if os.path.exists(nagios_objects_file):
            backup_path = nagios_objects_file + ".save"
            if opt_verbose:
                sys.stderr.write("Renaming %s to %s\n" % (nagios_objects_file, backup_path))
            os.rename(nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
            do_create_config()
        except Exception, e:
            sys.stderr.write("Error creating configuration: %s\n" % e)
            os.rename(backup_path, nagios_objects_file)
            if opt_debug:
                raise
            sys.exit(1)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            do_precompile_hostchecks()
            do_restart_nagios(only_reload)
        else:
            sys.stderr.write("Nagios configuration is invalid. Rolling back.\n")
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            else:
                os.remove(nagios_objects_file)
            sys.exit(1)

    except Exception, e:
        try:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
        except:
            pass
        if opt_debug:
            raise
        sys.stderr.write("An error occurred: %s\n" % e)
        sys.exit(1)

def do_donation():
    donate = []
    cache_files = os.listdir(tcp_cache_dir)
    for host in all_hosts_untagged:
        if in_binary_hostlist(host, donation_hosts):
            for f in cache_files:
                if f == host or f.startswith("%s." % host):
                    donate.append(f)
    if opt_verbose:
        print "Donating files %s" % " ".join(cache_files)
    import base64
    indata = base64.b64encode(os.popen("tar czf - -C %s %s" % (tcp_cache_dir, " ".join(donate))).read())
    output = os.popen(donation_command, "w")
    output.write("\n\n@STARTDATA\n")
    while len(indata) > 0:
        line = indata[:64]
        output.write(line)
        output.write('\n')
        indata = indata[64:]

def do_cleanup_autochecks():
    # 1. Read in existing autochecks
    hostdata = {}
    os.chdir(autochecksdir)
    checks = 0
    for fn in glob.glob("*.mk"):
        if opt_debug:
            sys.stdout.write("Scanning %s...\n" % fn)
        for line in file(fn):
            testline = line.lstrip().replace("'", '"')
            if testline.startswith('("'):
                splitted = testline.split('"')
                hostname = splitted[1]
                hostchecks = hostdata.get(hostname, [])
                hostchecks.append(line)
                checks += 1
                hostdata[hostname] = hostchecks
    if opt_verbose:
        sys.stdout.write("Found %d checks from %d hosts.\n" % (checks, len(hostdata)))

    # 2. Write out new autochecks.
    newfiles = set([])
    for host, lines in hostdata.items():
        lines.sort()
        fn = host.replace(":","_") + ".mk"
        if opt_verbose:
            sys.stdout.write("Writing %s: %d checks\n" % (fn, len(lines)))
        newfiles.add(fn)
        f = file(fn, "w+")
        f.write("[\n")
        for line in lines:
            f.write(line)
        f.write("]\n")

    # 3. Remove obsolete files
    for f in glob.glob("*.mk"):
        if f not in newfiles:
            if opt_verbose:
                sys.stdout.write("Deleting %s\n" % f)
            os.remove(f)

def do_scan_parents(hosts):
    global max_num_processes
    if len(hosts) == 0:
        hosts = filter(lambda h: in_binary_hostlist(h, scanparent_hosts), all_hosts_untagged)

    found = []
    parent_hosts = []
    parent_ips   = {}
    parent_rules = []
    gateway_hosts = set([])

    if max_num_processes < 1:
        max_num_processes = 1

    sys.stdout.write("Scanning for parents (%d processes)..." % max_num_processes)
    sys.stdout.flush()
    while len(hosts) > 0:
        chunk = []
        while len(chunk) < max_num_processes and len(hosts) > 0:
            host = hosts[0]
            del hosts[0]
            # skip hosts that already have a parent
            if len(parents_of(host)) > 0:
                if opt_verbose:
                    sys.stdout.write("(manual parent) ")
                    sys.stdout.flush()
                continue
            chunk.append(host)

        gws = scan_parents_of(chunk)

        for host, gw in zip(chunk, gws):
            if gw:
                gateway, gateway_ip = gw
                if not gateway: # create artificial host
                    gateway = "gw-%s" % (gateway_ip.replace(".", "-"))
                    if gateway not in gateway_hosts:
                        gateway_hosts.add(gateway)
                        parent_hosts.append("%s|parent" % gateway)
                        parent_ips[gateway] = gateway_ip
                        parent_rules.append( (monitoring_host, [gateway]) ) # make Nagios a parent of gw
                parent_rules.append( (gateway, [host]) )
            elif host != monitoring_host:
                # make monitoring host the parent of all hosts without real parent
                parent_rules.append( (monitoring_host, [host]) )

    import pprint
    outfilename = check_mk_configdir + "/parents.mk"
    out = file(outfilename, "w")
    out.write("# Automatically created by --scan-parents at %s\n\n" % time.asctime())
    out.write("# Do not edit this file. If you want to convert an\n")
    out.write("# artificial gateway host into a permanent one, then\n")
    out.write("# move its definition into another *.mk file\n")

    out.write("# Parents which are not listed in your all_hosts:\n")
    out.write("all_hosts += %s\n\n" % pprint.pformat(parent_hosts))

    out.write("# IP addresses of parents not listed in all_hosts:\n")
    out.write("ipaddresses.update(%s)\n\n" % pprint.pformat(parent_ips))

    out.write("# Parent definitions\n")
    out.write("parents += %s\n\n" % pprint.pformat(parent_rules))
    sys.stdout.write("\nWrote %s\n" % outfilename)


def scan_parents_of(hosts):
    nagios_ip = lookup_ipaddress(monitoring_host)
    os.putenv("LANG", "")
    os.putenv("LC_ALL", "")

    # Start processes in parallel
    procs = []
    for host in hosts:
        if opt_verbose:
            sys.stdout.write("%s " % host)
            sys.stdout.flush()
        try:
            ip = lookup_ipaddress(host)
        except:
            sys.stderr.write("%s: cannot resolve host name\n" % host)
            ip = None
        command = "traceroute -m 15 -n -w 3 %s" % ip
        if opt_debug:
            sys.stderr.write("Running '%s'\n" % command)
        procs.append( (host, ip, os.popen(command) ) )

    # Now all run and we begin to read the answers
    def dot(color, dot='o'):
        sys.stdout.write(tty_bold + color + dot + tty_normal)
        sys.stdout.flush()

    gateways = []
    for host, ip, proc in procs:
        lines = [l.strip() for l in proc.readlines()]
        exitstatus = proc.close()
        if exitstatus:
            dot(tty_red, '*')
            gateways.append(None)
            continue

        if len(lines) == 0:
            if opt_debug:
                raise MKGeneralException("Cannot execute %s. Is traceroute installed? Are you root?" % command)
            else:
                dot(tty_red, '!')
        elif len(lines) < 2:
            sys.stderr.write("%s: %s\n" % (host, ' '.join(lines)))
            gateways.append(None)
            dot(tty_blue)
            continue

        # Parse output of traceroute:
        # traceroute to 8.8.8.8 (8.8.8.8), 30 hops max, 40 byte packets
        #  1  * * *
        #  2  10.0.0.254  0.417 ms  0.459 ms  0.670 ms
        #  3  172.16.0.254  0.967 ms  1.031 ms  1.544 ms
        #  4  217.0.116.201  23.118 ms  25.153 ms  26.959 ms
        #  5  217.0.76.134  32.103 ms  32.491 ms  32.337 ms
        #  6  217.239.41.106  32.856 ms  35.279 ms  36.170 ms
        #  7  74.125.50.149  45.068 ms  44.991 ms *
        #  8  * 66.249.94.86  41.052 ms 66.249.94.88  40.795 ms
        #  9  209.85.248.59  43.739 ms  41.106 ms 216.239.46.240  43.208 ms
        # 10  216.239.48.53  45.608 ms  47.121 ms 64.233.174.29  43.126 ms
        # 11  209.85.255.245  49.265 ms  40.470 ms  39.870 ms
        # 12  8.8.8.8  28.339 ms  28.566 ms  28.791 ms
        routes = []
        for line in lines[1:]:
            parts = line.split()
            route = parts[1]
            if route.count('.') == 3:
                routes.append(route)
            elif route == '*':
                routes.append(None) # No answer from this router
            else:
                sys.stderr.write("%s: invalid output line from traceroute: '%s'\n" % (host, line))

        if len(routes) == 0:
            sys.stderr.write("%s: incomplete output from traceroute. No routes found.\n" % host)
            gateways.append(None)
            dot(tty_red)
            continue

        # Only one entry -> host is directly reachable and gets nagios as parent -
        # if nagios is not the parent itself. Problem here: How can we determine
        # if the host in question is the monitoring host? The user must configure
        # this in monitoring_host.
        elif len(routes) == 1:
            if ip == nagios_ip:
                gateways.append(None) # We are the monitoring host
                dot(tty_white, 'N')
            else:
                gateways.append( (monitoring_host, nagios_ip) )
                dot(tty_cyan, 'L')
            continue

        # Try far most route which is not identical with host itself
        route = None
        for r in routes[::-1]:
            if not r or (r == ip):
                continue
            route = r
            break
        if not route:
            sys.stderr.write("%s: No usable routing information\n" % host)
            gateways.append(None)
            dot(tty_blue)
            continue

        # TTLs already have been filtered out)
        gateway_ip = route
        gateway = ip_to_hostname(route)
        if opt_verbose:
            sys.stdout.write("%s(%s) " % (gateway, gateway_ip))
        gateways.append( (gateway, gateway_ip) )
        dot(tty_green, 'G')
    return gateways

# find hostname belonging to an ip address. We must not use
# reverse DNS but the Check_MK mechanisms
def ip_to_hostname(ip):
    global ip_to_hostname_cache
    if ip_to_hostname_cache == None:
        ip_to_hostname_cache = {}
        for host in all_hosts_untagged:
            try:
                ip_to_hostname_cache[lookup_ipaddress(host)] = host
            except:
                pass
    return ip_to_hostname_cache.get(ip)


#   +----------------------------------------------------------------------+
#   |        _         _                        _   _                      | 
#   |       / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __           |
#   |      / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \          |
#   |     / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |         |
#   |    /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|         |
#   |                                                                      | 
#   +----------------------------------------------------------------------+

class MKAutomationError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

def automation_try_inventory(args):
    hostname = args[0]
    try:
        ipaddress = lookup_ipaddress(hostname)
    except:
        raise MKAutomationError("Cannot lookup IP address of host %s" % hostname)

    f = []

    if is_snmp_host(hostname):
        f = do_snmp_scan([hostname], True, True)

    if is_tcp_host(hostname):
        for cn in inventorable_checktypes("tcp"):
            f += make_inventory(cn, [hostname], True, True)

    found = {}
    for hn, ct, item, paramstring, state_type in f:
       found[(ct, item)] = ( state_type, paramstring ) 

    # Check if already in autochecks (but not found anymore)
    for hn, ct, item, params in autochecks:
        if hn == hostname and (ct, item) not in found:
            found[(ct, item)] = ( 'vanished', repr(params) ) # This is not the real paramstring!

    # Find manual checks
    existing = get_check_table(hostname)
    for (ct, item), (params, descr, deps) in existing.items():
        if (ct, item) not in found:
            found[(ct, item)] = ('manual', repr(params) )
        
    # Add legacy checks with artificial type 'legacy'
    legchecks = host_extra_conf(hostname, legacy_checks)
    for cmd, descr, perf in legchecks:
        found[('legacy', descr)] = ( 'legacy', 'None' )

    table = []
    for (ct, item), (state_type, paramstring) in found.items():
        if state_type != 'legacy':
            descr = service_description(ct, item)
            infotype = ct.split('.')[0]
            opt_use_cachefile = True
            opt_no_tcp = True
            info = get_host_info(hostname, ipaddress, infotype)
            check_function = check_info[ct][0]
            # apply check_parameters
            try:
                if type(paramstring) == str:
                    params = eval(paramstring)
                else:
                    params = paramstring
            except:
                raise MKAutomationError("Invalid check parameter string '%s'" % paramstring)
            if state_type != 'manual':
                e = service_extra_conf(hostname, descr, check_parameters)
                if len(e) > 0:
                    params = e[0]

            try:
                result = check_function(item, params, info)
            except MKCounterWrapped, e:
                result = (None, "WAITING - Counter based check, cannot be done offline")
            except Exception, e:
                result = (3, "UNKNOWN - invalid output from agent or error in check implementation")
            if len(result) == 2:
                result = (result[0], result[1], [])
            exitcode, output, perfdata = result
        else:
            descr = item
            exitcode = None
            output = "WAITING - Legacy check, cannot be done offline"
            perfdata = []
        table.append((state_type, ct, item, paramstring, params, descr, exitcode, output, perfdata))

    return table

# Set the new list of autochecks. This list is specified by a 
# table of (checktype, item). No parameters are specified. Those
# are either (1) kept from existing autochecks or (2) computed
# from a new inventory. Note: we must never convert check parameters
# from python source code to actual values.
def automation_set_autochecks(args):
    hostname = args[0]
    new_items = eval(sys.stdin.read())

    do_cleanup_autochecks()
    existing = automation_parse_autochecks_file(hostname)

    # write new autochecks file, but take paramstrings from existing ones
    # for those checks which are kept
    new_autochecks = []
    for ct, item, params, paramstring in existing:
        if (ct, item) in new_items:
            new_autochecks.append((ct, item, paramstring))
            del new_items[(ct, item)]

    for (ct, item), paramstring in new_items.items():
        new_autochecks.append((ct, item, paramstring))

    # write new autochecks file for that host
    automation_write_autochecks_file(hostname, new_autochecks)


def automation_get_autochecks(args):
    hostname = args[0]
    do_cleanup_autochecks()
    return automation_parse_autochecks_file(hostname)

def automation_write_autochecks_file(hostname, table):
    if not os.path.exists(autochecksdir):
        os.makedirs(autochecksdir)
    path = "%s/%s.mk" % (autochecksdir, hostname)
    f = file(path, "w")
    f.write("# Autochecks for host %s, created by Check_MK automation\n[\n" % hostname)
    for ct, item, paramstring in table:
        f.write("  (%r, %r, %r, %s),\n" % (hostname, ct, item, paramstring))
    f.write("]\n")

def automation_parse_autochecks_file(hostname):
    def split_python_tuple(line):
        quote = None
        bracklev = 0
        backslash = False
        for i, c in enumerate(line):
            if backslash:
                backslash = False
                continue
            elif c == '\\':
                backslash = True
            elif c == quote:
                quote = None # end of quoted string
            elif c in [ '"', "'" ]:
                quote = c # begin of quoted string
            elif quote:
                continue
            elif c in [ '(', '{', '[' ]:
                bracklev += 1
            elif c in [ ')', '}', ']' ]:
                bracklev -= 1
            elif bracklev > 0:
                continue
            elif c == ',':
                value = line[0:i]
                rest = line[i+1:]
                return value.strip(), rest
        return line.strip(), None

    path = "%s/%s.mk" % (autochecksdir, hostname)
    if not os.path.exists(path):
        return []
    lineno = 0

    table = []
    for line in file(path):
        lineno += 1
        try:
            line = line.strip()
            if not line.startswith("("): 
                continue
            if line.endswith(","):
                line = line[:-1]
            line = line[1:-1] # drop brackets

            hostnamestring, line = split_python_tuple(line) # should be hostname
            checktypestring, line = split_python_tuple(line)
            itemstring, line = split_python_tuple(line)
            paramstring, line = split_python_tuple(line)
            table.append((eval(checktypestring), eval(itemstring), eval(paramstring), paramstring))
        except:
            if opt_debug:
                raise
            raise MKAutomationError("Invalid line %d in autochecks file %s" % (lineno, path))
    return table

def automation_delete_host(args):
    hostname = args[0]
    for path in [
        "%s/%s"    % (precompiled_hostchecks_dir, hostname),
        "%s/%s.py" % (precompiled_hostchecks_dir, hostname),
        "%s/%s.mk" % (autochecksdir, hostname),
        "%s/%s"    % (logwatch_dir, hostname),
        "%s/%s"    % (counters_directory, hostname),
        "%s/%s"    % (tcp_cache_dir, hostname),
        "%s/%s.*"  % (tcp_cache_dir, hostname)]:
        os.system("rm -rf '%s'" % path)

def automation_restart():
    old_stdout = sys.stdout
    sys.stdout = file('/dev/null', 'w')
    try:
        if os.path.exists(nagios_objects_file):
            backup_path = nagios_objects_file + ".save"
            os.rename(nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
	    create_nagios_config(file(nagios_objects_file, "w"))
        except Exception, e:
	    if backup_path:
		os.rename(backup_path, nagios_objects_file)
	    raise MKAutomationError("Error creating configuration: %s" % e)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            do_precompile_hostchecks()
            do_restart_nagios(False)
        else:
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            else:
                os.remove(nagios_objects_file)
            raise MKAutomationError("Nagios configuration is invalid. Rolling back.")

    except Exception, e:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
        raise MKAutomationError(str(e))

    sys.stdout = old_stdout


def do_automation(cmd, args):
    try:
        if cmd == "try-inventory":
            result = automation_try_inventory(args)
        elif cmd == "get-autochecks":
            result = automation_get_autochecks(args)
        elif cmd == "set-autochecks":
            result = automation_set_autochecks(args)
        elif cmd == "delete-host":
            result = automation_delete_host(args)
        elif cmd == "restart":
	    result = automation_restart()
        else:
            raise MKAutomationError("Automation command '%s' is not implemented." % cmd)

    except MKAutomationError, e:
        sys.stderr.write("%s\n" % e)
        if opt_debug:
            raise
        sys.exit(1)
    except Exception, e:
        if opt_debug:
            raise
        else:
            sys.stderr.write("%s\n" % e)
            sys.exit(2)

    if opt_debug:
        import pprint
        sys.stdout.write(pprint.pformat(result)+"\n")
    else:
        sys.stdout.write("%r\n" % result)
    sys.exit(0)

#   +----------------------------------------------------------------------+
#   |         ____                _                    __ _                |
#   |        |  _ \ ___  __ _  __| |   ___ ___  _ __  / _(_) __ _          |
#   |        | |_) / _ \/ _` |/ _` |  / __/ _ \| '_ \| |_| |/ _` |         |
#   |        |  _ <  __/ (_| | (_| | | (_| (_) | | | |  _| | (_| |         |
#   |        |_| \_\___|\__,_|\__,_|  \___\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+


# Now - at last - we can read in the user's configuration files
def all_nonfunction_vars():
    return set([ name for name,value in globals().items() if name[0] != '_' and type(value) != type(lambda:0) ])

vars_before_config = all_nonfunction_vars()


list_of_files = [ check_mk_configfile ] + glob.glob(check_mk_configdir + '/*.mk')
final_mk = check_mk_basedir + "/final.mk"
if os.path.exists(final_mk):
    list_of_files.append(final_mk)
for _f in list_of_files:
    # Hack: during parent scan mode we must not read in old version of parents.mk!
    if '--scan-parents' in sys.argv and _f.endswith("/parents.mk"):
        continue
    try:
        if opt_debug:
            sys.stderr.write("Reading config file %s...\n" % _f)
        execfile(_f)
    except Exception, e:
        sys.stderr.write("Cannot read in configuration file %s:\n%s\n" % (_f, e))
        if __name__ == "__main__":
            sys.exit(3)
        else:
            raise

# Strip off host tags from the list of all_hosts.  Host tags can be
# appended to the hostnames in all_hosts, separated by pipe symbols,
# e.g. "zbghlnx04|bgh|linux|test" and are stored in a separate
# dictionary called 'hosttags'
hosttags = {}
for taggedhost in all_hosts + clusters.keys():
    parts = taggedhost.split("|")
    hosttags[parts[0]] = parts[1:]
all_hosts_untagged = all_active_hosts()

# Sanity check for duplicate hostnames
seen_hostnames = set([])
for hostname in strip_tags(all_hosts + clusters.keys()):
    if hostname in seen_hostnames:
        sys.stderr.write("Error in configuration: duplicate host '%s'\n" % hostname)
        sys.exit(4)
    seen_hostnames.add(hostname)

# Load python-rrd if available and not switched off.
if do_rrd_update:
    try:
        import rrdtool
    except:
        sys.stdout.write("ERROR: Cannot do direct rrd updates since the Python module\n"+
                         "'rrdtool' could not be loaded. Please install python-rrdtool\n"+
                         "or set do_rrd_update to False in main.mk.\n")
        sys.exit(3)

# read automatically generated checks. They are prepended to the check
# table: explicit user defined checks override automatically generated
# ones. Do not read in autochecks, if check_mk is called as module.
def read_all_autochecks():
    global autochecks
    autochecks = []
    for f in glob.glob(autochecksdir + '/*.mk'):
        try:
            autochecks += eval(file(f).read())
        except SyntaxError,e:
            sys.stderr.write("Syntax error in file %s: %s\n" % (f, e))
            sys.exit(3)
        except Exception, e:
            sys.stderr.write("Error in file %s:\n%s\n" % (f, e))
            sys.exit(3)
    # Exchange inventorized check parameters with those configured by
    # the user.
    if check_parameters != []:
        new_autochecks = []
        for autocheck in autochecks:
            host, checktype, item, params = autocheck
            descr = service_description(checktype, item)
            entries = service_extra_conf(host, descr, check_parameters)
            if len(entries) > 0:
                new_autochecks.append( (host, checktype, item, entries[0] ) )
            else:
                new_autochecks.append(autocheck) # leave unchanged
        autochecks = new_autochecks

if __name__ == "__main__":
    read_all_autochecks()
    checks = autochecks + checks

vars_after_config = all_nonfunction_vars()
ignored_variables = set(['vars_before_config', 'rrdtool', 'final_mk', 'list_of_files', 'autochecks',
                          'parts' ,'hosttags' ,'seen_hostnames' ,'all_hosts_untagged' ,'taggedhost' ,'hostname'])
errors = 0
for name in vars_after_config:
    if name not in ignored_variables and name not in vars_before_config:
        sys.stderr.write("Invalid configuration variable '%s'\n" % name)
        errors += 1

# Special handling for certain deprecated variables
if filesystem_levels != []:
    sys.stderr.write("WARNING: filesystem_levels is deprecated and will be removed\n"
        "any decade now. Please use check_parameters instead! Details can be\n"
        "found at http://mathias-kettner.de/checkmk_check_parameters.html.\n")

if type(snmp_communities) == dict:
    sys.stderr.write("ERROR: snmp_communities cannot be a dict any more.\n")
    errors += 1

if errors > 0:
    sys.stderr.write("--> Found %d invalid variables\n" % errors)
    sys.stderr.write("If you use own helper variables, please prefix them with _.\n")
    sys.exit(1)


# Convert www_group into numeric id
if type(www_group) == str:
    try:
        import grp
        www_group = grp.getgrnam(www_group)[2]
    except Exception, e:
        sys.stderr.write("Cannot convert group '%s' into group id: %s\n" % (www_group, e))
        sys.stderr.write("Please set www_group to an existing group in main.mk.\n")
        sys.exit(3)

# --------------------------------------------------------------------------
# FINISHED WITH READING IN USER DATA
# Now we are finished with reading in user data and can safely define
# further functions and variables without fear of name clashes with user
# defined variables.
# --------------------------------------------------------------------------

backup_paths = [
    # tarname               path                 canonical name   description                is_dir owned_by_nagios www_group
    ('check_mk_configfile', check_mk_configfile, "main.mk",       "Main configuration file",           False, False, False ),
    ('final_mk',            final_mk,            "final.mk",      "Final configuration file final.mk", False, False, False ),
    ('check_mk_configdir',  check_mk_configdir,  "",              "Configuration sub files",           True,  False, False ),
    ('autochecksdir',       autochecksdir,       "",              "Automatically inventorized checks", True,  False, False ),
    ('counters_directory',  counters_directory,  "",              "Performance counters",              True,  True,  False ),
    ('tcp_cache_dir',       tcp_cache_dir,       "",              "Agent cache",                       True,  True,  False ),
    ('logwatch_dir',        logwatch_dir,        "",              "Logwatch",                          True,  True,  True  ),
    ]


#   +----------------------------------------------------------------------+
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Do option parsing and execute main function -
# if check_mk is not called as module
if __name__ == "__main__":
    short_options = 'SHVLCURODMd:Ic:nhvpXPuN'
    long_options = [ "help", "version", "verbose", "compile", "debug",
                     "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
                     "flush", "package", "donate", "snmpwalk", "usewalk",
                     "scan-parents", "procs=", "automation=", 
                     "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                     "man", "nowiki", "config-check", "backup=", "restore=",
                     "check-inventory=", "paths", "cleanup-autochecks", "checks=" ]

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(1)

    done = False
    seen_I = 0
    inventory_checks = None
    # Scan modifying options first (makes use independent of option order)
    for o,a in opts:
        if o in [ '-v', '--verbose' ]:
            opt_verbose = True
        elif o == '-c':
            check_mk_configfile = a
        elif o == '--cache':
            opt_use_cachefile = True
            check_max_cachefile_age     = 1000000000
            inventory_max_cachefile_age = 1000000000
        elif o == '--no-tcp':
            opt_no_tcp = True
        elif o == '--no-cache':
            opt_no_cache = True
        elif o == '-p':
            opt_showperfdata = True
        elif o == '-n':
            opt_dont_submit = True
        elif o == '-u':
            opt_cleanup_autochecks = True
        elif o == '--fake-dns':
            fake_dns = a
        elif o == '--usewalk':
            opt_use_snmp_walk = True
        elif o == '--procs':
            max_num_processes = int(a)
        elif o == '--nowiki':
            opt_nowiki = True
        elif o == '--debug':
            opt_debug = True
        elif o == '-I':
            seen_I += 1
        elif o == "--checks":
            inventory_checks = a

    # Perform actions (major modes)
    try:
        for o,a in opts:
            if o in [ '-h', '--help' ]:
                usage()
                sys.exit(0)
            elif o in [ '-V', '--version' ]:
                print_version()
                sys.exit(0)
            elif o in [ '-X', '--config-check' ]:
                sys.exit(0) # already done
            elif o in [ '-S', '-H' ]:
                sys.stderr.write(tty_bold + tty_red + "ERROR" + tty_normal + "\n")
                sys.stderr.write("The options -S and -H have been replaced with the option -N. If you \n")
                sys.stderr.write("want to generate only the service definitions, please set \n")
                sys.stderr.write("'generate_hostconf = False' in main.mk.\n")
                done = True
            elif o == '-N':
                do_output_nagios_conf(args)
                done = True
            elif o in [ '-C', '--compile' ]:
                precompile_hostchecks()
                done = True
            elif o in [ '-U', '--update' ] :
                do_update()
                done = True
            elif o in [ '-R', '--restart' ] :
                do_restart()
                done = True
            elif o in [ '-O', '--reload' ] :
                do_reload()
                done = True
            elif o in [ '-D', '--dump' ]:
                dump_all_hosts(args)
                done = True
            elif o == '--backup':
                do_backup(a)
                done = True
            elif o ==  '--restore':
                do_restore(a)
                done = True
            elif o == '--flush':
                do_flush(args)
                done = True
            elif o == '--paths':
                show_paths()
                done = True
            elif o in ['-P', '--package']:
                execfile(modules_dir + "/packaging.py")
                do_packaging(args)
                done = True
            elif o == '--donate':
                do_donation()
                done = True
            elif o == '--snmpwalk':
                do_snmpwalk(args)
                done = True
            elif o in [ '-M', '--man' ]:
                if len(args) > 0:
                    show_check_manual(args[0])
                else:
                    list_all_manuals()
                done = True
            elif o == '--list-hosts':
                l = list_all_hosts(args)
                sys.stdout.write("\n".join(l))
                if l != []:
                    sys.stdout.write("\n")
                done = True
            elif o == '--list-tag':
                l = list_all_hosts_with_tags(args)
                sys.stdout.write("\n".join(l))
                if l != []:
                    sys.stdout.write("\n")
                done = True
            elif o in [ '-L', '--list-checks' ]:
                output_check_info()
                done = True
            elif o == '-d':
                output_plain_hostinfo(a)
                done = True
            elif o == '--check-inventory':
                check_inventory(a)
                done = True
            elif o == '--scan-parents':
                do_scan_parents(args)
                done = True
            elif o == '--automation':
                do_automation(a, args)
                done = True


    except MKGeneralException, e:
        sys.stderr.write("%s\n" % e)
        if opt_debug:
            raise
        sys.exit(3)

    if not done and seen_I > 0:

        hostnames = args
        if inventory_checks:
            checknames = inventory_checks.split(",")

        # remove existing checks, if option -I is used twice
        if seen_I > 1:
            if inventory_checks == None:
                checknames = inventorable_checktypes("all")
            if len(hostnames) > 0:
                for host in hostnames:
                    remove_autochecks_of(host, checknames)
            else:
                for host in all_active_hosts() + all_active_clusters():
                    remove_autochecks_of(host, checknames)
            reread_autochecks()

        if inventory_checks == None:
            do_snmp_scan(hostnames)
            checknames = inventorable_checktypes("tcp")
        
        for checkname in checknames:
            make_inventory(checkname, hostnames, False)

        # -u, --cleanup-autochecks called in stand alone mode
        if opt_cleanup_autochecks or always_cleanup_autochecks:
            do_cleanup_autochecks()
        done = True

    if not done and opt_cleanup_autochecks: # -u as standalone option
        do_cleanup_autochecks()
        done = True


    if done:
        sys.exit(0)
    elif len(args) == 0 or len(args) > 2:
        usage()
        sys.exit(1)
    else:

        hostname = args[0]
        if len(args) == 2:
            ipaddress = args[1]
        else:
            if is_cluster(hostname):
                ipaddress = None
            else:
                try:
                    ipaddress = lookup_ipaddress(hostname)
                except:
                    print "Cannot resolve hostname '%s'." % hostname
                    sys.exit(2)

        do_check(hostname, ipaddress)
