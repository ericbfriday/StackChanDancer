import AudioOut from "pins/i2s";
import Time from "time";

// Short-clip prototype: flash-resident PCM and a calibrated elapsed clock.
// This is NOT a DAC sample clock; see docs/architecture.md before streaming.
export class PCMClip {
  constructor(buffer, metadata, outputLatencyMs = 0) {
    if (buffer.byteLength !== metadata.samples * 2)
      throw Error("PCM length does not match choreography");
    if (!Number.isFinite(outputLatencyMs) || outputLatencyMs < 0)
      throw Error("Invalid output latency");
    this.buffer = buffer;
    this.latency = outputLatencyMs;
    this.output = new AudioOut({sampleRate: metadata.sample_rate,
      bitsPerSample: 16, numChannels: 1, streams: 1});
  }
  start() {
    this.output.stop();
    this.output.enqueue(0, AudioOut.Flush);
    this.output.enqueue(0, AudioOut.RawSamples, this.buffer);
    this.startedAt = Time.ticks;
    this.output.start();
  }
  positionMs() { return Time.delta(this.startedAt) - this.latency; }
  stop() { this.output.stop(); }
  close() { this.output.close(); }
}
