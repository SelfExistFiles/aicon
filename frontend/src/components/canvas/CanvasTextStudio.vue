<template>
  <div
    v-if="item && style"
    ref="rootRef"
    class="canvas-text-studio-context"
    :style="style"
    @mousedown.stop
    @click.stop
    @wheel.stop
    @pointerdown.capture="handleRootPointerDown"
    @focusin="handleRootFocusIn"
  >
    <div class="floating-header">
      <div class="text-label">
        <el-icon class="icon"><Document /></el-icon>
        <span>文本节点</span>
      </div>
      <input
        :value="draft.title"
        class="header-title-input"
        placeholder="文本节点标题"
        :disabled="generating"
        @input="$emit('update:title', $event.target.value)"
      />
    </div>

    <div class="node-handle handle-left" @mousedown.prevent="$emit('handle-drag', $event, 'left')">
      <div class="plus-icon"><el-icon><Plus /></el-icon></div>
    </div>
    <div class="node-handle handle-right" @mousedown.prevent="$emit('handle-drag', $event, 'right')">
      <div class="plus-icon"><el-icon><Plus /></el-icon></div>
    </div>

    <div class="editor-glass-card">
      <textarea
        :value="draft.text"
        class="rich-textarea"
        :placeholder="'输入正文内容...'"
        :disabled="generating"
        @input="$emit('update:text', $event.target.value)"
      ></textarea>
    </div>

    <div class="studio-docked-panel">
      <CanvasPromptMentionEditor
        ref="promptEditorRef"
        :tokens="draft.promptTokens"
        :available-reference-items="availableReferenceItems"
        :global-reference-items="globalReferenceItems"
        prompt-placeholder="输入 prompt，可用 @ 引用节点"
        reference-picker-title="引用节点"
        :disabled="generating"
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
            :disabled="generating"
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
            :disabled="generating || !draft.apiKeyId"
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
          <button class="generate-action-btn" :disabled="!canSubmitPrompt || generating" @click="handleSubmitGeneration">
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
import { Delete, Document, Loading, Plus, Top } from '@element-plus/icons-vue'
import CanvasPromptMentionEditor from '@/components/canvas/CanvasPromptMentionEditor.vue'
import { useCanvasStudioCommitBoundary } from '@/composables/useCanvasStudioCommitBoundary'

const props = defineProps({
  item: { type: Object, default: null },
  style: { type: Object, default: null },
  draft: { type: Object, required: true },
  availableReferenceItems: { type: Array, default: () => [] },
  globalReferenceItems: { type: Array, default: () => [] },
  generating: { type: Boolean, default: false },
  apiKeyOptions: { type: Array, default: () => [] },
  modelOptions: { type: Array, default: () => [] },
  modelOptionsLoading: { type: Boolean, default: false }
})

const emit = defineEmits(['delete', 'focus-item', 'handle-drag', 'submit-generation', 'update:api-key-id', 'update:model-id', 'update:text', 'update:title', 'update:tokens', 'commit'])

const promptEditorRef = ref(null)
const rootRef = ref(null)
const canSubmitPrompt = computed(() => String(props.draft.promptPlainText || '').trim().length > 0)

const { handleRootPointerDown, handleRootFocusIn } = useCanvasStudioCommitBoundary(rootRef, () => {
  promptEditorRef.value?.flushTokens?.()
  emit('commit')
})

const handleSubmitGeneration = () => {
  promptEditorRef.value?.flushTokens?.()
  emit('submit-generation')
}
</script>

<style scoped>
button {
  all: unset;
  box-sizing: border-box;
  cursor: pointer;
}

.canvas-text-studio-context {
  position: absolute;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
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

.text-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #667085;
  font-size: 13px;
}

.header-title-input {
  background: transparent;
  border: none;
  outline: none;
  color: #1f2a44;
  font-size: 13px;
  font-weight: 600;
  width: 140px;
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
  pointer-events: auto;
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

.editor-glass-card {
  position: absolute;
  inset: 0;
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 24px;
  backdrop-filter: blur(28px);
  padding: 24px 28px;
}

.rich-textarea {
  width: 100%;
  height: 100%;
  background: transparent;
  border: none;
  outline: none;
  color: #1f2a44;
  font-size: 16px;
  line-height: 1.7;
  resize: none;
}

.studio-docked-panel {
  position: absolute;
  top: calc(100% + 22px);
  left: 50%;
  transform: translateX(-50%);
  width: min(560px, calc(100% + 80px));
  border-radius: 20px;
  padding: 14px 16px;
  box-shadow: 0 12px 48px -8px rgba(0, 0, 0, 0.55);
}

.panel-toolbar,
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-toolbar {
  margin-top: 14px;
  justify-content: space-between;
}

.tool-select {
  width: 170px;
}

.generate-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  height: 32px;
  padding: 0 14px;
  border-radius: 10px;
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
  font-weight: 700;
}

.panel-delete-btn {
  position: absolute;
  top: 12px;
  right: 14px;
  color: #98a2b3;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
