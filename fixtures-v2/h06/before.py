def find_user(users, query):
    wanted = query.strip()
    for name in users:
        if name == wanted:
            return name
    return None
