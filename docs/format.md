# Stack-chan Dance v1

The authoritative structural schema is
[`dance.schema.json`](../src/stackchan_dancer/dance.schema.json).
Python and JavaScript also validate cross-field/time/motion constraints.
This is a custom format, not an asserted upstream standard.

| Field | Contract |
| --- | --- |
| `format`, `version` | `stackchan-dance`, integer `1` |
| `duration_ms` | Rounded PCM sample duration, 100 ms–1 hour |
| `audio` | `playback.pcm`, 22050 Hz mono s16le, sample count and SHA-256 |
| `bpm` | Nonnegative global estimate; 0 means no detected tempo |
| `profile` | `conservative-v1`; firmware must recognize the profile |
| `motion` row | `[arrival_ms, pan_deg, tilt_deg]` |
| `face` row | `[activation_ms, expression_id]` |

Each track starts at zero; timestamps are integer milliseconds and strictly
increase within that track. Values must be finite. Motion begins at [90,90]
and ends at [90,90] at `duration_ms`; the final pose holds afterward.
Face values hold until the next event; repeated identical IDs may be omitted.
IDs: 0 neutral, 1 happy, 2 surprised, 3 sad. A face event does not modify motion.

Servo angles are logical degrees relative to neutral 90. Hardware adapters
convert `(angle - 90) * π/180` into upstream yaw/pitch and calibrate signs.
They are not GPIO pulse widths or universal raw motor positions.

Deployment must validate JSON before enabling choreography, compare sample
count/digest with the playback asset, and use locally calibrated limits.
The short-clip firmware example checks PCM size; desktop validation checks
the hash. Add device-side hash verification for untrusted/removable assets.

Use `stackchan-dancer validate dance.json --pcm playback.pcm` to check the
schema, track order, endpoints, nominal motion budgets and asset identity.
