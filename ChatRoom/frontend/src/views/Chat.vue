<template>
  <div class="chat-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <h3>聊天室</h3>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="goToStrangers">
              <el-icon><Search /></el-icon>
            </el-button>
            <el-button type="warning" size="small" @click="goToFriendRequests">
              <el-icon><Bell /></el-icon>
            </el-button>
            <el-button type="info" size="small" @click="goToGroupInvitations">
              <el-icon><ChatDotRound /></el-icon>
            </el-button>
            <el-button type="success" size="small" @click="goToCreateGroup">
              <el-icon><Plus /></el-icon>
            </el-button>
            <el-button type="danger" size="small" @click="handleLogout">
              <Close /> 退出登录
            </el-button>
          </div>
        </div>
        
        <el-tabs v-model="activeTab" class="tabs">
          <el-tab-pane name="friends" label="好友">
            <div class="search-box">
              <el-input
                v-model="friendSearch"
                placeholder="搜索好友"
                prefix-icon="Search"
                size="small"
              />
            </div>
            <div class="friend-list">
              <div 
                v-for="friend in filteredFriends" 
                :key="friend.id" 
                class="friend-item"
                :class="{ active: activeFriend === friend.id }"
                @click="selectFriend(friend.id)"
              >
                <div class="friend-info">
                  <el-avatar :icon="User" />
                  <div class="friend-name">{{ friend.username }}</div>
                </div>
                <div class="friend-status">
                  <span class="status-dot" :class="{ online: friend.is_online }"></span>
                </div>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane name="groups" label="群组">
            <div class="group-list">
              <div 
                v-for="group in groups" 
                :key="group.id" 
                class="group-item"
                :class="{ active: activeGroup === group.id }"
                @click="selectGroup(group.id)"
              >
                <div class="group-info">
                  <el-avatar :icon="ChatDotRound" />
                  <div class="group-name">{{ group.name }}</div>
                </div>
                <div class="group-member-count">
                  {{ group.member_count || 0 }}人
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-aside>
      
      <!-- 主聊天区域 -->
      <el-main class="main-content">
        <div class="chat-header">
          <h3>
            <el-avatar v-if="activeTab === 'friends' && activeFriend" :icon="User" />
            <el-avatar v-if="activeTab === 'groups' && activeGroup" :icon="ChatDotRound" />
            <span v-if="activeTab === 'friends' && activeFriend">
              {{ getFriendName(activeFriend) }}
            </span>
            <span v-if="activeTab === 'groups' && activeGroup">
              {{ getGroupName(activeGroup) }}
            </span>
          </h3>
        </div>
        
        <div class="chat-messages" ref="chatMessagesRef" @scroll="handleScroll">
          <div 
            v-for="message in chatMessages" 
            :key="message.id" 
            class="message"
            :class="{ 'message-sent': currentUser && message.sender_id === currentUser.id }"
          >
            <div class="message-content">
              <div class="message-header">
                <span class="message-sender">
                  {{ currentUser && message.sender_id === currentUser.id ? '我' : getSenderName(message.sender_id) }}
                </span>
                <span class="message-time">
                  {{ formatTime(message.created_at) }}
                </span>
              </div>
              <div class="message-text">{{ message.content }}</div>
            </div>
          </div>
        </div>
        
        <div class="chat-input">
          <el-input
            v-model="messageInput"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="输入消息..."
            @keydown.enter.prevent="sendMessage"
          />
          <el-button 
            type="primary" 
            :disabled="!messageInput.trim()"
            @click="sendMessage"
          >
            发送
          </el-button>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElNotification } from 'element-plus'
import {
  User,
  ChatDotRound,
  Search,
  Bell,
  Plus,
  Close
} from '@element-plus/icons-vue'

const router = useRouter()
const chatMessagesRef = ref()

const activeTab = ref('friends')
const activeFriend = ref(null)
const activeGroup = ref(null)
const messageInput = ref('')
const friendSearch = ref('')
const friends = ref([])
const groups = ref([])
const chatMessages = ref([])
const currentUser = ref(null)

const authStore = useAuthStore()

const filteredFriends = computed(() => {
  if (!friendSearch.value) return friends.value
  return friends.value.filter(f => 
    f.username.toLowerCase().includes(friendSearch.value.toLowerCase())
  )
})

const loadFriends = async () => {
  try {
    const friendsResponse = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/friends`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    const friendsData = await friendsResponse.json()
    friends.value = friendsData
    
    const onlineResponse = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/online`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    const onlineData = await onlineResponse.json()
    friends.value = friends.value.map(f => {
      const onlineUser = onlineData.find(u => u.id === f.id)
      return { ...f, is_online: !!onlineUser }
    })
  } catch (err) {
    console.error('加载好友列表失败:', err)
  }
}

const getFriendName = (friendId) => {
  const friend = friends.value.find(f => f.id === friendId)
  return friend ? friend.username : ''
}

const getGroupName = (groupId) => {
  const group = groups.value.find(g => g.id === groupId)
  return group ? group.name : ''
}

