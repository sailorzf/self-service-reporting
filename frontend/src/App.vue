<template>
  <el-container style="height: 100vh;">
    <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center;">
      <h2 style="margin: 0;">自助报表系统</h2>
      <el-menu mode="horizontal" :ellipsis="false" style="margin-left: 40px;">
        <router-link to="/tables" custom v-slot="{ navigate }">
          <el-menu-item @click="navigate">数据表管理</el-menu-item>
        </router-link>
        <router-link to="/import" custom v-slot="{ navigate }">
          <el-menu-item @click="navigate">数据导入</el-menu-item>
        </router-link>
        <router-link to="/reports" custom v-slot="{ navigate }">
          <el-menu-item @click="navigate">报表中心</el-menu-item>
        </router-link>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>
