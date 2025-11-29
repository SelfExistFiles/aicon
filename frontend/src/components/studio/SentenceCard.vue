<template>
  <el-card
    class="sentence-card"
    shadow="hover"
  >
    <template #header>
      <div class="card-header">
        <span class="card-index">#{{ index + 1 }}</span>
        <el-dropdown @command="handlePromptAction">
          <span class="el-dropdown-link">
            <el-icon><Setting /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="view">查看提示词</el-dropdown-item>
              <el-dropdown-item command="edit">编辑提示词</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </template>
    
    <div class="card-content">
      <p class="sentence-text">{{ sentence.content }}</p>
    </div>
    
    <div class="card-actions">
      <el-button
        type="primary"
        :loading="loadingStates.generatingPrompt"
        @click="handleRegeneratePrompt"
        size="small"
        v-show="sentence.image_prompt"
      >
        <el-icon><MagicStick /></el-icon>
        重新生成提示词
      </el-button>
      
      <el-button
        type="success"
        :loading="loadingStates.generatingAudio"
        :disabled="!sentence.image_prompt"
        @click="handleGenerateAudio"
        size="small"
      >
        <el-icon><Microphone /></el-icon>
        生成音频
      </el-button>
      
      <el-button
        type="warning"
        :loading="loadingStates.generatingImage"
        :disabled="!sentence.image_prompt"
        @click="handleGenerateImage"
        size="small"
        v-show="sentence.image_url"
      >
        <el-icon><Camera /></el-icon>
        生成图片
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, MagicStick, Microphone, Camera } from '@element-plus/icons-vue'
import api from '@/services/api'

const props = defineProps({
  sentence: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  loadingStates: {
    type: Object,
    default: () => ({
      generatingPrompt: false,
      generatingAudio: false,
      generatingImage: false
    })
  }
})

const emit = defineEmits(['prompt-action', 'regenerate-prompt', 'update:loadingStates'])

// 处理提示词操作（查看/编辑）
const handlePromptAction = async (action) => {
  emit('prompt-action', {
    action,
    sentence: props.sentence
  })
}

// 处理重新生成提示词
const handleRegeneratePrompt = () => {
  emit('regenerate-prompt', props.sentence)
}

// 处理生成音频
const handleGenerateAudio = async () => {
  // 更新加载状态
  emit('update:loadingStates', {
    ...props.loadingStates,
    generatingAudio: true
  })
  
  try {
    const response = await api.post('/audio/generate-audio', {
      sentence_id: props.sentence.id
    })
    
    if (response.success) {
      ElMessage.success('音频生成成功')
      // 可以通过事件通知父组件更新句子数据
      emit('audio-generated', {
        sentenceId: props.sentence.id,
        audioUrl: response.audio_url
      })
    }
  } catch (error) {
    console.error('生成单个音频失败', error)
    ElMessage.error('生成音频失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    // 重置加载状态
    emit('update:loadingStates', {
      ...props.loadingStates,
      generatingAudio: false
    })
  }
}

// 处理生成图片
const handleGenerateImage = async () => {
  // 更新加载状态
  emit('update:loadingStates', {
    ...props.loadingStates,
    generatingImage: true
  })
  
  try {
    const response = await api.post('/image/generate-image', {
      sentence_id: props.sentence.id
    })
    
    if (response.success) {
      ElMessage.success('图片生成成功')
      // 可以通过事件通知父组件更新句子数据
      emit('image-generated', {
        sentenceId: props.sentence.id,
        imageUrl: response.image_url
      })
    }
  } catch (error) {
    console.error('生成单个图片失败', error)
    ElMessage.error('生成图片失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    // 重置加载状态
    emit('update:loadingStates', {
      ...props.loadingStates,
      generatingImage: false
    })
  }
}
</script>

<style scoped>
/* 卡片基础样式 */
.sentence-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.06);
}

.sentence-card:hover {
  border-color: #c0c0c0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

/* 卡片头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border-bottom: 1px solid #e8e8e8;
  position: relative;
}

.card-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #202124;
  background: #ffffff;
  width: 24px;
  height: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  border: 1px solid #e0e0e0;
  font-family: 'Google Sans', 'Roboto', sans-serif;
}

/* 下拉菜单样式 */
.el-dropdown-link {
  color: #5f6368;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.el-dropdown-link:hover {
  color: #1a73e8;
  background: #f8f9fa;
  border-color: #1a73e8;
  box-shadow: 0 1px 3px rgba(26, 115, 232, 0.15);
}

/* 卡片内容样式 */
.card-content {
  padding: var(--space-lg);
}

.sentence-text {
  color: var(--text-primary);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 卡片操作区域样式 */
.card-actions {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-primary);
  border-top: 1px solid var(--border-primary);
}

.card-actions .el-button {
  flex: 1;
  height: 36px;
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-base);
  border: 1px solid var(--border-primary);
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: none;
  transition: all var(--transition-fast);
}

.card-actions .el-button:hover {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
  box-shadow: none;
}

.card-actions .el-button--primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.card-actions .el-button--primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.card-actions .el-button--success {
  background: var(--success-color);
  border-color: var(--success-color);
  color: white;
}

.card-actions .el-button--success:hover {
  background: var(--success-dark);
  border-color: var(--success-dark);
}

.card-actions .el-button--warning {
  background: var(--warning-color);
  border-color: var(--warning-color);
  color: white;
}

.card-actions .el-button--warning:hover {
  background: var(--warning-dark);
  border-color: var(--warning-dark);
}

.card-actions .el-button:disabled {
  background: var(--bg-tertiary);
  border-color: var(--border-primary);
  color: var(--text-tertiary);
  box-shadow: none;
}
</style>