<template>
  <div class="account-management">
    <div class="page-header">
      <h1>Bilibili账号管理</h1>
      <p class="page-description">管理您的B站账号,用于视频发布</p>
    </div>

    <!-- 账号列表 -->
    <el-card class="accounts-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的账号</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
        </div>
      </template>

      <el-empty v-if="accounts.length === 0" description="暂无账号,请添加">
        <el-button type="primary" @click="showAddDialog">添加第一个账号</el-button>
      </el-empty>

      <el-table v-else :data="accounts" v-loading="loading">
        <el-table-column prop="account_name" label="账号名称" min-width="150" />
        
        <el-table-column label="登录状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.cookie_valid" type="success">
              <el-icon><CircleCheck /></el-icon>
              已登录
            </el-tag>
            <el-tag v-else type="danger">
              <el-icon><CircleClose /></el-icon>
              未登录
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="默认账号" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="primary">默认</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="last_login_at" label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_login_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="!row.is_default && row.cookie_valid" 
              size="small" 
              @click="setDefault(row.id)"
            >
              设为默认
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteAccount(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加账号对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加B站账号"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-steps :active="currentStep" align-center finish-status="success">
        <el-step title="输入账号名称" />
        <el-step title="执行登录命令" />
        <el-step title="验证登录状态" />
      </el-steps>

      <div class="step-content">
        <!-- 步骤1: 输入账号名称 -->
        <div v-if="currentStep === 0" class="step-1">
          <el-form :model="addForm" label-width="100px">
            <el-form-item label="账号名称">
              <el-input 
                v-model="addForm.account_name" 
                placeholder="例如: 我的B站主号"
                maxlength="50"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2: 显示登录命令 -->
        <div v-if="currentStep === 1" class="step-2">
          <el-alert
            title="请按照以下步骤在服务器终端操作"
            type="warning"
            :closable="false"
            show-icon
          />

          <div class="command-section">
            <h4>步骤 1: 执行登录命令</h4>
            <div class="command-box">
              <div class="command-header">
                <span>登录命令</span>
                <el-button size="small" @click="copyCommand(loginCommand)">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
              <pre class="command-text">{{ loginCommand }}</pre>
            </div>
            <p class="command-tip">执行后选择"扫码登录",使用B站APP扫描二维码</p>
          </div>

          <div class="command-section">
            <h4>步骤 2: 移动cookie文件</h4>
            <div class="command-box">
              <div class="command-header">
                <span>移动命令</span>
                <el-button size="small" @click="copyCommand(postCommand)">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
              <pre class="command-text">{{ postCommand }}</pre>
            </div>
            <p class="command-tip">登录成功后,执行此命令将cookie文件移动到指定位置</p>
          </div>

          <el-alert
            title="操作提示"
            type="info"
            :closable="false"
          >
            <ul class="tips-list">
              <li>登录命令会显示二维码,请使用B站APP扫描</li>
              <li>登录成功后,cookie会保存在cookies.json</li>
              <li>执行移动命令将cookie移到正确位置</li>
              <li>完成后点击"下一步"验证登录状态</li>
            </ul>
          </el-alert>
        </div>

        <!-- 步骤3: 验证登录 -->
        <div v-if="currentStep === 2" class="step-3">
          <div v-if="!loginChecked" class="check-login">
            <el-icon class="check-icon"><Loading /></el-icon>
            <p>正在验证登录状态...</p>
          </div>

          <el-result
            v-else-if="loginSuccess"
            icon="success"
            title="登录成功!"
            sub-title="您的B站账号已成功添加"
          >
            <template #extra>
              <el-button type="primary" @click="finishAdd">完成</el-button>
            </template>
          </el-result>

          <el-result
            v-else
            icon="error"
            title="未检测到登录"
            sub-title="请确认已在服务器终端完成扫码登录"
          >
            <template #extra>
              <el-button @click="currentStep = 1">返回上一步</el-button>
              <el-button type="primary" @click="checkLogin">重新检查</el-button>
            </template>
          </el-result>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button 
            v-if="currentStep > 0 && currentStep < 2" 
            @click="prevStep"
          >
            上一步
          </el-button>
          <el-button 
            v-if="currentStep < 2" 
            type="primary" 
            @click="nextStep"
            :disabled="!canProceed"
            :loading="creating"
          >
            {{ currentStep === 0 ? '创建账号' : '下一步' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, CircleCheck, CircleClose, CopyDocument, Loading } from '@element-plus/icons-vue'
import bilibiliService from '@/services/bilibili'

const accounts = ref([])
const loading = ref(false)
const addDialogVisible = ref(false)
const currentStep = ref(0)
const creating = ref(false)
const loginChecked = ref(false)
const loginSuccess = ref(false)
const currentAccountId = ref('')
const loginCommand = ref('')
const postCommand = ref('')

const addForm = ref({
  account_name: ''
})

// 是否可以继续下一步
const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return addForm.value.account_name.trim().length > 0
  }
  return true
})

