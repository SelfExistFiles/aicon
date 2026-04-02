<template>
  <div class="canvas-workbench-layout">
    <div class="canvas-topbar" :class="{ 'is-assistant-expanded': assistantExpanded }">
      <button class="brand-chip" type="button" @click="$emit('back')">
        <span class="brand-chip__title">{{ title }}</span>
      </button>
    </div>

    <aside class="left-toolbar-panel">
      <el-dropdown trigger="click" placement="right-start" popper-class="canvas-create-dropdown" @command="handleMenuCommand">
        <button class="toolbar-btn toolbar-btn--primary" type="button" :disabled="creatingItem">
          <el-icon><Plus /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <div class="canvas-dropdown-header">
              <el-icon class="header-icon"><Plus /></el-icon>
              <span>新建节点类型</span>
            </div>
            <el-dropdown-item command="text">
              <div class="canvas-dropdown-item">
                <div class="item-title">文本节点</div>
                <div class="item-desc">创建文本内容节点</div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="image">
              <div class="canvas-dropdown-item">
                <div class="item-title">图片节点</div>
                <div class="item-desc">创建图片内容节点</div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="video">
              <div class="canvas-dropdown-item">
                <div class="item-title">视频节点</div>
                <div class="item-desc">创建视频内容节点</div>
              </div>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <div class="toolbar-icons-group">
        <button class="toolbar-btn" type="button" :disabled="creatingItem" @click="$emit('create-item', 'text')">
          <el-icon><Document /></el-icon>
        </button>
        <button class="toolbar-btn" type="button" :disabled="creatingItem" @click="$emit('create-item', 'image')">
          <el-icon><Picture /></el-icon>
        </button>
        <button class="toolbar-btn" type="button" :disabled="creatingItem" @click="$emit('create-item', 'video')">
          <el-icon><VideoPlay /></el-icon>
        </button>
      </div>
    </aside>

    <aside class="assistant-rail">
      <div class="assistant-rail__surface">
        <slot />
      </div>
    </aside>

    <div v-if="showLauncher" class="canvas-launcher">
      <div class="launcher-chip">
        <el-icon><MagicStick /></el-icon>
        <span>从这里开始搭建你的画布</span>
      </div>

      <div class="launcher-actions">
        <button class="launcher-action" type="button" :disabled="creatingItem" @click="$emit('create-item', 'text')">
          文本节点
        </button>
        <button class="launcher-action" type="button" :disabled="creatingItem" @click="$emit('create-item', 'image')">
          图片节点
        </button>
        <button class="launcher-action" type="button" :disabled="creatingItem" @click="$emit('create-item', 'video')">
          视频节点
        </button>
      </div>
    </div>

    <div class="zoom-panel">
      <div class="zoom-panel__controls">
        <div class="zoom-chip">
          <el-icon><Operation /></el-icon>
          <span>{{ zoomText }}</span>
        </div>
      </div>
      <div class="zoom-hint">{{ zoomHintText }}</div>
    </div>

    <div v-if="linkModeText" class="link-mode-toast">
      {{ linkModeText }}
    </div>
  </div>
</template>

<script setup>
import { Document, MagicStick, Operation, Picture, Plus, VideoPlay } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, default: '' },
  zoomHintText: { type: String, default: '' },
  zoomText: { type: String, default: '画布提示' },
  linkModeText: { type: String, default: '' },
  creatingItem: { type: Boolean, default: false },
  assistantExpanded: { type: Boolean, default: true },
  showLauncher: { type: Boolean, default: false }
})

const emit = defineEmits(['back', 'create-item'])

const handleMenuCommand = (command) => {
  emit('create-item', command)
}
</script>

<style scoped>
.canvas-workbench-layout {
  position: absolute;
  inset: 0;
  --canvas-assistant-rail-width: min(420px, calc(100vw - 132px));
  pointer-events: none;
}

.canvas-topbar {
  position: absolute;
  top: 20px;
  left: 24px;
  right: 24px;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  transition: right 0.35s cubic-bezier(0.25, 1, 0.5, 1);
  pointer-events: none;
}

.canvas-topbar.is-assistant-expanded {
  right: calc(var(--canvas-assistant-rail-width) + 24px);
}

.brand-chip,
.toolbar-btn {
  border: none;
  pointer-events: auto;
}

.brand-chip,
.toolbar-btn {
  cursor: pointer;
}

.brand-chip {
  display: inline-flex;
  align-items: center;
  background: transparent;
  padding: 0;
}

.brand-chip__title {
  color: #1f2a44;
  font-size: 15px;
  font-weight: 600;
}

.assistant-rail {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 24;
  width: var(--canvas-assistant-rail-width);
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.assistant-rail__surface {
  width: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  pointer-events: auto;
}

.left-toolbar-panel {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 18;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 999px;
  padding: 10px 6px;
  gap: 16px;
  box-shadow: 0 14px 32px rgba(34, 57, 98, 0.1);
  pointer-events: auto;
}

.canvas-launcher {
  position: absolute;
  left: 50%;
  bottom: 96px;
  z-index: 16;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  pointer-events: none;
}

.launcher-chip,
.launcher-action,
.zoom-chip {
  pointer-events: auto;
}

.launcher-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(34, 57, 98, 0.08);
  color: #52607a;
  box-shadow: 0 12px 30px rgba(34, 57, 98, 0.08);
  font-size: 13px;
}

.launcher-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
}

.launcher-action {
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  background: rgba(255, 255, 255, 0.98);
  color: #1f2a44;
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.08);
}

.launcher-action:hover:not(:disabled) {
  background: #f8fbff;
  transform: translateY(-1px);
}

.toolbar-icons-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f6fb;
  color: #52607a;
}

.toolbar-btn:hover:not(:disabled) {
  background: #e7edf8;
  color: #1f2a44;
}

.toolbar-btn--primary {
  width: 44px;
  height: 44px;
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
}

.zoom-panel {
  position: absolute;
  left: 14px;
  bottom: 14px;
  z-index: 18;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.zoom-panel__controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.zoom-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(34, 57, 98, 0.08);
  color: #52607a;
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.08);
  font-size: 12px;
}

.zoom-hint {
  max-width: 340px;
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  color: #52607a;
  font-size: 12px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.08);
  pointer-events: auto;
}

.link-mode-toast {
  position: absolute;
  left: 50%;
  top: 92px;
  transform: translateX(-50%);
  z-index: 19;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(75, 120, 255, 0.18);
  color: #355ce0;
  box-shadow: 0 12px 24px rgba(75, 120, 255, 0.12);
  font-size: 12px;
  pointer-events: auto;
}

@media (max-width: 960px) {
  .canvas-topbar {
    left: 16px;
    right: 16px;
  }

  .left-toolbar-panel {
    left: 12px;
  }

  .canvas-launcher {
    left: 24px;
    right: 24px;
    bottom: 88px;
    transform: none;
  }

  .launcher-actions {
    width: 100%;
  }
}
</style>

<style>
.canvas-create-dropdown {
  background: rgba(255, 255, 255, 0.98) !important;
  border: 1px solid rgba(34, 57, 98, 0.08) !important;
  border-radius: 14px !important;
  padding: 8px !important;
  box-shadow: 0 18px 40px rgba(34, 57, 98, 0.12) !important;
}

.canvas-create-dropdown .el-dropdown-menu {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

.canvas-dropdown-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 14px;
  font-size: 13px;
  color: #667085;
  font-weight: 600;
  border-bottom: 1px solid rgba(34, 57, 98, 0.08);
  margin-bottom: 8px;
}

.canvas-dropdown-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
