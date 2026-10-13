package com.yangbin.yangbinaicodeuser;

import org.apache.dubbo.config.spring.context.annotation.EnableDubbo;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@EnableDubbo
@MapperScan("com.yangbin.yangbinaicodeuser.mapper")
@ComponentScan("com.yangbin")
public class YangbinAiCodeUserApplication {
    public static void main(String[] args) {
        SpringApplication.run(YangbinAiCodeUserApplication.class, args);
    }
}