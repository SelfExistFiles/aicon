import api from './api'

/**
 * 章节管理服务
 * 简化版 - 仅包含Content Studio需要的方法
 */
export const chaptersService = {
  /**
   * 获取章节列表
   * @param {string} projectId 项目ID
   * @param {Object} params 查询参数
   * @returns {Promise<Object>}
   */
  async getChapters(projectId, params = {}) {
    return await api.get('/chapters/', {
      params: {
        project_id: projectId,
        ...params
      }
    })
  }
}

export default chaptersService