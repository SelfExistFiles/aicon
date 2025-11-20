import api from './api'

/**
 * 段落管理服务
 * 简化版 - 仅包含Content Studio需要的方法
 */
export const paragraphsService = {
    /**
     * 获取章节的段落列表
     * @param {string} chapterId 章节ID
     * @returns {Promise<Object>}
     */
    async getParagraphs(chapterId) {
        return await api.get(`/paragraphs/chapters/${chapterId}/paragraphs`)
    },

    /**
     * 批量更新段落
     * @param {string} chapterId 章节ID
     * @param {Object} data 包含paragraphs数组的数据对象
     * @returns {Promise<Object>}
     */
    async batchUpdateParagraphs(chapterId, data) {
        const response = await api.put(`/paragraphs/chapters/${chapterId}/paragraphs/batch`, data)
        return response.data
    }
}

export default paragraphsService
