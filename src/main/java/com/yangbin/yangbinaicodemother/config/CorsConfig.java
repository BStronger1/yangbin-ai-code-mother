package com.yangbin.yangbinaicodemother.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/** The frontend and API share an origin through the deployment proxy. */
@Configuration
public class CorsConfig implements WebMvcConfigurer {}
