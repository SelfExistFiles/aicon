<template>
  <div
    ref="rootRef"
    class="canvas-image-studio-context"
    :style="style"
    @mousedown.stop
    @click.stop
    @wheel.stop
    @pointerdown.capture="handleRootPointerDown"
    @focusin="handleRootFocusIn"
  >
    <div class="floating-header">
      <div class="image-label">
        <el-icon class="icon"><Picture /></el-icon>
        <span>图片节点</span>
      </div>
      <input :value="draft.title" class="header-title-input" placeholder="图片节点标题" @input="$emit('update:title', $event.target.value)" />
      <input ref="fileInputRef" class="image-upload-input" type="file" accept="image/*" @change="handleFileChange" />
      <button class="upload-btn" :disabled="uploading" @click="fileInputRef?.click()">
        <el-icon><Upload /></el-icon>
        <span>上传</span>
      </button>
    </div>

    <div class="image-preview-card">
      <img v-if="draft.resultImageUrl || draft.referenceImageUrl" :src="draft.resultImageUrl || draft.referenceImageUrl" class="preview-image" alt="canvas preview" />
      <div v-else class="empty-preview">输入提示词或上传参考图</div>
      <CanvasGeneratingOverlay :visible="generating" label="AI 正在生成图像" hint="预计 30 秒至 2 分钟" />
    </div>

    <div class="node-handle handle-left" @mousedown.prevent="$emit('handle-drag', $event, 'left')">
      <div class="plus-icon"><el-icon><Plus /></el-icon></div>
    </div>
    <div class="node-handle handle-right" @mousedown.prevent="$emit('handle-drag', $event, 'right')">
      <div class="plus-icon"><el-icon><Plus /></el-icon></div>
    </div>

    <div class="studio-docked-panel">
      <CanvasPromptMentionEditor
        ref="promptEditorRef"
        :tokens="draft.promptTokens"
        :available-reference-items="availableReferenceItems"
        :global-reference-items="globalReferenceItems"
        prompt-placeholder="输入 prompt，可用 @ 引用节点"
        reference-picker-title="引用节点"
        :disabled="generating || uploading"
        @focus-item="$emit('focus-item', $event)"
        @update:tokens="$emit('update:tokens', $event)"
      />

      <div class="panel-toolbar">
        <div class="toolbar-left">
          <el-select
            class="tool-select"
            :model-value="draft.apiKeyId"
            placeholder="选择 API Key"
            clearable
            filterable
            :disabled="generating || uploading"
            @change="$emit('update:api-key-id', $event || '')"
          >
            <el-option
              v-for="option in apiKeyOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-select
            class="tool-select"
            :model-value="draft.model"
            placeholder="选择模型"
            clearable
            filterable
            allow-create
            default-first-option
            :loading="modelOptionsLoading"
            :disabled="generating || uploading"
            @change="$emit('update:model-id', $event || '')"
          >
            <el-option
              v-for="option in modelOptions"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
        </div>
        <div class="toolbar-right">
          <button v-if="draft.resultImageUrl" class="history-action-btn" @click="$emit('history')">历史</button>
          <button class="generate-action-btn" :disabled="!canSubmitPrompt || generating || uploading" @click="handleGenerate">
            <el-icon v-if="generating" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><Top /></el-icon>
          </button>
        </div>
      </div>

      <button class="panel-delete-btn" @click="$emit('delete')">
        <el-icon><Delete /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Delete, Loading, Picture, Plus, Top, Upload } from '@element-plus/icons-vue'
import CanvasGeneratingOverlay from '@/components/canvas/CanvasGeneratingOverlay.vue'
import CanvasPromptMentionEditor from '@/components/canvas/CanvasPromptMentionEditor.vue'
import { useCanvasStudioCommitBoundary } from '@/composables/useCanvasStudioCommitBoundary'

const props = defineProps({
  style: { type: Object, default: null },
  draft: { type: Object, required: true },
  availableReferenceItems: { type: Array, default: () => [] },
  globalReferenceItems: { type: Array, default: () => [] },
  generating: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  apiKeyOptions: { type: Array, default: () => [] },
  modelOptions: { type: Array, default: () => [] },
  modelOptionsLoading: { type: Boolean, default: false }
})

const emit = defineEmits(['commit', 'delete', 'focus-item', 'generate', 'handle-drag', 'history', 'update:api-key-id', 'update:model-id', 'update:title', 'update:tokens', 'upload'])

const promptEditorRef = ref(null)
const rootRef = ref(null)
const fileInputRef = ref(null)
const canSubmitPrompt = computed(() => String(props.draft.promptPlainText || '').trim().length > 0)

const { handleRootPointerDown, handleRootFocusIn } = useCanvasStudioCommitBoundary(rootRef, () => {
  promptEditorRef.value?.flushTokens?.()
  emit('commit')
})

const handleGenerate = () => {
  promptEditorRef.value?.flushTokens?.()
  emit('generate')
}

const handleFileChange = (event) => {
  const [file] = event.target.files || []
  if (file) {
    emit('upload', file)
  }
  event.target.value = ''
}
</script>

<style scoped>
.canvas-image-studio-context,
.canvas-video-studio-context {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1000;
}

.floating-header,
.studio-docked-panel {
  pointer-events: auto;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 253, 0.98));
  border: 1px solid rgba(34, 57, 98, 0.1);
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 34px rgba(34, 57, 98, 0.12);
}

.floating-header {
  position: absolute;
  top: -48px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
  padding: 6px 16px;
  border-radius: 999px;
}

.image-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #667085;
  font-size: 13px;
}

.header-title-input {
  width: 140px;
  background: transparent;
  border: none;
  color: #1f2a44;
  font-size: 13px;
  font-weight: 600;
  outline: none;
}

.upload-btn,
.node-handle,
.studio-docked-panel,
.panel-delete-btn,
.image-preview-card {
  pointer-events: auto;
}

.image-upload-input { display: none; }

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 14px;
  background: #eef4ff;
  color: #355ce0;
}

.image-preview-card {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 30% 20%, rgba(75, 120, 255, 0.08), transparent 40%), #ffffff;
  backdrop-filter: blur(28px);
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.empty-preview {
  color: #98a2b3;
  font-size: 14px;
}

.node-handle {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.handle-left { left: -48px; }
.handle-right { right: -48px; }

.plus-icon {
  width: 28px;
  height: 28px;
  background: #fff;
  border: 1px solid rgba(75, 120, 255, 0.24);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #355ce0;
}

.studio-docked-panel {
  position: absolute;
  top: calc(100% + 22px);
  left: 50%;
  transform: translateX(-50%);
  width: min(620px, calc(100% + 120px));
  border-radius: 20px;
  padding: 14px 16px;
}

.panel-toolbar,
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-toolbar {
  margin-top: 14px;
  justify-content: space-between;
}

.tool-select {
  width: 170px;
}

.generate-action-btn,
.history-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 34px;
  padding: 0 14px;
  border-radius: 12px;
}

.generate-action-btn {
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
  font-weight: 700;
}

.history-action-btn {
  background: #eef4ff;
  color: #355ce0;
}

.panel-delete-btn {
  position: absolute;
  top: 10px;
  right: 12px;
  color: #98a2b3;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
