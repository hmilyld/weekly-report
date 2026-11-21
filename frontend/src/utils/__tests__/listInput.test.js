import { describe, it, expect } from 'vitest'

import { continueOrderedList } from '../listInput'

describe('continueOrderedList', () => {
  it('continues numbering at the end of an item', () => {
    expect(continueOrderedList('1. 修了导出', 7)).toEqual({
      value: '1. 修了导出\n2. ',
      caret: 11,
    })
  })

  it('keeps the delimiter and indentation the writer used', () => {
    expect(continueOrderedList('  1) 事项', 7)).toEqual({
      value: '  1) 事项\n  2) ',
      caret: 13,
    })
  })

  it('does nothing when the caret sits in the middle of a line', () => {
    expect(continueOrderedList('1. 一二三', 4)).toBeNull()
  })

  it('does nothing outside an ordered list item', () => {
    expect(continueOrderedList('普通段落', 4)).toBeNull()
    expect(continueOrderedList('- 无序列表', 5)).toBeNull()
  })

  it('ends the list when Enter is pressed on an empty item', () => {
    expect(continueOrderedList('1. 已完成\n2. ', 10)).toEqual({
      value: '1. 已完成\n',
      caret: 7,
    })
  })

  it('renumbers the following items after inserting one', () => {
    const result = continueOrderedList('1. 一\n2. 二\n3. 三', 4)
    expect(result.value).toBe('1. 一\n2. \n3. 二\n4. 三')
    expect(result.caret).toBe(8)
  })

  it('leaves nested items on the numbers their writer gave them', () => {
    const result = continueOrderedList('1. 一\n  5. 子项\n2. 二', 4)
    expect(result.value).toBe('1. 一\n2. \n  5. 子项\n3. 二')
  })

  it('stops renumbering at a paragraph or blank line', () => {
    const result = continueOrderedList('1. 一\n\n3. 另一段', 4)
    expect(result.value).toBe('1. 一\n2. \n\n3. 另一段')
  })
})
