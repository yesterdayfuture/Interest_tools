<template>
  <!-- 群组邀请页面 -->
  <div class="group-invitations-container">
    <el-container>
      <!-- 左侧边栏 -->
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" icon="Back" @click="goBack">返回</el-button>
        </div>
        
        <div class="invitations-header">
          <h3>群组邀请</h3>
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" type="danger">
            <el-button size="small" @click="loadInvitations" icon="Refresh">刷新</el-button>
          </el-badge>
        </div>
        
        <div class="invitation-tabs">
          <el-tabs v-model="activeTab" @tab-click="loadInvitations">
            <el-tab-pane label="待处理" name="pending"></el-tab-pane>
            <el-tab-pane label="已接受" name="accepted"></el-tab-pane>
            <el-tab-pane label="已拒绝" name="rejected"></el-tab-pane>
          </el-tabs>
        </div>
        
        <div class="invitation-list">
          <div 
            v-for="invitation in invitations" 
            :key="invitation.id" 
            class="invitation-item"
            :class="{ active: selectedInvitation?.id === invitation.id }"
            @click="selectInvitation(invitation)"
          >
            <el-avatar :icon="ChatDotRound" />
            <div class="invitation-info">
              <div class="group-name">{{ invitation.group_name }}</div>
              <div class="inviter-name">{{ invitation.username }} 邀请</div>
              <div class="invitation-time">{{ formatTime(invitation.created_at) }}</div>
            </div>
            <el-tag 
              v-if="invitation.status === 'pending'" 
              type="danger" 
              size="small"
            >
              待处理
            </el-tag>
            <el-tag 
              v-else-if="invitation.status === 'accepted'" 
              type="success" 
              size="small"
            >
              已接受
            </el-tag>
            <el-tag 
              v-else 
              type="info" 
              size="small"
            >
              已拒绝
            </el-tag>
          </div>
        </div>
      </el-aside>
      
      <!-- 主内容区域 -->
      <el-main class="main-content">
        <div class="content-header">
          <h2>群组邀请详情</h2>
        </div>
        
        <div class="invitation-detail" v-if="selectedInvitation">
          <el-card>
            <div class="detail-header">
              <el-avatar :icon="ChatDotRound" size="large" />
              <div class="detail-info">
                <h3>{{ selectedInvitation.group_name }}</h3>
                <p v-if="selectedInvitation.group_description">{{ selectedInvitation.group_description }}</p>
              </div>
            </div>
            
            <el-divider />
            
            <div class="detail-content">
              <div class="detail-row">
                <span class="label">邀请人：</span>
                <span class="value">{{ selectedInvitation.nickname || selectedInvitation.username }}</span>
              </div>
              <div class="detail-row">
                <span class="label">邀请消息：</span>
                <span class="value">{{ selectedInvitation.message || '无' }}</span>
              </div>
              <div class="detail-row">
                <span class="label">邀请时间：</span>
                <span class="value">{{ formatDateTime(selectedInvitation.created_at) }}</span>
              </div>
              <div class="detail-row">
                <span class="label">状态：</span>
                <el-tag 
                  v-if="selectedInvitation.status === 'pending'" 
                  type="danger"
                >
                  待处理
                </el-tag>
                <el-tag 
                  v-else-if="selectedInvitation.status === 'accepted'" 
                  type="success"
                >
                  已接受
                </el-tag>
                <el-tag 
                  v-else 
                  type="info"
                >
                  已拒绝
                </el-tag>
              </div>
            </div>
            
            <el-divider />
            
            <div class="detail-actions" v-if="selectedInvitation.status === 'pending'">
              <el-button type="success" @click="respondToInvitation(true)" :loading="responding">
                接受
              </el-button>
              <el-button type="danger" @click="respondToInvitation(false)" :loading="responding">
                拒绝
              </el-button>
            </div>
          </el-card>
        </div>
        
        <div class="empty-state" v-else>
          <el-empty description="请选择一个邀请查看详情" />
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
/**
 * 群组邀请页面组件
 * 功能：
 * - 查看收到的群组邀请
 * - 按状态筛选邀请（待处理/已接受/已拒绝）
 * - 接受或拒绝群组邀请
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ChatDotRound, Back, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// 选中的标签页
const activeTab = ref('pending')
// 邀请列表
const invitations = ref([])
// 选中的邀请
const selectedInvitation = ref(null)
// 待处理邀请数量
const pendingCount = ref(0)
// 是否正在响应
const responding = ref(false)

/**
 * 返回上一页
 */
