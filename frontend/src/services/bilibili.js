/**
 * Bilibili发布服务
 */

import { get, post, del, put } from './api'

export const bilibiliService = {
    /**
     * 二维码登录
     */
    async loginByQrcode() {
        return await post('/bilibili/login/qrcode')
    },

    /**
     * 发布视频到B站
     */
    async publishVideo(publishData) {
        return await post('/bilibili/publish', publishData)
    },

    /**
     * 获取发布任务状态
     */
    async getTaskStatus(taskId) {
        return await get(`/bilibili/tasks/${taskId}`)
    },

    /**
     * 获取发布任务列表
     */
    async getTasks(params = {}) {
        return await get('/bilibili/tasks', { params })
    },

    /**
     * 获取B站分区选项
     */
    async getTidOptions() {
        return await get('/bilibili/tid-options')
    },

    /**
     * 获取B站账号列表
     */
    async getAccounts() {
        return await get('/bilibili/accounts')
    },

    /**
     * 获取账号登录状态
     */
    async getAccountStatus() {
        return await get('/bilibili/accounts/status')
    },

    /**
     * 删除B站账号
     */
    async deleteAccount(accountId) {
        return await del(`/bilibili/accounts/${accountId}`)
    },

    /**
     * 获取可发布的视频列表
     */
    async getPublishableVideos(params = {}) {
        return await get('/bilibili/publishable-videos', { params })
    },

    /**
     * 创建账号
     */
    async createAccount(data) {
        return await post('/bilibili/accounts/create', data, {
            params: { account_name: data.account_name }
        })
    },

    /**
     * 检查账号登录状态
     */
    async checkAccountLogin(accountId) {
        return await post(`/bilibili/accounts/${accountId}/check-login`)
    },

    /**
     * 设置默认账号
     */
    async setDefaultAccount(accountId) {
        return await put(`/bilibili/accounts/${accountId}/set-default`)
    }
}

export default bilibiliService
