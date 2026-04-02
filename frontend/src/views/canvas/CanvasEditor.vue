<template>
  <section class="canvas-editor-page" v-loading="loading">
    <div ref="stageShellRef" class="canvas-stage-shell">
      <KonvaCanvasStage
        :items="items"
        :connections="connections"
        :selected-item-ids="selectedItemIds"
        :selected-connection-ids="selectedConnectionIds"
        :editing-item-id="selectedItem?.id || ''"
        @connection-click="handleConnectionClick"
        @item-click="handleItemClick"
        @item-drag-end="handleItemDragEnd"
        @item-handle-pointerdown="handleStageHandlePointerDown"
        @stage-click="handleStageClick"
        @viewport-change="handleViewportChange"
        @selection-box-end="handleSelectionBoxEnd"
      />

      <CanvasLinkDragOverlay :path="dragPath" />
      <CanvasConnectionActions
        :visible="Boolean(selectedConnection && connectionActionPosition)"
        :position="connectionActionPosition"
        @delete="handleRemoveSelectedConnection"
      />
      <CanvasLinkCreateMenu
        :visible="linkMenu.visible"
        :screen-x="linkMenu.screenX"
        :screen-y="linkMenu.screenY"
        :options="createOptions"
        @select="handleCreateLinkedNode"
      />

      <CanvasWorkbenchLayout
        :title="document?.title || 'Canvas'"
        :save-label="saving ? '保存中...' : dirty ? '保存变更' : '已保存'"
        :zoom-hint-text="zoomHintText"
        :link-mode-text="linkModeText"
        @back="router.push('/canvas')"
        @save="handleSave"
        @create-item="createNode"
      />

      <CanvasTextStudio
        v-if="selectedItem?.item_type === 'text'"
        :item="selectedItem"
        :style="selectedItemStyle"
        :draft="textStudioDraft"
        :available-reference-items="availableReferenceItems"
        :global-reference-items="globalReferenceItems"
        :generating="Boolean(generationLoadingByItem[selectedItem.id])"
        :api-key-options="apiKeyOptions"
        :model-options="textModelOptions"
        :model-options-loading="catalogLoading"
        @focus-item="setSelection"
        @handle-drag="handleStudioHandleDrag"
        @update:title="patchSelected({ title: $event })"
        @update:text="patchSelectedContent({ text: $event })"
        @update:api-key-id="patchGenerationConfig({ api_key_id: $event })"
        @update:model-id="patchGenerationConfig({ model: $event })"
        @update:tokens="updatePromptTokens($event)"
        @submit-generation="handleGenerate"
        @delete="removeSelectedItem"
      />

      <CanvasImageStudio
        v-if="selectedItem?.item_type === 'image'"
        :style="selectedItemStyle"
        :draft="imageStudioDraft"
        :available-reference-items="availableReferenceItems"
        :global-reference-items="globalReferenceItems"
        :generating="Boolean(generationLoadingByItem[selectedItem.id])"
        :uploading="uploading"
        :api-key-options="apiKeyOptions"
        :model-options="imageModelOptions"
        :model-options-loading="catalogLoading"
        @focus-item="setSelection"
        @handle-drag="handleStudioHandleDrag"
        @update:title="patchSelected({ title: $event })"
        @update:api-key-id="patchGenerationConfig({ api_key_id: $event })"
        @update:model-id="patchGenerationConfig({ model: $event })"
        @update:tokens="updatePromptTokens($event)"
        @generate="handleGenerate"
        @history="refreshHistory"
        @upload="uploadMedia($event, 'image')"
        @delete="removeSelectedItem"
      />

      <CanvasVideoStudio
        v-if="selectedItem?.item_type === 'video'"
        :style="selectedItemStyle"
        :draft="videoStudioDraft"
        :available-reference-items="availableReferenceItems"
        :global-reference-items="globalReferenceItems"
        :reference-hint-text="videoReferenceHint"
        :generating="Boolean(generationLoadingByItem[selectedItem.id])"
        :uploading="uploading"
        :api-key-options="apiKeyOptions"
        :model-options="videoModelOptions"
        :model-options-loading="catalogLoading"
        @focus-item="setSelection"
        @handle-drag="handleStudioHandleDrag"
        @update:title="patchSelected({ title: $event })"
        @update:api-key-id="patchGenerationConfig({ api_key_id: $event })"
        @update:model-id="patchGenerationConfig({ model: $event })"
        @update:tokens="updatePromptTokens($event)"
        @generate="handleGenerate"
        @history="refreshHistory"
        @upload="uploadMedia($event, 'video')"
        @delete="removeSelectedItem"
      />
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import CanvasConnectionActions from '@/components/canvas/CanvasConnectionActions.vue'
import CanvasImageStudio from '@/components/canvas/CanvasImageStudio.vue'
import CanvasLinkCreateMenu from '@/components/canvas/CanvasLinkCreateMenu.vue'
import CanvasLinkDragOverlay from '@/components/canvas/CanvasLinkDragOverlay.vue'
import CanvasTextStudio from '@/components/canvas/CanvasTextStudio.vue'
import CanvasVideoStudio from '@/components/canvas/CanvasVideoStudio.vue'
import CanvasWorkbenchLayout from '@/components/canvas/CanvasWorkbenchLayout.vue'
import KonvaCanvasStage from '@/components/canvas/KonvaCanvasStage.vue'
import { useCanvasEditor } from '@/composables/useCanvasEditor'
import { useCanvasGeneration } from '@/composables/useCanvasGeneration'
import { apiKeysService } from '@/services/apiKeys'
import { canvasService } from '@/services/canvas'
import { fileService } from '@/services/upload'
import { buildPromptDerivatives } from '@/utils/promptMentionTokens'

