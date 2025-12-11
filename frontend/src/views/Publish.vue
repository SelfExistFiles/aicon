<template>
  <div class="publish-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <el-icon class="title-icon"><Promotion /></el-icon>
          Bilibili发布管理
        </h1>
        <p class="page-description">将生成的视频发布到Bilibili平台</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="handleLogin" :loading="loginLoading">
          <el-icon><User /></el-icon>
          {{ accountStatus.logged_in ? '重新登录' : 'B站登录' }}
        </el-button>
      </div>
    </div>

    <!-- 账号状态卡片 -->
    <el-card v-if="accountStatus.logged_in" class="account-status-card" shadow="never">
      <div class="account-info">
        <el-icon class="status-icon success"><CircleCheck /></el-icon>
        <div class="info-content">
          <div class="account-name">{{ accountStatus.account_name }}</div>
          <div class="login-time">最后登录: {{ formatTime(accountStatus.last_login_at) }}</div>
        </div>
      </div>
    </el-card>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="publish-tabs">
      <!-- 可发布视频列表 -->
      <el-tab-pane label="可发布视频" name="videos">
        <div v-loading="videosLoading" class="videos-container">
          <el-empty v-if="!videosLoading && videos.length === 0" description="暂无可发布的视频">
            <el-button type="primary" @click="$router.push('/video-tasks')">
              前往视频任务
            </el-button>
          </el-empty>

          <div v-else class="video-grid">
            <div v-for="video in videos" :key="video.id" class="video-card">
              <div class="video-preview">
                <video :src="video.video_url" controls class="video-player"></video>
              </div>
              <div class="video-info">
                <h3 class="video-title">{{ video.project_title }} - {{ video.chapter_title }}</h3>
                <div class="video-meta">
                  <span class="meta-item">
                    <el-icon><Clock /></el-icon>
                    {{ formatDuration(video.video_duration) }}
                  </span>
                  <span class="meta-item">
                    <el-icon><Calendar /></el-icon>
                    {{ formatDate(video.created_at) }}
                  </span>
                </div>
                <el-button type="primary" @click="handlePublish(video)" class="publish-btn">
                  <el-icon><Upload /></el-icon>
                  发布到B站
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 发布任务列表 -->
      <el-tab-pane label="发布任务" name="tasks">
        <div v-loading="tasksLoading" class="tasks-container">
          <el-empty v-if="!tasksLoading && tasks.length === 0" description="暂无发布任务" />

          <div v-else class="task-list">
            <div v-for="task in tasks" :key="task.id" class="task-item">
              <div class="task-header">
                <h4 class="task-title">{{ task.title }}</h4>
                <el-tag :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
              </div>
              
              <el-progress 
                v-if="task.status === 'uploading'" 
                :percentage="task.progress" 
                :status="task.progress === 100 ? 'success' : undefined"
              />

              <div class="task-info">
                <span class="info-item">平台: {{ task.platform }}</span>
                <span class="info-item">创建时间: {{ formatDate(task.created_at) }}</span>
                <span v-if="task.bvid" class="info-item">
                  BV号: 
                  <a :href="`https://www.bilibili.com/video/${task.bvid}`" target="_blank" class="bv-link">
                    {{ task.bvid }}
                  </a>
                </span>
              </div>

              <el-alert v-if="task.error_message" :title="task.error_message" type="error" :closable="false" />
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 发布对话框 -->
    <el-dialog
      v-model="publishDialogVisible"
      title="发布到Bilibili"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="publishForm" :rules="publishRules" ref="publishFormRef" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="publishForm.title" maxlength="80" show-word-limit placeholder="请输入视频标题" />
        </el-form-item>

        <el-form-item label="简介" prop="desc">
          <el-input
            v-model="publishForm.desc"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请输入视频简介"
          />
        </el-form-item>

        <el-form-item label="分区" prop="tid">
          <el-select v-model="publishForm.tid" placeholder="请选择分区" style="width: 100%">
            <el-option
              v-for="option in tidOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="标签" prop="tag">
          <el-input v-model="publishForm.tag" placeholder="多个标签用逗号分隔,最多10个" />
        </el-form-item>

        <el-form-item label="类型" prop="copyright">
          <el-radio-group v-model="publishForm.copyright">
            <el-radio :label="1">原创</el-radio>
            <el-radio :label="2">转载</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="publishForm.copyright === 2" label="转载源" prop="source">
          <el-input v-model="publishForm.source" placeholder="请输入转载来源" />
        </el-form-item>

        <el-form-item label="上传线路" prop="upload_line">
          <el-select v-model="publishForm.upload_line" style="width: 100%">
            <el-option label="七牛云 (kodo)" value="kodo" />
            <el-option label="百度云 (bda2)" value="bda2" />
            <el-option label="腾讯云 (qn)" value="qn" />
            <el-option label="网宿 (ws)" value="ws" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="publishDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPublish" :loading="publishing">
          确认发布
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, User, CircleCheck, Clock, Calendar, Upload } from '@element-plus/icons-vue'
import bilibiliService from '@/services/bilibili'

