def active(now, expires_at):
    return not now > expires_at
