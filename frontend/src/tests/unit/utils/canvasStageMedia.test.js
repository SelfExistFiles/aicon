import { describe, it, expect } from 'vitest'
import {
  resolveCanvasRichTextHtml,
  resolveCanvasRunErrorSummary,
  resolveCanvasRunStatusMeta,
  resolveCanvasTextPreview,
  resolveCanvasStagePreviewText
} from '@/utils/canvasStageMedia'

describe('canvasStageMedia rich text preview', () => {
  it('preserves rich text structure in the text preview summary', () => {
    const preview = resolveCanvasTextPreview({
      content: {
        text: '<h1>Title</h1><p>First paragraph</p><ul><li>Alpha</li><li>Beta</li></ul>'
      }
    })

    expect(preview).toContain('Title')
    expect(preview).toContain('First paragraph')
    expect(preview).toContain('• Alpha')
    expect(preview).toContain('• Beta')
  })

  it('keeps plain text previews readable', () => {
    const preview = resolveCanvasStagePreviewText({
      item_type: 'text',
      content: {
        text: 'Plain text content'
      }
    })

    expect(preview).toBe('Plain text content')
  })

  it('converts plain text content into paragraph-based rich text html', () => {
    const richHtml = resolveCanvasRichTextHtml({
      content: {
        text: 'Title line\n\nSecond paragraph'
      }
    })

    expect(richHtml).toBe('<p>Title line</p><p>Second paragraph</p>')
  })

  it('preserves authored rich text html instead of escaping it into plain text', () => {
    const richHtml = resolveCanvasRichTextHtml({
      content: {
        text: '<h1>Heading</h1><blockquote>Quoted</blockquote><ul><li>One</li></ul>'
      }
    })

    expect(richHtml).toContain('<h1>Heading</h1>')
    expect(richHtml).toContain('<blockquote>Quoted</blockquote>')
    expect(richHtml).toContain('<ul><li>One</li></ul>')
  })

  it('returns retrying status meta for transient video status fetch failures', () => {
    const meta = resolveCanvasRunStatusMeta({
      item_type: 'video',
      last_run_status: 'processing',
      last_output: {
        transient_status_issue: true,
        status_fetch_error: 'temporary status failure'
      }
    })

    expect(meta).toMatchObject({
      tone: 'warning',
      label: '状态同步中'
    })
  })

  it('uses status detail as video preview fallback text', () => {
    const preview = resolveCanvasStagePreviewText({
      item_type: 'video',
      last_run_status: 'pending',
      content: {}
    })

    expect(preview).toBe('任务已入队，正在等待执行。')
  })

  it('treats completed video object keys as ready media even before a resolved url is present', () => {
    const meta = resolveCanvasRunStatusMeta({
      item_type: 'video',
      last_run_status: 'completed',
      content: {
        result_video_object_key: 'uploads/final-video.mp4'
      },
      last_output: {}
    })

    expect(meta).toMatchObject({
      tone: 'success',
      label: '视频已生成',
      detail: '结果已就绪，可直接预览。'
    })
  })

  it('compresses raw json-like errors into a readable summary', () => {
    const summary = resolveCanvasRunErrorSummary('{"code":"","message":"生成过程中出现异常，请重新发起请求"}')

    expect(summary).toBe('生成过程中出现异常，请重试。')
  })
})
