#!/usr/bin/env python

# Try to determine how much RAM is currently being used per program.
# Note per _program_, not per process. So for example this script
# will report RAM used by all httpd process together. In detail it reports:
# sum(private RAM for program processes) + sum(Shared RAM for program processes)
# The shared RAM is problematic to calculate, and this script automatically
# selects the most accurate method available for your kernel.

# Author: P@draigBrady.com
# Source: http://www.pixelbeat.org/scripts/ps_mem.py

# V1.0      06 Jul 2005     Initial release
# V1.1      11 Aug 2006     root permission required for accuracy
# V1.2      08 Nov 2006     Add total to output
#                           Use KiB,MiB,... for units rather than K,M,...
# V1.3      22 Nov 2006     Ignore shared col from /proc/$pid/statm for
#                           2.6 kernels up to and including 2.6.9.
#                           There it represented the total file backed extent
# V1.4      23 Nov 2006     Remove total from output as it's meaningless
#                           (the shared values overlap with other programs).
#                           Display the shared column. This extra info is
#                           useful, especially as it overlaps between programs.
# V1.5      26 Mar 2007     Remove redundant recursion from human()
# V1.6      05 Jun 2007     Also report number of processes with a given name.
#                           Patch from riccardo.murri@gmail.com
# V1.7      20 Sep 2007     Use PSS from /proc/$pid/smaps if available, which
#                           fixes some over-estimation and allows totalling.
#                           Enumerate the PIDs directly rather than using ps,
#                           which fixes the possible race between reading
#                           RSS with ps, and shared memory with this program.
#                           Also we can show non truncated command names.
# V1.8      28 Sep 2007     More accurate matching for stats in /proc/$pid/smaps
#                           as otherwise could match libraries causing a crash.
#                           Patch from patrice.bouchand.fedora@gmail.com
# V1.9      20 Feb 2008     Fix invalid values reported when PSS is available.
#                           Reported by Andrey Borzenkov <arvidjaar@mail.ru>
# V2.6      13 Aug 2011
#   http://github.com/pixelb/scripts/commits/master/scripts/ps_mem.py

# Notes:
#
# All interpreted programs where the interpreter is started
# by the shell or with env, will be merged to the interpreter
# (as that's what's given to exec). For e.g. all python programs
# starting with "#!/usr/bin/env python" will be grouped under python.
# You can change this by using the full command line but that will
# have the undesirable affect of splitting up programs started with
# differing parameters (for e.g. mingetty tty[1-6]).
#
# For 2.6 kernels up to and including 2.6.13 and later 2.4 redhat kernels
# (rmap vm without smaps) it can not be accurately determined how many pages
# are shared between processes in general or within a program in our case:
# http://lkml.org/lkml/2005/7/6/250
# A warning is printed if overestimation is possible.
# In addition for 2.6 kernels up to 2.6.9 inclusive, the shared
# value in /proc/$pid/statm is the total file-backed extent of a process.
# We ignore that, introducing more overestimation, again printing a warning.
# Since kernel 2.6.23-rc8-mm1 PSS is available in smaps, which allows
# us to calculate a more accurate value for the total RAM used by programs.
#
# Programs that use CLONE_VM without CLONE_THREAD are discounted by assuming
# they're the only programs that have the same /proc/$PID/smaps file for
# each instance.  This will fail if there are multiple real instances of a
# program that then use CLONE_VM without CLONE_THREAD, or if a clone changes
# its memory map while we're checksumming each /proc/$PID/smaps.
#
# I don't take account of memory allocated for a program
# by other programs. For e.g. memory used in the X server for
# a program could be determined, but is not.
#
# FreeBSD is supported if linprocfs is mounted at /compat/linux/proc/
# FreeBSD 8.0 supports up to a level of Linux 2.6.16

import sys, os, errno, string
try:
    # md5 module is deprecated on python 2.6
    # so try the newer hashlib first
    import hashlib
    md5_new = hashlib.md5
except ImportError:
    import md5
    md5_new = md5.new

# The following exits cleanly on Ctrl-C or EPIPE
# while treating other exceptions as before.
def std_exceptions(etype, value, tb):
    sys.excepthook=sys.__excepthook__
    if issubclass(etype, KeyboardInterrupt):
        pass
    elif issubclass(etype, IOError) and value.errno == errno.EPIPE:
        pass
    else:
        sys.__excepthook__(etype, value, tb)
sys.excepthook=std_exceptions

