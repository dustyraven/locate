import os, sys, sqlite3, time, ctypes, atexit, errno


class ArgsParse:
    """Parse args.

    Write some docs, pls ;)
    """

    def listpad(self, _lst, _len, _dflt = False):
        return _lst + (_dflt,) * (_len - len(_lst))

    def typecast(self, _var, _type):
        return getattr(__builtins__, _type)(_var)

    def parse(self, args, expected):
        # expected = [(name, aliases, expect),...]
        _args = args.split()[1:] if isinstance(args, basestring) else args[1:]
        _opts = {}
        _unkn = []

        #zerofill
        for i, ex in enumerate(expected):
            if isinstance(ex, basestring):
                ex = (ex,)
            expected[i] = self.listpad(ex, 4)
            _opts[ex[0]] = False

        while len(_args):
            arg = _args.pop(0)
            flg = False
            for name, aliases, expect, default in expected:
                aliases = aliases.replace(';',' ').replace(',',' ').split() if aliases != False else []
                aliases.append('--'+name)
                if arg in aliases:
                    flg = True
                    if False == expect:
                        _opts[name] = True
                    else:
                        try:
                            if '-' == _args[0][0:1]:
                                raise IndexError
                            _opts[name] = self.typecast(_args.pop(0), expect)
                        except IndexError:
                            _opts[name] = default
            if not flg:
                _unkn.append(arg)
        return _opts, _unkn
# End of class ArgsParse


# ####################################################
# Functions
# ####################################################

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

def status(st, mode = 0):
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

SHERB_NOCONFIRMATION = 1
SHERB_NOPROGRESSUI   = 2
SHERB_NOSOUND        = 4

def EmptyRecycleBin(options=SHERB_NOCONFIRMATION or SHERB_NOPROGRESSUI or SHERB_NOSOUND):
    from ctypes import windll
    windll.shell32.SHEmptyRecycleBinA(None, None, options)

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

def insertInDB():
    #L = list(set(L))
    L.sort()
    for i, f in enumerate(L):
        L[i] = (path,f)

    if len(L) > 0:
        cur.executemany("insert into idx (path, loc) values (?, ?)", L)
        conn.commit()


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

atexit.register(goodbye)

options = {}
options['db'] = os.path.dirname(os.path.realpath(__file__)) + SLASH + DATABASE

conn = sqlite3.connect(options['db'])
cur = conn.cursor()

for k, v in cur.execute("select key, val from cfg"):
    options[k.encode('utf8')] = (
        int(v) if v.isdigit() else v.encode('utf8')
    ) if v else False

if not options['lockfile']:
    options['lockfile'] = options['db'] + '.lock'

with open(options['lockfile'], 'w') as f:
    f.write('%f' % time.time())

#print options
#sys.exit()

# ####################################################
# Arguments
# ####################################################

args = sys.argv

if len(args) < 1:
    print("Usage: ...")
    sys.exit(1)

expected = [
    ('update', '-u /u', 'str', 'AUTO'),
    ('dirs', '-d'),
    ('files', '-f'),
    ('quiet', '-q /q'),
    ('info', '-i'),
    'history',
    'vacuum',
    'debug',
    'setup'
]

ap = ArgsParse()
opts, search = ap.parse(args, expected)

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
# U P D A T E
# ####################################################

if options['update']:

    DRIVES = getDrives()

    if "ALL" != options['update']:
        if 'AUTO' == options['update'].upper():
            if options['autoupdate'] is not False:
                cur.execute("SELECT path FROM paths ORDER BY indexed ASC LIMIT 1")
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
    ts = time.time()
    cur.execute("VACUUM")
    if not options['quiet']:
        elapsed = round(time.time() - ts, 4)
        print '\nVacuum completed in %.4f seconds.\n' % elapsed

# ####################################################
# I N F O
# ####################################################

elif options['info']:
    allIdx = 0
    lstIdx = 0
    data = []
    print

    for row in cur.execute("select path, count(path) from idx group by path"):
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

    query = 'SELECT loc FROM idx WHERE '

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
        print "Error: Nothing to search"
        sys.exit()

    query = query + ' AND '.join(conds) + ' ORDER BY loc'

    if options['debug']:
        print
        print query
        print params
        print

    if not options['quiet']:
        print

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

    cur.execute(
        """
        INSERT INTO hist (start, elapsed, action, params)
        VALUES (?, ?, ?, ?)
        """,
        (ts, elapsed, 'locate', ' '.join(search))
    )
    conn.commit()

    if not options['quiet'] and not cnt > options['max_results']:
        print '\n%d items found in %.4f seconds.\n' % (cnt, elapsed)

# ####################################################
# E X I T
# ####################################################

sys.exit(0)

