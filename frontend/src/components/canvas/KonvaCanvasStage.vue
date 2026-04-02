<template>
  <div ref="containerRef" class="konva-stage-shell">
    <v-stage
      v-if="stageReady"
      ref="stageRef"
      class="konva-stage"
      :config="stageConfig"
      @wheel="handleWheel"
      @dragmove="handleStageDragMove"
      @dragend="handleStageDragMove"
      @mousedown="handlePointerDown"
      @mousemove="handlePointerMove"
      @mouseup="handlePointerUp"
      @click="handleStageClick"
    >
      <v-layer>
        <v-line
          v-for="connection in normalizedConnections"
          :key="connection.id"
          :config="buildConnectionLineConfig(connection)"
        />
      </v-layer>

      <v-layer>
        <v-group
          v-for="item in renderedItems"
          :key="item.id"
          :config="buildItemGroupConfig(item)"
        >
          <v-rect :config="buildItemRectConfig(item)" />
          <v-image v-if="hasItemMedia(item)" :config="buildItemMediaConfig(item)" />
          <v-text :config="buildItemTitleConfig(item)" />
          <v-text :config="buildItemPreviewConfig(item)" />
          <v-circle :config="buildHandleConfig(item, 'left')" />
          <v-circle :config="buildHandleConfig(item, 'right')" />
        </v-group>
      </v-layer>
    </v-stage>

    <div v-else class="konva-stage-placeholder">画布加载中...</div>

    <div v-if="marqueeOverlayStyle" class="stage-selection-overlay" :style="marqueeOverlayStyle"></div>

    <div
      v-for="item in textOverlayItems"
      :key="`${item.id}-text-overlay`"
      class="stage-text-overlay"
      :class="{ 'stage-text-overlay--selected': selectedItemIds.includes(item.id) }"
      :style="buildTextOverlayStyle(item)"
    >
      <div class="stage-text-overlay__title">{{ item.title || fallbackTitle(item.item_type) }}</div>
      <div class="stage-text-overlay__body canvas-rich-text-content" v-html="item.richTextHtml"></div>
    </div>

    <div
      v-for="item in statusOverlayItems"
      :key="`${item.id}-status-overlay`"
      class="stage-status-chip"
      :class="`stage-status-chip--${item.statusMeta.tone}`"
      :style="buildStatusOverlayStyle(item)"
    >
      <div class="stage-status-chip__label">{{ item.statusMeta.label }}</div>
    </div>

    <div
      v-for="item in generatingOverlayItems"
      :key="`${item.id}-generating-overlay`"
      class="stage-generating-overlay"
      :style="buildGeneratingOverlayStyle(item)"
    >
      <CanvasGeneratingOverlay
        :visible="true"
        :label="item.generatingMeta.label"
        :hint="item.generatingMeta.hint"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CanvasGeneratingOverlay from '@/components/canvas/CanvasGeneratingOverlay.vue'
import { resolveCanvasImageNodeSize } from '@/utils/canvasImageNodeLayout'
import { resolveCanvasVideoNodeSize } from '@/utils/canvasVideoNodeLayout'
import {
  releaseCanvasStageVideoEntry,
  resolveCanvasRichTextHtml,
  resolveCanvasStageGeneratingMeta,
  resolveCanvasRunStatusMeta,
  resolveCanvasStageMediaUrl,
  resolveCanvasStagePreviewText,
  resolveStageVideoPreviewTargets
} from '@/utils/canvasStageMedia'

const props = defineProps({
  items: { type: Array, default: () => [] },
  connections: { type: Array, default: () => [] },
  selectedItemIds: { type: Array, default: () => [] },
  selectedConnectionIds: { type: Array, default: () => [] },
  editingItemId: { type: String, default: '' }
})

const emit = defineEmits([
  'connection-click',
  'item-click',
  'item-dblclick',
  'item-drag-end',
  'item-handle-pointerdown',
  'item-resize-suggest',
  'stage-click',
  'viewport-change',
  'selection-box-end'
])

