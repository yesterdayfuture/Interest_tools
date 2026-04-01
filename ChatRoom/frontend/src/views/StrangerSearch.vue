<template>
  <div class="stranger-search-container">
    <el-container>
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" icon="Back" @click="goBack">返回</el-button>
        </div>
        
        <div class="search-box">
          <el-input
            v-model="searchUsername"
            placeholder="搜索用户名"
            prefix-icon="Search"
            @change="handleSearch"
            clearable
          >
            <el-button
              slot="append"
              icon="Search"
              @click="handleSearch"
            />
          </el-input>
        </div>
        
        <div class="user-list">
          <div 
            v-for="user in searchResults" 
            :key="user.id" 
            class="user-item"
          >
            <el-avatar :icon="User" />
            <div class="user-info">
              <div class="user-name">{{ user.username }}</div>
              <div class="user-nickname" v-if="user.nickname">{{ user.nickname }}</div>
              <div class="user-status" v-if="isFriend(user.id)" style="color: #67c23a; font-size: 12px;">已是好友</div>
            </div>
            <el-button 
              v-if="!isFriend(user.id)"
              type="primary" 
              size="small"
              :loading="sendingRequest[user.id]"
              @click="sendFriendRequest(user.id)"
            >
              添加好友
            </el-button>
            <el-tag v-else type="success" size="small">好友</el-tag>
          </div>
        </div>
      </el-aside>
      
      <el-main class="main-content">
        <div class="content-header">
          <h2>搜索用户</h2>
          <p>输入用户名搜索陌生人</p>
        </div>
        
        <div class="search-results" v-if="searchResults.length > 0">
          <h4>搜索结果 ({{ searchResults.length }})</h4>
          <div 
            v-for="user in searchResults" 
            :key="user.id" 
            class="user-card"
          >
            <el-avatar :icon="User" size="large" />
            <div class="user-details">
              <div class="user-name">{{ user.username }}</div>
              <div class="user-nickname" v-if="user.nickname">{{ user.nickname }}</div>
              <div class="user-joined">
                加入时间：{{ formatDate(user.created_at) }}
              </div>
              <div class="user-status" v-if="isFriend(user.id)" style="color: #67c23a; font-size: 12px; margin-top: 5px;">已是好友</div>
            </div>
            <el-button 
              v-if="!isFriend(user.id)"
              type="primary" 
              size="small"
              :loading="sendingRequest[user.id]"
              @click="sendFriendRequest(user.id)"
            >
              添加好友
            </el-button>
            <el-tag v-else type="success" size="small">好友</el-tag>
          </div>
        </div>
        
        <div class="empty-state" v-else-if="searched">
          <el-empty description="未找到用户" />
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, Back, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const searchUsername = ref('')
const searchResults = ref([])
const sendingRequest = ref({})
const searched = ref(false)
const friends = ref([])

const goBack = () => {
  router.push('/')
}

const loadFriends = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/friends`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    if (response.ok) {
      friends.value = await response.json()
    }
  } catch (err) {
    console.error('加载好友列表失败:', err)
  }
}

const isFriend = (userId) => {
  return friends.value.some(f => f.id === userId)
}

const handleSearch = async () => {
  if (!searchUsername.value.trim()) {
    searchResults.value = []
    searched.value = false
    return
  }
  
  searched.value = true
  
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/search?username=${searchUsername.value}`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )

    if (response.ok) {
      const data = await response.json()
      searchResults.value = data.users || []
    } else {
      console.error('搜索失败:', response.statusText)
    }
  } catch (err) {
    console.error('搜索用户失败:', err)
  }
}

const sendFriendRequest = async (userId) => {
  if (isFriend(userId)) {
    ElMessage.warning('已经是好友了')
    return
  }
  
  sendingRequest.value[userId] = true

  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/friend-requests`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          to_user_id: userId,
          message: '你好，我想添加你为好友'
        })
      }
    )
    
    if (response.ok) {
      ElMessage.success('好友申请已发送')
      sendingRequest.value[userId] = false
    } else {
      const errorData = await response.json()
      ElMessage.error(errorData.detail || '发送申请失败')
      sendingRequest.value[userId] = false
    }
  } catch (err) {
    console.error('发送好友申请失败:', err)
    ElMessage.error('发送申请失败')
    sendingRequest.value[userId] = false
  }
}

const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadFriends()
})
</script>

<style scoped>
.stranger-search-container {
  height: 100vh;
  background: #f5f7fa;
}

.stranger-search-container :deep(.el-container) {
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

.search-box {
  padding: 20px;
}

.user-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.user-item:hover {
  background-color: #f5f7fa;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.user-nickname {
  font-size: 12px;
  color: #909399;
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
  padding: 30px;
  border-bottom: 1px solid #e4e7ed;
}

.content-header h2 {
  margin: 0 0 10px;
  font-size: 24px;
  color: #303133;
}

.content-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.search-results {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.search-results h4 {
  margin-bottom: 20px;
  font-size: 16px;
  color: #606266;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  margin-bottom: 15px;
  border-radius: 12px;
  background: #f5f7fa;
  transition: background-color 0.2s;
}

.user-card:hover {
  background: #ecf5ff;
}

.user-details {
  flex: 1;
}

.user-name {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 5px;
}

.user-nickname {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.user-joined {
  font-size: 12px;
  color: #909399;
}
</style>