const route = useRoute()
const router = useRouter()
const stageShellRef = ref(null)
const uploading = ref(false)
const catalogLoading = ref(false)
const apiKeyOptions = ref([])
const modelCatalog = ref({
  text: [],
  image: [],
  video: []
})

const {
  loading,
  saving,
  document,
  items,
  connections,
  selectedItemId,
  selectedItem,
  zoom,
  pan,
  dirty,
  loadDocument,
  save,
  createItem,
  updateItem,
  removeItem,
  setSelection,
  clearSelection,
  startConnection,
  completeConnection,
  removeConnection,
  updateViewport
} = useCanvasEditor()

const {
  generationLoadingByItem,
  generationHistories,
  historyLoadingByItem,
  loadHistory,
  generate,
  applyGeneration
} = useCanvasGeneration(updateItem)

const viewport = reactive({ width: 0, height: 0 })
const selectedConnectionId = ref(null)
const linkDrag = ref(null)
const linkMenu = reactive({
  visible: false,
  screenX: 0,
  screenY: 0,
  canvasX: 0,
  canvasY: 0,
  sourceItemId: '',
  sourceHandle: 'right'
})

const createOptions = [
  { type: 'text', label: '文本节点', description: '创建文本节点并自动连接' },
  { type: 'image', label: '图片节点', description: '创建图片节点并自动连接' },
  { type: 'video', label: '视频节点', description: '创建视频节点并自动连接' }
]

const selectedItemIds = computed(() => (selectedItem.value ? [selectedItem.value.id] : []))
const selectedConnectionIds = computed(() => (selectedConnectionId.value ? [selectedConnectionId.value] : []))
const selectedConnection = computed(() =>
  connections.value.find((connection) => connection.id === selectedConnectionId.value) || null
)

const selectedItemStyle = computed(() => {
  if (!selectedItem.value) {
    return null
  }
  return {
    position: 'absolute',
    left: '0',
    top: '0',
    width: `${selectedItem.value.width * zoom.value}px`,
    height: `${selectedItem.value.height * zoom.value}px`,
    transform: `translate(${selectedItem.value.position_x * zoom.value + pan.value.x}px, ${selectedItem.value.position_y * zoom.value + pan.value.y}px)`,
    transformOrigin: 'top left'
  }
})

const normalizePromptTokens = (tokens = []) => {
  const nextTokens = Array.isArray(tokens) ? tokens : []
  const { promptPlainText } = buildPromptDerivatives(nextTokens)
  return {
    promptTokens: nextTokens,
    prompt: promptPlainText,
    promptPlainText
  }
}

