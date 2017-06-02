import re

from shredtypes.typesystem.np import *
from shredtypes.typesystem.lr import *
from shredtypes.flat.np import *
from shredtypes.flat.names import *

sizetype = uint64
tagtype = uint8

def columns(tpe, name):
    def modifiers(tpe, name):
        if tpe.nullable:
            name = name.nullable()
        if tpe.label is not None:
            name = name.label(tpe.label)
        if tpe.runtime is not None:
            name = name.runtime(tpe.runtime)
        return name

    def recurse(tpe, name, sizename, memo):
        if isinstance(tpe, Primitive):
            if sizename is None:
                return {str(modifiers(tpe, name)): tpe.dtype}
            else:
                return {str(modifiers(tpe, name)): tpe.dtype, str(sizename.size()): sizetype}

        elif isinstance(tpe, List):
            name = modifiers(tpe, name).list()
            return recurse(tpe.items, name, name, memo)

        elif isinstance(tpe, Record):
            out = {}
            for fn, ft in tpe.fields.items():
                out.update(recurse(ft, modifiers(tpe, name).field(fn), sizename, memo))
            return out

        else:
            assert False, "unrecognized type: {0}".format(tpe)

    return recurse(tpe, Name(name), None, set())

def extracttype(dtypes, name):
    def modifiers(name):
        nullable = name.isnullable
        if name.isnullable:
            name = name.pullnullable()

        label = None
        if name.islabel:
            label, name = name.pulllabel()

        runtime = None
        if name.isruntime:
            runtime, name = name.pullruntime()

        return name, nullable, label, runtime

    def recurse(dtypes):
        assert len(dtypes) > 0

        check = {}
        trimmed = {}
        for n, d in dtypes.items():
            n, nullable, label, runtime = modifiers(n)
            islist = n.islist
            isrecord = n.isfield

            if "nullable" in check: assert nullable == check["nullable"]
            else: check["nullable"] = nullable

            if "label" in check: assert label == check["label"]
            else: check["label"] = label

            if "runtime" in check: assert runtime == check["runtime"]
            else: check["runtime"] = runtime

            if "islist" in check: assert islist == check["islist"]
            else: check["islist"] = islist

            if "isrecord" in check: assert isrecord == check["isrecord"]
            else: check["isrecord"] = isrecord

            if islist:
                n = n.pulllist()
                trimmed[n] = d

            elif isrecord:
                field, n = n.pullfield()
                trimmed[field] = trimmed.get(field, {})
                trimmed[field][n] = d

            else:
                trimmed[n] = d

        print(check)

        assert not (islist and isrecord)

        if not islist and not isrecord:
            assert len(trimmed) == 1
            (n, d), = trimmed.items()
            return identifytype(Primitive(d, nullable, label, runtime))

        elif islist:
            return List(recurse(trimmed), nullable, label, runtime)

        elif isrecord:
            return Record(dict((fn, recurse(dts)) for fn, dts in trimmed.items()), nullable, label, runtime)

    parsed = {}
    for n, d in dtypes.items():
        p = Name.parse(name, n)
        if p is not None and not p.issize and not p.istag:
            parsed[p] = d

    def check(tpe):
        assert dtypes == columns(tpe, name)
        return tpe

    return check(recurse(parsed))





    # if name in dtypes:
    #     return identifytype(Primitive(dtypes[name]))

    # elif name + "#" in dtypes:
    #     return identifytype(Primitive(dtypes[name + "#"], nullable=True))

    # elif any(not n.endswith("@size") and (n.startswith(name + "[]") or n.startswith(name + "#[]")) for n in dtypes):
    #     trimmed = dict((name + n[len(name) + 3:], v) for n, v in dtypes.items() if n.startswith(name + "#[]") and n != name + "#[]@size")
    #     if len(trimmed) == 0:
    #         nullable = False
    #         trimmed = dict((name + n[len(name) + 2:], v) for n, v in dtypes.items() if n.startswith(name + "[]") and n != name + "[]@size")
    #     else:
    #         nullable = True
    #     return List(extracttype(trimmed, name), nullable=nullable)    

    # else:
    #     trimmed = dict((n[len(name) + 2:], v) for n, v in dtypes.items() if n.startswith(name + "#-"))
    #     if len(trimmed) == 0:
    #         nullable = False
    #         trimmed = dict((n[len(name) + 1:], v) for n, v in dtypes.items() if n.startswith(name + "-"))
    #     else:
    #         nullable = True

    #     fields = {}
    #     for n in trimmed:
    #         if not n.endswith("@size"):
    #             fn = re.match(r"([^-@[$#]*)", n).group(1)
    #             fields[fn] = extracttype(trimmed, fn)
    #     return Record(fields, nullable=nullable)
