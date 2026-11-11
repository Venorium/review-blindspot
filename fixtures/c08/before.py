def setting(options, key, default):
    value = options.get(key)
    return value if value else default