const containerRef = ref(null)
const stageRef = ref(null)
const stageSize = ref({ width: 0, height: 0 })
const stageScale = ref(1)
const stagePosition = ref({ x: 0, y: 0 })
const stageReady = ref(false)
const loadedImageMap = ref({})
const loadedVideoMap = ref({})
const marqueeSelection = ref(null)
const suppressStageClick = ref(false)

let resizeObserver = null

const resolveCanvasItemWidth = (item) => {
  if (item.item_type === 'image') {
    return resolveCanvasImageNodeSize(item, loadedImageMap.value[item.id]?.image).width
  }
  if (item.item_type === 'video') {
    return resolveCanvasVideoNodeSize(item, loadedVideoMap.value[item.id]?.video).width
  }
  const width = Number(item.width || 0)
  return Math.min(Math.max(width || 340, 320), 420)
}

const resolveCanvasItemHeight = (item) => {
  if (item.item_type === 'image') {
    return resolveCanvasImageNodeSize(item, loadedImageMap.value[item.id]?.image).height
  }
  if (item.item_type === 'video') {
    return resolveCanvasVideoNodeSize(item, loadedVideoMap.value[item.id]?.video).height
  }
  const height = Number(item.height || 0)
  return Math.min(Math.max(height || 220, 180), 280)
}

const normalizedItems = computed(() =>
  props.items.map((item) => ({
    ...item,
    position_x: Number(item.position_x || 0),
    position_y: Number(item.position_y || 0),
    width: resolveCanvasItemWidth(item),
    height: resolveCanvasItemHeight(item)
  }))
)

const itemLookup = computed(() =>
  normalizedItems.value.reduce((map, item) => {
    map[item.id] = item
    return map
  }, {})
)

const renderedItems = computed(() =>
  normalizedItems.value.filter((item) => String(item.id || '') !== String(props.editingItemId || ''))
)

const textOverlayItems = computed(() =>
  renderedItems.value
    .filter((item) => item.item_type === 'text')
    .map((item) => ({
      ...item,
      richTextHtml: resolveCanvasRichTextHtml(item)
    }))
)

const generatingOverlayItems = computed(() =>
  renderedItems.value
    .map((item) => {
      const generatingMeta = resolveCanvasStageGeneratingMeta(item)
      if (!generatingMeta) {
        return null
      }
      return { ...item, generatingMeta }
    })
    .filter(Boolean)
)

const statusOverlayItems = computed(() =>
  renderedItems.value
    .map((item) => {
      const statusMeta = resolveCanvasRunStatusMeta(item)
      if (!statusMeta) {
        return null
      }
      return { ...item, statusMeta }
    })
    .filter(Boolean)
)

const normalizedConnections = computed(() =>
  props.connections
    .map((connection) => {
      const sourceItem = itemLookup.value[connection.source_item_id]
      const targetItem = itemLookup.value[connection.target_item_id]
      if (!sourceItem || !targetItem) {
        return null
      }

      const sourcePoint = resolveHandlePoint(sourceItem, connection.source_handle, 'source')
      const targetPoint = resolveHandlePoint(targetItem, connection.target_handle, 'target')
      const startX = sourcePoint.x
      const startY = sourcePoint.y
      const endX = targetPoint.x
      const endY = targetPoint.y
      const dx = Math.abs(endX - startX)
      const controlOffset = Math.min(Math.max(dx * 0.4, 60), 120)
      const controlX1 = connection.source_handle === 'left' ? startX - controlOffset : startX + controlOffset
      const controlX2 = connection.target_handle === 'right' ? endX + controlOffset : endX - controlOffset

      return {
        ...connection,
        points: [startX, startY, controlX1, startY, controlX2, endY, endX, endY]
      }
    })
    .filter(Boolean)
)

const stageConfig = computed(() => ({
  width: stageSize.value.width,
  height: stageSize.value.height,
  draggable: true,
  x: stagePosition.value.x,
  y: stagePosition.value.y,
  scaleX: stageScale.value,
  scaleY: stageScale.value
}))

