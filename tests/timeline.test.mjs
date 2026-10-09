import test from "node:test";
import assert from "node:assert/strict";
import {Timeline, validateDance} from "../firmware/dance-player.js";

const fixture = () => ({format: "stackchan-dance", version: 1,
  duration_ms: 2000, bpm: 120, profile: "conservative-v1",
  audio: {file: "playback.pcm", sample_rate: 22050, channels: 1,
    encoding: "s16le", samples: 44100, sha256: "0".repeat(64)},
  motion: [[0, 90, 90], [1000, 100, 95], [2000, 90, 90]],
  face: [[0, 0], [500, 1], [1100, 2], [1200, 1], [2000, 0]]});

test("interpolates toward arrival time and holds final neutral", () => {
  const player = new Timeline(fixture());
  assert.equal(player.sample(500).pan, 95);
  assert.equal(player.sample(1000).pan, 100);
  assert.deepEqual(player.sample(9000), {pan: 90, tilt: 90, expression: 0, done: true});
});
test("delayed ticks skip obsolete accents instead of replaying them", () => {
  const player = new Timeline(fixture());
  player.sample(0);
  assert.equal(player.sample(1300).expression, 1);
  assert.equal(player.sample(1300).pan, 97.84);
});
test("mechanical lead does not advance the expression track", () => {
  const player = new Timeline(fixture());
  const sample = player.sample(400, 100);
  assert.equal(sample.pan, 95);
  assert.equal(sample.expression, 0);
});
test("rewind resets indices", () => {
  const player = new Timeline(fixture());
  player.sample(1800);
  assert.equal(player.sample(500).pan, 95);
  assert.equal(player.sample(500).expression, 1);
});
test("rejects malformed timing, out-of-range motion and excess speed", () => {
  for (const mutate of [d => d.motion[1][0] = 0,
    d => d.motion[1][1] = 180, d => d.motion[1][0] = 10,
    d => d.face[1][1] = 8, d => d.motion[1][1] = NaN,
    d => d.audio.samples = 1]) {
    const dance = fixture(); mutate(dance);
    assert.throws(() => validateDance(dance));
  }
});
