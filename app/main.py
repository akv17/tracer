import sys; sys.path.insert(0, '.')  # noqa

from app.profile_ import app as profile_app


if __name__ == '__main__':
    action, script = sys.argv[-2:]
    if action == 'profile':
        profile_app.run(script)
    else:
        raise ValueError(action)