const resolveInitialPromptTokens = (item) => {
  const existingTokens = item?.content?.promptTokens
  if (Array.isArray(existingTokens) && existingTokens.length) {
    return existingTokens
  }
  const prompt = String(item?.content?.prompt || '')
  return prompt ? [{ type: 'text', text: prompt }] : []
}

const textStudioDraft = computed(() => {
  if (!selectedItem.value) return {}
  return {
    title: selectedItem.value.title || '',
    text: selectedItem.value.content?.text || '',
    apiKeyId: selectedItem.value.generation_config?.api_key_id || '',
    model: selectedItem.value.generation_config?.model || '',
    ...normalizePromptTokens(resolveInitialPromptTokens(selectedItem.value))
  }
})

const imageStudioDraft = computed(() => {
  if (!selectedItem.value) return {}
  return {
    title: selectedItem.value.title || '',
    resultImageUrl: selectedItem.value.content?.result_image_url || '',
    referenceImageUrl: selectedItem.value.content?.reference_image_url || '',
    apiKeyId: selectedItem.value.generation_config?.api_key_id || '',
    model: selectedItem.value.generation_config?.model || '',
    ...normalizePromptTokens(resolveInitialPromptTokens(selectedItem.value))
  }
})

const videoStudioDraft = computed(() => {
  if (!selectedItem.value) return {}
  return {
    title: selectedItem.value.title || '',
    resultVideoUrl: selectedItem.value.content?.result_video_url || '',
    apiKeyId: selectedItem.value.generation_config?.api_key_id || '',
    model: selectedItem.value.generation_config?.model || '',
    ...normalizePromptTokens(resolveInitialPromptTokens(selectedItem.value))
  }
})

const textModelOptions = computed(() => modelCatalog.value.text || [])
const imageModelOptions = computed(() => modelCatalog.value.image || [])
const videoModelOptions = computed(() => modelCatalog.value.video || [])

const reverseConnectionMap = computed(() => {
  const map = new Map()
  connections.value.forEach((connection) => {
    const list = map.get(connection.target_item_id) || []
    list.push(connection.source_item_id)
    map.set(connection.target_item_id, list)
  })
  return map
})

const buildReferenceItem = (item) => ({
  ...item,
  previewUrl: item.item_type === 'image' ? (item.content?.result_image_url || item.content?.reference_image_url || '') : '',
  previewText: item.item_type === 'text' ? String(item.content?.text || '') : ''
})

const hydrateCanvasConfigCatalog = async () => {
  catalogLoading.value = true
  try {
    const [apiKeysResponse, modelCatalogResponse] = await Promise.all([
      apiKeysService.getAPIKeys({ page: 1, size: 100, key_status: 'active' }),
      canvasService.getModelCatalog()
    ])

    apiKeyOptions.value = (apiKeysResponse?.api_keys || []).map((key) => ({
      value: key.id,
      label: `${key.name} (${key.provider})`
    }))

    modelCatalog.value = {
      text: Array.isArray(modelCatalogResponse?.text) ? modelCatalogResponse.text : [],
      image: Array.isArray(modelCatalogResponse?.image) ? modelCatalogResponse.image : [],
      video: Array.isArray(modelCatalogResponse?.video) ? modelCatalogResponse.video : []
    }
  } catch (error) {
    console.error('Load canvas config catalog failed', error)
    apiKeyOptions.value = []
    modelCatalog.value = { text: [], image: [], video: [] }
    ElMessage.warning('加载画布模型目录失败')
  } finally {
    catalogLoading.value = false
  }
}

const buildItemMap = (itemsList = []) =>
  itemsList.reduce((accumulator, item) => {
    accumulator[item.id] = item
    return accumulator
  }, {})

