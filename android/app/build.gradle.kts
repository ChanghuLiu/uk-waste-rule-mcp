import java.io.File
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val wasteUploadPropertiesPath = providers.gradleProperty("wasteUploadProperties").orElse("${System.getProperty("user.home")}/.config/regevidencehub/waste-upload.properties").get()
val wasteUploadPropertiesFile = file(wasteUploadPropertiesPath)
val wasteUploadProperties = Properties().apply { if (wasteUploadPropertiesFile.isFile) wasteUploadPropertiesFile.inputStream().use { load(it) } }
val wasteUploadValues = listOf("storeFile", "storePassword", "keyAlias", "keyPassword").map(wasteUploadProperties::getProperty)
val wasteUploadStoreFile = wasteUploadValues.firstOrNull()?.let { candidate ->
    val store = file(candidate)
    if (store.isAbsolute) store else File(wasteUploadPropertiesFile.parentFile, candidate)
}
val wasteUploadSigningReady = wasteUploadValues.all { !it.isNullOrBlank() } && wasteUploadPropertiesFile.isFile && wasteUploadStoreFile?.isFile == true

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
    signingConfigs {
        create("upload") {
            if (wasteUploadSigningReady) {
                storeFile = wasteUploadStoreFile
                storePassword = wasteUploadValues[1]
                keyAlias = wasteUploadValues[2]
                keyPassword = wasteUploadValues[3]
            }
        }
    }
    sourceSets.getByName("debug").manifest.srcFile("src/debug/AndroidManifest.xml")
    sourceSets.getByName("release").manifest.srcFile("src/release/AndroidManifest.xml")
    buildTypes {
        debug {
            isDebuggable = true
            buildConfigField("String", "API_BASE_URL", "\"http://127.0.0.1:8765\"")
            manifestPlaceholders["networkConfig"] = "@xml/network_security_config_debug"
        }
        release {
            if (wasteUploadSigningReady) signingConfig = signingConfigs.getByName("upload")
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
