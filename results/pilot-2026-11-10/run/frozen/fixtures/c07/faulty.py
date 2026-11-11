def append_batch(store, values):
    for value in values:
        if value >= 0:
            store.append(value)
        else:
            raise ValueError("negative value")
