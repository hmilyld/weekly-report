#!/usr/bin/env node

/**
 * Generate PWA SVG icons for the Weekly Report app.
 * Run: node scripts/generate-pwa-icons.mjs
 *
 * The icon design: A calendar with document/report lines and an AI sparkle,
 * using the app's accent color (#2563eb).
 */

import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const publicDir = resolve(__dirname, '..', 'public')

function generateSVG(size) {
  const s = size // shorthand
  const r = Math.round(s * 0.208) // corner radius
  const pad = Math.round(s * 0.1875) // outer padding
  const headerH = Math.round(s * 0.146) // calendar header height
  const ringW = Math.round(s * 0.031)
  const ringH = Math.round(s * 0.125)
  const ringR = Math.round(s * 0.016)
  const dotR = Math.round(s * 0.021)
  const lineH = Math.round(s * 0.021)
  const lineR = Math.round(s * 0.01)

  // Calendar body position
  const cx = pad
  const cy = Math.round(s * 0.25)
  const cw = s - pad * 2
  const ch = s - cy - Math.round(s * 0.1)

  // Header bar
  const hy = cy
  const hh = headerH

  // Ring positions
  const ring1x = Math.round(cw * 0.2) + cx
  const ring2x = Math.round(cw * 0.65) + cx
  const ringY = cy - Math.round(s * 0.06)

  // Dot positions
  const dotY = cy + hh + Math.round(s * 0.08)
  const dotSpacing = Math.round((cw - 40) / 4)

  // Line positions
  const lineStartX = cx + Math.round(s * 0.083)
  const line1y = dotY + Math.round(s * 0.094)
  const line2y = line1y + Math.round(s * 0.063)
  const line3y = line2y + Math.round(s * 0.063)

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${s} ${s}" width="${s}" height="${s}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2563eb"/>
      <stop offset="100%" style="stop-color:#1d4ed8"/>
    </linearGradient>
    <linearGradient id="paper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ffffff"/>
      <stop offset="100%" style="stop-color:#f0f4ff"/>
    </linearGradient>
  </defs>
  <!-- Background -->
  <rect width="${s}" height="${s}" rx="${r}" fill="url(#bg)"/>
  <!-- Calendar body -->
  <rect x="${cx}" y="${cy}" width="${cw}" height="${ch}" rx="${Math.round(s * 0.063)}" fill="url(#paper)" opacity="0.95"/>
  <!-- Calendar header -->
  <rect x="${cx}" y="${hy}" width="${cw}" height="${hh}" rx="${Math.round(s * 0.063)}" fill="#1e40af"/>
  <rect x="${cx}" y="${hy + hh - Math.round(s * 0.02)}" width="${cw}" height="${Math.round(s * 0.02)}" fill="#1e40af"/>
  <!-- Calendar rings -->
  <rect x="${ring1x}" y="${ringY}" width="${ringW}" height="${ringH}" rx="${ringR}" fill="#ffffff" opacity="0.9"/>
  <rect x="${ring2x}" y="${ringY}" width="${ringW}" height="${ringH}" rx="${ringR}" fill="#ffffff" opacity="0.9"/>
  <!-- Week day dots -->
  <circle cx="${cx + 20}" cy="${dotY}" r="${dotR}" fill="#93c5fd"/>
  <circle cx="${cx + 20 + dotSpacing}" cy="${dotY}" r="${dotR}" fill="#93c5fd"/>
  <circle cx="${cx + 20 + dotSpacing * 2}" cy="${dotY}" r="${dotR}" fill="#93c5fd"/>
  <circle cx="${cx + 20 + dotSpacing * 3}" cy="${dotY}" r="${dotR}" fill="#93c5fd"/>
  <circle cx="${cx + 20 + dotSpacing * 4}" cy="${dotY}" r="${dotR}" fill="#93c5fd"/>
  <!-- Report lines -->
  <rect x="${lineStartX}" y="${line1y}" width="${Math.round(cw * 0.72)}" height="${lineH}" rx="${lineR}" fill="#bfdbfe"/>
  <rect x="${lineStartX}" y="${line2y}" width="${Math.round(cw * 0.59)}" height="${lineH}" rx="${lineR}" fill="#bfdbfe"/>
  <rect x="${lineStartX}" y="${line3y}" width="${Math.round(cw * 0.47)}" height="${lineH}" rx="${lineR}" fill="#bfdbfe"/>
  <!-- AI sparkle -->
  <g transform="translate(${cx + cw - Math.round(s * 0.07)},${line1y - Math.round(s * 0.01)})" fill="#fbbf24">
    <polygon points="0,-${Math.round(s * 0.038)} ${Math.round(s * 0.01)},-${Math.round(s * 0.01)} ${Math.round(s * 0.038)},0 ${Math.round(s * 0.01)},${Math.round(s * 0.01)} 0,${Math.round(s * 0.038)} -${Math.round(s * 0.01)},${Math.round(s * 0.01)} -${Math.round(s * 0.038)},0 -${Math.round(s * 0.01)},-${Math.round(s * 0.01)}"/>
  </g>
</svg>`
}

// Generate icons
const sizes = [192, 512]
for (const size of sizes) {
  const svg = generateSVG(size)
  const path = resolve(publicDir, `pwa-${size}x${size}.svg`)
  writeFileSync(path, svg, 'utf-8')
  console.log(`✓ Generated ${path}`)
}

console.log('Done! PWA icons generated in public/')
