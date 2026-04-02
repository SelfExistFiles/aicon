<template>
  <div class="main-layout">
    <!-- 侧边栏导航 -->
    <AppSidebar
      :collapsed="sidebarCollapsed"
      @toggle="toggleSidebar"
    />

    <!-- 主内容区 -->
    <div class="main-container" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <!-- 顶部导航栏 - 类似PageNavigation的设计 -->
      <header class="app-header">
        <div class="header-content">
          <!-- 左侧：面包屑导航 -->
          <div class="header-left">
            <nav class="breadcrumb-nav" aria-label="面包屑导航" v-if="breadcrumbs.length > 0">
              <ol class="breadcrumb-list">
                <li
                  v-for="(item, index) in breadcrumbs"
                  :key="index"
                  class="breadcrumb-item"
                  :class="{ 'is-current': index === breadcrumbs.length - 1 }"
                >
                  <router-link
                    v-if="index < breadcrumbs.length - 1 && item.path"
                    :to="item.path"
                    class="breadcrumb-link"
                  >
                    <el-icon v-if="item.icon" class="breadcrumb-icon">
                      <component :is="item.icon" />
                    </el-icon>
                    <span class="breadcrumb-text">{{ item.title }}</span>
                  </router-link>

                  <span v-else class="breadcrumb-current">
                    <el-icon v-if="item.icon" class="breadcrumb-icon">
                      <component :is="item.icon" />
                    </el-icon>
                    <span class="breadcrumb-text">{{ item.title }}</span>
                  </span>

                  <span v-if="index < breadcrumbs.length - 1" class="breadcrumb-separator">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                    </svg>
                  </span>
                </li>
              </ol>
            </nav>
          </div>

          <!-- 右侧：操作区域 -->
          <div class="header-right">
            <!-- 页面特定的操作区域 -->
            <div v-if="headerActions.length > 0" class="header-actions">
              <el-button
                v-for="action in headerActions"
                :key="action.text"
                :type="action.type || 'default'"
                @click="action.action"
              >
                <el-icon v-if="action.icon">
                  <component :is="action.icon" />
                </el-icon>
                {{ action.text }}
              </el-button>
            </div>

            <!-- 用户信息 -->
            <div class="user-section">
              <el-dropdown @command="handleUserAction" trigger="click">
                <div class="user-info">
                  <el-avatar :size="36" :src="user?.avatar_url" class="user-avatar">
                    <el-icon><User /></el-icon>
                  </el-avatar>
                  <div class="user-details">
                    <span class="username">{{ user?.display_name || user?.username }}</span>
                    <span class="user-status">在线</span>
                  </div>
                  <el-icon class="expand-icon">
                    <ArrowDown />
                  </el-icon>
                </div>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="settings">
                      <el-icon><Setting /></el-icon>
                      <span>系统设置</span>
                    </el-dropdown-item>
                    <el-dropdown-item divided command="logout">
                      <el-icon><SwitchButton /></el-icon>
                      <span>退出登录</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="main-content">
        <div class="content-wrapper">
          <router-view v-slot="{ Component, route }">
            <transition name="fade" mode="out-in">
              <component :is="Component" :key="route.path" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Setting, SwitchButton, ArrowDown, House, Folder, Document, Share } from '@element-plus/icons-vue'
import AppSidebar from './AppSidebar.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 响应式数据
const sidebarCollapsed = ref(false)

// 计算属性
const user = computed(() => authStore.user)

// 注入页面提供的header actions
const headerActions = inject('headerActions', [])

// 面包屑导航
const breadcrumbs = computed(() => {
  const crumbs = []

  // 添加首页
  if (route.path !== '/dashboard') {
    crumbs.push({ title: '首页', path: '/dashboard', icon: House })
  }

  // 根据路由生成面包屑
  const routeMap = {
    '/dashboard': { title: '控制台', icon: House },
    '/projects': { title: '项目管理', icon: Folder },
    '/canvas': { title: '无限画布', icon: Share },
    '/generation': { title: '视频生成', icon: Document },
    '/publish': { title: '内容发布', icon: Document },
    '/settings': { title: '系统设置', icon: Setting }
  }

  const currentRoute = Object.keys(routeMap).find(key => route.path.startsWith(key))
  if (currentRoute) {
    const routeInfo = routeMap[currentRoute]
    crumbs.push({
      title: routeInfo.title,
      path: currentRoute === route.path ? null : currentRoute,
      icon: routeInfo.icon
    })

    // 如果是项目详情页
    if (route.path.startsWith('/projects/') && route.params.id) {
      crumbs.push({ title: '项目详情', path: null })
    }
  }

  return crumbs
})

// 方法
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar-collapsed', sidebarCollapsed.value.toString())
}

const handleUserAction = (command) => {
  switch (command) {
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      handleLogout()
      break
  }
}

