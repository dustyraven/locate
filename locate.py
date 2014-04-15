import os, sys, sqlite3, time, ctypes, atexit, errno
#from locatefiles.ArgsParse import ArgsParse
from locatefiles import *


# ####################################################
# Functions
# ####################################################

def insertInDB():
    #L = list(set(L))
    L.sort()
    for i, f in enumerate(L):
        L[i] = (path,f)

    if len(L) > 0:
        cur.executemany("insert into idx (path, loc) values (?, ?)", L)
        conn.commit()

def usage():
    with open (options['path'] + "usage.txt", "r") as usage:
        data=usage.read()
    print(data)


def sizeof_fmt(num):
    num = int(num)
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0:
            return "%3.2f%s" % (num, x)
        num /= 1024.0
    return "%3.2f%s" % (num, 'TB')

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise

def goodbye():
    silentremove(options['lockfile'])
    try:
        cur.close()
        conn.close()
    except:
        pass
    #print 'Bye bye...'


def errExit(st):
    highlightStr('Error: %s' % st, 'error:', highlight_error)
    sys.exit(1)

def status(st = '', mode = 0):
    """
    mode:
        0 - normal
        1 - no newline
        2 - with CR
        3 - with CR, no newline
    """
    if options['quiet']:
        return False

    if 2 == mode or 3 == mode:
        st = '\r' + (80*' ') + '\r' + st[:80]

    if 1 == mode or 3 == mode:
        print st,
    else:
        print st

    return True

def time2str(ts, fmt = "%d.%m.%Y %H:%M"):
    fmt = fmt.replace("%F", "%Y-%m-%d")
    fmt = fmt.replace("%T", "%H:%M:%S")
    ts = int(ts)
    ts = time.localtime(ts)
    return time.strftime(fmt, ts)

def get_csbi_attributes(handle):
    # Based on IPython's winconsole.py, written by Alexander Belchenko
    import struct
    csbi = ctypes.create_string_buffer(22)
    res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(handle, csbi)

    (bufx, bufy, curx, cury, wattr,
    left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
    return wattr

def set_color(color):
    """(color) -> BOOL
    Example: set_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    """
    bool = ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)
    return bool

def highlightStr(line, search, color):
    starts = []
    ends = []
    tmp = line.lower()

    if isinstance(search, basestring):
        search = [search]

    for s in search:
        s = s.lower()
        beg = 0
        while True:
            strt = tmp.find(s, beg)
            if -1 == strt:
                break
            starts.append(strt)
            ends.append(strt + len(s))
            beg = strt + 1

    for i, l in enumerate(list(line)):
        if i in starts:
            set_color(color)
        if i in ends:
            set_color(reset)
        sys.stdout.write(l)
    set_color(reset)
    print


def getDrives():
    import win32api, win32file

    drives = []
    for drive in win32api.GetLogicalDriveStrings().split('\000')[:-1]:
        if 3 == win32file.GetDriveType(drive):
            drives.append(drive)
    return drives

"""
SHERB_NOCONFIRMATION = 1
SHERB_NOPROGRESSUI   = 2
SHERB_NOSOUND        = 4

def EmptyRecycleBin(options=SHERB_NOCONFIRMATION or SHERB_NOPROGRESSUI or SHERB_NOSOUND):
    from ctypes import windll
    windll.shell32.SHEmptyRecycleBinA(None, None, options)
"""


