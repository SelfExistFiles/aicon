<template>
  <div class="chapter-management">
    <!-- 头部操作栏 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="handleBack">
        返回项目
      </el-button>
      <h2 class="page-title">{{ project?.title || '项目' }} - 章节管理</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="handleCreateChapter">
          新建章节
        </el-button>
      </div>
    </div>

    <!-- 用户引导 -->
    <div v-if="showGuidance && chapters.length === 0 && !loading" class="guidance-section">
      <el-card class="guidance-card">
        <div class="guidance-content">
          <div class="guidance-icon">
            <el-icon size="48"><Document /></el-icon>
          </div>
          <div class="guidance-text">
            <h3>开始创建章节</h3>
            <p>章节是将长文本内容组织化管理的重要方式。通过章节管理，您可以：</p>
            <ul class="guidance-list">
              <li>📝 创建和编辑章节内容</li>
              <li>🔍 搜索和筛选章节</li>
              <li>✅ 确认章节锁定内容</li>
              <li>📊 查看章节统计信息</li>
            </ul>
            <el-button type="primary" size="large" :icon="Plus" @click="handleCreateChapter">
              创建第一个章节
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 快速操作栏 -->
    <div class="quick-actions">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索章节标题或内容"
            :prefix-icon="Search"
            clearable
            @input="handleSearch"
            size="large"
          />
        </el-col>
        <el-col :span="6">
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilter" size="large">
            <el-option label="全部状态" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="sortBy" placeholder="排序方式" @change="handleSort" size="large">
            <el-option label="章节序号" value="chapter_number" />
            <el-option label="创建时间" value="created_at" />
            <el-option label="更新时间" value="updated_at" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button :icon="Refresh" @click="handleRefresh" :loading="refreshing" size="large">
            刷新
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 统计概览 -->
    <div v-if="chapters.length > 0" class="stats-overview">
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-icon">
              <el-icon><Collection /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ pagination.total }}</div>
              <div class="stat-label">总章节数</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card confirmed">
            <div class="stat-icon">
              <el-icon><Check /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ confirmedCount }}</div>
              <div class="stat-label">已确认</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card processing">
            <div class="stat-icon">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ processingCount }}</div>
              <div class="stat-label">处理中</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card words">
            <div class="stat-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ formatNumber(totalWords) }}</div>
              <div class="stat-label">总字数</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 章节列表 -->
    <div class="chapters-container">
      <!-- 加载状态优化 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-content">
          <div class="loading-spinner"></div>
          <p class="loading-text">正在加载章节数据...</p>
        </div>
        <div class="skeleton-cards">
          <div v-for="i in 3" :key="i" class="skeleton-card">
            <el-skeleton animated>
              <template #template>
                <div class="skeleton-header">
                  <el-skeleton-item variant="text" style="width: 30%" />
                  <el-skeleton-item variant="text" style="width: 60%" />
                </div>
                <div class="skeleton-body">
                  <el-skeleton-item variant="text" style="width: 100%" />
                  <el-skeleton-item variant="text" style="width: 80%" />
                  <el-skeleton-item variant="text" style="width: 90%" />
                </div>
              </template>
            </el-skeleton>
          </div>
        </div>
      </div>

      <!-- 空状态优化 -->
      <div v-else-if="chapters.length === 0 && !loading" class="empty-state">
        <div class="empty-content">
          <div class="empty-icon">
            <el-icon size="64"><Document /></el-icon>
          </div>
          <h3 class="empty-title">暂无章节数据</h3>
          <p class="empty-description">
            {{ searchQuery || statusFilter ? '没有找到符合条件的章节，请尝试调整筛选条件' : '还没有创建任何章节，开始创建第一个章节吧' }}
          </p>
          <div class="empty-actions">
            <el-button 
              v-if="!searchQuery && !statusFilter" 
              type="primary" 
              :icon="Plus" 
              @click="handleCreateChapter" 
              size="large"
            >
              创建第一个章节
            </el-button>
            <el-button 
              v-else 
              :icon="Refresh" 
              @click="handleClearFilters" 
              size="large"
            >
              清除筛选条件
            </el-button>
          </div>
        </div>
      </div>

      <!-- 章节卡片列表 -->
      <transition-group v-else name="chapter-list" tag="div" class="chapter-cards">
        <el-card
          v-for="chapter in chapters"
          :key="chapter.id"
          class="chapter-card"
          :class="{
            'confirmed': chapter.is_confirmed,
            'processing': chapter.status === 'processing',
            'failed': chapter.status === 'failed'
          }"
          shadow="hover"
        >
          <template #header>
            <div class="chapter-card-header">
              <div class="chapter-info">
                <div class="chapter-meta">
                  <span class="chapter-number">第 {{ chapter.chapter_number }} 章</span>
                  <el-tag v-if="chapter.is_confirmed" type="success" size="small">
                    <el-icon class="tag-icon"><Check /></el-icon>
                    已确认
                  </el-tag>
                  <el-tag :type="getStatusType(chapter.status)" size="small">
                    {{ getStatusText(chapter.status) }}
                  </el-tag>
                </div>
                <h3 class="chapter-title">{{ chapter.title }}</h3>
              </div>
              <div class="chapter-actions">
                <el-dropdown trigger="click" @command="(cmd) => handleChapterAction(cmd, chapter)">
                  <el-button :icon="MoreFilled" circle />
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view" :icon="View">
                        查看详情
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="!chapter.is_confirmed && chapter.status === 'completed'"
                        command="confirm"
                        :icon="Check"
                      >
                        确认章节
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="!chapter.is_confirmed"
                        command="edit"
                        :icon="Edit"
                      >
                        编辑章节
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="!chapter.is_confirmed"
                        command="delete"
                        :icon="Delete"
                        divided
                      >
                        删除章节
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </template>

          <div class="chapter-stats">
            <el-row :gutter="16">
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ formatNumber(chapter.word_count) }}</div>
                  <div class="stat-label">字数</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ formatNumber(chapter.paragraph_count) }}</div>
                  <div class="stat-label">段落</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="stat-item">
                  <div class="stat-value">{{ formatDateTime(chapter.updated_at, 'MM-DD') }}</div>
                  <div class="stat-label">更新时间</div>
                </div>
              </el-col>
            </el-row>
          </div>

          <div class="chapter-content-preview">
            <p>{{ truncateContent(chapter.content, 120) }}</p>
          </div>
        </el-card>
      </transition-group>

      <!-- 分页 -->
      <div v-if="chapters.length > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          background
        />
      </div>
    </div>

    <!-- 创建/编辑章节对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      :before-close="handleDialogClose"
      destroy-on-close
    >
      <ChapterForm
        v-if="dialogVisible"
        :chapter="currentChapter"
        :project-id="projectId"
        @submit="handleChapterSubmit"
        @cancel="handleDialogClose"
      />
    </el-dialog>

    <!-- 章节详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="章节详情"
      width="900px"
      destroy-on-close
    >
      <ChapterDetail
        v-if="detailVisible"
        :chapter="currentChapter"
        @edit="handleEditFromDetail"
        @close="detailVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Plus,
  Search,
  Refresh,
  View,
  Edit,
  Delete,
  Check,
  Document,
  Collection,
  Timer,
  MoreFilled
} from '@element-plus/icons-vue'
import chaptersService from '@/services/chapters'
import projectsService from '@/services/projects'
import ChapterForm from '@/components/chapter/ChapterForm.vue'
import ChapterDetail from '@/components/chapter/ChapterDetail.vue'

