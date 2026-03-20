package com.ruoyi;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

public class DbPatcher {
    public static void main(String[] args) {
        String url = "jdbc:postgresql://127.0.0.1:5432/nautilus_clinic";
        String user = "postgres";
        String password = "123456";

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