if os.geteuid() != 0:
    sys.stderr.write("Sorry, root permission required.\n");
    if __name__ == '__main__':
        sys.stderr.close()
        sys.exit(1)

uname=os.uname()
if uname[0]=="FreeBSD":
    proc="/compat/linux/proc/"
else:
    proc="/proc/"

split_args=False
if len(sys.argv)==2 and sys.argv[1] == "--split-args":
    split_args = True

PAGESIZE=os.sysconf("SC_PAGE_SIZE")/1024 #KiB
our_pid=os.getpid()

#(major,minor,release)
def kernel_ver():
    kv=open(proc+"sys/kernel/osrelease", "rt").readline().split(".")[:3]
    last=len(kv)
    if last == 2:
        kv.append('0')
    last -= 1
    for char in "-_":
        kv[last]=kv[last].split(char)[0]
    try:
        int(kv[last])
    except:
        kv[last]=0
    return (int(kv[0]), int(kv[1]), int(kv[2]))

try:
    kv=kernel_ver()
except (IOError, OSError):
    value = sys.exc_info()[1]
    if value.errno == errno.ENOENT:
        sys.stderr.write(
          "Couldn't access /proc\n"
          "Only GNU/Linux and FreeBSD (with linprocfs) are supported\n")
        sys.exit(2)
    else:
        raise

have_pss=0

#return Private,Shared
#Note shared is always a subset of rss (trs is not always)
def getMemStats(pid):
    global have_pss
    mem_id = pid #unique
    Private_lines=[]
    Shared_lines=[]
    Pss_lines=[]
    Rss=int(open(proc+str(pid)+"/statm", "rt").readline().split()[1])*PAGESIZE
    if os.path.exists(proc+str(pid)+"/smaps"): #stat
        digester = md5_new()
        for line in open(proc+str(pid)+"/smaps", "rb").readlines(): #open
            # Note we checksum smaps as maps is usually but
            # not always different for separate processes.
            digester.update(line)
            line = line.decode("ascii")
            if line.startswith("Shared"):
                Shared_lines.append(line)
            elif line.startswith("Private"):
                Private_lines.append(line)
            elif line.startswith("Pss"):
                have_pss=1
                Pss_lines.append(line)
        mem_id = digester.hexdigest()
        Shared=sum([int(line.split()[1]) for line in Shared_lines])
        Private=sum([int(line.split()[1]) for line in Private_lines])
        #Note Shared + Private = Rss above
        #The Rss in smaps includes video card mem etc.
        if have_pss:
            pss_adjust=0.5 #add 0.5KiB as this average error due to trunctation
            Pss=sum([float(line.split()[1])+pss_adjust for line in Pss_lines])
            Shared = Pss - Private
    elif (2,6,1) <= kv <= (2,6,9):
        Shared=0 #lots of overestimation, but what can we do?
        Private = Rss
    else:
        Shared=int(open(proc+str(pid)+"/statm", "rt").readline().split()[2])
        Shared*=PAGESIZE
        Private = Rss - Shared
    return (Private, Shared, mem_id)

def getCmdName(pid):
    cmdline = open(proc+"%d/cmdline" % pid, "rt").read().split("\0")
    if cmdline[-1] == '' and len(cmdline) > 1:
        cmdline = cmdline[:-1]
    path = os.path.realpath(proc+"%d/exe" % pid) #exception for kernel threads
    if split_args:
        return " ".join(cmdline)
    if path.endswith(" (deleted)"):
        path = path[:-10]
        if os.path.exists(path):
            path += " [updated]"
        else:
            #The path could be have prelink stuff so try cmdline
            #which might have the full path present. This helped for:
            #/usr/libexec/notification-area-applet.#prelink#.fX7LCT (deleted)
            if os.path.exists(cmdline[0]):
                path = cmdline[0] + " [updated]"
            else:
                path += " [deleted]"
    exe = os.path.basename(path)
    cmd = open(proc+"%d/status" % pid, "rt").readline()[6:-1]
    if exe.startswith(cmd):
        cmd=exe #show non truncated version
        #Note because we show the non truncated name
        #one can have separated programs as follows:
        #584.0 KiB +   1.0 MiB =   1.6 MiB    mozilla-thunder (exe -> bash)
        # 56.0 MiB +  22.2 MiB =  78.2 MiB    mozilla-thunderbird-bin
    return cmd

