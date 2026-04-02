/**
 * @vitest-environment jsdom
 */

import { createApp, defineComponent, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCanvasEditor } from '@/composables/useCanvasEditor'
import { canvasService } from '@/services/canvas'

vi.mock('@/services/canvas', () => ({
  canvasService: {
    getLite: vi.fn(),
    getItem: vi.fn(),
    updateItem: vi.fn(),
    createItem: vi.fn(),
    deleteItem: vi.fn(),
    createConnection: vi.fn(),
    deleteConnection: vi.fn()
  }
}))

const mountComposable = () => {
  let composable = null
  const root = document.createElement('div')
  const app = createApp(
    defineComponent({
      setup() {
        composable = useCanvasEditor()
        return () => null
      }
    })
  )
  app.mount(root)
  return {
    app,
    get composable() {
      return composable
    }
  }
}

describe('useCanvasEditor item merging', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('replaces last_output so stale video errors do not survive a later success', async () => {
    canvasService.getLite.mockResolvedValue({
      document: { id: 'doc-1', title: 'Canvas' },
      items: [
        {
          id: 'item-1',
          item_type: 'video',
          title: '视频节点 1',
          position_x: 10,
          position_y: 20,
          width: 360,
          height: 300,
          z_index: 1,
          content: { prompt: 'foo' },
          generation_config: {},
          last_run_status: 'failed',
          last_run_error: 'old failure',
          last_output: {
            transient_status_issue: true,
            status_fetch_error: 'temporary status failure'
          }
        }
      ],
      connections: []
    })

    const { app, composable } = mountComposable()
    await composable.loadDocument('doc-1')
    await nextTick()

    composable.updateItem('item-1', {
      last_run_status: 'completed',
      last_run_error: null,
      last_output: {
        result_video_object_key: 'uploads/final.mp4'
      }
    }, { persist: false })

    expect(composable.items.value[0].last_run_status).toBe('completed')
    expect(composable.items.value[0].last_run_error).toBeNull()
    expect(composable.items.value[0].last_output).toEqual({
      result_video_object_key: 'uploads/final.mp4'
    })

    app.unmount()
  })
})