const getSenderName = (senderId) => {
  if (senderId === currentUser.value?.id) return '我'
  const friend = friends.value.find(f => f.id === senderId)
  return friend ? friend.username : `用户${senderId}`
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const selectFriend = (friendId) => {
  activeFriend.value = friendId
  activeGroup.value = null
  loadMessages(null, friendId)
}

const selectGroup = (groupId) => {
  activeGroup.value = groupId
  activeFriend.value = null
  loadMessages(groupId, null)
}

const sendMessage = async () => {
  if (!messageInput.value.trim()) return
  
  const content = messageInput.value.trim()
  messageInput.value = ''
  
  try {
    if (activeTab.value === 'friends' && activeFriend.value) {
      await socket.send(JSON.stringify({
        type: 'personal',
        receiver_id: activeFriend.value,
        content: content
      }))
    } else if (activeTab.value === 'groups' && activeGroup.value) {
      await socket.send(JSON.stringify({
        type: 'group',
        group_id: activeGroup.value,
        content: content
      }))
    }
  } catch (err) {
    console.error('发送消息失败:', err)
  }
}

const loadMessages = async (groupId, receiverId) => {
  try {
    let url
    if (groupId) {
      url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/messages/history/group?group_id=${groupId}`
    } else if (receiverId) {
      url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/messages/history/personal?other_user_id=${receiverId}`
    } else {
      chatMessages.value = []
      return
    }
    
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      chatMessages.value = data.messages || []
      await nextTick()
      scrollToBottom()
    } else {
      chatMessages.value = []
    }
  } catch (err) {
    console.error('加载消息失败:', err)
    chatMessages.value = []
  }
}

const scrollToBottom = () => {
  if (chatMessagesRef.value) {
    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  }
}

const handleScroll = () => {
  // 可以添加滚动加载更多消息的逻辑
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const goToStrangers = () => {
  router.push('/strangers')
}

const goToFriendRequests = () => {
  router.push('/friend-requests')
}

const goToGroupInvitations = () => {
  router.push('/group-invitations')
}

const goToCreateGroup = () => {
  router.push('/create-group')
}

// WebSocket 连接
let socket
const connectWebSocket = () => {
  const token = authStore.token
  const wsHost = import.meta.env.VITE_API_HOST || 'ws://localhost:8000/ws'
  const socketUrl = `${wsHost}/${token}`
  
  socket = new WebSocket(socketUrl)
  
  socket.onopen = () => {
    console.log('WebSocket 连接成功')
  }
  
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data)
    handleWebSocketMessage(message)
  }
  
  socket.onclose = () => {
    console.log('WebSocket 连接关闭')
    setTimeout(connectWebSocket, 3000) // 3秒后重连
  }
  
  socket.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }
}

const handleWebSocketMessage = (message) => {
  if (message.type === 'personal_message') {
    chatMessages.value.push(message)
    scrollToBottom()
  } else if (message.type === 'group_message') {
    chatMessages.value.push(message)
    scrollToBottom()
  } else if (message.type === 'pong') {
    // 心跳响应
  } else if (message.type === 'friend_request') {
    // 好友申请通知
    const displayName = message.from_nickname || message.from_username
    ElNotification({
      title: '新的好友申请',
      message: `${displayName} 想和你成为好友`,
      type: 'info',
      duration: 5000
    })
  } else if (message.type === 'friend_response') {
    // 好友申请响应通知
    const displayName = message.to_nickname || message.to_username
    const responseText = message.accept ? '接受了你的好友申请' : '拒绝了你的好友申请'
    ElNotification({
      title: '好友申请结果',
      message: `${displayName} ${responseText}`,
      type: message.accept ? 'success' : 'warning',
      duration: 5000
    })
    if (message.accept) {
      loadFriends()
    }
  } else if (message.type === 'group_invitation') {
    // 群组邀请通知
    const displayName = message.from_nickname || message.from_username
    ElNotification({
      title: '群组邀请',
      message: `${displayName} 邀请你加入群组 "${message.group_name}"`,
      type: 'info',
      duration: 5000,
      onClick: () => {
        // 点击通知跳转到群组邀请页面
        router.push('/group-invitations')
      }
    })
  }
}

onMounted(async () => {
  if (!authStore.user && authStore.token) {
    try {
      await authStore.getUserInfo()
    } catch (err) {
      console.error('获取用户信息失败:', err)
      router.push('/login')
      return
    }
  }
  
  currentUser.value = authStore.user
  
  await loadFriends()
  
  try {
    const groupsResponse = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    const groupsData = await groupsResponse.json()
    console.log('[DEBUG] 群组列表数据:', groupsData)
    groups.value = groupsData
  } catch (err) {
    console.error('加载群组列表失败:', err)
  }
  
  connectWebSocket()
})

onUnmounted(() => {
  if (socket) {
    socket.close()
  }
})
</script>

<style scoped>
.chat-container {
  height: 100vh;
  background: #f5f7fa;
}

.chat-container :deep(.el-container) {
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

.header-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.tabs {
  flex: 1;
  overflow: hidden;
}

.search-box {
  padding: 10px;
}

.friend-list,
.group-list {
  padding: 10px;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.friend-item,
.group-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.friend-item:hover,
.group-item:hover {
  background-color: #f5f7fa;
}

.friend-item.active,
.group-item.active {
  background-color: #ecf5ff;
}

.friend-info,
.group-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.friend-name,
.group-name {
  font-size: 14px;
  color: #606266;
}

.friend-status {
  display: flex;
  align-items: center;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #909399;
}

.status-dot.online {
  background-color: #67c23a;
}

.group-member-count {
  font-size: 12px;
  color: #909399;
}

.main-content {
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.chat-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}

.message {
  margin-bottom: 16px;
  display: flex;
}

.message-sent {
  justify-content: flex-end;
}

.message-content {
  max-width: 60%;
  padding: 12px 16px;
  border-radius: 8px;
  background: #ecf5ff;
}

.message-sent .message-content {
  background: #67c23a;
  color: #fff;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}

.message-sender {
  font-weight: 500;
}

.message-time {
  color: #909399;
}

.message-text {
  word-wrap: break-word;
  white-space: pre-wrap;
}

.chat-input {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 10px;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
}
</style>
