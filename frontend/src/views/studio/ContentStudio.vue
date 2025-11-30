<template>
  <div class="content-studio">
    <!-- 顶部工具栏 -->
    <div class="studio-header">
      <div class="header-left">
        <el-button @click="handleBack" :icon="ArrowLeft" link>返回</el-button>
        <el-divider direction="vertical" />
        <el-tooltip content="切换章节列表" placement="bottom">
          <el-button 
            @click="showChapterNav = !showChapterNav" 
            :icon="showChapterNav ? Fold : Expand"
            link
          />
        </el-tooltip>
        <span class="project-title">{{ projectTitle }}</span>
      </div>
      <div class="header-right">
        <el-tooltip content="切换句子详情" placement="bottom">
          <el-button 
            @click="showInspector = !showInspector" 
            :icon="showInspector ? Expand : Fold"
            link
            style="margin-right: 10px"
          >
            {{ showInspector ? '隐藏详情' : '显示详情' }}
          </el-button>
        </el-tooltip>
        <el-button 
          v-if="canConfirm"
          type="success" 
          @click="handleConfirmCurrentChapter"
        >
          <el-icon><Check /></el-icon>
          确认章节
        </el-button>
        <el-button 
          v-if="readOnly && selectedChapterId"
          type="warning" 
          @click="goToDirector"
        >
          <el-icon><MagicStick /></el-icon>
          导演引擎
        </el-button>
        <el-button 
          type="primary" 
          :loading="saving"
          :disabled="!hasChanges || readOnly"
          @click="handleSave"
        >
          <el-icon><Check /></el-icon>
          保存修改
        </el-button>
      </div>
    </div>

    <!-- 统计信息面板 -->
    <div class="studio-stats">
      <div class="stat-item">
        <span class="stat-label">章节</span>
        <span class="stat-value">{{ totalChapters }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">段落</span>
        <span class="stat-value">{{ totalParagraphs }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">总字数</span>
        <span class="stat-value">{{ totalWords }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">已修改</span>
        <span class="stat-value">{{ hasChanges ? modifiedParagraphs.size : 0 }}</span>
      </div>
    </div>

    <!-- 章节确认后的引导提示 -->
    <el-alert
      v-if="showDirectorGuidance"
      type="success"
      title="章节已确认！"
      :closable="true"
      @close="showDirectorGuidance = false"
      style="margin: 16px 20px;"
    >
      <template #default>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span>现在可以进入导演引擎为这个章节生成分镜脚本了</span>
          <el-button type="primary" size="small" @click="goToDirector">
            <el-icon><MagicStick /></el-icon>
            进入导演引擎
          </el-button>
        </div>
      </template>
    </el-alert>

    <!-- 三栏布局 -->
    <div class="studio-body">
      <!-- 左侧：章节导航 -->
      <!-- 左侧：章节导航 -->
      <Transition name="slide-left">
        <div 
          v-show="showChapterNav && !inspectorMaximized" 
          class="panel-container left-panel"
          :style="{ width: leftPanelWidth + 'px' }"
        >
          <ChapterNav
            :chapters="chapters"
            :selected-id="selectedChapterId"
            :loading="chaptersLoading"
            :has-more="hasMoreChapters"
            @select="handleChapterSelect"
            @create="handleChapterCreate"
            @edit="handleChapterEdit"
            @delete="handleChapterDelete"
            @confirm="handleChapterConfirm"
            @load-more="loadMoreChapters"
            @director-engine="handleGoToDirector"
          />
        </div>
      </Transition>

      <!-- 左侧调整手柄 -->
      <div 
        v-show="showChapterNav && !inspectorMaximized"
        class="resize-handle left-handle"
        @mousedown="startResizeLeft"
      ></div>

      <!-- 左侧折叠条 -->
      <div 
        v-if="!showChapterNav && !inspectorMaximized" 
        class="collapsed-bar left-bar"
        @click="showChapterNav = true"
      >
        <el-tooltip content="展开章节列表" placement="right">
          <el-button :icon="Expand" link />
        </el-tooltip>
      </div>

      <!-- 中间：段落编辑器 -->
      <ParagraphStream
        v-show="!inspectorMaximized"
        :paragraphs="paragraphs"
        :selected-id="selectedParagraphId"
        :loading="paragraphsLoading"
        @select="handleParagraphSelect"
        @update="handleParagraphUpdate"
        @create="handleParagraphCreate"
        @physical-delete="handleParagraphPhysicalDelete"
        :read-only="readOnly"
      />

      <!-- 右侧折叠条 -->
      <div 
        v-if="!showInspector && !inspectorMaximized" 
        class="collapsed-bar right-bar"
        @click="showInspector = true"
      >
        <el-tooltip content="展开句子详情" placement="left">
          <el-button :icon="Fold" link />
        </el-tooltip>
      </div>

      <!-- 右侧调整手柄 -->
      <div 
        v-show="showInspector && !inspectorMaximized"
        class="resize-handle right-handle"
        @mousedown="startResizeRight"
      ></div>

      <!-- 右侧：句子检查器 -->
      <Transition name="slide-right">
        <div 
          v-show="showInspector || inspectorMaximized" 
          class="panel-container right-panel"
          :style="{ width: inspectorMaximized ? '100%' : rightPanelWidth + 'px' }"
        >
          <SentenceInspector
            :paragraph="selectedParagraph"
            :loading="sentencesLoading"
            :is-maximized="inspectorMaximized"
            @toggle-maximize="inspectorMaximized = !inspectorMaximized"
            :read-only="readOnly"
          />
        </div>
      </Transition>
    </div>

    <!-- 章节编辑对话框 -->
    <ChapterFormDialog
      v-model="showChapterDialog"
      :chapter="editingChapter"
      @submit="handleChapterSubmit"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, Fold, Expand, MagicStick } from '@element-plus/icons-vue'
import { useProjectsStore } from '@/stores/projects'

import ChapterNav from '@/components/studio/ChapterNav.vue'
import ParagraphStream from '@/components/studio/ParagraphStream.vue'
import SentenceInspector from '@/components/studio/SentenceInspector.vue'
import ChapterFormDialog from '@/components/studio/ChapterFormDialog.vue'

import chaptersService from '@/services/chapters'
import paragraphsService from '@/services/paragraphs'

const router = useRouter()
const route = useRoute()

// Props
const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
})

