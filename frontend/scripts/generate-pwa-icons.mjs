#!/usr/bin/env node

/**
 * Generate the app icon set from one geometric definition.
 * Run: pnpm generate:icons
 *
 * The mark is the product's own: a 2×2 grid of record cells on an ink tile,
 * with the last cell in signal blue. It is the same cell language as the
 * wordmark and the calendar, and stays legible at 16px.
 *
 * SVG is written always. PNG (for iOS and Android launchers) is written when
 * ffmpeg is available, so the repo can be refreshed with a single command.
 */

import { execFileSync } from 'node:child_process'
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const publicDir = resolve(__dirname, '..', 'public')

const INK = '#111111'
const PAPER = '#f4f6f9'
const SIGNAL = '#0057ff'

/** Geometry in fractions of the icon size. */
const CELL = 0.245
const GAP = 0.07
const CELL_RADIUS = 0.16 // of a cell
const TILE_RADIUS = 0.22 // of the tile

/**
 * @param {number} size
 * @param {{ rounded?: boolean, scale?: number }} [options]
 *   rounded: false keeps the background full-bleed for maskable icons.
 *   scale: shrinks the grid inside the safe area of a maskable icon.
 */
function icon(size, { rounded = true, scale = 1 } = {}) {
  const cell = size * CELL * scale
  const gap = size * GAP * scale
  const grid = cell * 2 + gap
  const origin = (size - grid) / 2
  const radius = rounded ? size * TILE_RADIUS : 0

  const cells = []
  for (let row = 0; row < 2; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      const isLast = row === 1 && col === 1
      cells.push(
        `<rect x="${round(origin + col * (cell + gap))}" y="${round(
          origin + row * (cell + gap),
        )}" width="${round(cell)}" height="${round(cell)}" rx="${round(
          cell * CELL_RADIUS,
        )}" fill="${isLast ? SIGNAL : PAPER}"/>`,
      )
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="日周报管理系统">
  <rect width="${size}" height="${size}" rx="${round(radius)}" fill="${INK}"/>
  ${cells.join('\n  ')}
</svg>
`
}

function round(value) {
  return Math.round(value * 1000) / 1000
}

const targets = [
  { file: 'favicon.svg', size: 32 },
  { file: 'pwa-192x192.svg', size: 192 },
  { file: 'pwa-512x512.svg', size: 512 },
  // Full-bleed and inset, so the OS mask never clips the grid.
  { file: 'pwa-maskable-512x512.svg', size: 512, options: { rounded: false, scale: 0.86 } },
  { file: 'pwa-192x192.png', size: 192, png: true },
  { file: 'pwa-512x512.png', size: 512, png: true },
  { file: 'apple-touch-icon.png', size: 180, png: true, options: { rounded: false } },
]

let ffmpeg = true
try {
  execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' })
} catch {
  ffmpeg = false
}

for (const target of targets) {
  const svg = icon(target.size, target.options)
  if (!target.png) {
    writeFileSync(join(publicDir, target.file), svg)
    console.log(`✅ ${target.file}`)
    continue
  }
  if (!ffmpeg) {
    console.log(`⏭️  ${target.file} skipped (ffmpeg not found)`)
    continue
  }
  const tempDir = mkdtempSync(join(tmpdir(), 'icon-'))
  const tempSvg = join(tempDir, 'icon.svg')
  writeFileSync(tempSvg, svg)
  execFileSync(
    'ffmpeg',
    ['-loglevel', 'error', '-y', '-i', tempSvg, '-vf', `scale=${target.size}:${target.size}`, join(publicDir, target.file)],
    { stdio: 'inherit' },
  )
  rmSync(tempDir, { recursive: true, force: true })
  console.log(`✅ ${target.file}`)
}
