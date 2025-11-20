<template>
  <div class="content-studio">
    <!-- 顶部工具栏 -->
    <div class="studio-header">
      <div class="header-left">
        <el-button @click="handleBack" :icon="ArrowLeft">返回项目</el-button>
        <el-divider direction="vertical" />
        <span class="project-title">{{ projectTitle }}</span>
      </div>
      <div class="header-right">
        <el-button 
          type="primary" 
          :loading="saving"
          :disabled="!hasChanges"
          @click="handleSave"
        >
          <el-icon><Check /></el-icon>
          保存修改
        </el-button>
      </div>
    </div>

    <!-- 三栏布局 -->
    <div class="studio-body">
      <!-- 左侧：章节导航 -->
      <ChapterNav
        :chapters="chapters"
        :selected-id="selectedChapterId"
        :loading="chaptersLoading"
        @select="handleChapterSelect"
      />

      <!-- 中间：段落编辑器 -->
      <ParagraphStream
        :paragraphs="paragraphs"
        :selected-id="selectedParagraphId"
        :loading="paragraphsLoading"
        @select="handleParagraphSelect"
        @update="handleParagraphUpdate"
      />

      <!-- 右侧：句子检查器 -->
      <SentenceInspector
        :paragraph="selectedParagraph"
        :loading="sentencesLoading"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check } from '@element-plus/icons-vue'

import ChapterNav from '@/components/studio/ChapterNav.vue'
import ParagraphStream from '@/components/studio/ParagraphStream.vue'
import SentenceInspector from '@/components/studio/SentenceInspector.vue'

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
const projectTitle = ref('')
const chapters = ref([])
const paragraphs = ref([])
const selectedChapterId = ref(null)
const selectedParagraphId = ref(null)
const selectedParagraph = computed(() => 
  paragraphs.value.find(p => p.id === selectedParagraphId.value)
)

// 加载状态
const chaptersLoading = ref(false)
const paragraphsLoading = ref(false)
const sentencesLoading = ref(false)
const saving = ref(false)

// 修改追踪
const modifiedParagraphs = ref(new Map())
const hasChanges = computed(() => modifiedParagraphs.value.size > 0)

// 加载章节列表
const loadChapters = async () => {
  try {
    chaptersLoading.value = true
    const response = await chaptersService.getChapters(props.projectId)
    chapters.value = response.chapters || []
    
    // 自动选中第一章
    if (chapters.value.length > 0 && !selectedChapterId.value) {
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
  // 记录修改
  modifiedParagraphs.value.set(paragraphId, {
    ...modifiedParagraphs.value.get(paragraphId),
    ...updates
  })
}

const handleSave = async () => {
  if (!hasChanges.value) return
  
  try {
    saving.value = true
    
    // 构建批量更新数据
    const updates = Array.from(modifiedParagraphs.value.entries()).map(([id, changes]) => ({
      id,
      ...changes
    }))
    
    await paragraphsService.batchUpdateParagraphs(selectedChapterId.value, {
      paragraphs: updates
    })
    
    ElMessage.success('保存成功')
    modifiedParagraphs.value.clear()
    
    // 重新加载当前章节的段落
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
      router.push({ name: 'Projects' })
    }).catch(() => {})
  } else {
    router.push({ name: 'Projects' })
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
onMounted(() => {
  loadChapters()
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

.studio-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
