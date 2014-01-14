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
        _errs = []

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
                if 0==arg.find('--') or 0==arg.find('/') or (2==len(arg) and 0==arg.find('-')):
                    _errs.append("Unknown option " + arg)
                else:
                    _unkn.append(arg)

        return _opts, _unkn, _errs
# End of class ArgsParse