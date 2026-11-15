/** Decode operator-only Cloud TTS audio and drive the hologram from actual PCM amplitude. */
export function startCloudSpeech(
  text: string,
  operatorToken: string,
  volume: number,
  onStart: () => void,
  onLevel: (level: number) => void,
  onEnd: () => void,
  onError: () => void,
): () => void {
  const controller = new AbortController();
  let context: AudioContext | null = null;
  let source: AudioBufferSourceNode | null = null;
  let frame = 0;
  let stopped = false;
  const stop = () => {
    stopped = true;
    controller.abort();
    if (frame) cancelAnimationFrame(frame);
    try { source?.stop(); } catch { /* already stopped */ }
    void context?.close();
    onLevel(0);
  };
  void (async () => {
    try {
      const response = await fetch('/api/speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': operatorToken },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Cloud speech unavailable');
      const data = await response.arrayBuffer();
      if (stopped) return;
      context = new AudioContext();
      const buffer = await context.decodeAudioData(data);
      if (stopped) return;
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      const gain = context.createGain();
      gain.gain.value = volume;
      source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(analyser);
      analyser.connect(gain);
      gain.connect(context.destination);
      const samples = new Uint8Array(analyser.fftSize);
      const tick = () => {
        if (stopped) return;
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (const sample of samples) { const centered = (sample - 128) / 128; sum += centered * centered; }
        const rms = Math.sqrt(sum / samples.length);
        onLevel(Math.min(1, rms * 5.5));
        frame = requestAnimationFrame(tick);
      };
      source.onended = () => { if (!stopped) { stop(); onEnd(); } };
      onStart();
      source.start();
      tick();
    } catch {
      if (!stopped) { stop(); onError(); }
    }
  })();
  return stop;
}
