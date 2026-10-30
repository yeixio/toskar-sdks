// swift-tools-version:5.9
// The Swift SDK for Toskar: local AI across your own computers. It lives in
// swift/; this manifest is at the root because Swift Package Manager reads
// a package from its repository's root.
import PackageDescription

let package = Package(
    name: "Toskar",
    platforms: [.macOS(.v13), .iOS(.v16), .tvOS(.v16), .watchOS(.v9), .visionOS(.v1)],
    products: [
        .library(name: "Toskar", targets: ["Toskar"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-openapi-runtime", from: "1.8.0"),
        .package(url: "https://github.com/apple/swift-openapi-urlsession", from: "1.1.0"),
    ],
    targets: [
        // Every route, typed, generated from Toskar Core's API spec.
        .target(
            name: "ToskarAPI",
            dependencies: [.product(name: "OpenAPIRuntime", package: "swift-openapi-runtime")],
            path: "swift/Sources/ToskarAPI"
        ),
        .target(
            name: "Toskar",
            dependencies: [
                "ToskarAPI",
                .product(name: "OpenAPIRuntime", package: "swift-openapi-runtime"),
                .product(name: "OpenAPIURLSession", package: "swift-openapi-urlsession"),
            ],
            path: "swift/Sources/Toskar"
        ),
        // The shared conformance cases (conformance/README.md); not a product.
        .executableTarget(name: "toskar-conformance", dependencies: ["Toskar"], path: "swift/conformance"),
        .testTarget(name: "ToskarTests", dependencies: ["Toskar"], path: "swift/Tests/ToskarTests"),
    ]
)
