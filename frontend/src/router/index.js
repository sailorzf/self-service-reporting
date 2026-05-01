import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/reports' },
  { path: '/tables', component: () => import('../views/DataTableManage.vue') },
  { path: '/import', component: () => import('../views/ImportView.vue') },
  { path: '/reports', component: () => import('../views/ReportListView.vue') },
  { path: '/reports/new', component: () => import('../views/ReportDesigner.vue') },
  { path: '/share/:token', component: () => import('../views/ShareView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
