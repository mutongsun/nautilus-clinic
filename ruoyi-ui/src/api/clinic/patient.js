import request from '@/utils/request'

// 查询患者列表
export function listPatient(query) {
    return request({
        url: '/clinic/patient/list',
        method: 'get',
        params: query
    })
}

// 高级搜索患者 (JSONB 标签查询)
export function advancedSearchPatient(query) {
    return request({
        url: '/clinic/patient/advanced-search',
        method: 'get',
        params: query
    })
}

// 查询患者详细
export function getPatient(patientId) {
    return request({
        url: '/clinic/patient/' + patientId,
        method: 'get'
    })
}

// 新增患者
export function addPatient(data) {
    return request({
        url: '/clinic/patient',
        method: 'post',
        data: data
    })
}

// 修改患者
export function updatePatient(data) {
    return request({
        url: '/clinic/patient',
        method: 'put',
        data: data
    })
}

// 删除患者
export function delPatient(patientId) {
    return request({
        url: '/clinic/patient/' + patientId,
        method: 'delete'
    })
}