def disk_usage(path):
    _, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
    if sys.version_info >= (3,) or isinstance(path, unicode):
        fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
    else:
        fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA
    ret = fun(path, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
    if ret == 0:
        raise ctypes.WinError()
    used = total.value - free.value
    return "%d %d %d" % (total.value, used, free.value)
    #return (total.value, used, free.value)


# ####################################################
# Variables
# ####################################################

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE= -11
STD_ERROR_HANDLE = -12

FOREGROUND_BLUE = 0x01 # text color contains blue.
FOREGROUND_GREEN = 0x02 # text color contains green.
FOREGROUND_RED  = 0x04 # text color contains red.
FOREGROUND_WHITE     = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
FOREGROUND_INTENSITY = 0x08 # text color is intensified.

BACKGROUND_BLUE = 0x10 # background color contains blue.
BACKGROUND_GREEN= 0x20 # background color contains green.
BACKGROUND_RED  = 0x40 # background color contains red.
BACKGROUND_INTENSITY = 0x80 # background color is intensified.

std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
reset = get_csbi_attributes(std_out_handle)

highlight = FOREGROUND_GREEN | FOREGROUND_INTENSITY
highlight_result = FOREGROUND_GREEN | FOREGROUND_INTENSITY
highlight_error = FOREGROUND_RED | FOREGROUND_INTENSITY

DATABASE = "locate.sqlite"
SLASH = os.sep

# ####################################################
# P R E P A R E
# ####################################################


options = {}
options['path'] = os.path.dirname(os.path.realpath(__file__)) + SLASH
options['db'] = options['path'] + DATABASE

conn = sqlite3.connect(options['db'])
cur = conn.cursor()

for k, v in cur.execute("select key, val from cfg"):
    options[k.encode('utf8')] = (
        int(v) if v.isdigit() else v.encode('utf8')
    ) if v else False

if not options['lockfile']:
    options['lockfile'] = options['db'] + '.lock'

if os.path.isfile(options['lockfile']):
    status('Another instance running!')
    sys.exit(0)

with open(options['lockfile'], 'w') as f:
    f.write('%f' % time.time())

DRIVES = getDrives()

DRIVES_COND = " path IN ('%s') " % ("','".join( map( str, DRIVES ) ))

atexit.register(goodbye)

#print options
#sys.exit()

# ####################################################
# Arguments
# ####################################################

args = sys.argv

if len(args) < 2:
    usage()
    sys.exit(1)

expected = [
    ('update', '-u /u', 'str', 'AUTO'),
    ('help', '-h /?'),
    ('dirs', '-d'),
    ('files', '-f'),
    ('quiet', '-q /q'),
    ('info', '-i'),
    'history',
    'vacuum',
    'debug',
    'setup'
]

opts, search, errs = ArgsParse.ArgsParse().parse(args, expected)


if len(errs):
    for e in errs:
        highlightStr('Error: %s' % e, 'error:', highlight_error)
    sys.exit(1)

for k, v in opts.items():
    #if k in options:
    options[k] = v

"""
for k, v in options.items():
    print k, v
print search
sys.exit(0)
"""


# ####################################################
# H E L P
# ####################################################

if options['help']:
    usage()

# ####################################################
# U P D A T E
# ####################################################

elif options['update']:


    if "ALL" != options['update']:
        if 'AUTO' == options['update'].upper():
            if options['autoupdate'] is not False:
                query = "SELECT path FROM paths WHERE %s ORDER BY indexed ASC LIMIT 1" % DRIVES_COND
                cur.execute(query)
                options['update'] = cur.fetchone()[0]
            else:
                errExit('Autoupdate disabled.')
        else:
            path = options['update'].upper() + SLASH
            if path in DRIVES:
                options['update'] = path
            else:
                errExit('Invalid update path %s' % options['update'])


    #print options['update']; sys.exit(0)


    # do update
    for path in DRIVES:
        if options['update'] != path and "ALL" != options['update']:
            continue

        ts = time.time()

        usage = disk_usage(path)

        cur.execute("SELECT usage FROM paths WHERE path = ?", (path,))
        old_usage = cur.fetchone()[0]

        if usage != old_usage:

            status('Indexing %s...' % path, 3)

            cur.execute("DELETE FROM idx WHERE path LIKE ?", (path+'%',))

            if options['autovacuum'] is not False and "ALL" != options['update']:
                status('Vacuum database...')
                cur.execute("VACUUM")

            conn.commit()

            status('Indexing %s started...' % path, 3)

            counter = 0;
            L = []

            for root, dirnames, filenames in os.walk(unicode(path)):
                counter = counter + 1
                if root != path:
                    L.append(root + SLASH)
                #for dname in dirnames:
                #    L.append(root + SLASH + dname + SLASH)
                for fname in filenames:
                    counter = counter + 1
                    L.append(os.path.join(root, fname))

                if counter > options['idx_chunk']:
                    status('Indexing %s...' % root, 3)
                    insertInDB()
                    counter = 0
                    L = []

            insertInDB()

        cur.execute("UPDATE paths SET indexed = strftime('%s', 'now'), usage = ? WHERE path = ?", (usage, path))
        conn.commit()

        elapsed = round(time.time() - ts, 4)
        params = args
        params.append(path)

        cur.execute(
            'INSERT INTO hist (start, elapsed, action, params) VALUES (?, ?, ?, ?)',
            (ts, elapsed, 'update', ' '.join(params))
        )

        conn.commit()

        status('Indexing %s completed in %.4f seconds' % (path, elapsed), 2)


# ####################################################
# H I S T O R Y
# ####################################################

elif options['history']:
    cur.execute("SELECT * FROM hist ORDER BY start DESC LIMIT 20")
    hist = cur.fetchall()
    print
    for h in reversed(hist):
        datetime = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(int(h[1])))
        print datetime + ' -> ' + h[4]
    print

