def advance(state, version, value):
    if version >= state['version']:
        state.update(version=version, value=value, writes=state['writes'] + 1)
        return True
    return False
