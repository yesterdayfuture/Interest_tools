import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Chat from '../views/Chat.vue'
import GroupChat from '../views/GroupChat.vue'
import StrangerSearch from '../views/StrangerSearch.vue'
import FriendRequests from '../views/FriendRequests.vue'
import CreateGroup from '../views/CreateGroup.vue'
import GroupInvitations from '../views/GroupInvitations.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/',
    name: 'Chat',
    component: Chat,
    meta: { requiresAuth: true }
  },
  {
    path: '/group/:groupId',
    name: 'GroupChat',
    component: GroupChat,
    meta: { requiresAuth: true }
  },
  {
    path: '/strangers',
    name: 'StrangerSearch',
    component: StrangerSearch,
    meta: { requiresAuth: true }
  },
  {
    path: '/friend-requests',
    name: 'FriendRequests',
    component: FriendRequests,
    meta: { requiresAuth: true }
  },
  {
    path: '/create-group',
    name: 'CreateGroup',
    component: CreateGroup,
    meta: { requiresAuth: true }
  },
  {
    path: '/group-invitations',
    name: 'GroupInvitations',
    component: GroupInvitations,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && token) {
    next('/')
  } else {
    next()
  }
})

export default router
