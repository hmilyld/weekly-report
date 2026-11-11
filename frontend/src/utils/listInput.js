/**
 * Markdown-style ordered lists typed into a plain textarea: Enter at the end
 * of "3. 修了导出" continues with "4. " on the next line, keeping the indent
 * and the delimiter the writer used. Enter on a still-empty item ("4. ")
 * ends the list instead of numbering forever, as editors normally do.
 *
 * Pure helper: given the whole value and the caret, return the next value
 * plus the caret to restore, or null when the caret is not on a list item.
 */

const ORDERED_MARKER = /^([ \t]{0,3})(\d{1,9})([.)])([ \t]+|$)/

export function continueOrderedList(value, caret) {
  const lineStart = value.lastIndexOf('\n', caret - 1) + 1
  const nextBreak = value.indexOf('\n', caret)
  const lineEnd = nextBreak === -1 ? value.length : nextBreak
  const line = value.slice(lineStart, lineEnd)

  const match = ORDERED_MARKER.exec(line)
  if (!match) return null

  const [, indent, number, delimiter] = match
  const rest = line.slice(match[0].length)

  // Only continue from the end of an item: Enter in the middle of a line
  // keeps its ordinary behaviour instead of renumbering the lines below.
  if (value.slice(caret, lineEnd).trim()) return null

  if (!rest.trim()) {
    // The item holds nothing yet: Enter drops the marker and ends the list.
    return { value: value.slice(0, lineStart) + value.slice(lineEnd), caret: lineStart }
  }

  const next = Number(number) + 1
  const insertion = `\n${indent}${next}${delimiter} `
  const tail = renumber(value.slice(lineEnd), next + 1, indent)
  return {
    value: value.slice(0, lineEnd) + insertion + tail,
    caret: lineEnd + insertion.length,
  }
}

/**
 * Bump the numbers of the items that follow a freshly inserted one, so an
 * item added in the middle of a list never repeats a number. Items nested
 * under a neighbour keep the numbers their writer gave them; the scan stops
 * where the list itself stops (a paragraph, a blank line, a parent level).
 */
function renumber(tail, firstNumber, indent) {
  const depth = indent.length
  const lines = tail.split('\n')
  let number = firstNumber
  for (let i = 1; i < lines.length; i += 1) {
    const match = ORDERED_MARKER.exec(lines[i])
    if (!match) break
    const lineDepth = match[1].length
    if (lineDepth < depth) break
    if (lineDepth > depth) continue
    lines[i] = lines[i].replace(/^([ \t]*)\d{1,9}/, `$1${number}`)
    number += 1
  }
  return lines.join('\n')
}
