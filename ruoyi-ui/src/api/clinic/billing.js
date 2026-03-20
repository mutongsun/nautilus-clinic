import request from '@/utils/request'

/** 查询所有有待缴费处方的患者列表（返回 {patientId, patientName}） */
export function getPendingPatients() {
    return request({
        url: '/clinic/billing/pending-patients',
        method: 'get'
    })
}

/** 按患者ID查询最新待缴费处方明细 */
export function getPrescription(patientId) {
    return request({
        url: '/clinic/billing/prescription',
        method: 'get',
        params: { patientId }
    })
}

/** 生成账单流水号 */
export function generateBill() {
    return request({
        url: '/clinic/billing/generate',
        method: 'get'
    })
}

/** 确认医保支付 */
export function payBill(billNo, patientId) {
    return request({
        url: '/clinic/billing/pay',
        method: 'post',
        params: { billNo, patientId }
    })
}
