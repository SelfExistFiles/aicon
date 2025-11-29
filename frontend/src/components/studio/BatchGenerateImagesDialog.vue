<template>
  <el-dialog
    v-model="dialogVisible"
    title="批量生成图片"
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
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          生成
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
  sentencesIds: {
    type: Array,
    required: true
  },
  apiKeys: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:visible', 'generate-success'])

const dialogVisible = ref(props.visible)
const selectedApiKey = ref('')
const generating = ref(false)

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
}

// 处理批量生成图片
const handleGenerate = async () => {
  if (!selectedApiKey.value) {
    ElMessage.warning('请选择API Key')
    return
  }
  
  generating.value = true
  try {
    const response = await api.post('/image/generate-images', {
      sentences_ids: props.sentencesIds,
      api_key_id: selectedApiKey.value
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      updateDialogVisible(false)
      emit('generate-success')
      resetForm()
    }
  } catch (error) {
    console.error('批量生成图片失败', error)
    ElMessage.error('批量生成图片失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
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