// 状态
const showDirectorGuidance = ref(false)
const projectTitle = ref('')
const project = ref(null)  // 添加项目数据
const chapters = ref([])
const paragraphs = ref([])
const selectedChapterId = ref(null)
const selectedParagraphId = ref(null)
const selectedParagraph = computed(() => 
  paragraphs.value.find(p => p.id === selectedParagraphId.value)
)

// 只读状态
const readOnly = computed(() => {
  if (!selectedChapterId.value) return true
  const chapter = chapters.value.find(c => c.id === selectedChapterId.value)
  return chapter ? chapter.is_confirmed : true
})

// 是否可以确认
const canConfirm = computed(() => {
  if (!selectedChapterId.value) return false
  const chapter = chapters.value.find(c => c.id === selectedChapterId.value)
  return chapter && !chapter.is_confirmed && chapter.status === 'pending'
})

// 章节对话框状态
const showChapterDialog = ref(false)
const editingChapter = ref(null)

// 加载状态
const chaptersLoading = ref(false)
const paragraphsLoading = ref(false)
const sentencesLoading = ref(false)
const saving = ref(false)

// UI状态
const showChapterNav = ref(true)
const showInspector = ref(true)
const inspectorMaximized = ref(false)
const leftPanelWidth = ref(280)
const rightPanelWidth = ref(320)