cmds={}
shareds={}
mem_ids={}
count={}
for pid in os.listdir(proc):
    if not pid.isdigit():
        continue
    pid = int(pid)
    if pid == our_pid:
        continue
    try:
        cmd = getCmdName(pid)
    except:
        #permission denied or
        #kernel threads don't have exe links or
        #process gone
        continue
    try:
        private, shared, mem_id = getMemStats(pid)
    except:
        continue #process gone
    if shareds.get(cmd):
        if have_pss: #add shared portion of PSS together
            shareds[cmd]+=shared
        elif shareds[cmd] < shared: #just take largest shared val
            shareds[cmd]=shared
    else:
        shareds[cmd]=shared
    cmds[cmd]=cmds.setdefault(cmd,0)+private
    if cmd in count:
       count[cmd] += 1
    else:
       count[cmd] = 1
    mem_ids.setdefault(cmd,{}).update({mem_id:None})

#Add shared mem for each program
total=0
for cmd in cmds:
    cmd_count = count[cmd]
    if len(mem_ids[cmd]) == 1 and cmd_count > 1:
        # Assume this program is using CLONE_VM without CLONE_THREAD
        # so only account for one of the processes
        cmds[cmd] /= cmd_count
        if have_pss:
            shareds[cmd] /= cmd_count
    cmds[cmd]=cmds[cmd]+shareds[cmd]
    total+=cmds[cmd] #valid if PSS available

if sys.version_info >= (2, 6):
    sort_list = sorted(cmds.items(), key=lambda x:x[1])
else:
    sort_list = cmds.items()
    sort_list.sort(lambda x,y:cmp(x[1],y[1]))
# list wrapping is redundant on <py3k, needed for >=pyk3 however
sort_list=list(filter(lambda x:x[1],sort_list)) #get rid of zero sized processes

#The following matches "du -h" output
#see also human.py
def human(num, power="Ki"):
    powers=["Ki","Mi","Gi","Ti"]
    while num >= 1000: #4 digits
        num /= 1024.0
        power=powers[powers.index(power)+1]
    return "%.1f %s" % (num,power)

def cmd_with_count(cmd, count):
    if count>1:
       return "%s (%u)" % (cmd, count)
    else:
       return cmd

if __name__ == '__main__':
    sys.stdout.write(" Private  +   Shared  =  RAM used\tProgram \n\n")
    for cmd in sort_list:
        sys.stdout.write("%8sB + %8sB = %8sB\t%s\n" %
                         (human(cmd[1]-shareds[cmd[0]]),
                          human(shareds[cmd[0]]), human(cmd[1]),
                          cmd_with_count(cmd[0], count[cmd[0]])))
    if have_pss:
        sys.stdout.write("%s\n%s%8sB\n%s\n" %
                         ("-" * 33, " " * 24, human(total), "=" * 33))
    sys.stdout.write("\n Private  +   Shared  =  RAM used\tProgram \n\n")
    # We must close explicitly, so that any EPIPE exception
    # is handled by our excepthook, rather than the default
    # one which is reenabled after this script finishes.
    sys.stdout.close()

#Warn of possible inaccuracies
#2 = accurate & can total
#1 = accurate only considering each process in isolation
#0 = some shared mem not reported
#-1= all shared mem not reported
def shared_val_accuracy():
    """http://wiki.apache.org/spamassassin/TopSharedMemoryBug"""
    if kv[:2] == (2,4):
        if open(proc+"meminfo", "rt").read().find("Inact_") == -1:
            return 1
        return 0
    elif kv[:2] == (2,6):
        pid = str(os.getpid())
        if os.path.exists(proc+pid+"/smaps"):
            if open(proc+pid+"/smaps", "rt").read().find("Pss:")!=-1:
                return 2
            else:
                return 1
        if (2,6,1) <= kv <= (2,6,9):
            return -1
        return 0
    elif kv[0] > 2:
        return 2
    else:
        return 1

if __name__ == '__main__':
    vm_accuracy = shared_val_accuracy()
    if vm_accuracy == -1:
        sys.stderr.write(
         "Warning: Shared memory is not reported by this system.\n"
        )
        sys.stderr.write(
         "Values reported will be too large, and totals are not reported\n"
        )
    elif vm_accuracy == 0:
        sys.stderr.write(
         "Warning: Shared memory is not reported accurately by this system.\n"
        )
        sys.stderr.write(
         "Values reported could be too large, and totals are not reported\n"
        )
    elif vm_accuracy == 1:
        sys.stderr.write(
         "Warning: Shared memory is slightly over-estimated by this system\n"
         "for each program, so totals are not reported.\n"
        )
    sys.stderr.close()
