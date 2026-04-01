import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function login(username, password) {
    loading.value = true
    error.value = null
    
    try {
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)
      
      const response = await axios.post(`${API_URL}/auth/token`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
      
      token.value = response.data.access_token
      localStorage.setItem('token', response.data.access_token)
      
      const userInfo = await getUserInfo()
      user.value = userInfo
      
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || '登录失败'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function register(username, password, nickname) {
    loading.value = true
    error.value = null
    
    try {
      const response = await axios.post(`${API_URL}/auth/register`, {
        username,
        password,
        nickname
      })
      
      return { success: true, user: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || '注册失败'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function getUserInfo() {
    try {
      const response = await axios.get(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token.value}`
        }
      })
      return response.data
    } catch (err) {
      logout()
      throw err
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    getUserInfo
  }
})
