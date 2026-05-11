import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import UserLoginPage from '@/pages/user/UserLoginPage.vue'
import UserRegisterPage from '@/pages/user/UserRegisterPage.vue'
import UserManagePage from '@/pages/admin/UserManagePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: '主页',
      component: HomePage,
    },
    {
      path: '/topic',
      name: '热点选题',
      component: () => import('@/pages/TopicPage.vue'),
    },
    {
      path: '/create',
      name: '创作文章',
      component: () => import('@/pages/article/ArticleCreatePage.vue'),
    },
    {
      path: '/article/list',
      name: '文章列表',
      component: () => import('@/pages/article/ArticleListPage.vue'),
    },
    {
      path: '/publish',
      name: '发布中心',
      component: () => import('@/pages/PublishPage.vue'),
    },
    {
      path: '/knowledge',
      name: '知识库',
      component: () => import('@/pages/KnowledgePage.vue'),
    },
    {
      path: '/article/:taskId',
      name: '文章详情',
      component: () => import('@/pages/article/ArticleDetailPage.vue'),
    },
    {
      path: '/user/profile',
      name: '个人设置',
      component: () => import('@/pages/user/UserProfilePage.vue'),
    },
    {
      path: '/user/login',
      name: '用户登录',
      component: UserLoginPage,
    },
    {
      path: '/user/register',
      name: '用户注册',
      component: UserRegisterPage,
    },
    {
      path: '/admin/userManage',
      name: '用户管理',
      component: UserManagePage,
    },
    {
      path: '/admin/statistics',
      name: '数据分析',
      component: () => import('@/pages/admin/StatisticsPage.vue'),
    },
    {
      path: '/vip',
      name: '会员购买',
      component: () => import('@/pages/VipPage.vue'),
    },
  ],
})

export default router
