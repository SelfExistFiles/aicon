<template>
  <el-dialog
    v-model="dialogVisible"
    title="重新生成提示词"
    width="500px"
  >
    <el-form :inline="false" class="dialog-form">
      <el-form-item label="API Key" style="width: 100%">
        <el-select v-model="selectedApiKey" placeholder="选择API Key" style="width: 100%">
          <el-option
            v-for="key in apiKeys"
            :key="key.id"
            :label="`${key.name} (${key.provider})`"
            :value="key.id"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="风格" style="width: 100%">
        <el-select v-model="selectedStyle" placeholder="选择风格" style="width: 100%">
          <el-option label="电影质感 (Cinematic)" value="cinematic" />
          <el-option label="二次元 (Anime)" value="anime" />
          <el-option label="插画 (Illustration)" value="illustration" />
          <el-option label="水墨 (Ink)" value="ink" />
        </el-select>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="regenerating" @click="handleRegenerate">
          重新生成
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, defineProps, defineEmits, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/services/api'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  sentenceIds: {
    type: Array,
    required: true
  },
  apiKeys: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:visible', 'regenerate-success'])

const dialogVisible = ref(props.visible)
const selectedApiKey = ref('')
const selectedStyle = ref('cinematic')
const regenerating = ref(false)

// 监听visible prop变化，更新dialogVisible
watch(() => props.visible, (newValue) => {
  dialogVisible.value = newValue
})

// 更新visible状态并通知父组件
const updateDialogVisible = (newValue) => {
  dialogVisible.value = newValue
  emit('update:visible', newValue)
}

// 处理取消
const handleCancel = () => {
  updateDialogVisible(false)
  resetForm()
}

// 重置表单
const resetForm = () => {
  selectedApiKey.value = ''
  selectedStyle.value = 'cinematic'
}

// 处理重新生成
const handleRegenerate = async () => {
  if (!selectedApiKey.value || props.sentenceIds.length === 0) {
    ElMessage.warning('请选择API Key和要重新生成的句子')
    return
  }
  
  regenerating.value = true
  try {
    const response = await api.post('/prompt/generate-prompts-ids', {
      api_key_id: selectedApiKey.value,
      sentence_ids: props.sentenceIds,
      style: selectedStyle.value
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      updateDialogVisible(false)
      emit('regenerate-success')
      resetForm()
    }
  } catch (error) {
    console.error('重新生成失败', error)
    ElMessage.error('重新生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    regenerating.value = false
  }
}
</script>

<style scoped>
.dialog-form {
  margin-bottom: 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}
</style>