const emitViewportChange = () => {
  emit('viewport-change', {
    x: stagePosition.value.x,
    y: stagePosition.value.y,
    scale: stageScale.value,
    width: stageSize.value.width,
    height: stageSize.value.height
  })
}

const updateStageSize = () => {
  if (!containerRef.value) {
    return
  }
  const rect = containerRef.value.getBoundingClientRect()
  stageSize.value = {
    width: Math.max(Math.floor(rect.width), 320),
    height: Math.max(Math.floor(rect.height), 480)
  }
  stageReady.value = true
  emitViewportChange()
}

const buildItemGroupConfig = (item) => ({
  x: item.position_x,
  y: item.position_y,
  draggable: true,
  listening: true,
  onClick: (event) => emit('item-click', item, event?.evt || {}),
  onDblclick: () => emit('item-dblclick', item),
  onDragend: (event) => handleItemDragEnd(item, event)
})

const buildItemRectConfig = (item) => {
  const isSelected = props.selectedItemIds.includes(item.id)
  return {
    width: item.width,
    height: item.height,
    cornerRadius: 20,
    fillLinearGradientStartPoint: { x: 0, y: 0 },
    fillLinearGradientEndPoint: { x: 0, y: Math.max(item.height, 1) },
    fillLinearGradientColorStops: resolveItemGradient(item.item_type),
    stroke: isSelected ? '#4b78ff' : pickItemStroke(item.item_type),
    strokeWidth: isSelected ? 1.8 : 1,
    shadowColor: isSelected ? 'rgba(75, 120, 255, 0.2)' : 'rgba(34, 57, 98, 0.12)',
    shadowBlur: isSelected ? 22 : 14,
    shadowOffsetY: 8,
    shadowOpacity: 1
  }
}

const hasItemImage = (item) => Boolean(item?.item_type === 'image' && resolveLoadedImageEntry(item.id)?.image)
const hasItemVideo = (item) => Boolean(item?.item_type === 'video' && resolveLoadedVideoEntry(item.id)?.video)
const hasItemMedia = (item) => hasItemImage(item) || hasItemVideo(item)
const resolveLoadedImageEntry = (itemId) => loadedImageMap.value[itemId] || null
const resolveLoadedVideoEntry = (itemId) => loadedVideoMap.value[itemId] || null

const buildItemMediaConfig = (item) => {
  const imageEntry = resolveLoadedImageEntry(item.id)
  const videoEntry = resolveLoadedVideoEntry(item.id)
  return {
    x: 1,
    y: 1,
    width: Math.max(item.width - 2, 0),
    height: Math.max(item.height - 2, 0),
    image: imageEntry?.image || videoEntry?.video || null,
    cornerRadius: 19,
    opacity: 1
  }
}

const buildItemTitleConfig = (item) => ({
  x: item.item_type === 'text' ? 18 : 20,
  y: item.item_type === 'text' ? 14 : 18,
  width: item.width - (item.item_type === 'text' ? 32 : 40),
  text: item.title || fallbackTitle(item.item_type),
  fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  fill: '#1f2a44',
  fontSize: item.item_type === 'text' ? 14 : 16,
  fontStyle: 'bold',
  lineHeight: 1.2,
  ellipsis: true,
  visible: item.item_type !== 'text' && !hasItemMedia(item)
})

const buildItemPreviewConfig = (item) => ({
  x: item.item_type === 'text' ? 16 : 20,
  y: item.item_type === 'text' ? 40 : 52,
  width: item.width - (item.item_type === 'text' ? 32 : 40),
  height: Math.max(item.height - (item.item_type === 'text' ? 56 : 84), 24),
  text: resolveCanvasStagePreviewText(item),
  fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  fill: item.item_type === 'text' ? '#52607a' : '#42526b',
  fontSize: item.item_type === 'text' ? 12.5 : 13,
  lineHeight: item.item_type === 'text' ? 1.65 : 1.6,
  wrap: 'word',
  ellipsis: true,
  visible: item.item_type !== 'text' && !hasItemMedia(item)
})