// 加载账号列表
const loadAccounts = async () => {
  loading.value = true
  try {
    accounts.value = await bilibiliService.getAccounts()
  } catch (error) {
    ElMessage.error('加载账号列表失败')
  } finally {
    loading.value = false
  }
}

// 显示添加对话框
const showAddDialog = () => {
  addForm.value.account_name = ''
  currentStep.value = 0
  loginCommand.value = ''
  currentAccountId.value = ''
  loginChecked.value = false
  loginSuccess.value = false
  addDialogVisible.value = true
}

// 下一步
const nextStep = async () => {
  if (currentStep.value === 0) {
    // 创建账号
    await createAccount()
  } else if (currentStep.value === 1) {
    // 检查登录
    currentStep.value = 2
    await checkLogin()
  }
}

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 创建账号
const createAccount = async () => {
  creating.value = true
  try {
    const res = await bilibiliService.createAccount({
      account_name: addForm.value.account_name
    })
    
    if (res.success) {
      currentAccountId.value = res.account_id
      loginCommand.value = res.command
      postCommand.value = res.post_command
      currentStep.value = 1
      ElMessage.success('账号创建成功,请按步骤执行命令')
    }
  } catch (error) {
    ElMessage.error('创建账号失败')
  } finally {
    creating.value = false
  }
}

// 检查登录状态
const checkLogin = async () => {
  loginChecked.value = false
  try {
    const res = await bilibiliService.checkAccountLogin(currentAccountId.value)
    loginChecked.value = true
    loginSuccess.value = res.logged_in
    
    if (res.logged_in) {
      ElMessage.success('登录成功!')
    } else {
      ElMessage.warning('未检测到登录,请确认已完成扫码')
    }
  } catch (error) {
    loginChecked.value = true
    loginSuccess.value = false
    ElMessage.error('检查登录状态失败')
  }
}

// 完成添加
const finishAdd = () => {
  addDialogVisible.value = false
  loadAccounts()
}

// 复制命令
const copyCommand = (command) => {
  navigator.clipboard.writeText(command)
  ElMessage.success('命令已复制到剪贴板')
}

// 设置默认账号
const setDefault = async (accountId) => {
  try {
    await bilibiliService.setDefaultAccount(accountId)
    ElMessage.success('已设置为默认账号')
    loadAccounts()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

// 删除账号
const deleteAccount = async (account) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号"${account.account_name}"吗?`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await bilibiliService.deleteAccount(account.id)
    ElMessage.success('删除成功')
    loadAccounts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.account-management {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-description {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.accounts-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-content {
  margin: 30px 0;
  min-height: 300px;
}

.command-section {
  margin: 24px 0;
}

.command-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.command-tip {
  margin: 8px 0 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.command-box {
  margin: 20px 0;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  overflow: hidden;
}

.command-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.command-text {
  margin: 0;
  padding: 16px;
  background: #f5f7fa;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #2c3e50;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.tips-list {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.tips-list li {
  margin: 4px 0;
  color: var(--text-secondary);
}

.check-login {
  text-align: center;
  padding: 60px 0;
}

.check-icon {
  font-size: 48px;
  color: var(--primary-color);
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.check-login p {
  margin-top: 16px;
  font-size: 16px;
  color: var(--text-secondary);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
