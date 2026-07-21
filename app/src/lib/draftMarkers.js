// Split a rendered draft body into segments so the two injection markers can
// be styled distinctly from the static template prose. The markers are
// authored by the draft renderer (src/draft/notice.py) and must stay visibly
// separate from official-looking legal text.
const FILLED = /\[FROM YOUR COMPLAINT: (.+?) \(verify\)\]/g
const MISSING = /\[NOT FOUND IN YOUR COMPLAINT: (.+?)\]/g

export function parseDraftBody(body) {
  const markers = []
  let match
  while ((match = FILLED.exec(body)) !== null) {
    markers.push({ start: match.index, end: FILLED.lastIndex, type: 'filled', value: match[1] })
  }
  while ((match = MISSING.exec(body)) !== null) {
    markers.push({ start: match.index, end: MISSING.lastIndex, type: 'missing', value: match[1] })
  }
  markers.sort((a, b) => a.start - b.start)

  const segments = []
  let cursor = 0
  for (const marker of markers) {
    if (marker.start > cursor) {
      segments.push({ type: 'text', value: body.slice(cursor, marker.start) })
    }
    segments.push({ type: marker.type, value: marker.value })
    cursor = marker.end
  }
  if (cursor < body.length) {
    segments.push({ type: 'text', value: body.slice(cursor) })
  }
  return segments
}
