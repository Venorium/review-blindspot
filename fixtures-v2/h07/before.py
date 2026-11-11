class TransientError(Exception):
    pass


def call_with_retry(operation, attempts, sleep, base_delay):
    for attempt in range(attempts):
        try:
            return operation()
        except TransientError:
            if attempt == attempts - 1:
                raise
            sleep(base_delay)
