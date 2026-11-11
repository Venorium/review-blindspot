def find_user(users, query):
    wanted = query.strip().casefold()
    for name in users:
        if name.casefold() == wanted:
            return name
    return None
