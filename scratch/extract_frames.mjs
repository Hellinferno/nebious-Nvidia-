import { execSync } from 'child_process';

const timestamps = [10, 35, 55, 75, 95, 115];
timestamps.forEach((sec, idx) => {
  const out = `recordings/frame_scene${idx + 1}.png`;
  execSync(`ffmpeg -y -ss ${sec} -i recordings/benchproof_demo_walkthrough.mp4 -frames:v 1 ${out}`, { stdio: 'ignore' });
  console.log(`Saved frame ${idx + 1} at ${sec}s -> ${out}`);
});
