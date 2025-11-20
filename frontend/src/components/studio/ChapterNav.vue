<template>
  <div class="chapter-nav">
    <div class="nav-header">
      <h3>章节列表</h3>
      <el-input
        v-model="searchQuery"
        placeholder="搜索章节..."
        :prefix-icon="Search"
        size="small"
        clearable
      />
    </div>

    <div v-if="loading" class="nav-loading">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="filteredChapters.length === 0" class="nav-empty">
      <el-empty description="暂无章节" :image-size="80" />
    </div>

    <div v-else class="nav-list">
      <div
        v-for="chapter in filteredChapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ 'is-selected': chapter.id === selectedId }"
        @click="$emit('select', chapter.id)"
      >
        <div class="chapter-number">{{ chapter.chapter_number }}</div>
        <div class="chapter-info">
          <div class="chapter-title">{{ chapter.title }}</div>
          <div class="chapter-meta">
            <span>{{ chapter.paragraph_count || 0 }} 段落</span>
            <span>{{ chapter.word_count || 0 }} 字</span>
          </div>
        </div>
        <div class="chapter-status">
          <el-tag
            v-if="chapter.is_confirmed"
            type="success"
            size="small"
            effect="plain"
          >
            已确认
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps({
  chapters: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select'])

const searchQuery = ref('')

const filteredChapters = computed(() => {
  if (!searchQuery.value) return props.chapters
  
  const query = searchQuery.value.toLowerCase()
  return props.chapters.filter(chapter =>
    chapter.title?.toLowerCase().includes(query) ||
    chapter.chapter_number?.toString().includes(query)
  )
})
</script>

<style scoped>
.chapter-nav {
  width: 280px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  overflow: hidden;
}

.nav-header {
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-primary);
}

.nav-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-sm) 0;
}

.nav-loading,
.nav-empty {
  padding: var(--space-lg);
}

.nav-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xs);
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-xs);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.chapter-item:hover {
  background: var(--bg-primary);
  border-color: var(--border-primary);
}

.chapter-item.is-selected {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.chapter-item.is-selected .chapter-title,
.chapter-item.is-selected .chapter-meta {
  color: white;
}

.chapter-number {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.chapter-item.is-selected .chapter-number {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.chapter-info {
  flex: 1;
  min-width: 0;
}

.chapter-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.chapter-meta {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  display: flex;
  gap: var(--space-sm);
}

.chapter-status {
  flex-shrink: 0;
}

/* 滚动条样式 */
.nav-list::-webkit-scrollbar {
  width: 6px;
}

.nav-list::-webkit-scrollbar-track {
  background: transparent;
}

.nav-list::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.nav-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-disabled);
}
</style>
