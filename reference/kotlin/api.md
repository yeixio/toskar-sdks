# Every route on `toskar.api`

*Generated from `api/Api.kt`, which `kotlin/scripts/generate.py` writes from Toskar Core's API spec.*

One method for each operation, named after its operationId. Each waits for its answer, so call it off the main thread; an error answer throws a `ToskarException`. The models are in `ai.toskar.api`, and every field is described at [toskar.ai/developers/api](https://toskar.ai/developers/api).

### acceptInvite(token, body)

Use a one-time link to set a username and password, or a new password, and sign in

```kotlin
fun acceptInvite(token: String, body: AcceptInviteRequest): Principal
```

### addCompanionDevice(body)

Connect a companion device, such as a watch with its phone

A connected device asks for a key of its own for a device that goes along with it (yeixio/toskar-apps#213), for the same person, so it shows in Devices and can be disconnected on its own. It works from anywhere, as no code is typed. The answer is the same as POST /devices/pair's. A person may have 20 connected devices.

```kotlin
fun addCompanionDevice(body: AddCompanionDeviceRequest): PairedDevice
```

### addConversations(id, body)

Add chats as training material

Parameters:

- `id`: Specialized AI id

```kotlin
fun addConversations(id: String, body: AddConversationsRequest): TrainingMaterial
```

### addExample(id, body)

Add an example

Parameters:

- `id`: Specialized AI id

```kotlin
fun addExample(id: String, body: AddExampleRequest): Unit
```

### addMaterial(id, body)

Add material

Parameters:

- `id`: Specialized AI id

```kotlin
fun addMaterial(id: String, body: AddMaterialRequest): TrainingMaterial
```

### addMCPServer(body)

Check a tool source connects and list its tools, then store it and add the tools

Send a gallery entry ({"preset", "values"}), a spec ({"spec", "values"}), or a server from another app ({"import": {"app", "name"}}). redirect_base is the address the browser uses, for a sign-in. When the service needs a sign-in, the source is stored and sign_in_url is returned.

```kotlin
fun addMCPServer(body: AddMCPServerRequest? = null): Unit
```

### addMemory(body)

Add a memory; an existing equal memory is returned instead

```kotlin
fun addMemory(body: AddMemoryRequest): Memory
```

### addPerson(body)

Add a person and make their invite link (Admins add Members and Visitors; the Owner adds Admins too)

```kotlin
fun addPerson(body: AddPersonRequest): AddedPerson
```

### approvePairing(id, body)

Approve a pairing offer

```kotlin
fun approvePairing(id: String, body: ApprovePairingRequest? = null): PairingSession
```

### browseModels(q, limit)

Search Hugging Face for GGUF models

```kotlin
fun browseModels(q: String? = null, limit: Long? = null): List<BrowseModel>
```

### cancelBenchmark(id)

Cancel a running benchmark

```kotlin
fun cancelBenchmark(id: String): OK
```

### cancelDevicePairing()

Stop showing the code

```kotlin
fun cancelDevicePairing(): Unit
```

### cancelImageSetup()

Stop the setup in progress; what was downloaded is kept and resumed next time

```kotlin
fun cancelImageSetup(): ImageSetup
```

### cancelTrainingJob(id)

Cancel a training job

```kotlin
fun cancelTrainingJob(id: String): TrainingJob
```

### cancelVideoSetup()

Stop the setup in progress; what was downloaded is kept and resumed next time

```kotlin
fun cancelVideoSetup(): ImageSetup
```

### changeMyPassword(body)

Change your own password (#592)

With your current one. A password an Admin set with must_change is changed here before anything else works; until then other routes answer PASSWORD_CHANGE_REQUIRED. You're signed out everywhere else.

```kotlin
fun changeMyPassword(body: ChangeMyPasswordRequest): Principal
```

### changePerson(id, body)

Rename, change the role of, disable, or enable a person

The Owner's role is fixed and they can't be disabled; nobody changes their own role or disables themselves. Disabling signs the person out everywhere and stops their keys.

```kotlin
fun changePerson(id: String, body: ChangePersonRequest): Person
```

### chat(body)

Send a chat message

Without stream, returns {content, metrics}. With stream, a server-sent event stream of token events, then done; an error event ends it early.

```kotlin
fun chat(body: ChatRequest): ChatAnswer
```

### checkConnector(id)

Check the stored credential again

```kotlin
fun checkConnector(id: String): Unit
```

### checkMCPServer(id)

Connect again and list the tools

```kotlin
fun checkMCPServer(id: String): Unit
```

### checkRemoteAccess()

Check access from anywhere from outside, now (#546)

The relay reaches this computer from the internet, through its tunnel and each direct way in, as a paired device away from home does: TLS to this computer's certificate and GET /api/v1/health. It also runs on its own every 30 minutes and after the relay connects or the ways in change. Answers what GET /api/v1/remote-access does, with check updated. Admins only. 409 REMOTE_ACCESS_OFF when access from anywhere is off or its listener isn't up.

```kotlin
fun checkRemoteAccess(): Unit
```

### claimPairing(body)

Pair using the code shown on the other computer

```kotlin
fun claimPairing(body: ClaimPairingRequest): PairingSession
```

### classifyMaterial(body)

Recommend whether material is for training, knowledge, or both

```kotlin
fun classifyMaterial(body: ClassifyMaterialRequest): ClassifiedMaterial
```

### clearCache(name)

Clear one cache

```kotlin
fun clearCache(name: String): Unit
```

### compactConversation(id)

Compact a chat now (#342)

Summarizes its older messages whatever its size, keeping the newest verbatim. NOTHING_TO_COMPACT for a chat too short.

```kotlin
fun compactConversation(id: String): ConversationSummary
```

### connectService(id, body)

Check values with the service, then store them and add its tools

```kotlin
fun connectService(id: String, body: ConnectServiceRequest? = null): Unit
```

### continueAutomationRun(id, runId)

Open a run's result in a chat to reply to

Returns the chat the result was already posted to, or makes one with the result as its first answer, marked with meta.automation_run.

```kotlin
fun continueAutomationRun(id: String, runId: String): ContinuedRun
```

### conversationFromSummary(id)

A new chat that begins with this chat's summary (#342)

```kotlin
fun conversationFromSummary(id: String): Conversation
```

### createAI(body)

Create a specialized AI

```kotlin
fun createAI(body: CreateAIRequest): SpecializedAI
```

### createAPIKey(body)

Create an API key; the secret is shown only in this response

```kotlin
fun createAPIKey(body: CreateAPIKeyRequest): NewAPIKey
```

### createAutomation(body)

Create an automation

```kotlin
fun createAutomation(body: AutomationInput): Automation
```

### createConversation(body)

Create conversation

```kotlin
fun createConversation(body: CreateConversationRequest? = null): Conversation
```

### createDiagnostics(body)

Create a diagnostics bundle

```kotlin
fun createDiagnostics(body: CreateDiagnosticsRequest? = null): DiagnosticsBundle
```

### createExampleAI()

Create the example specialized AI

```kotlin
fun createExampleAI(): SpecializedAI
```

### createJoinToken(body)

Make a one-time join token and the command that adds a computer to this network

The token is shown once and only its proof key is kept. It lasts `ttl_minutes` (15 by default, at most 1440) and can be used once. Refused with 409 when other computers can't reach this one's Bifrost.

```kotlin
fun createJoinToken(body: CreateJoinTokenRequest? = null): JoinTokenCreated
```

### createKnowledgeSource(body)

Connect a file, folder, upload, pasted text, database, or web API

```kotlin
fun createKnowledgeSource(body: CreateKnowledgeSourceRequest): KnowledgeSource
```

### createNotificationDestination(body)

Add an email or webhook destination; a webhook's signing secret is returned this once

```kotlin
fun createNotificationDestination(body: NotificationDestinationInput): CreatedDestination
```

### createPortal(body)

Add a chat portal (#205)

slug (2 to 40 lowercase letters, digits, or dashes) and name are required. It starts with no tools, no memory, passcode access (passcode required), and on.

```kotlin
fun createPortal(body: JsonObject): Portal
```

### createProfile(body)

Create a profile

```kotlin
fun createProfile(body: JsonObject): JsonObject
```

### createTask(body)

Run a prompt as a task

```kotlin
fun createTask(body: CreateTaskRequest): Task
```

### decideTool(body)

Answer a tool approval request

```kotlin
fun decideTool(body: DecideToolRequest): Status
```

### deleteAI(id)

Delete a specialized AI

Parameters:

- `id`: Specialized AI id

```kotlin
fun deleteAI(id: String): Unit
```

### deleteAPIKey(id)

Delete an API key

```kotlin
fun deleteAPIKey(id: String): Unit
```

### deleteArtifact(id)

Delete a file

```kotlin
fun deleteArtifact(id: String): Unit
```

### deleteAutomation(id)

Delete an automation

```kotlin
fun deleteAutomation(id: String): Unit
```

### deleteConversation(id)

Delete conversation

```kotlin
fun deleteConversation(id: String): Unit
```

### deleteConversations(body)

Delete several conversations

Deletes the caller's chats among ids, with their messages and files, in one request (#452, contract 1.25). Another person's chat, or one that doesn't exist, is skipped as not_found.

```kotlin
fun deleteConversations(body: DeleteConversationsRequest): ConversationsDeleted
```

### deleteExample(id, eid)

Delete an example

Parameters:

- `id`: Specialized AI id

```kotlin
fun deleteExample(id: String, eid: String): Unit
```

### deleteExport(id, rev)

Delete an exported file

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun deleteExport(id: String, rev: String): Unit
```

### deleteKnowledgeSource(id)

Remove a source and its index

```kotlin
fun deleteKnowledgeSource(id: String): Unit
```

### deleteMaterial(id, mid)

Remove material

Parameters:

- `id`: Specialized AI id

```kotlin
fun deleteMaterial(id: String, mid: String): Unit
```

### deleteMemory(id)

Delete a memory

```kotlin
fun deleteMemory(id: String): Unit
```

### deleteModel(id, body, nodeId)

Delete a model file

```kotlin
fun deleteModel(id: String, body: DeleteModelRequest? = null, nodeId: String? = null): Unit
```

### deleteModelRating(id)

Remove this person's rating, withdrawing it first if it was shared

```kotlin
fun deleteModelRating(id: String): Unit
```

### deleteNotificationDestination(id)

Remove a destination, its stored secret, and its waiting deliveries

```kotlin
fun deleteNotificationDestination(id: String): Unit
```

### deletePortal(id)

Remove a chat portal (#205)

Its guests can no longer chat.

```kotlin
fun deletePortal(id: String): Unit
```

### deleteProfile(id)

Delete a custom profile

```kotlin
fun deleteProfile(id: String): Unit
```

### deleteRunRecords()

Delete run records now

```kotlin
fun deleteRunRecords(): Unit
```

### deployedAIs()

Deployed specialized AIs, as model ids sai:<slug>

```kotlin
fun deployedAIs(): List<Model>
```

### deployRevision(id, rev)

Deploy an evaluated revision

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun deployRevision(id: String, rev: String): SpecializedAI
```

### describeTool(id)

One tool's descriptor

```kotlin
fun describeTool(id: String): ToolDescriptor
```

### disconnectMyDevice(id)

Disconnect one of your devices (#206)

```kotlin
fun disconnectMyDevice(id: String): Unit
```

### disconnectService(id)

Delete the stored credential and remove the service's tools

```kotlin
fun disconnectService(id: String): Unit
```

### disconnectThisDevice()

Disconnect this device, with its companions (#766)

A device's own key disconnects it, as the apps do when the person removes this computer. Its key and its companions' keys, such as its watch's, are revoked, and their notifications stop.

```kotlin
fun disconnectThisDevice(): Unit
```

### dismissModelRating(id)

Stop asking for a rating of a model

```kotlin
fun dismissModelRating(id: String): Unit
```

### dismissNotification(id)

Hide a notification from the notification center

```kotlin
fun dismissNotification(id: String): Unit
```

### downloadExport(id, rev)

Download the exported GGUF

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun downloadExport(id: String, rev: String): ByteArray
```

### editConversationSummary(id, body)

Correct a chat's summary (#342)

Later summaries keep the correction.

```kotlin
fun editConversationSummary(id: String, body: EditConversationSummaryRequest): ConversationSummary
```

### enterPortal(slug)

Enter a portal as its guest (#205)

With passcode when the portal has one. Makes this browser the portal's guest, signed in by a toskar_portal_<slug> cookie that counts only on requests carrying X-Toskar-Portal. A guest reaches only the portal's chat, with the portal's profile, tools, memory, and language.

```kotlin
fun enterPortal(slug: String): EnteredPortal
```

### evaluateRevision(id, rev)

Compare a revision with the base model

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun evaluateRevision(id: String, rev: String): Evaluation
```

### exportDiagnostics(includeConversations)

Create a diagnostics bundle (a zip without secrets or private keys)

```kotlin
fun exportDiagnostics(includeConversations: String? = null): DiagnosticsBundle
```

### exportRevision(id, rev)

Export a revision as one GGUF file

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun exportRevision(id: String, rev: String): ExportStatus
```

### exportStatus(id, rev)

Export status of a revision

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```kotlin
fun exportStatus(id: String, rev: String): ExportStatus
```

### findModelsInOtherApps()

Models other local AI apps keep on this computer

GGUF models LM Studio, Ollama (through its manifests), llama.cpp, and GPT4All already downloaded, to add with POST /api/v1/models/import without downloading them again. Only headers and Ollama's manifests are read; incomplete files and vision projectors are left out (#467). GGUF files put in Toskar's own models folder by hand that aren't models yet come first, as app toskar; one is always added in place (#763).

```kotlin
fun findModelsInOtherApps(): FoundModels
```

### getAbout()

AGPL corresponding-source offer

```kotlin
fun getAbout(): SourceOffer
```

### getAI(id)

A specialized AI with its materials, revisions, and jobs

Parameters:

- `id`: Specialized AI id

```kotlin
fun getAI(id: String): SpecializedAI
```

### getApiTLS()

How the API speaks HTTPS on the local network (#213)

```kotlin
fun getApiTLS(): TLSInfo
```

### getArtifact(id)

One file

```kotlin
fun getArtifact(id: String): Artifact
```

### getArtifactContent(id, inline)

A file's content

Parameters:

- `inline`: 1 shows a PDF or image in the browser instead of downloading it

```kotlin
fun getArtifactContent(id: String, inline: String? = null): ByteArray
```

### getAutomation(id)

An automation with its run history

```kotlin
fun getAutomation(id: String): AutomationDetail
```

### getBenchmark(id)

Get benchmark job status and results

```kotlin
fun getBenchmark(id: String): JsonObject
```

### getCapabilities(ask)

Capability inventory: what Toskar can do right now

Parameters:

- `ask`: A question such as "Can you generate an image?"; returns the abilities that answer it

```kotlin
fun getCapabilities(ask: String? = null): JsonElement?
```

### getCommunityRatings()

Everyone's ratings of the models here, from hardware like this computer's and overall

Empty unless `community_ratings` is on. The public summary is downloaded at most once a day; when that fails, the last one is used and `error` says why.

```kotlin
fun getCommunityRatings(): CommunityRatings
```

### getConversationSummary(id)

A chat's auto-compact summary (#342)

What the model sees in place of the chat's older messages, through which message. Every message stays saved.

```kotlin
fun getConversationSummary(id: String): ConversationSummary
```

### getDevicePairing()

Whether a phone has connected with the code shown

```kotlin
fun getDevicePairing(): DevicePairing
```

### getExternalServer()

The OpenAI-compatible server whose models can be chosen for a chat, and the models it offers

```kotlin
fun getExternalServer(): ExternalServer
```

### getFirstAnswers(days)

How long answers took to start, by app, cold or warm

Chat runs that reached a first token, grouped by the app that asked (the chat request's client) and by whether a model had to load first. Automations are left out.

Parameters:

- `days`: How many days back to look; 7 by default, 90 at most.

```kotlin
fun getFirstAnswers(days: Long? = null): FirstAnswers
```

### getGPUSetup()

What this computer still needs for Toskar to use its GPU

The graphics card found and each missing piece, most basic first, with a fix written for this computer: the Vulkan loader or drivers, permission to open the card's render device, NVIDIA's driver, a Windows card's driver, or the CPU-only llama.cpp build. No problems when the GPU is ready, when there is no GPU, and on macOS.

```kotlin
fun getGPUSetup(): GPUSetup
```

### getHardware()

Local hardware inventory

```kotlin
fun getHardware(): JsonObject
```

### getHealth()

Health check

```kotlin
fun getHealth(): HealthResponse
```

### getImageSetup()

What image generation has installed, the models on offer, and any setup in progress

```kotlin
fun getImageSetup(): ImageSetup
```

### getKnowledgeContent(id)

The text of a pasted or uploaded source

```kotlin
fun getKnowledgeContent(id: String): SourceText
```

### getKnowledgeSource(id)

One source

```kotlin
fun getKnowledgeSource(id: String): KnowledgeSource
```

### getLicense()

Toskar Pro's trial or Unlock, as its desktop app last said

Core on its own has no license (`kind` empty) and nothing is limited. The Toskar Pro desktop app from the Mac App Store or the Microsoft Store sets a 14-day trial, unlocked, or ended (yeixio/toskar-apps#336). While `limited`, installing models, creating automations, and adding people answer 403 `UNLOCK_REQUIRED`; what's set up keeps working.

```kotlin
fun getLicense(): License
```

### getLog(name, tailBytes)

Read a log file tail

```kotlin
fun getLog(name: String, tailBytes: Long? = null): LogContent
```

### getMCPPrompt(id, name, body)

Fill a prompt; returns its text

```kotlin
fun getMCPPrompt(id: String, name: String, body: GetMCPPromptRequest? = null): Unit
```

### getMCPServer(id)

One tool source

```kotlin
fun getMCPServer(id: String): Unit
```

### getMe()

Who the request is from (#206)

The person, their role, and how Toskar knows. A request from this computer is the Owner's; one with an API key is its person's.

```kotlin
fun getMe(): Me
```

### getModelPlacement(id)

Which computers can run an installed model

```kotlin
fun getModelPlacement(id: String): ModelPlacement
```

### getModelRating(id)

This person's rating of a model, and exactly what sharing it would send

```kotlin
fun getModelRating(id: String): ModelRating
```

### getNetwork()

This computer's network, its Bifrost address and fingerprint, and the computers it trusts

```kotlin
fun getNetwork(): NetworkStatus
```

### getNews()

The AI news from toskar.ai

New open models, runtime releases, and AI labs' announcements, a few lines each, from https://toskar.ai/news.json (#750). Read when asked, at most every six hours, and kept in the data folder so it shows offline; each read is listed in What left this computer as `news`. With the `ai_news` setting off, nothing is read and `enabled` is false. Members and Admins.

```kotlin
fun getNews(): News
```

### getNotification(id)

One notification with each channel's delivery

```kotlin
fun getNotification(id: String): Notification
```

### getNotificationDestination(id)

One destination

```kotlin
fun getNotificationDestination(id: String): NotificationDestination
```

### getOIDC()

Whether sign-in with an OpenID Connect provider is offered (#206)

```kotlin
fun getOIDC(): OIDCInfo
```

### getPerson(id)

One person (#592)

```kotlin
fun getPerson(id: String): Person
```

### getPersonalization()

How the person likes answers

```kotlin
fun getPersonalization(): PersonalStyle
```

### getPortal(id)

One chat portal (#205)

```kotlin
fun getPortal(id: String): Portal
```

### getPortalPage(slug)

What a portal's page shows (#205)

Its name, access, language, and branding, and whether this browser is already its guest. Answers without signing in.

```kotlin
fun getPortalPage(slug: String): PortalPage
```

### getPortalUsage(id)

How much a portal is used (#205)

Visitors who wrote, conversations, and messages they sent, over the last 7 and 30 days.

```kotlin
fun getPortalUsage(id: String): PortalUsage
```

### getPrivacy()

Run record retention and a 30-day summary of what left this computer

```kotlin
fun getPrivacy(): Unit
```

### getProfile(id)

One profile

```kotlin
fun getProfile(id: String): JsonObject
```

### getProfilePins()

The profiles each pinnable role is kept to (#345)

```kotlin
fun getProfilePins(): ProfilePins
```

### getPushStatus()

Push to the Toskar app on this device (#460)

What a paired phone or tablet needs to register with the push relay (the relay and this computer's key, which the relay seals into the device's handle), and whether this device has registered. See docs/push.md.

```kotlin
fun getPushStatus(): PushStatus
```

### getQuietHours()

Quiet hours

```kotlin
fun getQuietHours(): QuietHours
```

### getRemoteAccess()

Access from anywhere's setting and its listener (#456)

enabled, port, address (a forwarded address, when set), listening (the address it listens on) or error, port_mapping, mapped and mapped_by (pcp, nat-pmp, or upnp) for the router port it opened, map_error, ipv6, reachable (direct, ipv6, manual, relay, or none) with reason (off, not_listening, carrier_nat, or no_port), relay (name, state: no_token, ended (contract 1.41: the token ran out with nothing to renew it, so it isn't sent; a new one takes over within a minute), connecting, connected, or error, and error, its code) while the relay client runs, and check, the last outside check (#546, contract 1.28): at, relay and direct (each way in with address, ok, reason, and ms), tried, and error when the last attempt didn't reach the relay (CHECK_UNSUPPORTED, CHECK_TOO_SOON, NO_TOKEN, RELAY_UNREACHABLE). With Toskar's relay, subscription (#639, contract 1.38): state (none, pending, active, or ended; contract 1.41: ended also when the token from the app's store or a subscription ran out, with expires the day it did), store (stripe when bought here in Settings, app when bought in the Toskar app), expires, open (whether Toskar's relay takes new subscriptions now, when known), checkout (the open checkout's page while pending), error (the last exchange's code when it didn't reach the relay), and in_app_only (contract 1.39: this copy is the Mac App Store's, which neither sells nor manages it; the Toskar app on a phone or tablet does). Set it with PATCH /api/v1/settings: remote_access_enabled, remote_access_port, remote_access_address, remote_access_port_mapping, remote_access_relay (an organization's relay, empty for Toskar's), and remote_access_relay_secret (its enrollment secret; write-only, empty clears it).

```kotlin
fun getRemoteAccess(): Unit
```

### getReport()

What a problem report sends, scrubbed

Versions and the kind of computer, and for an Admin Core's last 40 warnings and errors. Email addresses, keys, tokens, home folder names, the computer's name, and internet addresses are taken out first. Members and paired devices may call it.

```kotlin
fun getReport(): DiagnosticsReport
```

### getRouteSecret()

The route secret, for a paired device on the home network (#456)

route_secret (base64url, 32 bytes), route_id, relay (the relay this computer uses away from home), and token, the computer's current token for Toskar's relay when it has one (contract 1.27), so each paired device can look it up away from home. Given only on the home network, never through the remote listener; pairing (POST /api/v1/devices/pair) returns them too.

```kotlin
fun getRouteSecret(): DeviceRoute
```

### getRun(id)

One run trace

```kotlin
fun getRun(id: String): Unit
```

### getRuntimeHistory()

The daemon's memory and goroutines now and over the last day

Sampled every five minutes and kept for a day, so a slow leak shows on the Diagnostics page. Resets when the daemon restarts.

```kotlin
fun getRuntimeHistory(): RuntimeHistory
```

### getSettings()

Get settings

```kotlin
fun getSettings(): JsonObject
```

### getSource()

AGPL corresponding-source offer

```kotlin
fun getSource(): SourceOffer
```

### getTask(id)

One task

```kotlin
fun getTask(id: String): Task
```

### getTopicAttempts(id, days)

A profile's off-topic attempts (#345)

What an Enforce profile held, or whose answer it replaced, over the last days (30 by default, up to 365), kept as run records are.

```kotlin
fun getTopicAttempts(id: String, days: Long? = null): Unit
```

### getTrainingJob(id)

One training job

```kotlin
fun getTrainingJob(id: String): TrainingJob
```

### getUpdates()

Whether a newer Toskar is out, from the daily check of toskar.ai

Release builds installed from a download check https://toskar.ai/releases/latest.json once a day, while the `update_check` setting is on. The App Store edition, the copy the desktop app runs (`TOSKAR_UPDATE_CHECK=off`), and development builds don't check, and say `supported` false.

```kotlin
fun getUpdates(): UpdateStatus
```

### getVersion()

Application version

```kotlin
fun getVersion(): VersionResponse
```

### getVideoSetup()

What video generation has installed, the models on offer, and any setup in progress

```kotlin
fun getVideoSetup(): ImageSetup
```

### importModel(body, filename, displayName, id)

Add a model from a GGUF file

A path on this computer as JSON, copied into the models folder (the default; progress comes as model.download events) or used in place with in_place, or the file itself as an application/octet-stream body with filename in the query. The header and tensor bounds are checked first (#467).

Parameters:

- `filename`: For an upload, the file's name, ending in .gguf

```kotlin
fun importModel(body: ImportModelRequest, filename: String? = null, displayName: String? = null, id: String? = null): ImportedModel
```

### installModel(id, body, wait, nodeId)

Download a catalog model, here or on a paired computer

```kotlin
fun installModel(id: String, body: InstallModelRequest? = null, wait: String? = null, nodeId: String? = null): ModelInstall
```

### installModelFromURL(body, wait)

Download a GGUF from a URL

Parameters:

- `wait`: true waits for the download to finish

```kotlin
fun installModelFromURL(body: InstallFromURLRequest, wait: String? = null): ModelInstall
```

### installRuntime(id)

Install a runtime, such as llamacpp

```kotlin
fun installRuntime(id: String): RuntimeInstall
```

### invitePortalVisitor(id, body)

Invite a visitor to a portal by name (#205)

Answers with the visitor and their one-time link (path /p/<slug>?invite=<token>, good for a week).

```kotlin
fun invitePortalVisitor(id: String, body: InvitePortalVisitorRequest): InvitedVisitor
```

### joinNetwork(body)

Join this computer to the network of the computer that made a join token

Verifies the server's key against the fingerprint before proving the token, which never leaves this computer. Safe to repeat; refuses to switch networks while paired.

```kotlin
fun joinNetwork(body: JoinNetworkRequest): JoinResult
```

### leaveNetwork()

Leave the network, telling each paired computer, and forget them all

Models, settings, and this computer's identity stay.

```kotlin
fun leaveNetwork(): LeaveResult
```

### listAIs()

Specialized AIs

```kotlin
fun listAIs(): List<SpecializedAI>
```

### listAPIKeys()

API keys, without their secrets

```kotlin
fun listAPIKeys(): List<APIKey>
```

### listAutomationRuns(id, before, limit)

A page of an automation's runs, newest first

Parameters:

- `before`: The id of the last run already shown; the page starts after it
- `limit`: Runs per page, 1 to 100 (default 20)

```kotlin
fun listAutomationRuns(id: String, before: String? = null, limit: Long? = null): AutomationRunsPage
```

### listAutomations()

Automations with their last result

```kotlin
fun listAutomations(): List<Automation>
```

### listBenchmarks()

List recent benchmark jobs

```kotlin
fun listBenchmarks(): List<JsonObject>
```

### listBenchmarkWorkloads()

List benchmark workload categories

```kotlin
fun listBenchmarkWorkloads(): List<JsonObject>
```

### listCaches()

Caches with their declared policies and sizes

```kotlin
fun listCaches(): List<CacheInfo>
```

### listConnectors()

List connected services and their status. Secret values are never returned.

```kotlin
fun listConnectors(): List<ConnectorStatus>
```

### listConversationArtifacts(id)

Files attached to or made in a conversation

```kotlin
fun listConversationArtifacts(id: String): List<Artifact>
```

### listConversationMessages(id)

Messages of a conversation, with sources, steps, and files

```kotlin
fun listConversationMessages(id: String): List<Message>
```

### listConversations()

List conversations

```kotlin
fun listConversations(): List<Conversation>
```

### listDevices(kind)

The connected services' devices, by kind (#586)

```kotlin
fun listDevices(kind: String? = null): Unit
```

### listEgress(conversationId, limit)

What left this computer, newest first

```kotlin
fun listEgress(conversationId: String? = null, limit: Long? = null): List<EgressRecord>
```

### listExamples(id)

Training examples and their statistics

Parameters:

- `id`: Specialized AI id

```kotlin
fun listExamples(id: String): TrainingExamples
```

### listJoinTokens()

Join tokens, active and from the last week, without their secrets

```kotlin
fun listJoinTokens(): List<JoinToken>
```

### listKnowledgeSources()

Connected knowledge sources

```kotlin
fun listKnowledgeSources(): List<KnowledgeSource>
```

### listLiveFigures()

Live CPU, memory, and GPU figures for this and paired computers

Each computer's figures now, every few seconds over the last hour (every minute when no model is loaded), and per-minute averages over the last day. A figure a computer can't give, such as GPU temperature on a Mac, is left out rather than reported as 0. A paired computer that doesn't answer within 5 seconds is left out.

```kotlin
fun listLiveFigures(): List<LiveFigures>
```

### listLogs()

List diagnostic log files

```kotlin
fun listLogs(): List<LogFile>
```

### listMCPServers()

List MCP tool sources with status, tools, and masked values. Secret values are never returned.

```kotlin
fun listMCPServers(): List<MCPServer>
```

### listMemories()

Memories and the categories they can have

```kotlin
fun listMemories(): MemoryList
```

### listModels()

List catalog and installed models

```kotlin
fun listModels(): List<Model>
```

### listMyDevices()

Your connected devices (#206)

The phones, tablets, and TVs connected as the request's person, whatever their role.

```kotlin
fun listMyDevices(): List<MyDevice>
```

### listNodes()

List local and discovered computers

```kotlin
fun listNodes(): List<JsonObject>
```

### listNotificationDestinations()

Email and webhook destinations. Passwords and signing secrets are never returned.

```kotlin
fun listNotificationDestinations(): List<NotificationDestination>
```

### listNotifications(unread, limit, category)

List notifications that were not dismissed, newest first

Parameters:

- `unread`: 1 lists unread notifications only
- `category`: automation, approval, model, training, health, or system

```kotlin
fun listNotifications(unread: String? = null, limit: Long? = null, category: String? = null): NotificationList
```

### listPeople(role, disabled)

Everyone who uses this Toskar (Admins and the Owner)

Parameters:

- `role`: Only people with this role (#592).
- `disabled`: true for only disabled people, false for only active ones.

```kotlin
fun listPeople(role: String? = null, disabled: Boolean? = null): List<Person>
```

### listPerformance(sort, order, limit)

List generation performance samples

```kotlin
fun listPerformance(sort: String? = null, order: String? = null, limit: Long? = null): List<JsonObject>
```

### listPortalConversations(id)

A portal's visitors' conversations (#205)

Newest first, for Admins. A Members only portal's chats are each Member's own, so they aren't here.

```kotlin
fun listPortalConversations(id: String): List<PortalConversation>
```

### listPortalMessages(id, cid)

One visitor's conversation, to read (#205)

```kotlin
fun listPortalMessages(id: String, cid: String): List<PortalMessage>
```

### listPortals()

Chat portals (#205)

Every portal, for Admins and the Owner.

```kotlin
fun listPortals(): List<Portal>
```

### listPortalVisitors(id)

A portal's invited visitors (#205)

```kotlin
fun listPortalVisitors(id: String): List<Person>
```

### listProfiles()

List AI profiles

```kotlin
fun listProfiles(): List<JsonObject>
```

### listRunningModels()

Loaded model instances on this and paired computers

```kotlin
fun listRunningModels(): List<RunningModelView>
```

### listRuns(conversationId, limit)

Recent run traces, newest first

```kotlin
fun listRuns(conversationId: String? = null, limit: Long? = null): Unit
```

### listRuntimes()

Runtimes and whether each is installed

```kotlin
fun listRuntimes(): List<RuntimeInfo>
```

### listTasks()

Recent tasks

```kotlin
fun listTasks(): List<Task>
```

### listToolRuns(toolId, conversationId, limit)

Audited tool calls, newest first; records expire with run records

```kotlin
fun listToolRuns(toolId: String? = null, conversationId: String? = null, limit: Long? = null): List<ToolRun>
```

### listTools()

Every tool's descriptor, with whether it is on, its health, and the profiles that allow it

```kotlin
fun listTools(): List<ToolDescriptor>
```

### listTrainingJobs(aiId)

Training jobs

```kotlin
fun listTrainingJobs(aiId: String? = null): List<TrainingJob>
```

### makeAutomationHook(id)

Make a webhook trigger's link

Returns a new token, the only time it's shown; only its hash is kept. The old link stops working.

```kotlin
fun makeAutomationHook(id: String): HookLink
```

### manageSubscription()

The billing page for the subscription bought here (#639)

Answers {url}, Stripe's billing page for the subscription bought in Settings: change the card, download receipts, cancel. Admins only. 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy; 404 SUBSCRIPTION_NONE when none was bought here (one bought in the Toskar app is managed in the device's store); 502 BILLING_UNAVAILABLE.

```kotlin
fun manageSubscription(): Unit
```

### markNotificationsRead(body)

Mark notifications read; no ids marks all of them

```kotlin
fun markNotificationsRead(body: MarkNotificationsReadRequest? = null): Unit
```

### markOnTopic(id, aid)

Mark an off-topic attempt as on topic (#345)

Adds its message to the profile's example questions and forgets the attempts with that message.

```kotlin
fun markOnTopic(id: String, aid: String): Unit
```

### mcpGallery()

Gallery entries, with programs that are missing and sources already added

```kotlin
fun mcpGallery(): Unit
```

### mcpImportCandidates()

MCP servers set up in other apps on this computer, with secret values hidden

```kotlin
fun mcpImportCandidates(): Unit
```

### mcpOAuthCallback()

Where a tool source's sign-in returns; shows a page that says how it went

```kotlin
fun mcpOAuthCallback(): Unit
```

### mcpServer(body)

Toskar's MCP server (Streamable HTTP, JSON-RPC). Tools ask_local_ai, list_local_models, search_my_knowledge.

Checked like /v1. A request with an Origin header from another site is refused.

```kotlin
fun mcpServer(body: JsonObject? = null): Unit
```

### mcpServerDelete()

End an MCP session

```kotlin
fun mcpServerDelete(): Unit
```

### mcpServerGet()

Not supported; the server does not open a stream

```kotlin
fun mcpServerGet(): Unit
```

### mcpServerLogs(id)

Recent log lines of a tool source

```kotlin
fun mcpServerLogs(id: String): Unit
```

### mcpServerPrompts(id)

The tool source's ready-made prompts

```kotlin
fun mcpServerPrompts(id: String): Unit
```

### mcpServerResources(id)

The tool source's resources

```kotlin
fun mcpServerResources(id: String): Unit
```

### mcpShare()

The address and command other apps use to reach Toskar's MCP server

```kotlin
fun mcpShare(): Unit
```

### modelsFit()

How well each catalog model fits this computer

```kotlin
fun modelsFit(): List<ModelsFit>
```

### oidcCallback(state, code)

Where the provider sends people back (#206)

Checks the state against this browser's cookie, swaps the code for an ID token and checks it, signs the browser in, and redirects to the path it started from. A failure redirects to /?oidc_error= failed, refused, disabled, or unavailable.

```kotlin
fun oidcCallback(state: String? = null, code: String? = null): Unit
```

### openaiChatCompletions(body)

OpenAI-compatible chat completions

temperature and max_tokens apply to the calls that write the answer (#70). The toskar object asks for memory, knowledge, tools, effort, and placement, within what the API key allows. yggdrasil, its name from before the rename, works too; toskar wins when both are sent. Responses carry the answer's extension fields under both names.

```kotlin
fun openaiChatCompletions(body: OpenaiChatCompletionsRequest): OpenAIChatCompletion
```

### openaiListModels()

OpenAI-compatible model list

auto, each profile as profile:<id>, and each deployed specialized AI as sai:<slug>.

```kotlin
fun openaiListModels(): OpenAIModelList
```

### outboundPairing(code)

The offer this computer made for a code

```kotlin
fun outboundPairing(code: String): PairingOffer
```

### pairDevice(body)

A phone exchanges the code for its own key (no key needed; local network only)

```kotlin
fun pairDevice(body: PairDeviceRequest): PairedDevice
```

### pairNode(body)

Offer to pair with a discovered computer

```kotlin
fun pairNode(body: PairNodeRequest): PairingSession
```

### parseAutomation(body)

Read a request such as "every morning at 8, tell me if the price is below $500" into an automation

```kotlin
fun parseAutomation(body: ParseAutomationRequest): AutomationRequest
```

### parseMCP(body)

Read pasted settings, a web address, or a command line into server specs and what each still needs

```kotlin
fun parseMCP(body: ParseMCPRequest? = null): Unit
```

### pauseAutomation(id)

Pause an automation

```kotlin
fun pauseAutomation(id: String): Automation
```

### peekInvite(token)

What a one-time sign-in link is for (#206)

```kotlin
fun peekInvite(token: String): Invite
```

### pendingPairings()

Pairing offers waiting for approval on this computer

```kotlin
fun pendingPairings(): List<PairingOffer>
```

### peopleActivity(person, limit)

Who changed whom (#592)

Newest first. Adding, changing, disabling, removing, setting passwords, making links, and revoking keys and devices; never a password.

Parameters:

- `person`: Only entries by or about this person.
- `limit`: At most this many, 100 by default and 500 at most.

```kotlin
fun peopleActivity(person: String? = null, limit: Long? = null): List<ActivityEntry>
```

### personCapabilities(id)

What one person may use (#589)

```kotlin
fun personCapabilities(id: String): PersonCapabilities
```

### personDevices(id)

A person's connected devices (#592)

```kotlin
fun personDevices(id: String): List<APIKey>
```

### personKeys(id)

A person's API keys, other than their devices (#592)

```kotlin
fun personKeys(id: String): List<APIKey>
```

### personLink(id)

A new one-time link for a person; a reset link once they have a sign-in

```kotlin
fun personLink(id: String): InviteLink
```

### portalVisitorLink(id, vid)

A new link for an invited visitor (#205)

Replaces any link they haven't used.

```kotlin
fun portalVisitorLink(id: String, vid: String): VisitorLink
```

### previewAutomation(body)

Check an automation and show its next runs without saving it

```kotlin
fun previewAutomation(body: AutomationInput): AutomationPreview
```

### previewModelFromURL(body)

What a download from a URL would bring, without downloading it

The file and its size (and its vision projector's) from the repository, the free space where models are kept, whether it's already a model here, and copies of the same file other apps have (by name, Ollama's SHA-256 blob, or a large file's exact size), which can be added where they are instead (#611).

```kotlin
fun previewModelFromURL(body: InstallFromURLRequest): URLPreview
```

### putLicense(xToskarShell, body)

Set Toskar Pro's trial or Unlock (the desktop app only)

Only the Toskar Pro desktop app on this computer, with the `X-Toskar-Shell` secret it started Core with (`TOSKAR_SHELL_SECRET`). Anything else gets 403 `SHELL_ONLY`.

```kotlin
fun putLicense(xToskarShell: String, body: PutLicenseRequest): License
```

### putModelRating(id, body)

Rate a model 1–5 stars, and share the rating with the community or keep it on this computer

Sharing sends the stars, tags, model identity, hardware class, a random rating ID, and the app version to the ratings service. `share` false withdraws a rating that was shared. A 502 means the rating was saved here but the service could not be reached.

```kotlin
fun putModelRating(id: String, body: PutModelRatingRequest): ModelRating
```

### putRelayToken()

Hand over a subscription's relay token (#456)

Body {token, enable}. token is the route token the app got for this computer by exchanging a store receipt with Toskar's relay; the computer keeps it and registers and keeps its tunnel there. A paired device may send it, from home or through the remote listener. enable also turns access from anywhere on, and needs an Admin (403 ROLE_REQUIRED). Answers state: the relay client's state, or off. 400 RELAY_TOKEN_INVALID for a token that isn't for this computer's route or has expired, RELAY_TOKEN_NOT_NEEDED when an organization's relay is set.

```kotlin
fun putRelayToken(): Unit
```

### putSettings(body)

Update settings (same as PATCH)

```kotlin
fun putSettings(body: JsonObject): JsonObject
```

### readAloud(body)

Read text aloud on this computer; the audio is kept as a file in the chat

```kotlin
fun readAloud(body: ReadAloudRequest): SpokenText
```

### receivePairingOffer(body)

Receive a pairing offer from another computer

```kotlin
fun receivePairingOffer(body: PairingOffer): PairingSession
```

### recommendModels(purpose)

Recommended models for this computer

Parameters:

- `purpose`: What the model is for, such as chat or coding

```kotlin
fun recommendModels(purpose: String? = null): Recommendation
```

### refreshKnowledgeSource(id)

Reindex a source; a failure is recorded on the source

```kotlin
fun refreshKnowledgeSource(id: String): KnowledgeSource
```

### refreshNodes()

Look for computers again

```kotlin
fun refreshNodes(): OK
```

### registerPush(body)

Register this device's push handle

A paired phone or tablet gives the sealed handle the push relay made from its push token. Only a paired device's key may; another gets PUSH_DEVICE_ONLY. The computer never sees the token. Disconnecting the device ends its pushes.

```kotlin
fun registerPush(body: RegisterPushRequest): PushStatus
```

### removeImageModel(id)

Delete an installed image model to free its space

```kotlin
fun removeImageModel(id: String): ImageSetup
```

### removeMCPServer(id)

Stop a tool source, remove its tools, and delete its stored secrets

```kotlin
fun removeMCPServer(id: String): Unit
```

### removePerson(id, body, transferTo)

Remove a person (#592)

Revokes their keys and devices, signs them out, and deletes their data or gives it to transfer_to. Nobody removes themselves or the Owner, and only the Owner removes Admins. The body's confirm must be their name.

Parameters:

- `transferTo`: A person to give their chats, memories, automations, files, and notifications to, instead of deleting them.

```kotlin
fun removePerson(id: String, body: RemovePersonRequest, transferTo: String? = null): Unit
```

### removePortalVisitor(id, vid)

Remove an invited visitor (#205)

They're disabled and signed out at once.

```kotlin
fun removePortalVisitor(id: String, vid: String): Unit
```

### removeVideoModel(id)

Delete an installed video model to free its space

```kotlin
fun removeVideoModel(id: String): ImageSetup
```

### replaceMCPServer(id, body)

Change how a tool source is reached, then check it. Blank secret values keep the stored ones.

```kotlin
fun replaceMCPServer(id: String, body: ReplaceMCPServerRequest? = null): Unit
```

### resetApp(body, deleteModels)

Reset application to defaults

Clears chats, custom profiles, tasks, and API keys; restores settings and built-in profiles. Downloaded models and runtimes are kept unless delete_models is true. The client should clear local UI state and restart onboarding. Not reversible.

```kotlin
fun resetApp(body: ResetAppRequest? = null, deleteModels: String? = null): JsonObject
```

### resetProfile(id)

Put a built-in profile back to how Toskar ships it

```kotlin
fun resetProfile(id: String): JsonObject
```

### resumeAutomation(id)

Resume an automation

```kotlin
fun resumeAutomation(id: String): Automation
```

### revokeJoinToken(id)

Revoke an unused join token

```kotlin
fun revokeJoinToken(id: String): JoinToken
```

### revokeNode(id)

Stop trusting a paired computer

```kotlin
fun revokeNode(id: String): Unit
```

### revokePersonDevice(id, key)

Disconnect one of a person's devices (#592)

```kotlin
fun revokePersonDevice(id: String, key: String): Unit
```

### revokePersonKey(id, key)

Revoke one of a person's keys (#592)

```kotlin
fun revokePersonKey(id: String, key: String): Unit
```

### roleCapabilities()

What each role may use (#589)

Every capability in order, each role's, and the defaults each role ships with. The Owner always has everything.

```kotlin
fun roleCapabilities(): RoleCapabilities
```

### rotateAPIKey(id)

Replace a key's secret; the old one stops working

```kotlin
fun rotateAPIKey(id: String): NewAPIKey
```

### rotateNotificationSecret(id)

Replace a webhook's signing secret; the old one stops working

```kotlin
fun rotateNotificationSecret(id: String): DestinationSecret
```

### runAutomation(id)

Run an automation now

```kotlin
fun runAutomation(id: String): AutomationRunInfo
```

### runHook(token, body)

Start the automation a webhook link belongs to

The token in the link is the only proof, so this needs no API key. The request body (up to 64 KB, any type) goes to the run as data from the caller, never as instructions. One automation's link takes a call at most every 10 seconds.

```kotlin
fun runHook(token: String, body: String? = null): HookRun
```

### searchKnowledge(body)

Search connected knowledge

```kotlin
fun searchKnowledge(body: SearchKnowledgeRequest): List<KnowledgeHit>
```

### sendReport()

Send a problem report to Toskar (#588)

Body {product (core, the default, or apps), app, where, code, error, note, email, details}. Core scrubs the error and note as it scrubs its own report, adds that report when details is true, and sends it to Toskar's report service (https://toskar.ai/api/report, or TOSKAR_REPORT_URL), which files it as an issue in a private repository, grouped with others for the same error and version. A reply address goes to the Toskar team by email, never into the issue. Answers {status: created or added, number}. Each one is listed in What left this computer as problem_report. Members and paired devices may send. 400 REPORT_INVALID; 403 REPORTS_OFF when an Admin turned problem_reports off; 429 REPORT_RATE_LIMITED; 502 REPORTS_UNAVAILABLE when the service can't be reached or isn't set up, for the client to send by email instead (contract 1.40).

```kotlin
fun sendReport(): Unit
```

### setAPIKeyPermissions(id, body)

Change what an API key may ask of the assistant

```kotlin
fun setAPIKeyPermissions(id: String, body: SetAPIKeyPermissionsRequest? = null): Unit
```

### setExternalServer(body)

Set the external server's base URL and API key

The key is stored in the secrets folder and never returned. An empty api_key keeps the stored one; clear_key removes it; an empty base_url turns the server off.

```kotlin
fun setExternalServer(body: SetExternalServerRequest): ExternalServer
```

### setModelProjector(id, body)

Give an added model its vision projector

A GGUF vision projector (mmproj) on this computer, copied beside the model so it can see pictures (#467).

```kotlin
fun setModelProjector(id: String, body: SetModelProjectorRequest): ModelVision
```

### setMyPreferences(body)

Save your own languages (#206)

The request's person's App language and assistant language, whatever their role. The Owner's are the install's, which others start from until they choose. Answers with the person's settings.

```kotlin
fun setMyPreferences(body: SetMyPreferencesRequest): JsonObject
```

### setPersonalization(body)

Save how the person likes answers. Style only; it cannot grant a permission.

```kotlin
fun setPersonalization(body: PersonalStyle? = null): Unit
```

### setPersonCapabilities(id, body)

Allow or Block something for one person (#589)

true allows, false blocks, and null is as their role's. The Owner's are fixed.

```kotlin
fun setPersonCapabilities(id: String, body: Map<String, Boolean?>): PersonCapabilities
```

### setPersonProfiles(id, body)

Pin a Member or Visitor to profiles (#345)

profiles: a list replaces their role's pin, [] is any profile, and null is their role's again. The Owner and Admins can't be pinned.

```kotlin
fun setPersonProfiles(id: String, body: SetPersonProfilesRequest): Person
```

### setQuietHours(body)

Set quiet hours

```kotlin
fun setQuietHours(body: QuietHours): QuietHours
```

### setRoleCapabilities(role, body)

Change what a role may use (#589)

Only the Owner changes the Admins'. The Owner's are fixed.

```kotlin
fun setRoleCapabilities(role: String, body: Map<String, Boolean>): Map<String
```

### setRoleProfiles(role, body)

Pin a role to profiles (#345)

```kotlin
fun setRoleProfiles(role: String, body: SetRoleProfilesRequest): ProfilePins
```

### setRunRetention(body)

Set how long run records are kept; 0 keeps them

```kotlin
fun setRunRetention(body: SetRunRetentionRequest? = null): Unit
```

### setTestPrompts(id, body)

Set the prompts evaluation compares

Parameters:

- `id`: Specialized AI id

```kotlin
fun setTestPrompts(id: String, body: SetTestPromptsRequest): List<EvalPrompt>
```

### setToolEnabled(id, body)

Turn a tool on or off

```kotlin
fun setToolEnabled(id: String, body: SetToolEnabledRequest): ToolEnabled
```

### showMessageVersion(id, mid)

Show a version of its point in the chat, with what followed it (#447)

```kotlin
fun showMessageVersion(id: String, mid: String): List<Message>
```

### signIn(body)

Sign in with a username and password (#206)

Sets the session cookie. Five failures for a username in 15 minutes, or twenty from an address in ten, answer 429 SIGN_IN_THROTTLED for a while.

```kotlin
fun signIn(body: SignInRequest): Principal
```

### signInMCPServer(id, body)

Start signing in to the tool source's service; returns the address to open

```kotlin
fun signInMCPServer(id: String, body: SignInMCPServerRequest? = null): Unit
```

### signOut()

Sign out this browser

```kotlin
fun signOut(): Unit
```

### signOutMCPServer(id)

Forget the tool source's sign-in

```kotlin
fun signOutMCPServer(id: String): Unit
```

### startBenchmark(body)

Start a multi-model benchmark

```kotlin
fun startBenchmark(body: JsonObject): JsonObject
```

### startDevicePairing(body)

Show a 6-digit code a phone connects with, replacing any other

```kotlin
fun startDevicePairing(body: StartDevicePairingRequest? = null): DevicePairing
```

### startImageSetup(body)

Install stable-diffusion.cpp and an image model in the background

```kotlin
fun startImageSetup(body: StartImageSetupRequest): ImageSetup
```

### startModel(id, body)

Load a model

```kotlin
fun startModel(id: String, body: StartModelRequest? = null): RunningModelView
```

### startOIDC()

Go to the provider to sign in (#206)

Redirects to the provider with PKCE, and sets a short-lived cookie with the sign-in's state. return is the path in Toskar to go to afterwards.

```kotlin
fun startOIDC(`return`: String? = null): Unit
```

### startSubscriptionCheckout()

Subscribe to access from anywhere here, with Stripe (#639)

Body {plan}: monthly or yearly. Opens a Stripe checkout at yeix.io, which bills for Toskar, for this computer's route on Toskar's relay, and answers {url}, its page, for the person to open. Toskar then asks the relay every few seconds whether it's paid; once it is, it keeps the relay token, turns access from anywhere on, and renews the token as the subscription does. Admins only. 400 SUBSCRIPTION_PLAN_INVALID; 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy, SUBSCRIPTION_OWN_RELAY with an organization's relay, SUBSCRIPTION_ACTIVE when this computer already has a current token; 503 RELAY_SOLD_OUT when Toskar's relay takes no new subscriptions; 502 BILLING_UNAVAILABLE.

```kotlin
fun startSubscriptionCheckout(): Unit
```

### startTraining(id, body)

Start training

Parameters:

- `id`: Specialized AI id

```kotlin
fun startTraining(id: String, body: StartTrainingRequest? = null): TrainingJob
```

### startVideoSetup(body)

Install stable-diffusion.cpp and a video model in the background

```kotlin
fun startVideoSetup(body: StartVideoSetupRequest): ImageSetup
```

### stopChat(body)

Stop a conversation's running turn

```kotlin
fun stopChat(body: StopChatRequest): ChatStopped
```

### stopModel(id, body)

Unload a model instance

```kotlin
fun stopModel(id: String, body: StopModelRequest? = null): OK
```

### testNotificationDestination(id)

Send a test notification now

```kotlin
fun testNotificationDestination(id: String): OK
```

### testTool(id, body)

Run a tool once with the given arguments

```kotlin
fun testTool(id: String, body: TestToolRequest): JsonObject
```

### toolActivity()

Recent tool calls and pending approvals

```kotlin
fun toolActivity(): List<ToolActivity>
```

### toolProviders()

Each computer's providers for tools that can run on any paired computer, and their state

```kotlin
fun toolProviders(): List<NodeToolProviders>
```

### trainingBackends()

Trainers on this computer and whether each can run

```kotlin
fun trainingBackends(): List<TrainingBackend>
```

### trainingBaseModels(goal)

Trainable base models, ranked for a goal

```kotlin
fun trainingBaseModels(goal: String? = null): List<TrainingBaseModel>
```

### trainingPlan(id)

Training plan: fit, downloads, disk, time, and the computer to train on

Parameters:

- `id`: Specialized AI id

```kotlin
fun trainingPlan(id: String): TrainingPlan
```

### trainingSamples()

Sample material files

```kotlin
fun trainingSamples(): List<TrainingSample>
```

### transcribeRecording(body)

A recording's text, for speaking a message instead of typing it (yeixio/toskar-apps#155)

The recording is attached first with POST /api/v1/artifacts (audio). Runs speech.transcribe (Whisper) on this computer or a paired one that has it, and answers the text for the person to check before sending. Visitors and paired devices may use it.

```kotlin
fun transcribeRecording(body: TranscribeRecordingRequest): Transcription
```

### tryTopics(id, body)

Try one message against a profile's topic controls (#345)

message (up to 2000 characters), and optional topics: draft topic controls used in place of the saved ones. Nothing is saved. The answer is a quick one, without tools, knowledge, or memories.

```kotlin
fun tryTopics(id: String, body: TryTopicsRequest): Unit
```

### undeployAI(id)

Stop serving a specialized AI

Parameters:

- `id`: Specialized AI id

```kotlin
fun undeployAI(id: String): SpecializedAI
```

### unregisterPush()

Stop pushes to this device

```kotlin
fun unregisterPush(): Unit
```

### updateAddedModel(id, body)

Rename or retag an added model

For a model added from a file or a link; catalog models keep their own (#467). Tags are general, coding, reasoning, and writing; vision comes with a projector.

```kotlin
fun updateAddedModel(id: String, body: UpdateAddedModelRequest): AddedModel
```

### updateAI(id, body)

Update a specialized AI

Parameters:

- `id`: Specialized AI id

```kotlin
fun updateAI(id: String, body: UpdateAIRequest): SpecializedAI
```

### updateAutomation(id, body)

Change only the fields given

```kotlin
fun updateAutomation(id: String, body: AutomationInput): Automation
```

### updateConversation(id, body)

Update conversation

```kotlin
fun updateConversation(id: String, body: UpdateConversationRequest? = null): Conversation
```

### updateExample(id, eid, body)

Edit or exclude an example

Parameters:

- `id`: Specialized AI id

```kotlin
fun updateExample(id: String, eid: String, body: UpdateExampleRequest): Unit
```

### updateKnowledgeSource(id, body)

Rename a source, replace a text source's content, or change its connection

```kotlin
fun updateKnowledgeSource(id: String, body: UpdateKnowledgeSourceRequest): KnowledgeSource
```

### updateMCPServer(id, body)

Change enabled, allow_sampling, always_offer, keywords, or per-tool policies (allow, ask, default)

```kotlin
fun updateMCPServer(id: String, body: JsonObject? = null): Unit
```

### updateMemory(id, body)

Edit, turn off, or keep a memory on this computer only

```kotlin
fun updateMemory(id: String, body: UpdateMemoryRequest): Memory
```

### updateNotificationDestination(id, body)

Change a destination; an empty password keeps the stored one

```kotlin
fun updateNotificationDestination(id: String, body: NotificationDestinationInput): NotificationDestination
```

### updatePortal(id, body)

Change a chat portal (#205)

Any of slug, name, profile_id, tools (none, read_only, profile), memory, language, access (open, passcode), passcode (empty removes it), branding (a JSON object), and enabled. Turning it off stops its visitors at once.

```kotlin
fun updatePortal(id: String, body: JsonObject): Portal
```

### updateProfile(id, body)

Update a profile, including its orchestration controls

```kotlin
fun updateProfile(id: String, body: JsonObject): JsonObject
```

### updateSettings(body)

Update settings

```kotlin
fun updateSettings(body: JsonObject): JsonObject
```

### uploadArtifact(body)

Upload a file to attach to a chat (up to 25 MB)

```kotlin
fun uploadArtifact(body: UploadArtifactRequest): Artifact
```

### useImageBuild(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

```kotlin
fun useImageBuild(body: UseImageBuildRequest): ImageSetup
```

### useVideoBuild(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

```kotlin
fun useVideoBuild(body: UseVideoBuildRequest): ImageSetup
```

### warmModel(body)

Start loading the model a chat would use

Starts loading, in the background, the model a chat on the profile would use, and answers at once (#498), so it loads while someone types or speaks. Never loads beside a model that is answering, nor one that wouldn't fit beside those already loaded.

```kotlin
fun warmModel(body: WarmModelRequest? = null): ModelWarmResponse
```
