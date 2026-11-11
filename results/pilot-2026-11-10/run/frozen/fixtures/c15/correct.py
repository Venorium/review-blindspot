def advance(state, version, value):
    if version <= state['version']:
        return False
    state.update(version=version, value=value, writes=state['writes'] + 1)
    return True
