<template>
  <div class="group-chat-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" icon="Back" @click="goBack">返回</el-button>
        </div>
        
        <div class="group-info">
          <el-avatar :icon="ChatDotRound" size="large" />
          <h2>{{ currentGroup?.name }}</h2>
          <p v-if="currentGroup?.description">{{ currentGroup.description }}</p>
        </div>
        
        <div class="group-actions">
          <el-button 
            type="primary" 
            size="small" 
            @click="showInviteDialog = true"
            icon="Plus"
          >
            邀请好友
          </el-button>
        </div>
        
        <div class="group-members">
          <h4>群成员 ({{ groupMembers.length }})</h4>
          <div 
            v-for="member in groupMembers" 
            :key="member.id" 
            class="member-item"
          >
            <el-avatar :icon="User" />
            <div class="member-info">
              <div class="member-name">{{ member.username }}</div>
              <div class="member-role">{{ member.role }}</div>
            </div>
          </div>
        </div>
      </el-aside>
      
      <!-- 群组聊天区域 -->
      <el-main class="main-content">
        <div class="chat-header">
          <h3>
            <el-avatar :icon="ChatDotRound" />
            <span>{{ currentGroup?.name }}</span>
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
    
    <!-- 邀请好友进群对话框 -->
    <el-dialog
      v-model="showInviteDialog"
      title="邀请好友进群"
      width="500px"
    >
      <el-select
        v-model="selectedFriends"
        multiple
        filterable
        placeholder="选择要邀请的好友"
        style="width: 100%"
      >
        <el-option
          v-for="friend in friends"
          :key="friend.id"
          :label="friend.username"
          :value="friend.id"
        >
          <span style="float: left">{{ friend.username }}</span>
          <span style="float: right; color: #909399; font-size: 13px">
            {{ friend.nickname || '无昵称' }}
          </span>
        </el-option>
      </el-select>
      <template #footer>
        <el-button @click="showInviteDialog = false">取消</el-button>
        <el-button type="primary" @click="handleInvite" :loading="inviting">邀请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 群组聊天页面组件
 * 功能：
 * - 显示群组信息和群成员
 * - 发送和接收群聊消息
 * - 邀请好友进群
 * - 查看群聊历史记录
 */
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, ChatDotRound, Back, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const chatMessagesRef = ref()

// 群组 ID，从路由参数中获取
const groupId = ref(parseInt(route.params.groupId))
// 当前群组信息
const currentGroup = ref(null)
// 群成员列表
const groupMembers = ref([])
// 消息输入框内容
const messageInput = ref('')
// 聊天消息列表
const chatMessages = ref([])
// 当前登录用户信息
const currentUser = ref(null)
// 好友列表（用于邀请）
const friends = ref([])
// 是否显示邀请对话框
const showInviteDialog = ref(false)
// 是否正在邀请
const inviting = ref(false)
// 选中的好友 ID 列表
const selectedFriends = ref([])

const authStore = useAuthStore()

/**
 * 获取消息发送者名称
 * @param {number} senderId - 发送者 ID
 * @returns {string} 发送者名称
 */
const getSenderName = (senderId) => {
  if (senderId === currentUser.value?.id) return '我'
  const member = groupMembers.value.find(m => m.id === senderId)
  return member ? member.username : `用户${senderId}`
}

/**
 * 格式化时间戳为 HH:mm 格式
 * @param {string} timestamp - 时间戳
 * @returns {string} 格式化后的时间
 */
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/**
 * 发送群聊消息
 * 通过 WebSocket 发送消息到群组
 */
const sendMessage = async () => {
  if (!messageInput.value.trim()) return
  
  const content = messageInput.value.trim()
  messageInput.value = ''
  
  try {
    await socket.send(JSON.stringify({
      type: 'group',
      group_id: groupId.value,
      content: content
    }))
  } catch (err) {
    console.error('发送消息失败:', err)
  }
}

/**
 * 加载群组信息
 * 从后端 API 获取群组详细信息
 */
const loadGroupInfo = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/${groupId.value}`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    currentGroup.value = await response.json()
  } catch (err) {
    console.error('加载群组信息失败:', err)
  }
}

/**
 * 加载群成员列表
 * 从后端 API 获取群组所有成员信息
 */
const loadGroupMembers = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/${groupId.value}/members`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    const data = await response.json()
    console.log('[DEBUG] 群组成员数据:', data)
    groupMembers.value = data
  } catch (err) {
    console.error('加载群组成员失败:', err)
  }
}

/**
 * 加载群聊历史消息
 * 从后端 API 获取群组历史消息记录
 */