const buildTextOverlayStyle = (item) => ({
  width: `${item.width * stageScale.value}px`,
  height: `${item.height * stageScale.value}px`,
  transform: `translate(${item.position_x * stageScale.value + stagePosition.value.x}px, ${item.position_y * stageScale.value + stagePosition.value.y}px)`
})

const buildGeneratingOverlayStyle = (item) => ({
  width: `${item.width * stageScale.value}px`,
  height: `${item.height * stageScale.value}px`,
  transform: `translate(${item.position_x * stageScale.value + stagePosition.value.x}px, ${item.position_y * stageScale.value + stagePosition.value.y}px)`
})

const buildStatusOverlayStyle = (item) => ({
  transform: `translate(${item.position_x * stageScale.value + stagePosition.value.x + 14}px, ${item.position_y * stageScale.value + stagePosition.value.y + 14}px)`
})

const buildConnectionLineConfig = (connection) => ({
  points: connection.points,
  stroke: props.selectedConnectionIds.includes(connection.id) ? '#4b78ff' : 'rgba(82, 96, 122, 0.42)',
  strokeWidth: props.selectedConnectionIds.includes(connection.id) ? 3.2 : 2.4,
  hitStrokeWidth: 16,
  shadowColor: props.selectedConnectionIds.includes(connection.id) ? 'rgba(75, 120, 255, 0.22)' : 'rgba(82, 96, 122, 0.12)',
  shadowBlur: props.selectedConnectionIds.includes(connection.id) ? 12 : 8,
  lineCap: 'round',
  lineJoin: 'round',
  bezier: true,
  opacity: 0.9,
  onClick: (event) => emit('connection-click', connection, event?.evt || {})
})

const buildHandleConfig = (item, handle) => {
  const isLeft = handle === 'left'
  const isSelected = props.selectedItemIds.includes(item.id)
  const offset = isSelected ? 32 : 0
  return {
    x: isLeft ? -offset : item.width + offset,
    y: item.height / 2,
    radius: 8,
    fill: isSelected ? 'rgba(75, 120, 255, 0.12)' : 'transparent',
    stroke: isSelected ? 'rgba(75, 120, 255, 0.45)' : 'transparent',
    opacity: isSelected ? 1 : 0,
    hitStrokeWidth: 20,
    onMouseDown: (event) => {
      event.cancelBubble = true
      emit('item-handle-pointerdown', { item, handle, event })
    }
  }
}

const resolveItemGradient = (itemType) => {
  if (itemType === 'text') return [0, '#ffffff', 1, '#f8fafc']
  if (itemType === 'image') return [0, '#ffffff', 1, '#f4f8ff']
  if (itemType === 'video') return [0, '#ffffff', 1, '#f8f6ff']
  return [0, '#ffffff', 1, '#f8fafc']
}

const fallbackTitle = (itemType) => itemType === 'text' ? '文本节点' : itemType === 'image' ? '图片节点' : '视频节点'
const pickItemStroke = (itemType) => itemType === 'image' ? 'rgba(75, 120, 255, 0.18)' : itemType === 'video' ? 'rgba(114, 90, 255, 0.16)' : 'rgba(34, 57, 98, 0.12)'

const resolveHandlePoint = (item, handle, role) => {
  const centerY = item.position_y + item.height / 2
  const isSelected = props.selectedItemIds.includes(item.id)
  const offset = isSelected ? 32 : 0
  const leftX = item.position_x - offset
  const rightX = item.position_x + item.width + offset
  if (handle === 'left') return { x: leftX, y: centerY }
  if (handle === 'right') return { x: rightX, y: centerY }
  return role === 'target' ? { x: leftX, y: centerY } : { x: rightX, y: centerY }
}

const handleWheel = (event) => {
  event.evt.preventDefault()
  const stage = stageRef.value?.getNode()
  if (!stage) {
    return
  }
  const scaleBy = 1.06
  const oldScale = stage.scaleX()
  const pointer = stage.getPointerPosition()
  if (!pointer) {
    return
  }

  const mousePointTo = {
    x: (pointer.x - stage.x()) / oldScale,
    y: (pointer.y - stage.y()) / oldScale
  }

  const nextScale = event.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy
  const clampedScale = Math.min(Math.max(nextScale, 0.25), 2.8)
  stageScale.value = clampedScale
  stagePosition.value = {
    x: pointer.x - mousePointTo.x * clampedScale,
    y: pointer.y - mousePointTo.y * clampedScale
  }
  emitViewportChange()
}

