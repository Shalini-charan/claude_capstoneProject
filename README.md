# Auto Doc Sync

Keeps `README.md` in sync with Python docstrings automatically.

Run `sh install_hook.sh` once to activate the pre-push hook.
Every subsequent `git push` will auto-update the `## API Reference` section below.

## API Reference
### `greet(name: str)`

Return a greeting string.

Args:
    name: The name to greet.

Returns:
    A greeting message.

### `Calculator`

A simple calculator.

Attributes:
    value: The current accumulated value.
