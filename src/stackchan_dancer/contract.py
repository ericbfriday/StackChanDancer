"""Format validation and example chassis limits (not universal limits)."""

import hashlib
import json
import math
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

NEUTRAL = (90.0, 90.0)
MINIMUM = (70.0, 78.0)
MAXIMUM = (110.0, 102.0)
VELOCITY = (60.0, 45.0)  # degrees/second
ACCELERATION = (240.0, 180.0)  # degrees/second^2
PROFILE_ID = "conservative-v1"


def segment_budget(dt):
    """Maximum displacement for a cubic smoothstep segment of dt seconds."""
    return tuple(min(v * dt / 1.5, a * dt * dt / 6)
                 for v, a in zip(VELOCITY, ACCELERATION))


def validate(dance, pcm_path=None):
    schema = json.loads(files(__package__).joinpath("dance.schema.json").read_text())
    Draft202012Validator(schema).validate(dance)
    duration = dance["duration_ms"]
    expected_duration = round(dance["audio"]["samples"] * 1000 / 22050)
    if duration != expected_duration:
        raise ValueError("Duration disagrees with audio sample count")

    for name in ("motion", "face"):
        rows = dance[name]
        if rows[0][0] != 0:
            raise ValueError(f"{name} must start at zero")
        previous = -1
        for row in rows:
            if not all(math.isfinite(value) for value in row):
                raise ValueError("Nonfinite value")
            if not previous < row[0] <= duration:
                raise ValueError(f"{name} timestamps must strictly increase")
            previous = row[0]

    motion = dance["motion"]
    if tuple(motion[0][1:]) != NEUTRAL or tuple(motion[-1][1:]) != NEUTRAL:
        raise ValueError("Motion must begin and end at neutral")
    if motion[-1][0] != duration:
        raise ValueError("Final motion timestamp must equal duration")
    for left, right in zip(motion, motion[1:]):
        budget = segment_budget((right[0] - left[0]) / 1000)
        for axis in range(2):
            if abs(right[axis + 1] - left[axis + 1]) > budget[axis] + 1e-8:
                raise ValueError("Motion exceeds velocity/acceleration budget")

    if pcm_path is not None:
        raw = Path(pcm_path).read_bytes()
        if len(raw) != dance["audio"]["samples"] * 2:
            raise ValueError("PCM length mismatch")
        if hashlib.sha256(raw).hexdigest() != dance["audio"]["sha256"]:
            raise ValueError("PCM digest mismatch")
    return dance
