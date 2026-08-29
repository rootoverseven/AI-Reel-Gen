import { describe, it } from 'node:test';
import assert from 'node:assert';
import axios from 'axios';
import { readFileSync } from 'node:fs';

const appSource = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');

const okResponse = (config, data) => ({
  data,
  status: 200,
  statusText: 'OK',
  headers: {},
  config,
});

describe('Repository axios usage patterns from App.jsx', () => {
  it('App.jsx imports and calls axios', () => {
    assert.match(appSource, /import axios from ['"]axios['"]/);
    assert.match(appSource, /axios\.get\(['"]\/voices['"]\)/);
    assert.match(appSource, /axios\.post\(['"]\/generate-script['"],/);
    assert.match(appSource, /axios\.post\(['"]\/generate-video['"],/);
  });

  it('default axios export provides get and post', () => {
    assert.strictEqual(typeof axios, 'function');
    assert.strictEqual(typeof axios.get, 'function');
    assert.strictEqual(typeof axios.post, 'function');
  });

  it('axios.get resolves with res.data like voices fetch', async () => {
    const voices = [
      { id: 'voice-savita', name: 'Savita' },
      { id: 'voice-suraj', name: 'Suraj' },
    ];
    const res = await axios.get('/voices', {
      adapter: (config) => Promise.resolve(okResponse(config, voices)),
    });
    assert.deepStrictEqual(res.data, voices);
  });

  it('axios.post with topic resolves with res.data.script', async () => {
    const res = await axios.post('/generate-script', { topic: 'React Hooks' }, {
      adapter: (config) => Promise.resolve(okResponse(config, { script: 'Generated script' })),
    });
    assert.strictEqual(res.data.script, 'Generated script');
  });

  it('axios.post with video payload resolves with res.data.video_path', async () => {
    const payload = {
      script: 'Generated script',
      savita_voice_id: 'voice-savita',
      suraj_voice_id: 'voice-suraj',
      savita_img: 'savita.png',
      suraj_img: 'suraj.png',
    };
    const res = await axios.post('/generate-video', payload, {
      adapter: (config) => Promise.resolve(okResponse(config, { video_path: '/tmp/output.mp4' })),
    });
    assert.strictEqual(res.data.video_path, '/tmp/output.mp4');
  });

  it('axios request rejection can be caught like App.jsx error handlers', async () => {
    await assert.rejects(
      axios.get('/voices', {
        adapter: () => Promise.reject(new Error('network down')),
      }),
      /network down/
    );
  });
});
