def find_user(users, query):
    wanted = query.strip().lower()
    for name in users:
        if name.lower() == wanted:
            return name
    return None