const resolvePromptMentions = (tokens = [], itemMap = {}) =>
  tokens
    .filter((token) => token.type === 'mention')
    .map((token) => {
      const item = itemMap[token.nodeId]
      if (!item) {
        return {
          mentionId: token.mentionId,
          nodeId: token.nodeId,
          nodeType: token.nodeType,
          nodeTitle: token.nodeTitleSnapshot || '',
          resolvedContent: null,
          status: 'missing'
        }
      }

      if (token.nodeType === 'text' && item.item_type === 'text') {
        const text = String(item.content?.text || item.content?.text_preview || '')
        return {
          mentionId: token.mentionId,
          nodeId: token.nodeId,
          nodeType: token.nodeType,
          nodeTitle: item.title || token.nodeTitleSnapshot || '',
          resolvedContent: {
            text,
            length: text.length
          },
          status: text ? 'resolved' : 'missing'
        }
      }

      if (token.nodeType === 'image' && item.item_type === 'image') {
        const objectKey = String(
          item.content?.result_image_object_key ||
          item.content?.reference_image_object_key ||
          item.content?.result_image_key ||
          item.content?.object_key ||
          item.content?.objectKey ||
          item.content?.result_image_url ||
          item.content?.reference_image_url ||
          ''
        )
        const previewUrl = String(
          item.content?.result_image_url ||
          item.content?.reference_image_url ||
          ''
        )
        return {
          mentionId: token.mentionId,
          nodeId: token.nodeId,
          nodeType: token.nodeType,
          nodeTitle: item.title || token.nodeTitleSnapshot || '',
          resolvedContent: {
            object_key: objectKey,
            objectKey,
            url: previewUrl,
            width: Number(item.width || 0),
            height: Number(item.height || 0)
          },
          status: objectKey || previewUrl ? 'resolved' : 'missing'
        }
      }

      return {
        mentionId: token.mentionId,
        nodeId: token.nodeId,
        nodeType: token.nodeType,
        nodeTitle: item.title || token.nodeTitleSnapshot || '',
        resolvedContent: null,
        status: 'invalid_type'
      }
    })

const availableReferenceItems = computed(() => {
  if (!selectedItem.value) return []
  const visited = new Set()
  const queue = [...(reverseConnectionMap.value.get(selectedItem.value.id) || [])]
  const references = []
  while (queue.length) {
    const currentId = queue.shift()
    if (!currentId || visited.has(currentId)) continue
    visited.add(currentId)
    const item = items.value.find((entry) => entry.id === currentId)
    if (item && ['text', 'image'].includes(item.item_type)) {
      references.push(buildReferenceItem(item))
    }
    ;(reverseConnectionMap.value.get(currentId) || []).forEach((upstreamId) => {
      if (!visited.has(upstreamId)) {
        queue.push(upstreamId)
      }
    })
  }
  return references
})

const globalReferenceItems = computed(() =>
  items.value
    .filter((item) => item.id !== selectedItem.value?.id && ['text', 'image'].includes(item.item_type))
    .map(buildReferenceItem)
)

const videoReferenceHint = computed(() => {
  if (!selectedItem.value || selectedItem.value.item_type !== 'video') return ''
  const imageCount = availableReferenceItems.value.filter((item) => item.item_type === 'image').length
  const textCount = availableReferenceItems.value.filter((item) => item.item_type === 'text').length
  return `上游可引用 ${imageCount} 个图片节点，${textCount} 个文本节点。视频生成会自动带上上游图片 URL。`
})

const zoomHintText = computed(() => `缩放 ${Math.round(zoom.value * 100)}%，拖动画布平移，按住 Shift 拖拽框选节点。`)
const linkModeText = computed(() => {
  if (!linkDrag.value) return ''
  return '拖到目标节点上完成连线，在线路空白处松开可直接创建下游节点。'
})

const connectionActionPosition = computed(() => {
  if (!selectedConnection.value) {
    return null
  }
  const source = items.value.find((item) => item.id === selectedConnection.value.source_item_id)
  const target = items.value.find((item) => item.id === selectedConnection.value.target_item_id)
  if (!source || !target) {
    return null
  }
  const sourceX = source.position_x + (selectedConnection.value.source_handle === 'left' ? 0 : source.width)
  const sourceY = source.position_y + source.height / 2
  const targetX = target.position_x + (selectedConnection.value.target_handle === 'right' ? target.width : 0)
  const targetY = target.position_y + target.height / 2
  return {
    x: ((sourceX + targetX) / 2) * zoom.value + pan.value.x,
    y: ((sourceY + targetY) / 2) * zoom.value + pan.value.y
  }
})

