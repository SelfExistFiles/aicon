<template>
  <div class="director-mode">
    <div class="toolbar">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="选择章节" style="width: 300px">
          <el-select v-model="selectedChapterId" placeholder="请选择已确认的章节" @change="loadSentences">
            <el-option
              v-for="chapter in chapters"
              :key="chapter.id"
              :label="`第${chapter.chapter_number}章: ${chapter.title} (${chapter.status})`"
              :value="chapter.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="selectedChapterId">
          <el-button type="primary" @click="generatePromptsVisible = true">
            批量生成图片提示词
          </el-button>
          <el-button type="warning" v-if="chapters.find(c => c.id === selectedChapterId)?.status === 'generated_prompts'" @click="batchGenerateImagesVisible = true">
            批量生成图片
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 生成提示词对话框 -->
      <GeneratePromptsDialog
        v-model:visible="generatePromptsVisible"
        :chapter-id="selectedChapterId"
        :api-keys="apiKeys"
        @generate-success="handleGenerateSuccess"
      />
      
      <!-- 重新生成提示词对话框 -->
      <RegeneratePromptsDialog
        v-model:visible="regeneratePromptsVisible"
        :sentence-ids="selectedSentenceIds"
        :api-keys="apiKeys"
        @regenerate-success="handleRegenerateSuccess"
      />
      
      <!-- 批量生成图片对话框 -->
      <BatchGenerateImagesDialog
        v-model:visible="batchGenerateImagesVisible"
        :chapter-id="selectedChapterId"
        :api-keys="apiKeys"
        @generate-success="handleGenerateSuccess"
      />
    </div>

    <div class="content-area" v-loading="loading">
      <el-empty v-if="!sentences.length" description="请选择章节以开始" />
      
      <div v-else class="card-grid">
        <SentenceCard
          v-for="(sentence, index) in sentences"
          :key="sentence.id"
          :sentence="sentence"
          :index="index"
          :loading-states="loadingStates[sentence.id]"
          @prompt-action="handlePromptAction"
          @regenerate-prompt="handleRegeneratePrompt"
          @update:loading-states="(newState) => updateSentenceLoadingState(sentence.id, newState)"
        />
      </div>
    </div>
    
    <!-- 查看/编辑提示词对话框 - 使用新组件 -->
    <PromptDialog
      v-model:visible="promptDialogVisible"
      v-model:sentence="currentSentence"
      :is-editing="isEditingPrompt"
      :dialog-title="promptDialogTitle"
      @save="handlePromptSave"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useDirectorEngine } from '@/composables/useDirectorEngine'
import GeneratePromptsDialog from '@/components/studio/GeneratePromptsDialog.vue'
import RegeneratePromptsDialog from '@/components/studio/RegeneratePromptsDialog.vue'
import BatchGenerateImagesDialog from '@/components/studio/BatchGenerateImagesDialog.vue'
import SentenceCard from '@/components/studio/SentenceCard.vue'
import PromptDialog from '@/components/studio/PromptDialog.vue'

// Props
const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
})

// 使用 composable 管理状态和逻辑
const {
  chapters,
  apiKeys,
  sentences,
  selectedChapterId,
  loading,
  loadingStates,
  generatePromptsVisible,
  regeneratePromptsVisible,
  batchGenerateImagesVisible,
  selectedSentenceIds,
  loadSentences,
  updateSentenceLoadingState,
  handlePromptAction: fetchPromptAction
} = useDirectorEngine(props.projectId)

// 提示词对话框状态
const promptDialogVisible = ref(false)
const promptDialogTitle = ref('')
const currentSentence = ref({})
const isEditingPrompt = ref(false)

// 处理生成成功
const handleGenerateSuccess = async () => {
  await loadSentences()
}

// 处理重新生成成功
const handleRegenerateSuccess = async () => {
  await loadSentences()
}

// 处理提示词操作（查看/编辑）
const handlePromptAction = async (event) => {
  const { action, sentence } = event
  const result = await fetchPromptAction(action, sentence)
  
  if (result) {
    currentSentence.value = { ...result.sentence }
    if (action === 'view') {
      promptDialogTitle.value = '查看提示词'
      isEditingPrompt.value = false
    } else if (action === 'edit') {
      promptDialogTitle.value = '编辑提示词'
      isEditingPrompt.value = true
    }
    promptDialogVisible.value = true
  }
}

// 处理重新生成提示词
const handleRegeneratePrompt = (sentence) => {
  // 设置当前句子ID
  selectedSentenceIds.value = [sentence.id]
  // 打开重新生成提示词对话框
  regeneratePromptsVisible.value = true
}

// 处理提示词保存
const handlePromptSave = (updatedSentence) => {
  // 更新原句子的提示词
  const index = sentences.value.findIndex(s => s.id === updatedSentence.id)
  if (index !== -1) {
    sentences.value[index].image_prompt = updatedSentence.image_prompt
  }
}
</script>

<style scoped>
/* 页面基础样式 */
.director-mode {
  padding: var(--space-lg);
}

/* 工具栏样式 */
.toolbar {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  box-shadow: var(--shadow-sm);
}

/* 内容区域样式 */
.content-area {
  margin-top: var(--space-lg);
}

/* 卡片网格样式 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: var(--space-lg);
}

/* 表单样式 */
.filter-form {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.filter-form .el-form-item {
  margin-bottom: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .card-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }

  .filter-form {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>