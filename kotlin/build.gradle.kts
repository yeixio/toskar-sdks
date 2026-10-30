import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.21"
    kotlin("plugin.serialization") version "2.4.21"
    `java-library`
    `maven-publish`
}

group = "ai.toskar"
version = "0.3.0"

kotlin {
    explicitApi()
    jvmToolchain(21)
    compilerOptions {
        // Java 11 bytecode, for Android and older servers.
        jvmTarget.set(JvmTarget.JVM_11)
        freeCompilerArgs.add("-Xjdk-release=11")
    }
}

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(21))
    withSourcesJar()
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            artifactId = "toskar"
            from(components["java"])
            pom {
                name.set("Toskar")
                description.set("The official Kotlin and Java SDK for Toskar: local AI across your own computers.")
                url.set("https://toskar.ai/developers")
                licenses {
                    license {
                        name.set("Apache-2.0")
                        url.set("https://www.apache.org/licenses/LICENSE-2.0")
                    }
                }
                scm {
                    url.set("https://github.com/yeixio/toskar-sdks")
                }
            }
        }
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(11)
}

dependencies {
    api("com.squareup.okhttp3:okhttp:5.5.1")
    api("org.jetbrains.kotlinx:kotlinx-serialization-json:1.12.0")
    testImplementation(kotlin("test"))
    testImplementation("com.squareup.okhttp3:mockwebserver3:5.5.1")
}

tasks.test {
    useJUnitPlatform()
}
