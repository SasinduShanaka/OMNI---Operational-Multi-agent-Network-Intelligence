export function focusChatComposer(composer, isAsking) {
  if (!isAsking) {
    composer?.focus()
  }
}