// 调整大小逻辑
const startResizeLeft = (e) => {
  e.preventDefault()
  const startX = e.clientX
  const startWidth = leftPanelWidth.value
  
  const onMouseMove = (e) => {
    const newWidth = startWidth + (e.clientX - startX)
    if (newWidth >= 200 && newWidth <= 500) {
      leftPanelWidth.value = newWidth
    }
  }
  
  const onMouseUp = () => {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

const startResizeRight = (e) => {
  e.preventDefault()
  const startX = e.clientX
  const startWidth = rightPanelWidth.value
  
  const onMouseMove = (e) => {
    const newWidth = startWidth - (e.clientX - startX) // 右侧是减去增量
    if (newWidth >= 250 && newWidth <= 600) {
      rightPanelWidth.value = newWidth
    }
  }
  
  const onMouseUp = () => {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// 修改追踪
const modifiedParagraphs = ref(new Map())
const hasChanges = computed(() => modifiedParagraphs.value.size > 0)

// 加载项目信息
const loadProject = async () => {
  try {
    const projectsStore = useProjectsStore()
    project.value = await projectsStore.getProject(props.projectId)
    projectTitle.value = project.value?.title || ''
  } catch (error) {
    console.error('加载项目信息失败:', error)
  }
}

// 加载章节列表
const currentPage = ref(1)
const pageSize = ref(20)  // 每页20个章节（与后端默认值匹配）
const hasMoreChapters = ref(true)

const loadChapters = async (reset = false) => {
  try {
    chaptersLoading.value = true
    
    if (reset) {
      currentPage.value = 1
      chapters.value = []
    }
    
    // 后端API使用 size 参数，不是 page_size
    const response = await chaptersService.getChapters(props.projectId, {
      page: currentPage.value,
      size: pageSize.value  // 使用 size 而不是 page_size
    })
    
    const newChapters = response.chapters || []
    
    if (reset) {
      chapters.value = newChapters
    } else {
      chapters.value = [...chapters.value, ...newChapters]
    }
    
    // 检查是否还有更多章节
    // 如果返回的章节数少于请求的数量，说明没有更多了
    hasMoreChapters.value = newChapters.length >= pageSize.value
    
    console.log('章节加载:', {
      currentPage: currentPage.value,
      loaded: newChapters.length,
      total: chapters.value.length,
      hasMore: hasMoreChapters.value
    })
    
    // 自动选中第一章（仅在首次加载时）
    if (reset && chapters.value.length > 0 && !selectedChapterId.value) {
      selectedChapterId.value = chapters.value[0].id
      await loadParagraphs(chapters.value[0].id)
    }
  } catch (error) {
    console.error('加载章节失败:', error)
    ElMessage.error('加载章节失败')
  } finally {
    chaptersLoading.value = false
  }
}

// 加载更多章节
const loadMoreChapters = async () => {
  if (!hasMoreChapters.value || chaptersLoading.value) return
  currentPage.value++
  await loadChapters(false)
}

// 加载段落列表
const loadParagraphs = async (chapterId) => {
  try {
    paragraphsLoading.value = true
    const response = await paragraphsService.getParagraphs(chapterId)
    paragraphs.value = response.paragraphs || []
  } catch (error) {
    console.error('加载段落失败:', error)
    ElMessage.error('加载段落失败')
  } finally {
    paragraphsLoading.value = false
  }
}

// 事件处理
const handleChapterSelect = async (chapterId) => {
  if (selectedChapterId.value === chapterId) return
  
  // 如果有未保存的修改，提示用户
  if (hasChanges.value) {
    try {
      await ElMessageBox.confirm(
        '当前有未保存的修改，切换章节将丢失这些修改。是否继续？',
        '提示',
        {
          confirmButtonText: '继续',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      modifiedParagraphs.value.clear()
    } catch {
      return
    }
  }
  
  selectedChapterId.value = chapterId
  selectedParagraphId.value = null
  await loadParagraphs(chapterId)
}

const handleParagraphSelect = (paragraphId) => {
  selectedParagraphId.value = paragraphId
}

const handleParagraphUpdate = (paragraphId, updates) => {
  // 找到段落对象并更新
  const paragraph = paragraphs.value.find(p => p.id === paragraphId)
  if (paragraph) {
    // 直接更新段落对象以触发响应式更新
    Object.assign(paragraph, updates)
  }
  
  // 同时记录到修改Map中
  modifiedParagraphs.value.set(paragraphId, {
    ...modifiedParagraphs.value.get(paragraphId),
    ...updates
  })
}

// 创建段落
const handleParagraphCreate = async (paragraphData) => {
  if (!selectedChapterId.value) {
    ElMessage.warning('请先选择一个章节')
    return
  }

  try {
    await paragraphsService.createParagraph(selectedChapterId.value, paragraphData)
    ElMessage.success('段落创建成功')
    // 重新加载段落列表
    await loadParagraphs(selectedChapterId.value)
  } catch (error) {
    console.error('创建段落失败:', error)
    ElMessage.error('创建段落失败')
  }
}

// 立即物理删除段落
const handleParagraphPhysicalDelete = async (paragraphId) => {
  try {
    await paragraphsService.deleteParagraph(paragraphId)
    ElMessage.success('段落删除成功')
    // 重新加载段落列表
    if (selectedChapterId.value) {
      await loadParagraphs(selectedChapterId.value)
    }
  } catch (error) {
    console.error('删除段落失败:', error)
    ElMessage.error('删除段落失败')
  }
}

// 统计信息计算属性 - 从项目数据获取
const totalParagraphs = computed(() => {
  return project.value?.paragraph_count || 0
})

const totalWords = computed(() => {
  return project.value?.word_count || 0
})

const totalChapters = computed(() => {
  return project.value?.chapter_count || chapters.value.length
})

// 章节管理
const handleChapterCreate = () => {
  editingChapter.value = null
  showChapterDialog.value = true
}

const handleChapterEdit = (chapter) => {
  editingChapter.value = chapter
  showChapterDialog.value = true
}

const handleChapterDelete = async (chapter) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除章节"${chapter.title}"吗？这将同时删除该章节下的所有段落。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const wasCurrentChapter = selectedChapterId.value === chapter.id
    
    await chaptersService.deleteChapter(chapter.id)
    ElMessage.success('章节删除成功')
    
    // 重新加载章节列表
    await loadChapters()
    
    // 如果删除的是当前选中的章节
    if (wasCurrentChapter) {
      // 尝试选择下一个章节
      if (chapters.value.length > 0) {
        selectedChapterId.value = chapters.value[0].id
        await loadParagraphs(chapters.value[0].id)
      } else {
        // 如果没有章节了，清空
        selectedChapterId.value = null
        paragraphs.value = []
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除章节失败:', error)
      ElMessage.error('删除章节失败')
    }
  }
}

const handleChapterSubmit = async (chapterData) => {
  try {
    const isEditingCurrentChapter = chapterData.id === selectedChapterId.value
    
    if (chapterData.id) {
      // 编辑
      await chaptersService.updateChapter(chapterData.id, chapterData)
      ElMessage.success('章节更新成功')
    } else {
      // 创建
      await chaptersService.createChapter(props.projectId, chapterData)
      ElMessage.success('章节创建成功')
    }
    
    // 重新加载章节列表
    await loadChapters()
    
    // 如果编辑的是当前选中的章节，需要重新加载段落列表
    // 因为章节内容可能改变，段落会重新解析
    if (isEditingCurrentChapter && selectedChapterId.value) {
      await loadParagraphs(selectedChapterId.value)
    }
  } catch (error) {
    console.error('保存章节失败:', error)
    ElMessage.error('保存章节失败')
  }
}

const handleChapterConfirm = async (chapter) => {
  try {
    await ElMessageBox.confirm(
      `确定要确认章节"${chapter.title}"吗？确认后章节将变为只读，无法再修改。`,
      '确认章节',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await chaptersService.confirmChapter(chapter.id)
    ElMessage.success('章节确认成功')
    
    // 显示导演引擎引导提示
    showDirectorGuidance.value = true
    
    // 更新本地状态，避免重新加载导致列表跳动或重复
    const index = chapters.value.findIndex(c => c.id === chapter.id)
    if (index !== -1) {
      chapters.value[index].is_confirmed = true
      chapters.value[index].status = 'confirmed' // 假设后端返回的状态是 confirmed
    }
    
    // 如果确认的是当前章节，需要重新加载段落以更新状态
    if (selectedChapterId.value === chapter.id) {
      await loadParagraphs(chapter.id)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('确认章节失败:', error)
      ElMessage.error('确认章节失败')
    }
  }
}

const handleConfirmCurrentChapter = () => {
  const chapter = chapters.value.find(c => c.id === selectedChapterId.value)
  if (chapter) {
    handleChapterConfirm(chapter)
  }
}

// 从章节列表进入导演引擎
const handleGoToDirector = (chapter) => {
  router.push({
    name: 'DirectorEngine',
    params: { projectId: props.projectId },
    query: { chapterId: chapter.id }
  })
}

// 进入导演引擎
const goToDirector = () => {
  router.push({
    name: 'DirectorEngine',
    params: { projectId: props.projectId },
    query: { chapterId: selectedChapterId.value }
  })
}

const handleSave = async () => {
  if (!hasChanges.value || !selectedChapterId.value) return
  
  try {
    saving.value = true
    
    // 分离编辑和删除的段落
    const toUpdate = []
    const toDelete = []
    
    modifiedParagraphs.value.forEach((changes, paragraphId) => {
      if (changes.action === 'delete') {
        // 标记为删除
        toDelete.push(paragraphId)
      } else if (changes.action === 'edit' && changes.edited_content) {
        // 更新内容
        toUpdate.push({
          id: paragraphId,
          content: changes.edited_content
        })
      }
    })
    
    // 执行删除操作（物理删除）
    for (const paragraphId of toDelete) {
      await paragraphsService.deleteParagraph(paragraphId)
    }
    
    // 执行更新操作
    for (const update of toUpdate) {
      await paragraphsService.updateParagraph(update.id, {
        content: update.content
      })
    }
    
    const message = `保存成功：${toUpdate.length > 0 ? `编辑${toUpdate.length}个` : ''}${toUpdate.length > 0 && toDelete.length > 0 ? '，' : ''}${toDelete.length > 0 ? `删除${toDelete.length}个` : ''}`
    ElMessage.success(message || '保存成功')
    
    // 清空修改记录
    modifiedParagraphs.value.clear()
    
    // 重新加载段落列表
    await loadParagraphs(selectedChapterId.value)
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleBack = () => {
  if (hasChanges.value) {
    ElMessageBox.confirm(
      '当前有未保存的修改，返回将丢失这些修改。是否继续？',
      '提示',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      router.push({ 
        name: 'ProjectDetail', 
        params: { projectId: props.projectId }
      })
    }).catch(() => {})
  } else {
    router.push({ 
      name: 'ProjectDetail', 
      params: { projectId: props.projectId }
    })
  }
}

// 路由守卫
onBeforeRouteLeave((to, from, next) => {
  if (hasChanges.value) {
    ElMessageBox.confirm(
      '当前有未保存的修改，离开将丢失这些修改。是否继续？',
      '提示',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      next()
    }).catch(() => {
      next(false)
    })
  } else {
    next()
  }
})

// 生命周期
onMounted(async () => {
  await loadProject()
  await loadChapters(true)  // reset=true 首次加载
})
</script>

<style scoped>
.content-studio {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

.studio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  box-shadow: var(--shadow-sm);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.project-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.studio-stats {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  min-width: 100px;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-xs);
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--primary-color);
}

.studio-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative; /* 确保过渡效果正常 */
}

/* 过渡动画 */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.slide-left-enter-from,
.slide-left-leave-to {
  width: 0 !important;
  min-width: 0 !important;
  opacity: 0;
  margin-left: -280px; /* ChapterNav width */
}

.slide-right-enter-from,
.slide-right-leave-to {
  width: 0 !important;
  min-width: 0 !important;
  opacity: 0;
  margin-right: -320px; /* SentenceInspector width */
}

.panel-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.1s; /* 拖动时稍微平滑一点，但不要太慢 */
}

.resize-handle {
  width: 4px;
  height: 100%;
  background: transparent;
  cursor: col-resize;
  transition: background-color 0.2s;
  z-index: 10;
  flex-shrink: 0;
}

.resize-handle:hover,
.resize-handle:active {
  background: var(--primary-color);
}

.collapsed-bar {
  width: 40px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: var(--space-md);
  cursor: pointer;
  transition: background-color 0.2s;
}

.collapsed-bar:hover {
  background: var(--bg-hover);
}

.collapsed-bar.left-bar {
  border-left: none;
}

.collapsed-bar.right-bar {
  border-right: none;
}
</style>
