import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import { fetchVoices, generateScript, generateVideo } from '../src/api.js';

const originalAdapter = axios.defaults.adapter;

function parseData(config) {
  if (config.data == null) return undefined;
  return typeof config.data === 'string' ? JSON.parse(config.data) : config.data;
}

function createStubAdapter(handlers) {
  return function stubAdapter(config) {
    const method = (config.method || 'get').toLowerCase();
    const url = config.url;
    const data = parseData(config);

    for (const handler of handlers) {
      if (handler.url === url && handler.method === method) {
        return Promise.resolve({
          data: handler.respond(config, data),
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
          request: {},
        });
      }
    }

    return Promise.reject(new Error(`Unexpected ${method.toUpperCase()} ${url}`));
  };
}

describe('api', () => {
  before(() => {
    axios.defaults.adapter = createStubAdapter([
      {
        method: 'get',
        url: '/voices',
        respond: () => [
          { id: 'voice-1', name: 'Savita' },
          { id: 'voice-2', name: 'Suraj' },
        ],
      },
      {
        method: 'post',
        url: '/generate-script',
        respond: (config, data) => {
          assert.equal(data.topic, 'React Hooks');
          return { script: 'A script about React Hooks' };
        },
      },
      {
        method: 'post',
        url: '/generate-video',
        respond: (config, data) => {
          assert.equal(data.script, 'A script about React Hooks');
          assert.equal(data.savita_voice_id, 'voice-1');
          assert.equal(data.suraj_voice_id, 'voice-2');
          assert.equal(data.savita_img, 'savita.png');
          assert.equal(data.suraj_img, 'suraj.png');
          return { video_path: '/output/reel.mp4' };
        },
      },
    ]);
  });

  after(() => {
    axios.defaults.adapter = originalAdapter;
  });

  it('fetches available voices', async () => {
    const voices = await fetchVoices();
    assert.deepEqual(voices, [
      { id: 'voice-1', name: 'Savita' },
      { id: 'voice-2', name: 'Suraj' },
    ]);
  });

  it('generates a script for a topic', async () => {
    const script = await generateScript('React Hooks');
    assert.equal(script, 'A script about React Hooks');
  });

  it('generates a video with the configured voices and images', async () => {
    const videoPath = await generateVideo({
      script: 'A script about React Hooks',
      savitaVoice: 'voice-1',
      surajVoice: 'voice-2',
    });
    assert.equal(videoPath, '/output/reel.mp4');
  });
});
