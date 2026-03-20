<template>
  <div>
    <svg-icon icon-class="question" @click="goto" />
  </div>
</template>

<script>
export default {
  name: 'RuoYiDoc',
  methods: {
    goto() {
      this.$message.info('系统帮助请通过菜单功能或联系管理员获取，未配置外部文档链接。')
    }
  }
}
</script>
