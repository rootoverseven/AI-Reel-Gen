import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import axios from 'axios';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

async function readRepoFile(...segments) {
  return fs.readFile(path.join(repoRoot, ...segments), 'utf8');
}

// Build a stub adapter that captures the request and returns a canned response.
function stubAdapter(expectedResponse, capture = null) {
  return function adapter(config) {
    if (capture) {
      capture(config);
    }
    return Promise.resolve({
      data: expectedResponse,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
      request: {},
    });
  };
}

describe('repository axios usage on installed version', () => {
  it('uses axios ^1.18.0 or a compatible semver minor/patch update', async () => {
    const pkg = JSON.parse(await readRepoFile('node_modules', 'axios', 'package.json'));
    const major = parseInt(pkg.version.split('.')[0], 10);
    const minor = parseInt(pkg.version.split('.')[1], 10);
    const patch = parseInt(pkg.version.split('.')[2], 10);

    // Ground truth: installed package must satisfy the ^1.18.0 range.
    assert.strictEqual(major, 1, `expected axios major version 1, got ${pkg.version}`);
    assert.ok(
      minor > 18 || (minor === 18 && patch >= 0),
      `expected axios >= 1.18.0, got ${pkg.version}`
    );
  });

  it('App.jsx still imports axios and calls the backend endpoints', async () => {
    const appSource = await readRepoFile('src', 'App.jsx');
    assert.match(appSource, /import axios from ['"]axios['"]/);
    assert.match(appSource, /axios\.get\(['"]\/voices['"]\)/);
    assert.match(appSource, /axios\.post\(['"]\/generate-script['"]/);
    assert.match(appSource, /axios\.post\(['"]\/generate-video['"]/);
  });

  it('vite proxy config matches the axios endpoints', async () => {
    const viteConfig = await readRepoFile('vite.config.js');
    assert.match(viteConfig, /['"]\/voices['"]:\s*['"]http:\/\/127\.0\.0\.1:8000['"]/);
    assert.match(viteConfig, /['"]\/generate-script['"]:\s*['"]http:\/\/127\.0\.0\.1:8000['"]/);
    assert.match(viteConfig, /['"]\/generate-video['"]:\s*['"]http:\/\/127\.0\.0\.1:8000['"]/);
  });

  it('GET /voices behaves as App.jsx expects', async () => {
    const voices = [
      { id: 'voice-1', name: 'Savita' },
      { id: 'voice-2', name: 'Suraj' },
    ];
    const res = await axios.get('/voices', { adapter: stubAdapter(voices) });
    assert.ok(Array.isArray(res.data));
    assert.deepStrictEqual(res.data, voices);
    assert.ok(res.data[0].id);
    assert.ok(res.data[0].name);
  });

  it('POST /generate-script behaves as App.jsx expects', async () => {
    const topic = 'Explain React Hooks vs Classes';
    const captured = [];
    const response = { script: 'A sample dialogue script.' };
    const res = await axios.post('/generate-script', { topic }, {
      adapter: stubAdapter(response, cfg => captured.push(cfg)),
    });

    assert.strictEqual(captured.length, 1);
    assert.strictEqual(captured[0].method, 'post');
    assert.strictEqual(captured[0].url, '/generate-script');
    assert.deepStrictEqual(JSON.parse(captured[0].data), { topic });
    assert.strictEqual(res.data.script, response.script);
  });

  it('POST /generate-video behaves as App.jsx expects', async () => {
    const payload = {
      script: 'A sample dialogue script.',
      savita_voice_id: 'voice-1',
      suraj_voice_id: 'voice-2',
      savita_img: 'savita.png',
      suraj_img: 'suraj.png',
    };
    const captured = [];
    const response = { video_path: '/videos/output.mp4' };
    const res = await axios.post('/generate-video', payload, {
      adapter: stubAdapter(response, cfg => captured.push(cfg)),
    });

    assert.strictEqual(captured.length, 1);
    assert.strictEqual(captured[0].method, 'post');
    assert.strictEqual(captured[0].url, '/generate-video');
    assert.deepStrictEqual(JSON.parse(captured[0].data), payload);
    assert.strictEqual(res.data.video_path, response.video_path);
  });
});