const activeTab = ref('videos')
const videos = ref([])
const tasks = ref([])
const videosLoading = ref(false)
const tasksLoading = ref(false)
const loginLoading = ref(false)
const publishing = ref(false)
const publishDialogVisible = ref(false)
const publishFormRef = ref(null)
const tidOptions = ref([])
const currentVideo = ref(null)

const accountStatus = ref({
  logged_in: false,
  account_name: '',
  last_login_at: null,
  message: ''
})

const publishForm = reactive({
  video_task_id: '',
  title: '',
  desc: '',
  tid: 171,
  tag: '',
  copyright: 1,
  source: '',
  upload_line: 'kodo',
  upload_limit: 3
})

const publishRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  tid: [{ required: true, message: '请选择分区', trigger: 'change' }]
}

// 加载账号状态
const loadAccountStatus = async () => {
  try {
    const res = await bilibiliService.getAccountStatus()
    accountStatus.value = res
  } catch (error) {
    console.error('获取账号状态失败:', error)
  }
}

// 加载可发布视频
const loadVideos = async () => {
  videosLoading.value = true
  try {
    const res = await bilibiliService.getPublishableVideos()
    videos.value = res.videos || []
  } catch (error) {
    ElMessage.error('加载视频列表失败')
  } finally {
    videosLoading.value = false
  }
}

// 加载发布任务
const loadTasks = async () => {
  tasksLoading.value = true
  try {
    const res = await bilibiliService.getTasks()
    tasks.value = res || []
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    tasksLoading.value = false
  }
}

// 加载分区选项
const loadTidOptions = async () => {
  try {
    tidOptions.value = await bilibiliService.getTidOptions()
  } catch (error) {
    console.error('加载分区选项失败:', error)
  }
}

// 登录B站
const handleLogin = async () => {
  loginLoading.value = true
  try {
    const res = await bilibiliService.loginByQrcode()
    if (res.success) {
      ElMessage.success('登录成功')
      await loadAccountStatus()
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (error) {
    ElMessage.error('登录失败')
  } finally {
    loginLoading.value = false
  }
}

// 打开发布对话框
const handlePublish = (video) => {
  if (!accountStatus.value.logged_in) {
    ElMessage.warning('请先登录B站账号')
    return
  }

  currentVideo.value = video
  publishForm.video_task_id = video.id
  publishForm.title = `${video.project_title} - ${video.chapter_title}`
  publishForm.desc = ''
  publishDialogVisible.value = true
}

// 提交发布
const submitPublish = async () => {
  const valid = await publishFormRef.value.validate().catch(() => false)
  if (!valid) return

  publishing.value = true
  try {
    const res = await bilibiliService.publishVideo(publishForm)
    if (res.success) {
      ElMessage.success('发布任务已提交')
      publishDialogVisible.value = false
      activeTab.value = 'tasks'
      await loadTasks()
    } else {
      ElMessage.error(res.message || '发布失败')
    }
  } catch (error) {
    ElMessage.error('发布失败')
  } finally {
    publishing.value = false
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// 格式化日期
const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 获取状态类型
const getStatusType = (status) => {
  const typeMap = {
    pending: 'info',
    uploading: 'warning',
    published: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    pending: '等待中',
    uploading: '上传中',
    published: '已发布',
    failed: '失败'
  }
  return textMap[status] || status
}

onMounted(async () => {
  await Promise.all([
    loadAccountStatus(),
    loadVideos(),
    loadTasks(),
    loadTidOptions()
  ])
})
</script>

<style scoped>
.publish-management {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.title-icon {
  font-size: 32px;
  color: var(--primary-color);
}

.page-description {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.account-status-card {
  margin-bottom: 24px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-icon {
  font-size: 24px;
}

.status-icon.success {
  color: var(--el-color-success);
}

.info-content {
  flex: 1;
}

.account-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.login-time {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.publish-tabs {
  background: white;
  border-radius: 8px;
  padding: 16px;
}

.videos-container,
.tasks-container {
  min-height: 400px;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

.video-card {
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
}

.video-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.video-preview {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
}

.video-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-info {
  padding: 16px;
}

.video-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.publish-btn {
  width: 100%;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-item {
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 16px;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.task-info {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.bv-link {
  color: var(--primary-color);
  text-decoration: none;
}

.bv-link:hover {
  text-decoration: underline;
}
</style>