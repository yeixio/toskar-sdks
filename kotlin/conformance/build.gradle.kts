// The conformance program (conformance/README.md at the repository root).
plugins {
    kotlin("jvm")
    application
}

kotlin { jvmToolchain(21) }

dependencies { implementation(project(":")) }

application {
    applicationName = "toskar-conformance"
    mainClass.set("ai.toskar.conformance.MainKt")
}