const toCanvasPoint = (pointer) => ({
  x: (pointer.x - stagePosition.value.x) / Number(stageScale.value || 1),
  y: (pointer.y - stagePosition.value.y) / Number(stageScale.value || 1)
})

const resolveMarqueeBounds = (selection) => ({
  left: Math.min(selection.startX, selection.currentX),
  right: Math.max(selection.startX, selection.currentX),
  top: Math.min(selection.startY, selection.currentY),
  bottom: Math.max(selection.startY, selection.currentY)
})

const handlePointerDown = (event) => {
  const target = event.target
  const stage = stageRef.value?.getNode()
  const nativeEvent = event?.evt
  if (!stage) {
    return
  }

  if (target === stage && nativeEvent?.shiftKey) {
    nativeEvent?.preventDefault?.()
    const pointer = stage.getPointerPosition()
    if (!pointer) {
      return
    }
    const canvasPoint = toCanvasPoint(pointer)
    marqueeSelection.value = {
      startX: canvasPoint.x,
      startY: canvasPoint.y,
      currentX: canvasPoint.x,
      currentY: canvasPoint.y,
      appendToSelection: Boolean(nativeEvent.metaKey || nativeEvent.ctrlKey)
    }
    suppressStageClick.value = true
    stage.draggable(false)
    return
  }

  if (target === stage) {
    nativeEvent?.preventDefault?.()
    return
  }

  nativeEvent?.preventDefault?.()
  stage.draggable(false)
  requestAnimationFrame(() => {
    stage.draggable(true)
  })
}

const handlePointerMove = () => {
  const stage = stageRef.value?.getNode()
  if (!stage || !marqueeSelection.value) {
    return
  }
  const pointer = stage.getPointerPosition()
  if (!pointer) {
    return
  }
  const canvasPoint = toCanvasPoint(pointer)
  marqueeSelection.value = { ...marqueeSelection.value, currentX: canvasPoint.x, currentY: canvasPoint.y }
}

const handlePointerUp = () => {
  const stage = stageRef.value?.getNode()
  if (!stage || !marqueeSelection.value) {
    return
  }
  emit('selection-box-end', {
    bounds: resolveMarqueeBounds(marqueeSelection.value),
    appendToSelection: marqueeSelection.value.appendToSelection
  })
  marqueeSelection.value = null
  stage.draggable(true)
  window.setTimeout(() => {
    suppressStageClick.value = false
  }, 0)
}

const handleStageClick = (event) => {
  const stage = stageRef.value?.getNode()
  if (!stage || event.target !== stage || suppressStageClick.value) {
    return
  }
  emit('stage-click')
}

const handleStageDragMove = (event) => {
  const stage = stageRef.value?.getNode()
  if (!stage || event.target !== stage) {
    return
  }
  stagePosition.value = { x: stage.x(), y: stage.y() }
  emitViewportChange()
}

const handleItemDragEnd = (item, event) => {
  const position = event.target.position()
  emit('item-drag-end', { id: item.id, positionX: position.x, positionY: position.y })
}

const marqueeOverlayStyle = computed(() => {
  if (!marqueeSelection.value) {
    return null
  }
  const bounds = resolveMarqueeBounds(marqueeSelection.value)
  return {
    width: `${Math.max((bounds.right - bounds.left) * stageScale.value, 0)}px`,
    height: `${Math.max((bounds.bottom - bounds.top) * stageScale.value, 0)}px`,
    transform: `translate(${bounds.left * stageScale.value + stagePosition.value.x}px, ${bounds.top * stageScale.value + stagePosition.value.y}px)`
  }
})

