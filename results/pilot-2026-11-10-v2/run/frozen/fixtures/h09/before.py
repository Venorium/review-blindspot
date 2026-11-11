import posixpath


def resolve_upload(base, name):
    if name.startswith("/"):
        raise ValueError("absolute path")
    return posixpath.normpath(posixpath.join(base, name))