const dragPath = computed(() => {
  if (!linkDrag.value) return ''
  const startScreenX = linkDrag.value.startCanvasX * zoom.value + pan.value.x
  const startScreenY = linkDrag.value.startCanvasY * zoom.value + pan.value.y
  const endScreenX = linkDrag.value.currentScreenX
  const endScreenY = linkDrag.value.currentScreenY
  const delta = Math.max(80, Math.abs(endScreenX - startScreenX) / 2)
  return `M ${startScreenX} ${startScreenY} C ${startScreenX + delta} ${startScreenY}, ${endScreenX - delta} ${endScreenY}, ${endScreenX} ${endScreenY}`
})

const getCanvasPointFromMouse = (event) => {
  const rect = stageShellRef.value?.getBoundingClientRect()
  if (!rect) {
    return { screenX: 0, screenY: 0, canvasX: 0, canvasY: 0 }
  }
  const screenX = event.clientX - rect.left
  const screenY = event.clientY - rect.top
  return {
    screenX,
    screenY,
    canvasX: (screenX - pan.value.x) / zoom.value,
    canvasY: (screenY - pan.value.y) / zoom.value
  }
}

const resolveHandleCanvasPoint = (item, handle) => ({
  x: handle === 'left' ? item.position_x : item.position_x + item.width,
  y: item.position_y + item.height / 2
})

const findItemAtCanvasPoint = (canvasX, canvasY, ignoreItemId = '') =>
  [...items.value]
    .sort((a, b) => (b.z_index || 0) - (a.z_index || 0))
    .find((item) => {
      if (item.id === ignoreItemId) return false
      return canvasX >= item.position_x &&
        canvasX <= item.position_x + item.width &&
        canvasY >= item.position_y &&
        canvasY <= item.position_y + item.height
    }) || null

const closeLinkMenu = () => {
  linkMenu.visible = false
  linkMenu.screenX = 0
  linkMenu.screenY = 0
  linkMenu.canvasX = 0
  linkMenu.canvasY = 0
  linkMenu.sourceItemId = ''
  linkMenu.sourceHandle = 'right'
}

const startLinkDrag = (item, handle, event) => {
  const pointer = getCanvasPointFromMouse(event)
  const startPoint = resolveHandleCanvasPoint(item, handle)
  linkDrag.value = {
    sourceItemId: item.id,
    sourceHandle: handle,
    startCanvasX: startPoint.x,
    startCanvasY: startPoint.y,
    currentScreenX: pointer.screenX,
    currentScreenY: pointer.screenY,
    currentCanvasX: pointer.canvasX,
    currentCanvasY: pointer.canvasY
  }
  closeLinkMenu()
  window.addEventListener('mousemove', handleGlobalPointerMove)
  window.addEventListener('mouseup', handleGlobalPointerUp)
}

const handleGlobalPointerMove = (event) => {
  if (!linkDrag.value) return
  const point = getCanvasPointFromMouse(event)
  linkDrag.value = {
    ...linkDrag.value,
    currentScreenX: point.screenX,
    currentScreenY: point.screenY,
    currentCanvasX: point.canvasX,
    currentCanvasY: point.canvasY
  }
}

const handleGlobalPointerUp = async () => {
  if (!linkDrag.value) return
  const sourceItemId = linkDrag.value.sourceItemId
  const sourceHandle = linkDrag.value.sourceHandle
  const targetItem = findItemAtCanvasPoint(linkDrag.value.currentCanvasX, linkDrag.value.currentCanvasY, sourceItemId)
  try {
    if (targetItem) {
      const targetHandle = linkDrag.value.currentCanvasX < targetItem.position_x + targetItem.width / 2 ? 'left' : 'right'
      startConnection(sourceItemId, sourceHandle)
      await completeConnection(targetItem.id, targetHandle)
      setSelection(targetItem.id)
    } else {
      linkMenu.visible = true
      linkMenu.screenX = linkDrag.value.currentScreenX
      linkMenu.screenY = linkDrag.value.currentScreenY
      linkMenu.canvasX = linkDrag.value.currentCanvasX
      linkMenu.canvasY = linkDrag.value.currentCanvasY
      linkMenu.sourceItemId = sourceItemId
      linkMenu.sourceHandle = sourceHandle
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '创建连线失败')
  } finally {
    linkDrag.value = null
    window.removeEventListener('mousemove', handleGlobalPointerMove)
    window.removeEventListener('mouseup', handleGlobalPointerUp)
  }
}

