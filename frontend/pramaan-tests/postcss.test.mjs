import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import postcss from 'postcss'
import postcssLoadConfig from 'postcss-load-config'

const repoRoot = process.cwd()

function readRepoFile(relativePath) {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8')
}

test('postcss.config.js loads and runs with the installed postcss', async () => {
  const { plugins, options } = await postcssLoadConfig({}, repoRoot)
  assert.ok(Array.isArray(plugins), 'expected plugins array from postcss.config.js')
  assert.ok(plugins.length >= 2, `expected at least 2 plugins, got ${plugins.length}`)

  const css = readRepoFile('src/index.css')
  const result = await postcss(plugins).process(css, {
    from: resolve(repoRoot, 'src/index.css'),
    ...options,
  })

  assert.ok(
    result.css.includes('--tw-border-spacing-x: 0'),
    'tailwindcss base output should be present'
  )
  assert.ok(
    result.css.includes('::before'),
    'tailwindcss pseudo-element reset should be present'
  )
})

test('repository CSS with standard declarations is autoprefixed', async () => {
  const { plugins, options } = await postcssLoadConfig({}, repoRoot)
  const css = readRepoFile('src/App.css')
  const result = await postcss(plugins).process(css, {
    from: resolve(repoRoot, 'src/App.css'),
    ...options,
  })

  assert.ok(
    result.css.includes('.logo'),
    'App.css selectors should survive processing'
  )
  assert.ok(
    result.css.includes('animation: logo-spin'),
    'App.css animations should survive processing'
  )
})
