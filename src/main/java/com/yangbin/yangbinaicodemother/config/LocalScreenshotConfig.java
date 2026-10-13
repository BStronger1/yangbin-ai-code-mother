package com.yangbin.yangbinaicodemother.config;

import java.nio.file.Path;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class LocalScreenshotConfig implements WebMvcConfigurer {
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String location = Path.of(System.getProperty("user.dir"), "tmp", "covers").toUri().toString();
        if (!location.endsWith("/")) location += "/";
        registry.addResourceHandler("/screenshots/**").addResourceLocations(location);
    }
}
