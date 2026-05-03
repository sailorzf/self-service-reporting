import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/reports' },
  { path: '/tables', component: () => import('../views/DataTableManage.vue') },
  { path: '/import', component: () => import('../views/ImportView.vue') },
  { path: '/import/new', component: () => import('../views/ImportForm.vue') },
  { path: '/import/:id', component: () => import('../views/ImportDetailView.vue') },
  { path: '/reports', component: () => import('../views/ReportListView.vue') },
  { path: '/reports/new', component: () => import('../views/ReportDesigner.vue') },
  { path: '/reports/:id', component: () => import('../views/ReportDesigner.vue') },
  { path: '/share/:token', component: () => import('../views/ShareView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
