// swift-tools-version:5.9
// Runs swift-openapi-generator to write the Swift SDK's generated code
// (Sources/ToskarAPI) from the spec. Kept out of the SDK's own package, so
// apps that use the SDK never build the generator.
import PackageDescription

let package = Package(
    name: "generator",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/apple/swift-openapi-generator", exact: "1.10.3"),
    ]
)
