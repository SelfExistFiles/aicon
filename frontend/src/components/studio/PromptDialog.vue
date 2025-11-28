<template>
  <!-- 查看/编辑提示词对话框 -->
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="dialogTitle"
    width="600px"
  >
    <el-form :inline="false" class="dialog-form">
      <el-form-item label="句子内容" style="width: 100%">
        <el-input
          v-model="localSentence.content"
          type="textarea"
          :rows="2"
          readonly
          placeholder="句子内容"
        />
      </el-form-item>
      
      <el-form-item label="图片 Prompt" style="width: 100%">
        <el-input
          v-model="localSentence.image_prompt"
          type="textarea"
          :rows="6"
          placeholder="提示词内容"
          :disabled="!isEditing"
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button v-if="isEditing" type="primary" @click="handleSave">
          保存
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/services/api'

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  sentence: {
    type: Object,
    default: () => ({})
  },
  isEditing: {
    type: Boolean,
    default: false
  },
  dialogTitle: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['update:visible', 'update:sentence', 'save'])

// Local state
const localSentence = ref({ ...props.sentence })

// Watch for prop changes
watch(() => props.sentence, (newSentence) => {
  localSentence.value = { ...newSentence }
}, { deep: true })

watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    localSentence.value = { ...props.sentence }
  }
})

// Handle close dialog
const handleClose = () => {
  emit('update:visible', false)
}

// Handle save prompt
const handleSave = async () => {
  try {
    const response = await api.put(`/sentences/${localSentence.value.id}/prompt`, {
      prompt: localSentence.value.image_prompt
    })
    
    if (response) {
      ElMessage.success('提示词保存成功')
      emit('save', localSentence.value)
      emit('update:visible', false)
      emit('update:sentence', localSentence.value)
    }
  } catch (error) {
    console.error('保存提示词失败', error)
    ElMessage.error('保存提示词失败: ' + (error.response?.data?.detail || error.message))
  }
}
</script>

<style scoped>
.dialog-form {
  max-width: 100%;
}

.dialog-form .el-form-item {
  margin-bottom: 24px;
}
</style>