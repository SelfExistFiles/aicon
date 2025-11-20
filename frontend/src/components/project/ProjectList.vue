<template>
  <div class="project-list">
    <!-- 视图切换栏 -->
    <div class="view-header">
      <div class="header-right">
        <el-button-group>
          <el-button
            :type="viewMode === 'grid' ? 'primary' : 'default'"
            @click="viewMode = 'grid'"
            title="网格视图"
          >
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button
            :type="viewMode === 'list' ? 'primary' : 'default'"
            @click="viewMode = 'list'"
            title="列表视图"
          >
            <el-icon><List /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && projects.length === 0" class="empty-state">
      <el-empty :image-size="160">
        <template #image>
          <el-icon :size="120" class="empty-icon">
            <FolderOpened />
          </el-icon>
        </template>
        <template #description>
          <div class="empty-description">
            <h3>还没有项目</h3>
            <p>创建您的第一个项目，开始AI内容生成之旅</p>
            <p class="empty-hint">上传文本文件，系统将自动解析章节和段落</p>
          </div>
        </template>
        <template #default>
          <el-button type="primary" size="large" @click="$emit('create-project')">
            <el-icon><Plus /></el-icon>
            创建第一个项目
          </el-button>
        </template>
      </el-empty>
    </div>

    <!-- 网格视图 -->
    <ProjectGridView
      v-else-if="viewMode === 'grid'"
      :projects="projects"
      @view-project="$emit('view-project', $event)"
    />

    <!-- 列表视图 -->
    <ProjectTableView
      v-else
      :projects="projects"
      @view-project="$emit('view-project', $event)"
      @retry-project="$emit('retry-project', $event)"
      @edit-project="$emit('edit-project', $event)"
      @archive-project="$emit('archive-project', $event)"
      @row-click="$emit('row-click', $event)"
    />

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination-container">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Grid, List, FolderOpened, Plus } from '@element-plus/icons-vue'
import ProjectGridView from './ProjectGridView.vue'
import ProjectTableView from './ProjectTableView.vue'

// Props定义
defineProps({
  projects: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  total: {
    type: Number,
    default: 0,
  },
  currentPage: {
    type: Number,
    default: 1,
  },
  pageSize: {
    type: Number,
    default: 20,
  },
})

// Emits定义
const emit = defineEmits([
  'edit-project',
  'archive-project',
  'view-project',
  'retry-project',
  'page-change',
  'size-change',
  'row-click',
  'create-project',
])

// 响应式数据
const viewMode = ref('grid')

// 方法
const handleSizeChange = (size) => {
  emit('size-change', size)
}

const handlePageChange = (page) => {
  emit('page-change', page)
}

// 暴露给父组件的方法
defineExpose({
  getViewMode: () => viewMode.value,
})
</script>

<style scoped>
.project-list {
  width: 100%;
  padding: var(--space-md);
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: var(--space-lg);
  padding: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.loading-container {
  padding: var(--space-xl);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-primary);
}

.empty-state {
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-primary);
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon {
  color: var(--text-disabled);
  opacity: 0.5;
}

.empty-description h3 {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: var(--space-md) 0 var(--space-sm) 0;
}

.empty-description p {
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin: var(--space-xs) 0;
  line-height: 1.6;
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  font-style: italic;
}

:deep(.el-empty__bottom) {
  margin-top: var(--space-lg);
}

/* 分页样式优化 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl);
  padding: var(--space-xl) 0;
}

:deep(.el-pagination) {
  --el-pagination-button-bg-color: var(--bg-primary);
  --el-pagination-button-color: var(--text-primary);
  --el-pagination-hover-color: var(--primary-color);
  --el-pagination-bg-color: var(--bg-primary);
  --el-pagination-border-radius: var(--radius-lg);
  --el-pagination-font-size: var(--text-sm);
}

:deep(.el-pagination .el-pager li) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  margin: 0 2px;
}

:deep(.el-pagination .el-pager li:hover) {
  border-color: var(--primary-color);
}

:deep(.el-pagination .el-pager li.is-active) {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

/* 按钮组样式 */
:deep(.el-button-group) {
  border-radius: var(--radius-lg);
  overflow: hidden;
}

:deep(.el-button-group .el-button) {
  border-radius: 0;
  border-right: none;
}

:deep(.el-button-group .el-button:first-child) {
  border-top-left-radius: var(--radius-lg);
  border-bottom-left-radius: var(--radius-lg);
}

:deep(.el-button-group .el-button:last-child) {
  border-top-right-radius: var(--radius-lg);
  border-bottom-right-radius: var(--radius-lg);
  border-right: 1px solid var(--border-primary);
}

:deep(.el-button-group .el-button--primary) {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  border-color: var(--primary-color);
}

:deep(.el-button-group .el-button) {
  transition: all var(--transition-base);
}

:deep(.el-button-group .el-button:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .project-list {
    padding: var(--space-sm);
  }

  .view-header {
    justify-content: flex-end;
    padding: 0;
  }

  .loading-container,
  .empty-state {
    padding: var(--space-lg) var(--space-md);
  }

  .pagination-container {
    padding: var(--space-lg) 0;
    margin-top: var(--space-lg);
  }

  :deep(.el-button-group .el-button) {
    padding: var(--space-xs) var(--space-sm);
    font-size: var(--text-xs);
  }
}

@media (max-width: 480px) {
  .project-list {
    padding: var(--space-xs);
  }

  .loading-container,
  .empty-state {
    padding: var(--space-md);
  }
}
</style>