const maybeEmitResizeSuggestion = (itemId, nextWidth, nextHeight) => {
  const item = props.items.find((entry) => entry.id === itemId)
  if (!item) {
    return
  }
  const width = Math.round(Number(nextWidth || 0))
  const height = Math.round(Number(nextHeight || 0))
  if (!width || !height) {
    return
  }
  if (Math.abs(Number(item.width || 0) - width) < 2 && Math.abs(Number(item.height || 0) - height) < 2) {
    return
  }
  emit('item-resize-suggest', { id: itemId, width, height })
}

const syncLoadedImages = () => {
  const nextMap = { ...loadedImageMap.value }
  props.items.filter((item) => item?.item_type === 'image').forEach((item) => {
    const imageUrl = resolveCanvasStageMediaUrl(item)
    const currentEntry = nextMap[item.id]
    if (!imageUrl) {
      delete nextMap[item.id]
      return
    }
    if (currentEntry?.url === imageUrl && currentEntry?.image) {
      return
    }
    const img = new window.Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const resolvedSize = resolveCanvasImageNodeSize(item, img)
      loadedImageMap.value = { ...loadedImageMap.value, [item.id]: { url: imageUrl, image: img } }
      maybeEmitResizeSuggestion(item.id, resolvedSize.width, resolvedSize.height)
    }
    img.onerror = () => {
      loadedImageMap.value = { ...loadedImageMap.value, [item.id]: { url: imageUrl, image: null } }
    }
    img.src = imageUrl
  })
  loadedImageMap.value = nextMap
}

const releaseLoadedVideoEntryById = (itemId, nextMap = loadedVideoMap.value) => {
  releaseCanvasStageVideoEntry(nextMap[itemId])
}

const syncLoadedVideos = () => {
  const nextMap = { ...loadedVideoMap.value }
  resolveStageVideoPreviewTargets({
    items: props.items,
    editingItemId: props.editingItemId
  }).forEach((item) => {
    const previewUrl = resolveCanvasStageMediaUrl(item)
    const currentEntry = nextMap[item.id]
    if (!previewUrl) {
      releaseLoadedVideoEntryById(item.id, nextMap)
      delete nextMap[item.id]
      return
    }
    if (currentEntry?.url === previewUrl && currentEntry?.video) {
      return
    }
    const video = document.createElement('video')
    video.crossOrigin = 'anonymous'
    video.muted = true
    video.playsInline = true
    video.preload = 'auto'
    let resolved = false
    const commitVideoFrame = () => {
      if (resolved) {
        return
      }
      resolved = true
      const resolvedSize = resolveCanvasVideoNodeSize(item, video)
      loadedVideoMap.value = { ...loadedVideoMap.value, [item.id]: { url: previewUrl, video } }
      maybeEmitResizeSuggestion(item.id, resolvedSize.width, resolvedSize.height)
      stageRef.value?.getNode()?.batchDraw?.()
    }
    video.onloadeddata = () => {
      if (video.readyState >= 2) {
        commitVideoFrame()
      }
    }
    video.onseeked = () => commitVideoFrame()
    video.onerror = () => {
      loadedVideoMap.value = { ...loadedVideoMap.value, [item.id]: { url: previewUrl, video: null } }
    }
    video.onloadedmetadata = () => {
      const duration = Number(video.duration || 0)
      if (!duration || duration <= 0.05) {
        commitVideoFrame()
        return
      }
      try {
        video.currentTime = Math.min(duration / 2, 0.05)
      } catch {
        commitVideoFrame()
      }
    }
    video.src = previewUrl
    video.load()
  })
  loadedVideoMap.value = nextMap
}

onMounted(() => {
  updateStageSize()
  syncLoadedImages()
  syncLoadedVideos()

  if (containerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => updateStageSize())
    resizeObserver.observe(containerRef.value)
  } else {
    window.addEventListener('resize', updateStageSize)
  }
  emitViewportChange()
})

onBeforeUnmount(() => {
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
    resizeObserver.disconnect()
    resizeObserver = null
  } else {
    window.removeEventListener('resize', updateStageSize)
  }
  Object.keys(loadedVideoMap.value).forEach((itemId) => releaseLoadedVideoEntryById(itemId))
  loadedVideoMap.value = {}
})