const handleLogout = async () => {
  try {
    await authStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } catch (error) {
    console.error('退出登录失败:', error)
    ElMessage.error('退出登录失败')
  }
}

// 组件挂载时恢复侧边栏状态
import { onMounted } from 'vue'
onMounted(() => {
  const savedState = localStorage.getItem('sidebar-collapsed')
  if (savedState) {
    sidebarCollapsed.value = savedState === 'true'
  }
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  background-color: var(--bg-primary);
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px;
  transition: margin-left var(--transition-base);
  height: 100vh;
}

.main-container.sidebar-collapsed {
  margin-left: 64px;
}

/* 应用头部 */
.app-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  position: sticky;
  top: 0;
  z-index: 100;
  height: 72px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-lg) var(--space-xl);
  height: 100%;
}

.header-left {
  flex: 1;
  min-width: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

/* 面包屑样式 - 复用PageNavigation的优秀设计 */
.breadcrumb-nav {
  max-width: 100%;
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  font-size: var(--text-sm);
}

.breadcrumb-link {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-base);
  font-weight: 500;
}

.breadcrumb-link:hover {
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.08);
  transform: translateY(-1px);
}

.breadcrumb-current {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  color: var(--text-primary);
  font-weight: 600;
}

.breadcrumb-icon {
  font-size: 14px;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.breadcrumb-item:not(.is-current) .breadcrumb-icon {
  color: var(--text-tertiary);
}

.breadcrumb-item.is-current .breadcrumb-icon {
  color: var(--primary-color);
}

.breadcrumb-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.breadcrumb-separator {
  display: flex;
  align-items: center;
  margin: 0 var(--space-xs);
  color: var(--text-tertiary);
  opacity: 0.6;
  transition: opacity var(--transition-base);
}

.breadcrumb-separator:hover {
  opacity: 1;
}

/* 用户信息区域 */
.user-section {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);
  position: relative;
}

.user-info:hover {
  background: rgba(99, 102, 241, 0.05);
}

.user-avatar {
  box-shadow: var(--shadow-sm);
  border: 2px solid var(--bg-primary);
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.username {
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.user-status {
  font-size: var(--text-xs);
  color: var(--success-color);
  font-weight: 500;
}

.user-status::before {
  content: '●';
  margin-right: 2px;
  font-size: 8px;
}

.expand-icon {
  font-size: 14px;
  color: var(--text-secondary);
  transition: transform var(--transition-base);
  margin-left: var(--space-xs);
}

.user-info:hover .expand-icon {
  color: var(--primary-color);
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-wrapper {
  flex: 1;
  padding: var(--space-lg);
  overflow-y: auto;
  background-color: var(--bg-primary);
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 下拉菜单样式 */
.el-dropdown-menu {
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
  border-radius: var(--radius-lg);
  padding: var(--space-xs);
  min-width: 160px;
}

.el-dropdown-menu .el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  margin: var(--space-xs) 0;
  transition: all var(--transition-base);
  font-weight: 500;
}

.el-dropdown-menu .el-dropdown-menu__item:hover {
  background: rgba(99, 102, 241, 0.05);
  color: var(--primary-color);
  transform: translateX(2px);
}

.el-dropdown-menu .el-dropdown-menu__item .el-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.el-dropdown-menu .el-dropdown-menu__item.is-divided {
  border-top: 1px solid var(--border-primary);
  margin-top: var(--space-sm);
  padding-top: var(--space-sm);
  color: var(--danger-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-container {
    margin-left: 0;
  }

  .main-container.sidebar-collapsed {
    margin-left: 0;
  }

  .header-content {
    padding: var(--space-md);
  }

  .header-right {
    gap: var(--space-md);
  }

  .header-actions {
    gap: var(--space-sm);
  }

  .content-wrapper {
    padding: var(--space-md);
  }

  .username {
    display: none;
  }

  .breadcrumb-text {
    max-width: 80px;
  }
}

@media (max-width: 480px) {
  .header-content {
    padding: var(--space-sm) var(--space-md);
  }

  .breadcrumb-text {
    max-width: 60px;
  }

  .header-actions :deep(.el-input) {
    max-width: 150px;
  }

  .header-actions :deep(.el-select) {
    max-width: 100px;
  }
}

/* 深色主题 */
@media (prefers-color-scheme: dark) {
  .main-layout {
    background-color: var(--bg-dark);
  }

  .app-header {
    background: var(--bg-dark);
    border-bottom-color: var(--border-primary);
  }

  .content-wrapper {
    background-color: var(--bg-dark);
  }

  .breadcrumb-link:hover {
    background: rgba(99, 102, 241, 0.12);
  }
}

/* 无障碍支持 */
.breadcrumb-link:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--primary-color);
  position: relative;
  z-index: 10;
}

.breadcrumb-link:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: var(--radius-md);
}
</style>
