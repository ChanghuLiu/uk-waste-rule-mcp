plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.regevidencehub.waste"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.regevidencehub.waste"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }
    buildFeatures { compose = true; buildConfig = true }
    sourceSets.getByName("debug").manifest.srcFile("src/debug/AndroidManifest.xml")
    sourceSets.getByName("release").manifest.srcFile("src/release/AndroidManifest.xml")
    buildTypes {
        debug {
            isDebuggable = true
            buildConfigField("String", "API_BASE_URL", "\"http://127.0.0.1:8765\"")
            manifestPlaceholders["networkConfig"] = "@xml/network_security_config_debug"
        }
        release {
            isDebuggable = false
            buildConfigField("String", "API_BASE_URL", "\"https://waste.regevidencehub.com\"")
            manifestPlaceholders["networkConfig"] = "@xml/network_security_config"
            isMinifyEnabled = false
        }
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.02.01")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("com.android.billingclient:billing-ktx:9.1.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
}