const loadMessages = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/messages/history/group?group_id=${groupId.value}`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    const data = await response.json()
    console.log('[DEBUG] 群聊消息数据:', data)
    chatMessages.value = data.messages || []
    await nextTick()
    scrollToBottom()
  } catch (err) {
    console.error('加载消息失败:', err)
  }
}

/**
 * 滚动到消息列表底部
 * 用于加载消息后自动滚动到最新消息
 */
const scrollToBottom = () => {
  if (chatMessagesRef.value) {
    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  }
}

/**
 * 处理滚动事件
 * 可以添加滚动加载更多消息的逻辑
 */
const handleScroll = () => {
  // 可以添加滚动加载更多消息的逻辑
}

/**
 * 返回上一页
 */
const goBack = () => {
  router.push('/')
}

/**
 * 加载好友列表
 * 用于邀请好友进群
 */
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

/**
 * 处理邀请好友进群
 * 向选中的好友发送群组邀请
 */
const handleInvite = async () => {
  if (selectedFriends.value.length === 0) {
    ElMessage.warning('请选择要邀请的好友')
    return
  }
  
  inviting.value = true
  
  let successCount = 0
  let failCount = 0
  const failedUsers = []
  
  try {
    // 遍历选中的好友，逐个发送邀请
    for (const friendId of selectedFriends.value) {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/${groupId.value}/invitations`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authStore.token}`
          },
          body: JSON.stringify({
            to_user_id: friendId,
            message: `邀请你加入群组：${currentGroup.value?.name}`
          })
        }
      )
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error(`邀请好友 ${friendId} 失败:`, errorData.detail)
        failCount++
        failedUsers.push(friendId)
        
        // 根据错误类型给出提示
        if (errorData.detail === 'User is already a group member') {
          console.warn(`用户 ${friendId} 已是群成员`)
        } else if (errorData.detail === 'User already has a pending invitation for this group') {
          console.warn(`用户 ${friendId} 已有待处理的邀请`)
        }
      } else {
        successCount++
      }
    }
    
    // 显示结果
    if (successCount > 0 && failCount === 0) {
      ElMessage.success('邀请已发送')
    } else if (successCount > 0 && failCount > 0) {
      ElMessage.warning(`邀请已发送，但 ${failCount} 个用户邀请失败（可能已是群成员或已有待处理邀请）`)
    } else if (failCount > 0) {
      ElMessage.warning('所有邀请都发送失败，可能这些用户已是群成员或已有待处理邀请')
    }
    
    showInviteDialog.value = false
    selectedFriends.value = []
  } catch (err) {
    console.error('邀请好友失败:', err)
    ElMessage.error('邀请发送失败')
  } finally {
    inviting.value = false
  }
}

// WebSocket 连接
/**
 * 连接 WebSocket 服务器
 * 用于实时接收群聊消息
 */
let socket
const connectWebSocket = () => {
  const token = authStore.token
  const wsHost = import.meta.env.VITE_API_HOST || 'ws://localhost:8000/ws'
  const socketUrl = `${wsHost}/${token}`
  
  socket = new WebSocket(socketUrl)
  
  /**
   * WebSocket 连接成功回调
   * 连接成功后加入群组聊天室
   */
  socket.onopen = () => {
    console.log('WebSocket 连接成功')
    socket.send(JSON.stringify({
      type: 'join_group',
      group_id: groupId.value
    }))
  }
  
  /**
   * WebSocket 接收消息回调
   * 处理接收到的群聊消息
   * @param {MessageEvent} event - WebSocket 消息事件
   */
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data)
    handleWebSocketMessage(message)
  }
  
  /**
   * WebSocket 连接关闭回调
   * 连接关闭后 3 秒自动重连
   */
  socket.onclose = () => {
    console.log('WebSocket 连接关闭')
    setTimeout(connectWebSocket, 3000)
  }
  
  /**
   * WebSocket 错误处理回调
   * @param {Error} error - WebSocket 错误对象
   */
  socket.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }
}

/**
 * 处理 WebSocket 接收到的消息
 * @param {Object} message - WebSocket 消息对象
 */
const handleWebSocketMessage = (message) => {
  if (message.type === 'group_message') {
    chatMessages.value.push(message)
    scrollToBottom()
  } else if (message.type === 'pong') {
    // 心跳响应
  }
}

/**
 * 组件挂载时的初始化操作
 * - 加载当前用户信息
 * - 加载群组信息
 * - 加载群成员列表
 * - 加载历史消息
 * - 连接 WebSocket
 */
onMounted(async () => {
  currentUser.value = authStore.user
  await loadGroupInfo()
  await loadGroupMembers()
  await loadMessages()
  await loadFriends()  // 加载好友列表用于邀请
  connectWebSocket()
})

/**
 * 组件卸载时的清理操作
 * 关闭 WebSocket 连接
 */
onUnmounted(() => {
  if (socket) {
    socket.close()
  }
})
</script>

<style scoped>
.group-chat-container {
  height: 100vh;
  background: #f5f7fa;
}

.group-chat-container :deep(.el-container) {
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

.group-info {
  padding: 30px 20px;
  text-align: center;
}

.group-info h2 {
  margin: 15px 0 10px;
  font-size: 20px;
  color: #303133;
}

.group-info p {
  color: #909399;
  font-size: 14px;
}

.group-members {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.group-members h4 {
  margin-bottom: 15px;
  font-size: 14px;
  color: #909399;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.member-item:hover {
  background-color: #f5f7fa;
}

.member-info {
  display: flex;
  flex-direction: column;
}

.member-name {
  font-size: 14px;
  color: #606266;
}

.member-role {
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