const patchSelected = (patch) => {
  if (!selectedItem.value) return
  updateItem(selectedItem.value.id, patch)
}

const patchSelectedContent = (patch) => {
  if (!selectedItem.value) return
  updateItem(selectedItem.value.id, {
    content: {
      ...selectedItem.value.content,
      ...patch
    }
  })
}

const patchGenerationConfig = (patch) => {
  if (!selectedItem.value) return
  updateItem(selectedItem.value.id, {
    generation_config: {
      ...selectedItem.value.generation_config,
      ...patch
    }
  })
}

const updatePromptTokens = (tokens) => {
  if (!selectedItem.value) return
  patchSelectedContent(normalizePromptTokens(tokens))
}

const createNode = async (type) => {
  try {
    const item = await createItem(type)
    closeLinkMenu()
    if (item?.id) {
      setSelection(item.id)
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '创建节点失败')
  }
}

const handleCreateLinkedNode = async (type) => {
  try {
    const item = await createItem(type, {
      position_x: Math.max(40, linkMenu.canvasX),
      position_y: Math.max(40, linkMenu.canvasY)
    })
    if (!item?.id) {
      return
    }
    startConnection(linkMenu.sourceItemId, linkMenu.sourceHandle)
    await completeConnection(item.id, 'left')
    setSelection(item.id)
    closeLinkMenu()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '创建下游节点失败')
  }
}

const handleSave = async () => {
  await save()
  ElMessage.success('画布已保存')
}

const handleRemoveSelectedConnection = async () => {
  if (!selectedConnection.value) return
  try {
    await removeConnection(selectedConnection.value.id)
    selectedConnectionId.value = null
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '删除连线失败')
  }
}

const handleStageClick = () => {
  clearSelection()
  selectedConnectionId.value = null
  closeLinkMenu()
}

const handleItemClick = (item) => {
  setSelection(item.id)
  selectedConnectionId.value = null
  closeLinkMenu()
}

const handleConnectionClick = (connection) => {
  selectedConnectionId.value = connection.id
  clearSelection()
  closeLinkMenu()
}

const handleItemDragEnd = ({ id, positionX, positionY }) => {
  updateItem(id, { position_x: positionX, position_y: positionY })
}

const handleViewportChange = ({ x, y, scale, width, height }) => {
  updateViewport({ zoom: scale, pan: { x, y } })
  viewport.width = width
  viewport.height = height
}

const handleStageHandlePointerDown = ({ item, handle, event }) => {
  startLinkDrag(item, handle, event.evt)
}

const handleStudioHandleDrag = (event, handle) => {
  if (!selectedItem.value) return
  startLinkDrag(selectedItem.value, handle, event)
}

const handleSelectionBoxEnd = ({ bounds, appendToSelection }) => {
  const hitItem = items.value.find((item) =>
    item.position_x < bounds.right &&
    item.position_x + item.width > bounds.left &&
    item.position_y < bounds.bottom &&
    item.position_y + item.height > bounds.top
  )
  if (hitItem) {
    setSelection(hitItem.id)
    selectedConnectionId.value = null
  } else if (!appendToSelection) {
    clearSelection()
  }
}

