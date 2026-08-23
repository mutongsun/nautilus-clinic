package com.ruoyi.biz.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ruoyi.biz.domain.PurchaseOrder;
import org.apache.ibatis.annotations.Select;

/**
 * 采购订单 Mapper（MyBatis-Plus BaseMapper，无自定义 XML）
 *
 * @author nautilus-agent
 */
public interface PurchaseOrderMapper extends BaseMapper<PurchaseOrder> {

    /**
     * 预取订单主键序列（业务系统侧生成真实单号，单段式插入避免先空后补）
     */
    @Select("SELECT nextval('ruoyi.nautilus_purchase_order_order_id_seq')")
    Long nextOrderId();
}
