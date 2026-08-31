// 构建时 pangu：HTML 生成后为中英文交界补空格，替代运行时脚本（消除首屏闪变）
// 规则与前端 pangu 一致（pangu.spacingText），但跳过代码块与 KaTeX 公式，避免污染
'use strict'

const cheerio = require('cheerio')
const pangu = require('pangu')

// 跳过这些元素内部的文本：脚本/样式、代码块、KaTeX 公式
const SKIP_SELECTOR = 'script, style, pre, code, .katex'

hexo.extend.filter.register('after_render:html', function (html) {
  const $ = cheerio.load(html)
  let changed = 0

  $('body *').each(function () {
    $(this)
      .contents()
      .each(function () {
        if (this.type !== 'text') return
        if ($(this).closest(SKIP_SELECTOR).length) return
        const text = this.data
        if (!text) return
        const spaced = pangu.spacingText(text)
        if (spaced !== text) {
          this.data = spaced
          changed++
        }
      })
  })

  return changed ? $.html() : html
})
