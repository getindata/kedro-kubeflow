import os
from contextlib import contextmanager


@contextmanager
def environment(env, delete_keys=None):
    original_environ = os.environ.copy()
    os.environ.update(env)
    if delete_keys is None:
        delete_keys = []
    for key in delete_keys:
        os.environ.pop(key, None)

    yield
    os.environ = original_environ
