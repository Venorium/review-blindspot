def append_batch(store, values):
    if any(value < 0 for value in values):
        raise ValueError("negative value")
    store.extend(values)
