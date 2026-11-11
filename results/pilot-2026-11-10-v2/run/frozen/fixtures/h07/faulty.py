class TransientError(Exception):
    pass


def call_with_retry(operation, attempts, sleep, base_delay):
    last_error = None
    for attempt in range(attempts):
        try:
            return operation()
        except TransientError as error:
            last_error = error
            sleep(base_delay * 2 ** attempt)
    raise last_error
