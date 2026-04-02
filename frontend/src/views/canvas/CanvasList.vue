<template>
  <section class="canvas-list-page">
    <div class="hero-card">
      <div>
        <p class="eyebrow">无限画布</p>
        <h1>无限画布</h1>
      </div>
      <el-button type="primary" size="large" @click="handleCreate" :loading="creating">
        新建画布
      </el-button>
    </div>

    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="list-header">
          <div>
            <h2>我的画布</h2>
            <span>{{ documents.length }} 个文档</span>
          </div>
          <el-button text @click="loadDocuments" :loading="loading">刷新</el-button>
        </div>
      </template>

      <el-empty v-if="!loading && documents.length === 0" description="还没有画布，先创建一个。" />

      <div v-else class="canvas-grid">
        <article
          v-for="document in documents"
          :key="document.id"
          class="canvas-card"
          @click="router.push(`/canvas/${document.id}`)"
        >
          <div class="canvas-card__header">
            <div>
              <h3>{{ document.title }}</h3>
              <p>{{ formatDate(document.updated_at) }}</p>
            </div>
            <el-dropdown trigger="click" @command="(command) => handleMenu(command, document)">
              <button class="menu-button" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="canvas-card__body">
            <div class="preview-grid">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>{{ document.description || '自由节点图、生成面板和历史记录都保存在这张画布里。' }}</p>
          </div>
        </article>
      </div>
    </el-card>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled } from '@element-plus/icons-vue'
import { canvasService } from '@/services/canvas'

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const documents = ref([])

const formatDate = (value) => {
  if (!value) return '刚刚更新'
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await canvasService.list({ page: 1, size: 100 })
    documents.value = response.documents || []
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  creating.value = true
  try {
    const response = await canvasService.create({ title: `新画布 ${documents.value.length + 1}` })
    ElMessage.success('画布已创建')
    await loadDocuments()
    router.push(`/canvas/${response.id}`)
  } finally {
    creating.value = false
  }
}

const handleRename = async (document) => {
  const { value } = await ElMessageBox.prompt('输入新的画布名称', '重命名', {
    inputValue: document.title,
    confirmButtonText: '保存',
    cancelButtonText: '取消'
  })
  await canvasService.update(document.id, { title: value })
  ElMessage.success('画布已重命名')
  await loadDocuments()
}

const handleDelete = async (document) => {
  await ElMessageBox.confirm(`确认删除「${document.title}」？`, '删除画布', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  })
  await canvasService.remove(document.id)
  ElMessage.success('画布已删除')
  await loadDocuments()
}

const handleMenu = async (command, document) => {
  if (command === 'rename') {
    await handleRename(document)
    return
  }
  if (command === 'delete') {
    await handleDelete(document)
  }
}

onMounted(loadDocuments)
</script>

<style scoped>
.canvas-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 28px 32px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(32, 33, 36, 0.12), transparent 34%),
    linear-gradient(135deg, #f8f6f1 0%, #ffffff 58%, #f2f5f7 100%);
  border: 1px solid rgba(32, 33, 36, 0.08);
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.hero-card h1 {
  margin-top: 8px;
  font-size: 34px;
}

.list-card {
  border-radius: 24px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h2 {
  font-size: 20px;
}

.list-header span {
  color: var(--text-tertiary);
}

.canvas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.canvas-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(32, 33, 36, 0.08);
  background: white;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.canvas-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 30px rgba(32, 33, 36, 0.08);
}

.canvas-card__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.canvas-card__header h3 {
  font-size: 18px;
}

.canvas-card__header p {
  margin-top: 6px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.menu-button {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-secondary);
}

.menu-button:hover {
  background: var(--bg-secondary);
}

.canvas-card__body {
  margin-top: 18px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.preview-grid span {
  height: 56px;
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(32, 33, 36, 0.12), rgba(32, 33, 36, 0.04)),
    #f2f5f7;
}

.canvas-card__body p {
  color: var(--text-secondary);
  line-height: 1.6;
  font-size: 14px;
}
</style>
