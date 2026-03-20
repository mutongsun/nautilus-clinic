-- 插入工作站页面路由与菜单
INSERT INTO ruoyi.sys_menu (menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, update_by, update_time, remark)
VALUES ('医生工作站', 
        (SELECT menu_id FROM ruoyi.sys_menu WHERE menu_name = '社区诊所' LIMIT 1), 
        1, -- 放在诊所菜单第一位
        'workstation', 
        'clinic/workstation/index', 
        1, 0, 'C', '0', '0', 
        'clinic:workstation:list', 
        'peoples', 
        'admin', current_timestamp, '', null, '一站式接诊与处方工作站');
