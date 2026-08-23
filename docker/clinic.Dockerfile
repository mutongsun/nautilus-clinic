# ===== 诊所业务底座镜像（多阶段：Maven 构建 -> JRE 运行）=====
# 构建含 Agent 平台对接模块：/clinic/inventory/list（库存查询）+ /clinic/purchase/order（采购下单，下游幂等）
# 启动：docker compose --profile clinic up -d --build nautilus-clinic

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY docker/maven-settings.xml /usr/share/maven/conf/settings.xml
COPY pom.xml .
# 先解析父 POM 依赖（提升缓存命中），再拷源码构建
COPY ruoyi-common/pom.xml ruoyi-common/
COPY ruoyi-system/pom.xml ruoyi-system/
COPY ruoyi-framework/pom.xml ruoyi-framework/
COPY ruoyi-quartz/pom.xml ruoyi-quartz/
COPY ruoyi-generator/pom.xml ruoyi-generator/
COPY ruoyi-biz/pom.xml ruoyi-biz/
COPY ruoyi-admin/pom.xml ruoyi-admin/
RUN mvn -q -pl ruoyi-admin -am dependency:go-offline -DskipTests || true
COPY ruoyi-common ruoyi-common
COPY ruoyi-system ruoyi-system
COPY ruoyi-framework ruoyi-framework
COPY ruoyi-quartz ruoyi-quartz
COPY ruoyi-generator ruoyi-generator
COPY ruoyi-biz ruoyi-biz
COPY ruoyi-admin ruoyi-admin
RUN mvn -q -pl ruoyi-admin -am package -DskipTests

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=build /build/ruoyi-admin/target/*.jar app.jar
ENV TZ=Asia/Shanghai JAVA_OPTS=""
EXPOSE 8087
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar --spring.profiles.active=prodpg"]
