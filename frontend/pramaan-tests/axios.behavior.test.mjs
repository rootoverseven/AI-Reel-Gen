// Repository source files were not provided in the prompt, so this file tests the
// installed axios 1.18.0 surface directly. Replace the import below with the
// repository's actual axios-wrapping module once the workspace contents are known.

import { test, describe } from 'node:test';
import assert from 'node:assert';
import axios from 'axios';

describe('axios 1.18.0 exposed API', () => {
  test('axios is a callable request factory with expected static methods', () => {
    assert.strictEqual(typeof axios, 'function');
    assert.strictEqual(typeof axios.get, 'function');
    assert.strictEqual(typeof axios.post, 'function');
    assert.strictEqual(typeof axios.put, 'function');
    assert.strictEqual(typeof axios.delete, 'function');
    assert.strictEqual(typeof axios.patch, 'function');
    assert.strictEqual(typeof axios.create, 'function');
  });

  test('axios.create returns an independent instance with inherited defaults', () => {
    const instance = axios.create({ baseURL: 'https://api.example.test', timeout: 1234 });
    assert.ok(instance);
    assert.strictEqual(typeof instance.request, 'function');
    assert.strictEqual(typeof instance.get, 'function');
    assert.strictEqual(instance.defaults.baseURL, 'https://api.example.test');
    assert.strictEqual(instance.defaults.timeout, 1234);
  });

  test('axios interceptors API is present', () => {
    assert.ok(axios.interceptors);
    assert.strictEqual(typeof axios.interceptors.request.use, 'function');
    assert.strictEqual(typeof axios.interceptors.response.use, 'function');
  });
});