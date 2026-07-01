package com.ruoyi.web.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 数据库补丁控制器 — 仅限管理员访问
 */
@RestController
public class PatchController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @PreAuthorize("@ss.hasRole('admin')")
    @GetMapping("/patch-db")
    public String patchDb() {
        try {
            jdbcTemplate.execute("ALTER TABLE nautilus_consultation ADD COLUMN diagnosis TEXT");
            return "SUCCESS: Column 'diagnosis' added to ruoyi.nautilus_consultation";
        } catch (Exception e) {
            e.printStackTrace();
            Throwable cause = e.getCause();
            while (cause != null && cause.getCause() != null) {
                cause = cause.getCause();
            }
            return "RESULT: " + (cause != null ? cause.getMessage() : e.getMessage());
        }
    }
}