# ####################################################
# S E T U P
# ####################################################

elif options['setup']:
    errExit('Setup procedure not ready.')

# ####################################################
# V A C U U M
# ####################################################

elif options['vacuum']:
    status('Vacuum started...')
    ts = time.time()
    cur.execute("VACUUM")
    elapsed = round(time.time() - ts, 4)
    status('\nVacuum completed in %.4f seconds.\n' % elapsed)

# ####################################################
# I N F O
# ####################################################

elif options['info']:
    allIdx = 0
    lstIdx = 0
    data = []
    print

    for row in cur.execute("SELECT path, COUNT(path) FROM idx WHERE %s GROUP BY path" % DRIVES_COND):
        data.append(row)

    for row in data:
        allIdx += row[1]

        cur.execute("SELECT indexed, usage FROM paths WHERE path = ?", (row[0],))
        timestamp, usage = cur.fetchone()
        usage = usage.split()

        if(timestamp > lstIdx):
            lstIdx = timestamp

        print "  Drive: %s" % row[0]
        print "Indexes: %d" % row[1]
        print "Indexed: %s" % time2str(timestamp)
        print "   Size: %s" % sizeof_fmt(usage[0])
        print "   Used: %s (%.2f%%)" % (sizeof_fmt(usage[1]), 100 * float(usage[1])/float(usage[0]))
        print "   Free: %s (%.2f%%)" % (sizeof_fmt(usage[2]), 100 * float(usage[2])/float(usage[0]))
        print

    dbsize = os.path.getsize(options['db'])

    print
    print "Database file: %s" % options['db']
    print "Database size: %s (%d bytes)" % (sizeof_fmt(dbsize), dbsize)
    print "Total indexes: %d" % allIdx
    print " Last indexed: %s" % time2str(lstIdx)
    print


# ####################################################
# S E A R C H
# ####################################################

else:
    ts = time.time()

    query = "SELECT loc FROM idx WHERE %s AND " % DRIVES_COND

    params = []
    conds  = []
    for s in search:
        try:
            unicode_s = unicode(s)
            if '-' == s[0]:
                unicode_s = unicode_s[1:]
                conds.append('loc NOT LIKE ?')
            else:
                conds.append('loc LIKE ?')
            params.append( '%' + unicode_s + '%' )
        except UnicodeDecodeError:
            pass


    if len(params) < 1 or len(conds) < 1:
        errExit('Nothing to search')

    query = query + ' AND '.join(conds) + ' ORDER BY loc'

    if options['debug']:
        print
        print query
        print params
        print

    status()

    results = []
    cnt = 0
    for row in cur.execute(query, params):
        try:
            result = row[0] #repr(row[0]).decode('ascii')
            if options['quiet']:
                print result
            else:
                highlightStr(result, search, highlight_result)
        except UnicodeEncodeError:
            if options['quiet']:
                print options['cutstr']
            else:
                highlightStr(options['cutstr'], options['cutstr'], highlight_error)
        except Exception, e:
            print "\n\n\nERROR: %s\n\n\n" % str(e)

        cnt += 1
        if cnt > options['max_results']:
            set_color(highlight_error)
            print "\nMore than %d results found. Please refine your search.\n" % options['max_results']
            set_color(reset)
            break

    elapsed = round(time.time() - ts, 4)

    if cnt <= options['max_results']:
        status('\n%d items found in %.4f seconds.\n' % (cnt, elapsed))

    cur.execute(
        """
        INSERT INTO hist (start, elapsed, action, params)
        VALUES (?, ?, ?, ?)
        """,
        (ts, elapsed, 'locate', ' '.join(search))
    )
    conn.commit()


# ####################################################
# E X I T
# ####################################################

sys.exit(0)

