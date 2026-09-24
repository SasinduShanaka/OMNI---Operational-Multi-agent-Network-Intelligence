import test from 'node:test'
import assert from 'node:assert/strict'

test('focuses the chat composer when Omni is ready for another question', async () => {
  let focusCount = 0
  const composer = { focus: () => { focusCount += 1 } }
  const { focusChatComposer = () => {} } = await import('./chatFocus.js').catch(() => ({}))

  focusChatComposer(composer, false)

  assert.equal(focusCount, 1)
})
