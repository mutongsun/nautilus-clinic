package com.ruoyi.web.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ruoyi.common.annotation.Anonymous;

@RestController
@Anonymous
public class PatchController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

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
