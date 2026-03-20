import request from '@/utils/request'

// 查询就诊单列表
export function listConsultation(query) {
    return request({
        url: '/clinic/consultation/list',
        method: 'get',
        params: query
    })
}

// 查询就诊单详细
export function getConsultation(consultationId) {
    return request({
        url: '/clinic/consultation/' + consultationId,
        method: 'get'
    })
}

// 新增就诊单
export function addConsultation(data) {
    return request({
        url: '/clinic/consultation',
        method: 'post',
        data: data
    })
}

// 修改就诊单
export function updateConsultation(data) {
    return request({
        url: '/clinic/consultation',
        method: 'put',
        data: data
    })
}

// 删除就诊单
export function delConsultation(consultationId) {
    return request({
        url: '/clinic/consultation/' + consultationId,
        method: 'delete'
    })
}

// 一键发药（防超卖）
export function dispenseMedication(consultationId) {
    return request({
        url: '/clinic/consultation/' + consultationId + '/dispense',
        method: 'post'
    })
}

// 查询患者就诊历史时间线
export function getConsultationTimeline(patientId) {
    return request({
        url: '/clinic/consultation/timeline/' + patientId,
        method: 'get'
    })
}

// 一键接诊 (医生工作站)
export function quickConsultation(data) {
    return request({
        url: '/clinic/consultation/workstation/quick-consultation',
        method: 'post',
        data: data
    })
}
