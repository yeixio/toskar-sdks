import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.21"
    kotlin("plugin.serialization") version "2.4.21"
    `java-library`
    id("com.vanniktech.maven.publish") version "0.37.0"
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
}

// Maven Central (RELEASING.md): signed, with sources and docs, uploaded and
// released by the release workflow. Credentials and the signing key come
// from ORG_GRADLE_PROJECT_mavenCentralUsername, _mavenCentralPassword,
// _signingInMemoryKey, and _signingInMemoryKeyPassword.
mavenPublishing {
    coordinates("ai.toskar", "toskar", version.toString())
    publishToMavenCentral(automaticRelease = true)
    if (providers.gradleProperty("signingInMemoryKey").isPresent) {
        signAllPublications()
    }
    pom {
        name.set("Toskar")
        description.set("The official Kotlin and Java SDK for Toskar: local AI across your own computers.")
        url.set("https://toskar.ai/developers")
        inceptionYear.set("2026")
        licenses {
            license {
                name.set("Apache-2.0")
                url.set("https://www.apache.org/licenses/LICENSE-2.0")
                distribution.set("repo")
            }
        }
        developers {
            developer {
                id.set("yeixio")
                name.set("Yeix.io")
                url.set("https://yeix.io")
            }
        }
        scm {
            url.set("https://github.com/yeixio/toskar-sdks")
            connection.set("scm:git:https://github.com/yeixio/toskar-sdks.git")
            developerConnection.set("scm:git:ssh://git@github.com/yeixio/toskar-sdks.git")
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
    testImplementation("com.squareup.okhttp3:okhttp-tls:5.5.1")
}

tasks.test {
    useJUnitPlatform()
}
