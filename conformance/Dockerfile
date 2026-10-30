# One image with every SDK's conformance program, for a test bed that runs
# them as devices on its own networks (toskar-core's outside-network check).
# Build it from the repository root:
#
#	docker build -f conformance/Dockerfile -t toskar-conformance .
FROM golang:1.25-bookworm AS go
WORKDIR /src/go
COPY go/go.mod go/go.sum ./
RUN go mod download
COPY go/ ./
RUN CGO_ENABLED=0 go build -o /out/toskar-conformance-go ./cmd/toskar-conformance

FROM eclipse-temurin:21-jdk AS kotlin
WORKDIR /src/kotlin
COPY kotlin/ ./
RUN ./gradlew --no-daemon -q :conformance:installDist

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS dotnet
WORKDIR /src
COPY dotnet/ dotnet/
RUN dotnet publish dotnet/conformance -c Release -o /out/dotnet

FROM node:22-bookworm-slim AS typescript
WORKDIR /src/typescript
COPY typescript/package.json typescript/package-lock.json ./
RUN npm ci
COPY typescript/ ./
RUN npm run build && npm prune --omit=dev

FROM node:22-bookworm-slim
# iproute2: a test bed sets each device's routes.
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv iproute2 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY python/ /opt/python/
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir "/opt/python[anywhere]"
COPY --from=typescript /src/typescript/dist /opt/typescript/dist
COPY --from=typescript /src/typescript/node_modules /opt/typescript/node_modules
COPY --from=typescript /src/typescript/package.json /src/typescript/conformance.mjs /opt/typescript/
COPY --from=go /out/toskar-conformance-go /usr/local/bin/
COPY --from=eclipse-temurin:21-jre /opt/java/openjdk /opt/jre
COPY --from=kotlin /src/kotlin/conformance/build/install/toskar-conformance /opt/kotlin
COPY --from=mcr.microsoft.com/dotnet/runtime:8.0 /usr/share/dotnet /opt/dotnet
COPY --from=dotnet /out/dotnet /opt/dotnet-conformance
RUN printf '#!/bin/sh\nexec /opt/venv/bin/python /opt/python/conformance.py "$@"\n' > /usr/local/bin/toskar-conformance-python \
 && printf '#!/bin/sh\nexec node /opt/typescript/conformance.mjs "$@"\n' > /usr/local/bin/toskar-conformance-node \
 && printf '#!/bin/sh\nJAVA_HOME=/opt/jre exec /opt/kotlin/bin/toskar-conformance "$@"\n' > /usr/local/bin/toskar-conformance-kotlin \
 && printf '#!/bin/sh\nexec /opt/dotnet/dotnet /opt/dotnet-conformance/toskar-conformance.dll "$@"\n' > /usr/local/bin/toskar-conformance-dotnet \
 && chmod +x /usr/local/bin/toskar-conformance-*