// 路由相关
const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const refreshing = ref(false)
const chapters = ref([])
const project = ref(null)
const searchQuery = ref('')
const statusFilter = ref('')
const sortBy = ref('chapter_number')
const showGuidance = ref(true)

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 对话框状态
const dialogVisible = ref(false)
const detailVisible = ref(false)
const dialogTitle = ref('')
const currentChapter = ref(null)
const editingChapterId = ref(null)

// 计算属性
const projectId = computed(() => route.params.projectId)

const confirmedCount = computed(() =>
  chapters.value.filter(chapter => chapter.is_confirmed).length
)

const processingCount = computed(() =>
  chapters.value.filter(chapter => chapter.status === 'processing').length
)

const totalWords = computed(() =>
  chapters.value.reduce((total, chapter) => total + (chapter.word_count || 0), 0)
)

// 状态映射
const statusMap = {
  pending: { type: 'info', text: '待处理' },
  confirmed: { type: 'success', text: '已确认' },
  processing: { type: 'warning', text: '处理中' },
  completed: { type: 'success', text: '已完成' },
  failed: { type: 'danger', text: '失败' }
}

// 方法
const getStatusType = (status) => {
  return statusMap[status]?.type || 'info'
}

const getStatusText = (status) => {
  return statusMap[status]?.text || status
}

const formatNumber = (num) => {
  return num ? num.toLocaleString() : 0
}

const formatDateTime = (dateStr, format = 'full') => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)

  if (format === 'MM-DD') {
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit'
    })
  }

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const truncateContent = (content, length) => {
  return content && content.length > length
    ? content.substring(0, length) + '...'
    : content
}

const loadProjectInfo = async () => {
  try {
    project.value = await projectsService.getProject(projectId.value)
  } catch (error) {
    console.error('加载项目信息失败:', error)
  }
}

