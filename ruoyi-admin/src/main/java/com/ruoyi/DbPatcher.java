package com.ruoyi;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

/**
 * 数据库补丁工具 — 手动执行，凭据从环境变量读取。
 * 用法：java -cp ... com.ruoyi.DbPatcher
 * 环境变量：DB_PATCHER_URL, DB_PATCHER_USER, DB_PATCHER_PASSWORD
 */
public class DbPatcher {
    public static void main(String[] args) {
        String url = System.getenv().getOrDefault("DB_PATCHER_URL",
                "jdbc:postgresql://127.0.0.1:5432/nautilus_clinic");
        String user = System.getenv().getOrDefault("DB_PATCHER_USER", "postgres");
        String password = System.getenv("DB_PATCHER_PASSWORD");
        if (password == null || password.isEmpty()) {
            System.err.println("❌ 请设置环境变量 DB_PATCHER_PASSWORD");
            return;
        }

        try {
            Class.forName("org.postgresql.Driver");
        } catch (ClassNotFoundException e) {
            System.err.println("Driver not found!");
            return;
        }

        try (Connection conn = DriverManager.getConnection(url, user, password);
                Statement stmt = conn.createStatement()) {

            String sql = "ALTER TABLE ruoyi.nautilus_consultation ADD COLUMN diagnosis VARCHAR(2000)";
            stmt.executeUpdate(sql);
            System.out.println("✅ Column 'diagnosis' successfully added to ruoyi.nautilus_consultation!");

        } catch (Exception e) {
            String msg = e.getMessage();
            if (msg.contains("already exists")) {
                System.out.println("✅ Column 'diagnosis' already exists.");
            } else {
                System.err.println("❌ Error: " + msg);
            }
        }
    }
}
