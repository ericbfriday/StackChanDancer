// Platform-independent timeline evaluator. Imports no hardware modules so
// Node tests can exercise the same scheduler used by the Moddable adapter.
const MIN = [70, 78], MAX = [110, 102];
const V = [60, 45], A = [240, 180];

export function validateDance(d) {
  if (d.format !== "stackchan-dance" || d.version !== 1 ||
      d.profile !== "conservative-v1") throw Error("Unsupported dance/profile");
  if (!Number.isInteger(d.duration_ms) || d.duration_ms < 100 ||
      d.duration_ms > 3600000 || !Number.isFinite(d.bpm) || d.bpm < 0)
    throw Error("Invalid duration/tempo");
  const audio = d.audio;
  if (!audio || audio.file !== "playback.pcm" || audio.sample_rate !== 22050 ||
      audio.channels !== 1 || audio.encoding !== "s16le" ||
      !Number.isInteger(audio.samples) || audio.samples < 1 ||
      Math.round(audio.samples * 1000 / 22050) !== d.duration_ms ||
      !/^[0-9a-f]{64}$/.test(audio.sha256)) throw Error("Invalid audio metadata");
  for (const [name, size] of [["motion", 3], ["face", 2]]) {
    const rows = d[name];
    if (!Array.isArray(rows) || !rows.length || rows.length > 50000 ||
        !Array.isArray(rows[0]) || rows[0][0] !== 0) throw Error("Invalid track");
    let previous = -1;
    for (const row of rows) {
      if (!Array.isArray(row) || row.length !== size ||
          !row.every(Number.isFinite) || !Number.isInteger(row[0]) ||
          row[0] <= previous || row[0] > d.duration_ms) throw Error("Invalid row");
      if (name === "motion") {
        for (let axis = 0; axis < 2; axis++)
          if (row[axis + 1] < MIN[axis] || row[axis + 1] > MAX[axis])
            throw Error("Pose outside device limits");
      } else if (!Number.isInteger(row[1]) || row[1] < 0 || row[1] > 3)
        throw Error("Unknown expression");
      previous = row[0];
    }
  }
  const rows = d.motion, first = rows[0], last = rows[rows.length - 1];
  if (rows.length < 2 || first[1] !== 90 || first[2] !== 90 ||
      last[1] !== 90 || last[2] !== 90 || last[0] !== d.duration_ms)
    throw Error("Invalid motion endpoints");
  for (let i = 1; i < rows.length; i++) {
    const dt = (rows[i][0] - rows[i - 1][0]) / 1000;
    for (let axis = 0; axis < 2; axis++) {
      const delta = Math.abs(rows[i][axis + 1] - rows[i - 1][axis + 1]);
      if (delta > Math.min(V[axis] * dt / 1.5, A[axis] * dt * dt / 6) + 1e-8)
        throw Error("Motion exceeds nominal limits");
    }
  }
  return d;
}

export class Timeline {
  constructor(dance) {
    this.dance = validateDance(dance);
    this.motionIndex = this.faceIndex = 0;
    this.lastTime = -Infinity;
  }

  sample(timeMs, motionLeadMs = 0) {
    if (!Number.isFinite(timeMs) || !Number.isFinite(motionLeadMs) || motionLeadMs < 0)
      throw Error("Invalid clock/lead");
    // Rewind support is explicit; normal playback is monotonically increasing.
    if (timeMs < this.lastTime) this.motionIndex = this.faceIndex = 0;
    this.lastTime = timeMs;
    const t = Math.max(0, Math.min(this.dance.duration_ms, timeMs + motionLeadMs));
    const rows = this.dance.motion;
    while (this.motionIndex + 1 < rows.length && rows[this.motionIndex + 1][0] <= t)
      this.motionIndex++;
    const a = rows[this.motionIndex];
    const b = rows[Math.min(this.motionIndex + 1, rows.length - 1)];
    const u = a === b ? 1 : (t - a[0]) / (b[0] - a[0]);
    const e = u * u * (3 - 2 * u);
    const faces = this.dance.face;
    while (this.faceIndex + 1 < faces.length && faces[this.faceIndex + 1][0] <= timeMs)
      this.faceIndex++;
    return {
      pan: a[1] + (b[1] - a[1]) * e,
      tilt: a[2] + (b[2] - a[2]) * e,
      expression: faces[this.faceIndex][1],
      done: timeMs >= this.dance.duration_ms
    };
  }
}
