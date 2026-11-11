def append_batch(store, values):
    for value in values:
        if value < 0:
            raise ValueError("negative value")
        store.append(value)