const loadChapters = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      search: searchQuery.value,
      chapter_status: statusFilter.value,
      sort_by: sortBy.value,
      sort_order: 'asc'
    }

    const response = await chaptersService.getChapters(projectId.value, params)
    chapters.value = response.chapters
    pagination.total = response.total || 0
    pagination.page = response.page || pagination.page
    pagination.size = response.size || pagination.size

    // 如果有章节数据，隐藏引导
    if (chapters.value.length > 0) {
      showGuidance.value = false
    }
  } catch (error) {
    ElMessage.error('加载章节数据失败')
    console.error('加载章节失败:', error)
    chapters.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadChapters()
}

const handleFilter = () => {
  pagination.page = 1
  loadChapters()
}

const handleSort = () => {
  pagination.page = 1
  loadChapters()
}

const handleRefresh = () => {
  refreshing.value = true
  loadChapters().finally(() => {
    setTimeout(() => {
      refreshing.value = false
    }, 1000)
  })
}

const handleSizeChange = (newSize) => {
  pagination.size = newSize
  pagination.page = 1
  loadChapters()
}

const handleCurrentChange = (newPage) => {
  pagination.page = newPage
  loadChapters()
}

const handleBack = () => {
  if (!projectId.value) {
    console.error('projectId 为空，无法返回')
    ElMessage.error('项目ID丢失，无法返回')
    return
  }

  // 返回到项目详情页面
  const targetRoute = `/projects/${projectId.value}`
  console.log('正在返回项目详情页面:', targetRoute)
  router.push(targetRoute).then(() => {
    console.log('返回项目详情页面成功')
  }).catch((error) => {
    console.error('返回项目详情页面失败:', error)
    ElMessage.error('返回项目详情页面失败，请手动导航')
  })
}

const handleCreateChapter = () => {
  try {
    dialogTitle.value = '新建章节'
    currentChapter.value = null
    editingChapterId.value = null
    dialogVisible.value = true
  } catch (error) {
    console.error('创建章节功能出错:', error)
    ElMessage.error('创建章节功能失败')
  }
}

const handleChapterAction = async (command, chapter) => {
  switch (command) {
    case 'view':
      handleViewChapter(chapter)
      break
    case 'edit':
      handleEditChapter(chapter)
      break
    case 'delete':
      await handleDeleteChapter(chapter)
      break
    case 'confirm':
      await handleConfirmChapter(chapter)
      break
  }
}

const handleViewChapter = (chapter) => {
  currentChapter.value = chapter
  detailVisible.value = true
}

const handleEditChapter = (chapter) => {
  dialogTitle.value = '编辑章节'
  currentChapter.value = { ...chapter }
  editingChapterId.value = chapter.id
  dialogVisible.value = true
}

const handleEditFromDetail = (chapter) => {
  detailVisible.value = false
  handleEditChapter(chapter)
}

const handleDeleteChapter = async (chapter) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除章节"${chapter.title}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await chaptersService.deleteChapter(chapter.id)
    ElMessage.success('章节删除成功')
    loadChapters()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除章节失败')
      console.error('删除章节失败:', error)
    }
  }
}

const handleConfirmChapter = async (chapter) => {
  try {
    await chaptersService.confirmChapter(chapter.id)
    ElMessage.success('章节确认成功')
    loadChapters()
  } catch (error) {
    ElMessage.error('确认章节失败')
    console.error('确认章节失败:', error)
  }
}

const handleChapterSubmit = async (chapterData) => {
  try {
    if (editingChapterId.value) {
      // 更新章节
      await chaptersService.updateChapter(editingChapterId.value, chapterData)
      ElMessage.success('章节更新成功')
    } else {
      // 创建章节
      await chaptersService.createChapter(projectId.value, chapterData)
      ElMessage.success('章节创建成功')
    }

    dialogVisible.value = false
    loadChapters()
  } catch (error) {
    ElMessage.error(editingChapterId.value ? '更新章节失败' : '创建章节失败')
    console.error('章节操作失败:', error)
  }
}

const handleDialogClose = () => {
  dialogVisible.value = false
  currentChapter.value = null
  editingChapterId.value = null
}

const handleClearFilters = () => {
  searchQuery.value = ''
  statusFilter.value = ''
  pagination.page = 1
  loadChapters()
}

// 生命周期
onMounted(async () => {
  await loadProjectInfo()
  await loadChapters()
})
</script>

<style scoped>
.chapter-management {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  padding: var(--space-lg);
}

/* 头部操作栏 */
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-sm);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
}

