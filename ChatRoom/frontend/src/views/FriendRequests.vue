<template>
  <div class="friend-requests-container">
    <el-container>
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" icon="Back" @click="goBack">返回</el-button>
        </div>
        
        <div class="tabs">
          <el-tabs v-model="activeTab" type="border-card">
            <el-tab-pane name="pending" label="待处理">
              <div class="request-item" v-for="request in pendingRequests" :key="request.id">
                <div class="request-info">
                  <el-avatar :icon="User" />
                  <div class="request-details">
                    <div class="request-sender">{{ request.username }}</div>
                    <div class="request-message" v-if="request.message">
                      附言: {{ request.message }}
                    </div>
                    <div class="request-time">
                      {{ formatTime(request.created_at) }}
                    </div>
                  </div>
                </div>
                <div class="request-actions">
                  <el-button
                    type="success"
                    size="small"
                    @click="respondRequest(request.id, true)"
                  >
                    同意
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    @click="respondRequest(request.id, false)"
                  >
                    拒绝
                  </el-button>
                </div>
              </div>
            </el-tab-pane>
            
            <el-tab-pane name="sent" label="已发送">
              <div class="request-item" v-for="request in sentRequests" :key="request.id">
                <div class="request-info">
                  <el-avatar :icon="User" />
                  <div class="request-details">
                    <div class="request-receiver">{{ request.username }}</div>
                    <div class="request-message" v-if="request.message">
                      附言: {{ request.message }}
                    </div>
                    <div class="request-status" :class="request.status">
                      {{ getStatusText(request.status) }}
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
            
            <el-tab-pane name="history" label="历史记录">
              <div class="request-item" v-for="request in historyRequests" :key="request.id">
                <div class="request-info">
                  <el-avatar :icon="User" />
                  <div class="request-details">
                    <div class="request-other">{{ request.from_user_id === authStore.user.id ? request.username : '我' }}</div>
                    <div class="request-message" v-if="request.message">
                      附言: {{ request.message }}
                    </div>
                    <div class="request-status" :class="request.status">
                      {{ getStatusText(request.status) }}
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-aside>
      
      <el-main class="main-content">
        <div class="content-header">
          <h2>好友申请</h2>
          <el-badge :value="pendingRequests.length" :hidden="pendingRequests.length === 0" type="danger">
            <el-button type="primary" size="small" @click="activeTab = 'pending'">
              待处理 ({{ pendingRequests.length }})
            </el-button>
          </el-badge>
        </div>
        
        <div class="empty-state" v-if="pendingRequests.length === 0 && activeTab === 'pending'">
          <el-empty description="暂无待处理的好友申请" />
        </div>
        
        <div class="empty-state" v-if="sentRequests.length === 0 && activeTab === 'sent'">
          <el-empty description="暂无已发送的好友申请" />
        </div>
        
        <div class="empty-state" v-if="historyRequests.length === 0 && activeTab === 'history'">
          <el-empty description="暂无历史记录" />
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('pending')
const pendingRequests = ref([])
const sentRequests = ref([])
const historyRequests = ref([])

const goBack = () => {
  router.push('/')
}

const loadRequests = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/friend-requests`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )

    if (response.ok) {
      const requests = await response.json()

      pendingRequests.value = requests.filter(r => r.status === 'pending' && r.to_user_id === authStore.user.id)
      sentRequests.value = requests.filter(r => r.status === 'pending' && r.from_user_id === authStore.user.id)
      historyRequests.value = requests.filter(r => r.status === 'accepted' || r.status === 'rejected')
    } else {
      console.error('加载好友申请失败:', response.statusText)
    }
  } catch (err) {
    console.error('加载好友申请失败:', err)
  }
}

const respondRequest = async (requestId, accept) => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/friend-requests/${requestId}/respond`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.token}`
        },
        body: JSON.stringify({ accept })
      }
    )
    
    if (response.ok) {
      ElMessage.success(accept ? '已同意好友申请' : '已拒绝好友申请')
      await loadRequests()
    } else {
      const errorData = await response.json()
      ElMessage.error(errorData.detail || '操作失败')
    }
  } catch (err) {
    console.error('操作失败:', err)
    ElMessage.error('操作失败')
  }
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待处理',
    accepted: '已同意',
    rejected: '已拒绝',
    sent: '已发送'
  }
  return statusMap[status] || status
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadRequests()
})
</script>

<style scoped>
.friend-requests-container {
  height: 100vh;
  background: #f5f7fa;
}

.friend-requests-container :deep(.el-container) {
  height: 100%;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.tabs {
  flex: 1;
  overflow: hidden;
}

.request-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 8px;
  background: #f5f7fa;
  transition: background-color 0.2s;
}

.request-item:hover {
  background: #ecf5ff;
}

.request-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.request-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.request-sender,
.request-receiver,
.request-other {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.request-message {
  font-size: 12px;
  color: #606266;
}

.request-time {
  font-size: 12px;
  color: #909399;
}

.request-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.request-status.pending {
  background: #fef0f0;
  color: #f56c6c;
}

.request-status.accepted {
  background: #f0f9ff;
  color: #67c23a;
}

.request-status.rejected {
  background: #fef0f0;
  color: #f56c6c;
}

.request-status.sent {
  background: #fef0f0;
  color: #909399;
}

.request-actions {
  display: flex;
  gap: 8px;
}

.main-content {
  display: flex;
  flex-direction: column;
  background: #fff;
  margin: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.content-header {
  padding: 20px 30px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.empty-state {
  padding: 50px 20px;
  text-align: center;
}
</style>
