import axios from 'axios';

export async function fetchVoices() {
  const res = await axios.get('/voices');
  return res.data;
}

export async function generateScript(topic) {
  const res = await axios.post('/generate-script', { topic });
  return res.data.script;
}

export async function generateVideo({ script, savitaVoice, surajVoice }) {
  const res = await axios.post('/generate-video', {
    script,
    savita_voice_id: savitaVoice,
    suraj_voice_id: surajVoice,
    savita_img: 'savita.png',
    suraj_img: 'suraj.png',
  });
  return res.data.video_path;
}