const buildGenerationPayload = (item) => {
  const content = item.content || {}
  const promptTokens = content.promptTokens || []
  const { promptPlainText } = buildPromptDerivatives(promptTokens)
  const resolvedMentions = resolvePromptMentions(promptTokens, buildItemMap(items.value))
  const payload = {
    prompt: promptPlainText || content.prompt || '',
    prompt_plain_text: promptPlainText || content.prompt || '',
    prompt_tokens: promptTokens,
    resolved_mentions: resolvedMentions,
    model: item.generation_config?.model || undefined,
    api_key_id: item.generation_config?.api_key_id || undefined
  }

  if (item.item_type === 'video') {
    const upstreamImageUrls = resolvedMentions
      .filter((reference) => reference.nodeType === 'image' && reference.status === 'resolved')
      .map((reference) => reference.resolvedContent?.object_key || reference.resolvedContent?.url || '')
      .filter(Boolean)
    payload.options = { reference_image_urls: upstreamImageUrls }
    patchSelectedContent({
      reference_image_urls: upstreamImageUrls,
      reference_text_ids: resolvedMentions
        .filter((reference) => reference.nodeType === 'text' && reference.status === 'resolved')
        .map((reference) => reference.nodeId)
    })
  }

  return payload
}

const handleGenerate = async () => {
  if (!selectedItem.value) return
  try {
    if (dirty.value) {
      await save()
    }
    const response = await generate(selectedItem.value, buildGenerationPayload(selectedItem.value))
    ElMessage.success(response.message || '生成任务已提交')
    await loadHistory(selectedItem.value.id)
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成提交失败')
  }
}

const uploadMedia = async (file, type) => {
  if (!selectedItem.value || !file) return
  uploading.value = true
  try {
    if (type === 'image') {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fileService.uploadFile(formData)
      const fileUrl =
        response?.storage_info?.url ||
        response?.data?.url ||
        response?.storage_info?.object_key ||
        response?.data?.storage_key ||
        ''
      if (!fileUrl) {
        ElMessage.warning('上传成功，但没有拿到可预览地址')
        return
      }
      patchSelectedContent({
        reference_image_object_key: response?.storage_info?.object_key || response?.data?.storage_key || '',
        reference_image_url: fileUrl,
        result_image_url: selectedItem.value.content?.result_image_url || fileUrl
      })
    } else {
      const formDataForCanvas = new FormData()
      formDataForCanvas.append('file', file)
      const canvasResponse = await canvasService.uploadVideo(document.value.id, selectedItem.value.id, formDataForCanvas)
      updateItem(selectedItem.value.id, {
        content: canvasResponse.item.content,
        generation_config: canvasResponse.item.generation_config,
        last_run_status: canvasResponse.item.last_run_status,
        last_run_error: canvasResponse.item.last_run_error,
        last_output: canvasResponse.item.last_output
      })
    }
    ElMessage.success('文件已上传')
  } finally {
    uploading.value = false
  }
}

const refreshHistory = async () => {
  if (!selectedItem.value?.id) return
  await loadHistory(selectedItem.value.id)
}

const removeSelectedItem = async () => {
  if (!selectedItem.value) return
  try {
    await removeItem(selectedItem.value.id)
    selectedConnectionId.value = null
    closeLinkMenu()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '删除节点失败')
  }
}

const handleBeforeUnload = (event) => {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

watch(
  () => selectedItem.value?.id,
  async (itemId) => {
    if (itemId && selectedItem.value?.is_persisted) {
      selectedConnectionId.value = null
      await loadHistory(itemId)
    }
  },
  { immediate: true }
)

watch(
  () => route.params.canvasId,
  async (canvasId) => {
    if (canvasId) {
      await loadDocument(canvasId)
    }
  },
  { immediate: true }
)

onMounted(() => {
  void hydrateCanvasConfigCatalog()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.removeEventListener('mousemove', handleGlobalPointerMove)
  window.removeEventListener('mouseup', handleGlobalPointerUp)
})
</script>

<style scoped>
.canvas-editor-page {
  height: calc(100vh - 120px);
  min-height: 720px;
}

.canvas-stage-shell {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 28px;
  background:
    radial-gradient(circle at top, rgba(79, 117, 255, 0.14), transparent 30%),
    linear-gradient(180deg, #fbfcff 0%, #f4f7fb 100%);
  border: 1px solid rgba(26, 43, 77, 0.08);
  box-shadow: 0 18px 48px rgba(46, 82, 144, 0.1);
}

</style>
