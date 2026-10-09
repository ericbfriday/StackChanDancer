import Resource from "Resource";
import Timer from "timer";
import Time from "time";
import {Timeline} from "dance-player";
import {PCMClip} from "pcm-audio";

// Integration example for upstream's namespaced context API.
// Confirm setPose units, emotion strings and I2S ownership for YOUR revision.
const RAD = Math.PI / 180;
const EMOTIONS = ["neutral", "happy", "surprised", "sad"];
const PAN_SIGN = 1, TILT_SIGN = 1;
const OUTPUT_LATENCY_MS = 0, MECHANICAL_LEAD_MS = 0;
let closeActive;

export async function onContextCreated(context) {
  closeActive?.();
  const dance = JSON.parse(String.fromArrayBuffer(new Resource("dance.json")));
  const timeline = new Timeline(dance);
  let audio, timer, busy = false, closing = false, lastExpression = -1;
  let commandTime = Time.ticks;
  const commanded = [90, 90];

  // Hook closeDance() into your host revision's MOD teardown mechanism.
  const stop = () => {
    closing = true;
    Timer.clear(timer);
    timer = undefined;
    audio?.close();
    audio = undefined;
  };
  closeActive = stop;

  function pose(pan, tilt, seconds) {
    return context.motion.setPose({position: {x: 0, y: 0, z: 0},
      rotation: {y: PAN_SIGN * (pan - 90) * RAD,
                 p: TILT_SIGN * (tilt - 90) * RAD, r: 0}}, seconds);
  }

  try {
    context.motion.lookAway();
    await context.motion.setTorque(true);
    if (closing) return;
    await pose(90, 90, 1.0);
    await new Promise(resolve => Timer.set(resolve, 1100));
    if (closing) return;
    // The host must release any other AudioOut owner first. A MOD cannot
    // safely create competing I2S output instances on every firmware build.
    audio = new PCMClip(new Resource("playback.pcm"), dance.audio, OUTPUT_LATENCY_MS);
    commandTime = Time.ticks;
    audio.start();

    const update = () => {
      if (closing) return;
      const time = audio.positionMs();
      if (time < 0) return;
      const sample = timeline.sample(time, MECHANICAL_LEAD_MS);
      if (sample.expression !== lastExpression) {
        context.face.setEmotion(EMOTIONS[sample.expression]);
        lastExpression = sample.expression;
      }
      if (busy) return; // Sample current time next tick; never queue stale poses.
      busy = true;
      // Limit catch-up displacement after JS stalls. Nominal acceleration
      // limits come from the mapper; hardware needs its own stall guard.
      const dt = Math.min(.04, Math.max(0, Time.delta(commandTime) / 1000));
      const next = [sample.pan, sample.tilt].map((target, axis) => {
        const limit = [60, 45][axis] * dt;
        return commanded[axis] + Math.max(-limit, Math.min(limit, target - commanded[axis]));
      });
      commandTime = Time.ticks;
      pose(next[0], next[1], .02).then(() => {
        commanded[0] = next[0]; commanded[1] = next[1]; busy = false;
        if (!closing && sample.done &&
            Math.abs(commanded[0] - 90) < .01 && Math.abs(commanded[1] - 90) < .01)
          stop();
      }, error => { busy = false; stop(); trace(`Dance stopped: ${error}\n`); });
    };
    timer = Timer.repeat(() => {
      try { update(); } catch (error) { stop(); trace(`Dance stopped: ${error}\n`); }
    }, 20);
  } catch (error) {
    stop();
    throw error;
  }
}

export function closeDance() { closeActive?.(); closeActive = undefined; }
