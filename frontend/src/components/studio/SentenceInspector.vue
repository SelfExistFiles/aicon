<template>
  <div class="sentence-inspector">
    <div class="inspector-header">
      <h3>详情面板</h3>
    </div>

    <div v-if="!paragraph" class="inspector-empty">
      <el-empty description="请选择一个段落" :image-size="100" />
    </div>

    <div v-else class="inspector-content">
      <!-- 段落信息 -->
      <div class="info-section">
        <h4>段落信息</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">字数</span>
            <span class="value">{{ paragraph.word_count || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">句子数</span>
            <span class="value">{{ paragraph.sentence_count || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">状态</span>
            <el-tag :type="getActionType(paragraph.action)" size="small">
              {{ getActionText(paragraph.action) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 句子列表 (未来扩展) -->
      <div class="info-section">
        <h4>句子管理</h4>
        <div class="coming-soon">
          <el-icon :size="48" color="var(--text-disabled)">
            <InfoFilled />
          </el-icon>
          <p>句子管理功能即将上线</p>
          <p class="hint">将支持句子级别的编辑和音频生成</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { InfoFilled } from '@element-plus/icons-vue'

defineProps({
  paragraph: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const getActionType = (action) => {
  const map = {
    keep: 'success',
    edit: 'primary',
    delete: 'danger'
  }
  return map[action] || 'info'
}

const getActionText = (action) => {
  const map = {
    keep: '保留',
    edit: '编辑',
    delete: '删除'
  }
  return map[action] || '未知'
}
</script>

<style scoped>
.sentence-inspector {
  width: 320px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  overflow: hidden;
}

.inspector-header {
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-primary);
}

.inspector-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.inspector-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2xl);
}

.inspector-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-md);
}

.info-section {
  margin-bottom: var(--space-lg);
  padding: var(--space-md);
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
}

.info-section h4 {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-md) 0;
}

.info-grid {
  display: grid;
  gap: var(--space-sm);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.info-item .label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.info-item .value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.coming-soon {
  text-align: center;
  padding: var(--space-xl) var(--space-md);
  color: var(--text-secondary);
}

.coming-soon p {
  margin: var(--space-sm) 0;
  font-size: var(--text-sm);
}

.coming-soon .hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-style: italic;
}

/* 滚动条样式 */
.inspector-content::-webkit-scrollbar {
  width: 6px;
}

.inspector-content::-webkit-scrollbar-track {
  background: transparent;
}

.inspector-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.inspector-content::-webkit-scrollbar-thumb:hover {
  background: var(--text-disabled);
}
</style>
