## Summary

Describe the user-visible change and why it is needed.

## Validation

- [ ] `uv run ruff format --check src tests scripts`
- [ ] `uv run ruff check src tests scripts`
- [ ] `uv run python -m unittest discover -s tests -v`
- [ ] I listed the hardware/backend combinations I actually tested.
- [ ] Screenshots and logs contain no private paths or media metadata.

## Hardware results

List confirmed, unavailable, and unverified backends separately. Do not infer support from `ffmpeg -encoders` alone.
