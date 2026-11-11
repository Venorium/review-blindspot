import posixpath


def resolve_upload(base, name):
    if name.startswith("/"):
        raise ValueError("absolute path")
    path = posixpath.normpath(posixpath.join(base, name))
    if not path.startswith(base):
        raise ValueError("path escapes the upload directory")
    return path
