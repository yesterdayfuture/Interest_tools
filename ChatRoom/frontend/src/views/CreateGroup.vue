<template>
  <!-- 创建群组页面容器 -->
  <div class="create-group-container">
    <el-container>
      <!-- 左侧边栏：显示已创建的群组列表 -->
      <el-aside width="300px" class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" icon="Back" @click="goBack">返回</el-button>
        </div>
        
        <div class="group-list">
          <h4>我创建的群组</h4>
          <div 
            v-for="group in myGroups" 
            :key="group.id" 
            class="group-item"
            @click="goToGroup(group.id)"
          >
            <el-avatar :icon="ChatDotRound" />
            <div class="group-info">
              <div class="group-name">{{ group.name }}</div>
              <div class="group-member-count">{{ group.member_count || 0 }}人</div>
            </div>
          </div>
        </div>
      </el-aside>
      
      <!-- 主内容区域：创建群组表单 -->
      <el-main class="main-content">
        <div class="content-header">
          <h2>创建新群组</h2>
        </div>
        
        <el-card class="create-card">
          <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
            <el-form-item label="群组名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入群组名称" />
            </el-form-item>
            
            <el-form-item label="群组描述" prop="description">
              <el-input
                v-model="form.description"
                type="textarea"
                :autosize="{ minRows: 3, maxRows: 6 }"
                placeholder="请输入群组描述（可选）"
              />
            </el-form-item>
            
            <el-form-item label="邀请好友">
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
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleCreate">
                创建群组
              </el-button>
              <el-button @click="goBack">取消</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
/**
 * 创建群组页面组件
 * 功能：
 * - 创建新群组
 * - 创建时邀请好友进群
 * - 查看已创建的群组列表
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, ChatDotRound, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const formRef = ref()
// 是否正在创建
const loading = ref(false)
// 选中的好友 ID 列表
const selectedFriends = ref([])
// 我创建的群组列表
const myGroups = ref([])
// 好友列表
const friends = ref([])

// 表单数据
const form = reactive({
  name: '',
  description: ''
})

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入群组名称', trigger: 'blur' },
    { min: 2, max: 50, message: '群组名称长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

/**
 * 返回上一页
 */
const goBack = () => {
  router.push('/')
}

/**
 * 跳转到群组聊天页面
 * @param {number} groupId - 群组 ID
 */
const goToGroup = (groupId) => {
  router.push(`/group/${groupId}`)
}

/**
 * 加载我创建的群组列表
 * 从后端 API 获取当前用户创建的群组
 */
const loadGroups = async () => {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups`,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`
        }
      }
    )
    
    if (response.ok) {
      myGroups.value = await response.json()
    }
  } catch (err) {
    console.error('加载群组列表失败:', err)
  }
}

/**
 * 加载好友列表
 * 用于创建群组时邀请好友
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

const handleCreate = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          name: form.name,
          description: form.description
        })
      }
    )
    
    if (response.ok) {
      const group = await response.json()
      ElMessage.success('群组创建成功')
      
      if (selectedFriends.value.length > 0) {
        await inviteFriends(group.id)
      }
      
      setTimeout(() => {
        router.push(`/group/${group.id}`)
      }, 1000)
    } else {
      const errorData = await response.json()
      ElMessage.error(errorData.detail || '创建群组失败')
      loading.value = false
    }
  } catch (err) {
    console.error('创建群组失败:', err)
    ElMessage.error('创建群组失败')
    loading.value = false
  }
}

const inviteFriends = async (groupId) => {
  try {
    for (const friendId of selectedFriends.value) {
      await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/groups/${groupId}/invitations`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authStore.token}`
          },
          body: JSON.stringify({
            to_user_id: friendId,
            message: `邀请你加入群组: ${form.name}`
          })
        }
      )
    }
  } catch (err) {
    console.error('邀请好友失败:', err)
  }
}

onMounted(() => {
  loadGroups()
  loadFriends()
})
</script>

<style scoped>
.create-group-container {
  height: 100vh;
  background: #f5f7fa;
}

.create-group-container :deep(.el-container) {
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

.group-list {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.group-list h4 {
  margin-bottom: 15px;
  font-size: 14px;
  color: #909399;
}

.group-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.group-item:hover {
  background-color: #ecf5ff;
}

.group-info {
  flex: 1;
}

.group-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.group-member-count {
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
  padding: 20px 30px;
  border-bottom: 1px solid #e4e7ed;
}

.content-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.create-card {
  margin: 20px;
  padding: 30px;
}
</style>