/* 按钮样式 */
.header-actions .el-button {
  border-radius: var(--radius-lg);
  font-weight: 600;
  padding: var(--space-md) var(--space-lg);
  min-width: 120px;
  transition: all var(--transition-base);
}

.header-actions .el-button--primary {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  border: none;
  box-shadow: var(--shadow-md);
}

.header-actions .el-button--primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* 卡片样式 */
:deep(.el-card) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

:deep(.el-card__header) {
  padding: var(--space-xl);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.02), rgba(139, 92, 246, 0.02));
  border-bottom: 1px solid var(--border-primary);
}

:deep(.el-card__body) {
  padding: var(--space-xl);
}

/* 用户引导 */
.guidance-section {
  width: 100%;
}

.guidance-card {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.guidance-content {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
  padding: var(--space-xl);
}

.guidance-icon {
  color: var(--primary-color);
  flex-shrink: 0;
}

.guidance-text h3 {
  margin: 0 0 var(--space-md) 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.guidance-text p {
  margin: 0 0 var(--space-lg) 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.guidance-list {
  margin: 0 0 var(--space-xl) 0;
  padding-left: var(--space-lg);
}

.guidance-list li {
  margin-bottom: var(--space-sm);
  color: var(--text-secondary);
}

/* 快速操作栏 */
.quick-actions {
  width: 100%;
}

/* 统计概览 */
.stats-overview {
  width: 100%;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  transition: all var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-card.total {
  border-left: 4px solid var(--primary-color);
}

.stat-card.confirmed {
  border-left: 4px solid var(--success-color);
}

.stat-card.processing {
  border-left: 4px solid var(--warning-color);
}

.stat-card.words {
  border-left: 4px solid var(--info-color);
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  color: white;
  border-radius: var(--radius-lg);
  font-size: var(--text-xl);
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
  line-height: 1;
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

/* 章节容器 */
.chapters-container {
  width: 100%;
}

/* 加载状态优化 */
.loading-state {
  padding: var(--space-xl);
  text-align: center;
}

.loading-content {
  margin-bottom: var(--space-xl);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-primary);
  border-top: 3px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto var(--space-md);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: var(--text-secondary);
  font-size: var(--text-base);
  margin: 0;
}

.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
  gap: var(--space-lg);
  margin-top: var(--space-xl);
}

.skeleton-card {
  padding: var(--space-lg);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}

.skeleton-header {
  margin-bottom: var(--space-md);
}

.skeleton-body {
  margin-top: var(--space-md);
}

/* 空状态优化 */
.empty-state {
  padding: var(--space-xl);
  text-align: center;
}

.empty-content {
  max-width: 400px;
  margin: 0 auto;
}

.empty-icon {
  color: var(--text-tertiary);
  margin-bottom: var(--space-lg);
}

.empty-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-md) 0;
}

.empty-description {
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 var(--space-xl) 0;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-md);
}

.chapter-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
  gap: var(--space-lg);
}

.chapter-card {
  transition: all var(--transition-fast);
  border-radius: var(--radius-lg);
}

.chapter-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.chapter-card.confirmed {
  border-color: var(--success-color);
}

.chapter-card.processing {
  border-color: var(--warning-color);
}

.chapter-card.failed {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.02);
}

.chapter-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.chapter-info {
  flex: 1;
}

.chapter-meta {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
  margin-bottom: var(--space-sm);
}

.chapter-number {
  font-size: var(--text-sm);
  color: var(--primary-color);
  font-weight: 600;
}

.tag-icon {
  margin-right: var(--space-xs);
}

.chapter-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
}

.chapter-actions {
  margin-left: var(--space-md);
}

.chapter-stats {
  margin-bottom: var(--space-md);
}

.stat-item {
  text-align: center;
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.stat-item .stat-value {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.stat-item .stat-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: 500;
}

.chapter-content-preview {
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
}

.chapter-content-preview p {
  margin: 0;
  line-height: 1.6;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

/* 分页 */
.pagination-container {
  display: flex;
  justify-content: center;
  padding: var(--space-xl) 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-md);
  }

  .guidance-content {
    flex-direction: column;
    text-align: center;
  }

  .chapter-cards {
    grid-template-columns: 1fr;
  }

  .quick-actions :deep(.el-row) {
    flex-direction: column;
  }

  .quick-actions :deep(.el-col) {
    width: 100%;
    margin-bottom: var(--space-sm);
  }
}

/* 章节列表动画 */
.chapter-list-enter-active {
  transition: all 0.3s ease-out;
}

.chapter-list-leave-active {
  transition: all 0.3s ease-in;
}

.chapter-list-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.chapter-list-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.chapter-list-move {
  transition: transform 0.3s ease;
}
</style>