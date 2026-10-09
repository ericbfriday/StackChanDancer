"""Deterministic mapping with nominal smoothstep motion constraints."""

from .contract import (MAXIMUM, MINIMUM, NEUTRAL, PROFILE_ID,
                       segment_budget, validate)

FACE = {"idle": 0, "steady": 1, "energetic": 1, "dramatic": 3}
GAIN = {"idle": .25, "steady": .55, "energetic": 1.0, "dramatic": .4}


def state_at(sections, timestamp):
    state = "idle"
    for section in sections:
        if section["t_ms"] > timestamp:
            break
        state = section["state"]
    return state


def map_dance(features):
    duration, beats = features["duration_ms"], features["beats"]
    sections = features["sections"]
    candidates = {0: NEUTRAL, duration: NEUTRAL}
    for index, beat in enumerate(beats):
        t = beat["t_ms"]
        if not 0 < t < duration:
            continue
        gain = GAIN[state_at(sections, t)] * (.4 + .6 * beat["intensity"])
        direction = 1 if (index // 2) % 2 == 0 else -1
        pan = 90 + direction * 16 * gain
        candidates[t] = (pan, 90 + 9 * gain * beat["bass"])
        following = beats[index + 1]["t_ms"] if index + 1 < len(beats) else duration
        recovery = (t + following) // 2
        if t < recovery < duration:
            candidates[recovery] = (pan, 90)

    times = [0]
    for t in sorted(candidates):
        if 0 < t <= duration - 80 and t - times[-1] >= 80:
            times.append(t)
    times.append(duration)
    budgets = [segment_budget((b - a) / 1000) for a, b in zip(times, times[1:])]

    # Reserve enough displacement budget to finish exactly at neutral.
    remaining = [[0.0, 0.0] for _ in times]
    for index in range(len(times) - 2, -1, -1):
        remaining[index] = [remaining[index + 1][axis] + budgets[index][axis]
                            for axis in range(2)]
    motion = [[0, *NEUTRAL]]
    for index, t in enumerate(times[1:], 1):
        pose = []
        for axis in range(2):
            previous = motion[-1][axis + 1]
            step = budgets[index - 1][axis]
            low = max(MINIMUM[axis], previous - step, 90 - remaining[index][axis])
            high = min(MAXIMUM[axis], previous + step, 90 + remaining[index][axis])
            # Floating-point accumulation can leave low a few ulps above
            # high. Fix the endpoint exactly; validation allows only 1e-8
            # numerical tolerance on segment budgets.
            pose.append(90.0 if index == len(times) - 1 else
                        max(low, min(high, candidates[t][axis])))
        motion.append([t, *pose])

    # Union of boundaries and accent edges; evaluate the active state at
    # each edge so an accent reset cannot erase a simultaneous transition.
    accents, last = [], -1000
    for t in sorted(set(features["treble_events_ms"])):
        if 0 <= t < duration and t - last >= 350:
            accents.append((t, min(duration, t + 150)))
            last = t
    edges = {0, duration} | {s["t_ms"] for s in sections
                            if 0 <= s["t_ms"] <= duration}
    for start, stop in accents:
        edges.update((start, stop))
    face, accent_index = [], 0
    for t in sorted(edges):
        while accent_index < len(accents) and accents[accent_index][1] <= t:
            accent_index += 1
        accented = (accent_index < len(accents) and
                    accents[accent_index][0] <= t < accents[accent_index][1])
        expression = 0 if t == duration else 2 if accented else FACE[state_at(sections, t)]
        if not face or expression != face[-1][1]:
            face.append([t, expression])

    return validate({"format": "stackchan-dance", "version": 1,
                     "duration_ms": duration, "audio": features["audio"],
                     "bpm": features["bpm"], "profile": PROFILE_ID,
                     "motion": motion, "face": face})