const goBack = () => {
  router.push('/')
}

/**
 * 加载群组邀请列表
 * 根据当前标签页的状态加载
 */
const loadInvitations = async () => {
  console.log('[DEBUG] 开始加载邀请列表，status:', activeTab.value)
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/invitations/list?status=${activeTab.value}`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    
    console.log('[DEBUG] API 响应状态:', response.status)
    
    if (response.ok) {
      const data = await response.json()
      console.log('[DEBUG] 邀请数据:', data)
      invitations.value = data
      
      // 如果是待处理标签页，计算待处理数量
      if (activeTab.value === 'pending') {
        pendingCount.value = invitations.value.length
        console.log('[DEBUG] 待处理邀请数量:', pendingCount.value)
      }
    } else {
      console.error('[DEBUG] API 响应失败:', response.status)
    }
  } catch (err) {
    console.error('[DEBUG] 加载邀请列表异常:', err)
    ElMessage.error('加载邀请列表失败')
  }
}

/**
 * 选择邀请查看详情
 * @param {Object} invitation - 邀请对象
 */
const selectInvitation = (invitation) => {
  selectedInvitation.value = invitation
}

/**
 * 响应群组邀请
 * @param {boolean} accept - 是否接受
 */
const respondToInvitation = async (accept) => {
  if (!selectedInvitation.value) return
  
  responding.value = true
  
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/invitations/${selectedInvitation.value.id}/respond`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          accept: accept
        })
      }
    )
    
    if (response.ok) {
      const actionText = accept ? '接受' : '拒绝'
      ElMessage.success(`已${actionText}邀请`)
      
      // 发送通知
      ElNotification({
        title: '操作成功',
        message: `你已${actionText}加入群组 "${selectedInvitation.value.group_name}"`,
        type: accept ? 'success' : 'info',
        duration: 3000
      })
      
      // 如果接受，跳转到群组页面
      if (accept) {
        setTimeout(() => {
          router.push(`/group/${selectedInvitation.value.group_id}`)
        }, 1000)
      } else {
        // 重新加载列表
        await loadInvitations()
        selectedInvitation.value = null
      }
    } else {
      const errorData = await response.json()
      ElMessage.error(errorData.detail || '操作失败')
    }
  } catch (err) {
    console.error('响应邀请失败:', err)
    ElMessage.error('响应邀请失败')
  } finally {
    responding.value = false
  }
}

/**
 * 格式化时间为 HH:mm
 * @param {string} timestamp - 时间戳
 * @returns {string} 格式化后的时间
 */
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/**
 * 格式化日期时间
 * @param {string} timestamp - 时间戳
 * @returns {string} 格式化后的日期时间
 */
const formatDateTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

// 组件挂载时加载待处理邀请
onMounted(() => {
  loadInvitations()
})
</script>

<style scoped>
.group-invitations-container {
  height: 100vh;
  background: #f5f7fa;
}

.el-container {
  height: 100%;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e6e6e6;
}

.invitations-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
}

.invitations-header h3 {
  margin: 0;
  font-size: 18px;
}

.invitation-tabs {
  padding: 10px 20px;
  border-bottom: 1px solid #e6e6e6;
}

.invitation-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.invitation-item {
  display: flex;
  align-items: center;
  padding: 15px;
  margin-bottom: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.invitation-item:hover {
  background: #ecf5ff;
}

.invitation-item.active {
  background: #409eff;
  color: #fff;
}

.invitation-info {
  flex: 1;
  margin-left: 10px;
}

.group-name {
  font-weight: bold;
  margin-bottom: 5px;
}

.inviter-name {
  font-size: 12px;
  color: #909399;
  margin-bottom: 3px;
}

.invitation-time {
  font-size: 12px;
  color: #909399;
}

.main-content {
  background: #f5f7fa;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.content-header {
  padding: 20px;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
}

.content-header h2 {
  margin: 0;
  font-size: 20px;
}

.invitation-detail {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.detail-info {
  margin-left: 15px;
}

.detail-info h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
}

.detail-info p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.detail-content {
  padding: 10px 0;
}

.detail-row {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.detail-row .label {
  width: 80px;
  color: #909399;
  font-size: 14px;
}

.detail-row .value {
  flex: 1;
  color: #606266;
  font-size: 14px;
}

.detail-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding-top: 20px;
}

.empty-state {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
