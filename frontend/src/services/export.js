/**
 * 导出服务 - 处理章节导出相关功能
 */

import { post, get } from './api'

export const exportService = {
    /**
     * 导出章节为剪映格式
     * @param {string} chapterId - 章节ID
     * @returns {Promise} 导出结果
     */
    async exportToJianYing(chapterId) {
        return await post(`/export/jianying/${chapterId}`)
    },

    /**
     * 下载导出的文件
     * @param {string} downloadUrl - 下载URL
     * @param {string} filename - 文件名
     */
    downloadFile(downloadUrl, filename) {
        // 创建隐藏的a标签触发下载
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = filename
        link.style.display = 'none'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }
}

export default exportService