watch(
  () => props.items,
  () => {
    syncLoadedImages()
    syncLoadedVideos()
  },
  { deep: true }
)
</script>

<style scoped>
.konva-stage-shell {
  position: relative;
  width: 100%;
  height: 100%;
}

.konva-stage {
  width: 100%;
  height: 100%;
}

.stage-text-overlay {
  position: absolute;
  left: 0;
  top: 0;
  padding: 16px 18px;
  box-sizing: border-box;
  pointer-events: none;
  overflow: hidden;
  color: #1f2a44;
}

.stage-text-overlay__title {
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.2;
  font-weight: 700;
  color: #1f2a44;
}

.stage-text-overlay__body {
  max-height: calc(100% - 28px);
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.6;
  color: #52607a;
}

.canvas-rich-text-content :deep(h1),
.canvas-rich-text-content :deep(h2),
.canvas-rich-text-content :deep(h3) {
  margin: 0 0 10px;
  line-height: 1.28;
  color: #1f2a44;
  letter-spacing: -0.01em;
}

.canvas-rich-text-content :deep(h1) {
  font-size: 18px;
}

.canvas-rich-text-content :deep(h2) {
  font-size: 16px;
}

.canvas-rich-text-content :deep(h3) {
  font-size: 14px;
}

.canvas-rich-text-content :deep(p),
.canvas-rich-text-content :deep(ul),
.canvas-rich-text-content :deep(ol),
.canvas-rich-text-content :deep(blockquote),
.canvas-rich-text-content :deep(pre) {
  margin: 0 0 8px;
}

.canvas-rich-text-content :deep(ul),
.canvas-rich-text-content :deep(ol) {
  padding-left: 18px;
}

.canvas-rich-text-content :deep(li) {
  margin-bottom: 4px;
}

.canvas-rich-text-content :deep(blockquote) {
  padding-left: 10px;
  border-left: 3px solid rgba(75, 120, 255, 0.24);
  color: #42526b;
}

.canvas-rich-text-content :deep(pre) {
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(17, 24, 39, 0.05);
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
}

.canvas-rich-text-content :deep(code) {
  padding: 0 4px;
  border-radius: 6px;
  background: rgba(17, 24, 39, 0.08);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.94em;
}

.canvas-rich-text-content :deep(a) {
  color: #355ce0;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.konva-stage-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667085;
  font-size: 14px;
}

.stage-generating-overlay {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  border-radius: 20px;
  overflow: hidden;
  z-index: 3;
  transform-origin: top left;
}

.stage-status-chip {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  z-index: 4;
  transform-origin: top left;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 24px rgba(34, 57, 98, 0.12);
}

.stage-status-chip__label {
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.stage-status-chip--info {
  background: rgba(238, 244, 255, 0.94);
  border-color: rgba(75, 120, 255, 0.2);
}

.stage-status-chip--info .stage-status-chip__label {
  color: #355ce0;
}

.stage-status-chip--pending,
.stage-status-chip--warning {
  background: rgba(255, 248, 235, 0.94);
  border-color: rgba(245, 158, 11, 0.22);
}

.stage-status-chip--pending .stage-status-chip__label,
.stage-status-chip--warning .stage-status-chip__label {
  color: #b7791f;
}

.stage-status-chip--success {
  background: rgba(238, 249, 242, 0.94);
  border-color: rgba(34, 197, 94, 0.18);
}

.stage-status-chip--success .stage-status-chip__label {
  color: #15803d;
}

.stage-status-chip--error {
  background: rgba(254, 242, 242, 0.94);
  border-color: rgba(239, 68, 68, 0.18);
}

.stage-status-chip--error .stage-status-chip__label {
  color: #dc2626;
}

.stage-selection-overlay {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  border: 1px solid rgba(75, 120, 255, 0.75);
  background: rgba(75, 120, 255, 0.12);
  box-shadow: inset 0 0 0 1px rgba(75, 120, 255, 0.18);
  z-index: 4;
  transform-origin: top left;
}
</style>
