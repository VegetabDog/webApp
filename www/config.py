import config_default, config_override

class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, name=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k,v in zip(name, values):
            self[k] = v

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return AttributeError(r"'Dict' object has no attribute '%s'" % item)

    def __setattr__(self, key, value):
        self[key] = value

def merge(default, override):
    r = {}
    for k,v in default.items():
        if k in override:
            # if isinstance(v, dict):
            #     r[k] = merge(v, override[k])
            # else:
            #     r[k] = override[k]
            r[k] = merge(v, override[k]) if isinstance(v, dict) else override[k]
        else:
            r[k] = v
    return r
# 提供了xxx.key.key的访问方式，可不用
def toDict(d):
    D = Dict()
    for k, v in d.items():
        # 如果v是dict，递归执行toDict，否则直接赋值为v
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)
print(configs)

