# Every route on `toskar.Api`

*Generated from `Generated/ToskarApi.cs`, which `dotnet/scripts/generate.py` writes from Toskar Core's API spec.*

One async method for each operation, named after its operationId, and each takes a `CancellationToken`. An error answer throws a `ToskarException`. The models are in `Toskar.Models` (`M.` below), and every field is described at [toskar.ai/developers/api](https://toskar.ai/developers/api).

### AcceptInviteAsync(token, body)

Use a one-time link to set a username and password, or a new password, and sign in

Parameters:

- `token`: The token.
- `body`: The request.

```csharp
Task<M.Principal> AcceptInviteAsync(string token, M.AcceptInviteRequest body, CancellationToken cancellationToken = default)
```

### AddCompanionDeviceAsync(body)

Connect a companion device, such as a watch with its phone

A connected device asks for a key of its own for a device that goes along with it (yeixio/toskar-apps#213), for the same person, so it shows in Devices and can be disconnected on its own. It works from anywhere, as no code is typed. The answer is the same as POST /devices/pair's. A person may have 20 connected devices.

Parameters:

- `body`: The request.

```csharp
Task<M.PairedDevice> AddCompanionDeviceAsync(M.AddCompanionDeviceRequest body, CancellationToken cancellationToken = default)
```

### AddConversationsAsync(id, body)

Add chats as training material

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task<M.TrainingMaterial> AddConversationsAsync(string id, M.AddConversationsRequest body, CancellationToken cancellationToken = default)
```

### AddExampleAsync(id, body)

Add an example

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task AddExampleAsync(string id, M.AddExampleRequest body, CancellationToken cancellationToken = default)
```

### AddMaterialAsync(id, body)

Add material

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task<M.TrainingMaterial> AddMaterialAsync(string id, M.AddMaterialRequest body, CancellationToken cancellationToken = default)
```

### AddMCPServerAsync(body)

Check a tool source connects and list its tools, then store it and add the tools

Send a gallery entry ({"preset", "values"}), a spec ({"spec", "values"}), or a server from another app ({"import": {"app", "name"}}). redirect_base is the address the browser uses, for a sign-in. When the service needs a sign-in, the source is stored and sign_in_url is returned.

Parameters:

- `body`: The request.

```csharp
Task AddMCPServerAsync(M.AddMCPServerRequest? body = null, CancellationToken cancellationToken = default)
```

### AddMemoryAsync(body)

Add a memory; an existing equal memory is returned instead

Parameters:

- `body`: The request.

```csharp
Task<M.Memory> AddMemoryAsync(M.AddMemoryRequest body, CancellationToken cancellationToken = default)
```

### AddPersonAsync(body)

Add a person and make their invite link (Admins add Members and Visitors; the Owner adds Admins too)

Parameters:

- `body`: The request.

```csharp
Task<M.AddedPerson> AddPersonAsync(M.AddPersonRequest body, CancellationToken cancellationToken = default)
```

### ApprovePairingAsync(id, body)

Approve a pairing offer

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.PairingSession> ApprovePairingAsync(string id, M.ApprovePairingRequest? body = null, CancellationToken cancellationToken = default)
```

### BrowseModelsAsync(q, limit)

Search Hugging Face for GGUF models

Parameters:

- `q`: The q.
- `limit`: The limit.

```csharp
Task<List<M.BrowseModel>> BrowseModelsAsync(string? q = null, long? limit = null, CancellationToken cancellationToken = default)
```

### CancelBenchmarkAsync(id)

Cancel a running benchmark

Parameters:

- `id`: The id.

```csharp
Task<M.OK> CancelBenchmarkAsync(string id, CancellationToken cancellationToken = default)
```

### CancelDevicePairingAsync()

Stop showing the code

```csharp
Task CancelDevicePairingAsync(CancellationToken cancellationToken = default)
```

### CancelImageSetupAsync()

Stop the setup in progress; what was downloaded is kept and resumed next time

```csharp
Task<M.ImageSetup> CancelImageSetupAsync(CancellationToken cancellationToken = default)
```

### CancelTrainingJobAsync(id)

Cancel a training job

Parameters:

- `id`: The id.

```csharp
Task<M.TrainingJob> CancelTrainingJobAsync(string id, CancellationToken cancellationToken = default)
```

### CancelVideoSetupAsync()

Stop the setup in progress; what was downloaded is kept and resumed next time

```csharp
Task<M.ImageSetup> CancelVideoSetupAsync(CancellationToken cancellationToken = default)
```

### ChangeMyPasswordAsync(body)

Change your own password (#592)

With your current one. A password an Admin set with must_change is changed here before anything else works; until then other routes answer PASSWORD_CHANGE_REQUIRED. You're signed out everywhere else.

Parameters:

- `body`: The request.

```csharp
Task<M.Principal> ChangeMyPasswordAsync(M.ChangeMyPasswordRequest body, CancellationToken cancellationToken = default)
```

### ChangePersonAsync(id, body)

Rename, change the role of, disable, or enable a person

The Owner's role is fixed and they can't be disabled; nobody changes their own role or disables themselves. Disabling signs the person out everywhere and stops their keys.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Person> ChangePersonAsync(string id, M.ChangePersonRequest body, CancellationToken cancellationToken = default)
```

### ChatAsync(body)

Send a chat message

Without stream, returns {content, metrics}. With stream, a server-sent event stream of token events, then done; an error event ends it early.

Parameters:

- `body`: The request.

```csharp
Task<M.ChatAnswer> ChatAsync(M.ChatRequest body, CancellationToken cancellationToken = default)
```

### CheckConnectorAsync(id)

Check the stored credential again

Parameters:

- `id`: The id.

```csharp
Task CheckConnectorAsync(string id, CancellationToken cancellationToken = default)
```

### CheckMCPServerAsync(id)

Connect again and list the tools

Parameters:

- `id`: The id.

```csharp
Task CheckMCPServerAsync(string id, CancellationToken cancellationToken = default)
```

### CheckRemoteAccessAsync()

Check access from anywhere from outside, now (#546)

The relay reaches this computer from the internet, through its tunnel and each direct way in, as a paired device away from home does: TLS to this computer's certificate and GET /api/v1/health. It also runs on its own every 30 minutes and after the relay connects or the ways in change. Answers what GET /api/v1/remote-access does, with check updated. Admins only. 409 REMOTE_ACCESS_OFF when access from anywhere is off or its listener isn't up.

```csharp
Task CheckRemoteAccessAsync(CancellationToken cancellationToken = default)
```

### ClaimPairingAsync(body)

Pair using the code shown on the other computer

Parameters:

- `body`: The request.

```csharp
Task<M.PairingSession> ClaimPairingAsync(M.ClaimPairingRequest body, CancellationToken cancellationToken = default)
```

### ClassifyMaterialAsync(body)

Recommend whether material is for training, knowledge, or both

Parameters:

- `body`: The request.

```csharp
Task<M.ClassifiedMaterial> ClassifyMaterialAsync(M.ClassifyMaterialRequest body, CancellationToken cancellationToken = default)
```

### ClearCacheAsync(name)

Clear one cache

Parameters:

- `name`: The name.

```csharp
Task ClearCacheAsync(string name, CancellationToken cancellationToken = default)
```

### CompactConversationAsync(id)

Compact a chat now (#342)

Summarizes its older messages whatever its size, keeping the newest verbatim. NOTHING_TO_COMPACT for a chat too short.

Parameters:

- `id`: The id.

```csharp
Task<M.ConversationSummary> CompactConversationAsync(string id, CancellationToken cancellationToken = default)
```

### ConnectServiceAsync(id, body)

Check values with the service, then store them and add its tools

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task ConnectServiceAsync(string id, M.ConnectServiceRequest? body = null, CancellationToken cancellationToken = default)
```

### ContinueAutomationRunAsync(id, runId)

Open a run's result in a chat to reply to

Returns the chat the result was already posted to, or makes one with the result as its first answer, marked with meta.automation_run.

Parameters:

- `id`: The id.
- `runId`: The runId.

```csharp
Task<M.ContinuedRun> ContinueAutomationRunAsync(string id, string runId, CancellationToken cancellationToken = default)
```

### ConversationFromSummaryAsync(id)

A new chat that begins with this chat's summary (#342)

Parameters:

- `id`: The id.

```csharp
Task<M.Conversation> ConversationFromSummaryAsync(string id, CancellationToken cancellationToken = default)
```

### CreateAIAsync(body)

Create a specialized AI

Parameters:

- `body`: The request.

```csharp
Task<M.SpecializedAI> CreateAIAsync(M.CreateAIRequest body, CancellationToken cancellationToken = default)
```

### CreateAPIKeyAsync(body)

Create an API key; the secret is shown only in this response

Parameters:

- `body`: The request.

```csharp
Task<M.NewAPIKey> CreateAPIKeyAsync(M.CreateAPIKeyRequest body, CancellationToken cancellationToken = default)
```

### CreateAutomationAsync(body)

Create an automation

Parameters:

- `body`: The request.

```csharp
Task<M.Automation> CreateAutomationAsync(M.AutomationInput body, CancellationToken cancellationToken = default)
```

### CreateConversationAsync(body)

Create conversation

Parameters:

- `body`: The request.

```csharp
Task<M.Conversation> CreateConversationAsync(M.CreateConversationRequest? body = null, CancellationToken cancellationToken = default)
```

### CreateDiagnosticsAsync(body)

Create a diagnostics bundle

Parameters:

- `body`: The request.

```csharp
Task<M.DiagnosticsBundle> CreateDiagnosticsAsync(M.CreateDiagnosticsRequest? body = null, CancellationToken cancellationToken = default)
```

### CreateExampleAIAsync()

Create the example specialized AI

```csharp
Task<M.SpecializedAI> CreateExampleAIAsync(CancellationToken cancellationToken = default)
```

### CreateJoinTokenAsync(body)

Make a one-time join token and the command that adds a computer to this network

The token is shown once and only its proof key is kept. It lasts `ttl_minutes` (15 by default, at most 1440) and can be used once. Refused with 409 when other computers can't reach this one's Bifrost.

Parameters:

- `body`: The request.

```csharp
Task<M.JoinTokenCreated> CreateJoinTokenAsync(M.CreateJoinTokenRequest? body = null, CancellationToken cancellationToken = default)
```

### CreateKnowledgeSourceAsync(body)

Connect a file, folder, upload, pasted text, database, or web API

Parameters:

- `body`: The request.

```csharp
Task<M.KnowledgeSource> CreateKnowledgeSourceAsync(M.CreateKnowledgeSourceRequest body, CancellationToken cancellationToken = default)
```

### CreateNotificationDestinationAsync(body)

Add an email or webhook destination; a webhook's signing secret is returned this once

Parameters:

- `body`: The request.

```csharp
Task<M.CreatedDestination> CreateNotificationDestinationAsync(M.NotificationDestinationInput body, CancellationToken cancellationToken = default)
```

### CreatePortalAsync(body)

Add a chat portal (#205)

slug (2 to 40 lowercase letters, digits, or dashes) and name are required. It starts with no tools, no memory, passcode access (passcode required), and on.

Parameters:

- `body`: The request.

```csharp
Task<M.Portal> CreatePortalAsync(JsonObject body, CancellationToken cancellationToken = default)
```

### CreateProfileAsync(body)

Create a profile

Parameters:

- `body`: The request.

```csharp
Task<JsonObject> CreateProfileAsync(JsonObject body, CancellationToken cancellationToken = default)
```

### CreateTaskAsync(body)

Run a prompt as a task

Parameters:

- `body`: The request.

```csharp
Task<M.ToskarTask> CreateTaskAsync(M.CreateTaskRequest body, CancellationToken cancellationToken = default)
```

### DecideToolAsync(body)

Answer a tool approval request

Parameters:

- `body`: The request.

```csharp
Task<M.Status> DecideToolAsync(M.DecideToolRequest body, CancellationToken cancellationToken = default)
```

### DeleteAIAsync(id)

Delete a specialized AI

Parameters:

- `id`: Specialized AI id

```csharp
Task DeleteAIAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteAPIKeyAsync(id)

Delete an API key

Parameters:

- `id`: The id.

```csharp
Task DeleteAPIKeyAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteArtifactAsync(id)

Delete a file

Parameters:

- `id`: The id.

```csharp
Task DeleteArtifactAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteAutomationAsync(id)

Delete an automation

Parameters:

- `id`: The id.

```csharp
Task DeleteAutomationAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteConversationAsync(id)

Delete conversation

Parameters:

- `id`: The id.

```csharp
Task DeleteConversationAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteConversationsAsync(body)

Delete several conversations

Deletes the caller's chats among ids, with their messages and files, in one request (#452, contract 1.25). Another person's chat, or one that doesn't exist, is skipped as not_found.

Parameters:

- `body`: The request.

```csharp
Task<M.ConversationsDeleted> DeleteConversationsAsync(M.DeleteConversationsRequest body, CancellationToken cancellationToken = default)
```

### DeleteExampleAsync(id, eid)

Delete an example

Parameters:

- `id`: Specialized AI id
- `eid`: The eid.

```csharp
Task DeleteExampleAsync(string id, string eid, CancellationToken cancellationToken = default)
```

### DeleteExportAsync(id, rev)

Delete an exported file

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task DeleteExportAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### DeleteKnowledgeSourceAsync(id)

Remove a source and its index

Parameters:

- `id`: The id.

```csharp
Task DeleteKnowledgeSourceAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteMaterialAsync(id, mid)

Remove material

Parameters:

- `id`: Specialized AI id
- `mid`: The mid.

```csharp
Task DeleteMaterialAsync(string id, string mid, CancellationToken cancellationToken = default)
```

### DeleteMemoryAsync(id)

Delete a memory

Parameters:

- `id`: The id.

```csharp
Task DeleteMemoryAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteModelAsync(id, body, nodeId)

Delete a model file

Parameters:

- `id`: The id.
- `body`: The request.
- `nodeId`: The nodeId.

```csharp
Task DeleteModelAsync(string id, M.DeleteModelRequest? body = null, string? nodeId = null, CancellationToken cancellationToken = default)
```

### DeleteModelRatingAsync(id)

Remove this person's rating, withdrawing it first if it was shared

Parameters:

- `id`: The id.

```csharp
Task DeleteModelRatingAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteNotificationDestinationAsync(id)

Remove a destination, its stored secret, and its waiting deliveries

Parameters:

- `id`: The id.

```csharp
Task DeleteNotificationDestinationAsync(string id, CancellationToken cancellationToken = default)
```

### DeletePortalAsync(id)

Remove a chat portal (#205)

Its guests can no longer chat.

Parameters:

- `id`: The id.

```csharp
Task DeletePortalAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteProfileAsync(id)

Delete a custom profile

Parameters:

- `id`: The id.

```csharp
Task DeleteProfileAsync(string id, CancellationToken cancellationToken = default)
```

### DeleteRunRecordsAsync()

Delete run records now

```csharp
Task DeleteRunRecordsAsync(CancellationToken cancellationToken = default)
```

### DeployedAIsAsync()

Deployed specialized AIs, as model ids sai:<slug>

```csharp
Task<List<M.Model>> DeployedAIsAsync(CancellationToken cancellationToken = default)
```

### DeployRevisionAsync(id, rev)

Deploy an evaluated revision

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task<M.SpecializedAI> DeployRevisionAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### DescribeToolAsync(id)

One tool's descriptor

Parameters:

- `id`: The id.

```csharp
Task<M.ToolDescriptor> DescribeToolAsync(string id, CancellationToken cancellationToken = default)
```

### DisconnectMyDeviceAsync(id)

Disconnect one of your devices (#206)

Parameters:

- `id`: The id.

```csharp
Task DisconnectMyDeviceAsync(string id, CancellationToken cancellationToken = default)
```

### DisconnectServiceAsync(id)

Delete the stored credential and remove the service's tools

Parameters:

- `id`: The id.

```csharp
Task DisconnectServiceAsync(string id, CancellationToken cancellationToken = default)
```

### DisconnectThisDeviceAsync()

Disconnect this device, with its companions (#766)

A device's own key disconnects it, as the apps do when the person removes this computer. Its key and its companions' keys, such as its watch's, are revoked, and their notifications stop.

```csharp
Task DisconnectThisDeviceAsync(CancellationToken cancellationToken = default)
```

### DismissModelRatingAsync(id)

Stop asking for a rating of a model

Parameters:

- `id`: The id.

```csharp
Task DismissModelRatingAsync(string id, CancellationToken cancellationToken = default)
```

### DismissNotificationAsync(id)

Hide a notification from the notification center

Parameters:

- `id`: The id.

```csharp
Task DismissNotificationAsync(string id, CancellationToken cancellationToken = default)
```

### DownloadExportAsync(id, rev)

Download the exported GGUF

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task<byte[]> DownloadExportAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### EditConversationSummaryAsync(id, body)

Correct a chat's summary (#342)

Later summaries keep the correction.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.ConversationSummary> EditConversationSummaryAsync(string id, M.EditConversationSummaryRequest body, CancellationToken cancellationToken = default)
```

### EnterPortalAsync(slug)

Enter a portal as its guest (#205)

With passcode when the portal has one. Makes this browser the portal's guest, signed in by a toskar_portal_<slug> cookie that counts only on requests carrying X-Toskar-Portal. A guest reaches only the portal's chat, with the portal's profile, tools, memory, and language.

Parameters:

- `slug`: The slug.

```csharp
Task<M.EnteredPortal> EnterPortalAsync(string slug, CancellationToken cancellationToken = default)
```

### EvaluateRevisionAsync(id, rev)

Compare a revision with the base model

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task<M.Evaluation> EvaluateRevisionAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### ExportDiagnosticsAsync(includeConversations)

Create a diagnostics bundle (a zip without secrets or private keys)

Parameters:

- `includeConversations`: The includeConversations.

```csharp
Task<M.DiagnosticsBundle> ExportDiagnosticsAsync(string? includeConversations = null, CancellationToken cancellationToken = default)
```

### ExportRevisionAsync(id, rev)

Export a revision as one GGUF file

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task<M.ExportStatus> ExportRevisionAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### ExportStatusAsync(id, rev)

Export status of a revision

Parameters:

- `id`: Specialized AI id
- `rev`: Revision number

```csharp
Task<M.ExportStatus> ExportStatusAsync(string id, string rev, CancellationToken cancellationToken = default)
```

### FindModelsInOtherAppsAsync()

Models other local AI apps keep on this computer

GGUF models LM Studio, Ollama (through its manifests), llama.cpp, and GPT4All already downloaded, to add with POST /api/v1/models/import without downloading them again. Only headers and Ollama's manifests are read; incomplete files and vision projectors are left out (#467). GGUF files put in Toskar's own models folder by hand that aren't models yet come first, as app toskar; one is always added in place (#763).

```csharp
Task<M.FoundModels> FindModelsInOtherAppsAsync(CancellationToken cancellationToken = default)
```

### GetAboutAsync()

AGPL corresponding-source offer

```csharp
Task<M.SourceOffer> GetAboutAsync(CancellationToken cancellationToken = default)
```

### GetAIAsync(id)

A specialized AI with its materials, revisions, and jobs

Parameters:

- `id`: Specialized AI id

```csharp
Task<M.SpecializedAI> GetAIAsync(string id, CancellationToken cancellationToken = default)
```

### GetApiTLSAsync()

How the API speaks HTTPS on the local network (#213)

```csharp
Task<M.TLSInfo> GetApiTLSAsync(CancellationToken cancellationToken = default)
```

### GetArtifactAsync(id)

One file

Parameters:

- `id`: The id.

```csharp
Task<M.Artifact> GetArtifactAsync(string id, CancellationToken cancellationToken = default)
```

### GetArtifactContentAsync(id, inline)

A file's content

Parameters:

- `id`: The id.
- `inline`: 1 shows a PDF or image in the browser instead of downloading it

```csharp
Task<byte[]> GetArtifactContentAsync(string id, string? inline = null, CancellationToken cancellationToken = default)
```

### GetAutomationAsync(id)

An automation with its run history

Parameters:

- `id`: The id.

```csharp
Task<M.AutomationDetail> GetAutomationAsync(string id, CancellationToken cancellationToken = default)
```

### GetBenchmarkAsync(id)

Get benchmark job status and results

Parameters:

- `id`: The id.

```csharp
Task<JsonObject> GetBenchmarkAsync(string id, CancellationToken cancellationToken = default)
```

### GetCapabilitiesAsync(ask)

Capability inventory: what Toskar can do right now

Parameters:

- `ask`: A question such as "Can you generate an image?"; returns the abilities that answer it

```csharp
Task<JsonNode?> GetCapabilitiesAsync(string? ask = null, CancellationToken cancellationToken = default)
```

### GetCommunityRatingsAsync()

Everyone's ratings of the models here, from hardware like this computer's and overall

Empty unless `community_ratings` is on. The public summary is downloaded at most once a day; when that fails, the last one is used and `error` says why.

```csharp
Task<M.CommunityRatings> GetCommunityRatingsAsync(CancellationToken cancellationToken = default)
```

### GetConversationSummaryAsync(id)

A chat's auto-compact summary (#342)

What the model sees in place of the chat's older messages, through which message. Every message stays saved.

Parameters:

- `id`: The id.

```csharp
Task<M.ConversationSummary> GetConversationSummaryAsync(string id, CancellationToken cancellationToken = default)
```

### GetDevicePairingAsync()

Whether a phone has connected with the code shown

```csharp
Task<M.DevicePairing> GetDevicePairingAsync(CancellationToken cancellationToken = default)
```

### GetExternalServerAsync()

The OpenAI-compatible server whose models can be chosen for a chat, and the models it offers

```csharp
Task<M.ExternalServer> GetExternalServerAsync(CancellationToken cancellationToken = default)
```

### GetFirstAnswersAsync(days)

How long answers took to start, by app, cold or warm

Chat runs that reached a first token, grouped by the app that asked (the chat request's client) and by whether a model had to load first. Automations are left out.

Parameters:

- `days`: How many days back to look; 7 by default, 90 at most.

```csharp
Task<M.FirstAnswers> GetFirstAnswersAsync(long? days = null, CancellationToken cancellationToken = default)
```

### GetGPUSetupAsync()

What this computer still needs for Toskar to use its GPU

The graphics card found and each missing piece, most basic first, with a fix written for this computer: the Vulkan loader or drivers, permission to open the card's render device, NVIDIA's driver, a Windows card's driver, or the CPU-only llama.cpp build. No problems when the GPU is ready, when there is no GPU, and on macOS.

```csharp
Task<M.GPUSetup> GetGPUSetupAsync(CancellationToken cancellationToken = default)
```

### GetHardwareAsync()

Local hardware inventory

```csharp
Task<JsonObject> GetHardwareAsync(CancellationToken cancellationToken = default)
```

### GetHealthAsync()

Health check

```csharp
Task<M.HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default)
```

### GetImageSetupAsync()

What image generation has installed, the models on offer, and any setup in progress

```csharp
Task<M.ImageSetup> GetImageSetupAsync(CancellationToken cancellationToken = default)
```

### GetKnowledgeContentAsync(id)

The text of a pasted or uploaded source

Parameters:

- `id`: The id.

```csharp
Task<M.SourceText> GetKnowledgeContentAsync(string id, CancellationToken cancellationToken = default)
```

### GetKnowledgeSourceAsync(id)

One source

Parameters:

- `id`: The id.

```csharp
Task<M.KnowledgeSource> GetKnowledgeSourceAsync(string id, CancellationToken cancellationToken = default)
```

### GetLicenseAsync()

Toskar Pro's trial or Unlock, as its desktop app last said

Core on its own has no license (`kind` empty) and nothing is limited. The Toskar Pro desktop app from the Mac App Store or the Microsoft Store sets a 14-day trial, unlocked, or ended (yeixio/toskar-apps#336). While `limited`, installing models, creating automations, and adding people answer 403 `UNLOCK_REQUIRED`; what's set up keeps working.

```csharp
Task<M.License> GetLicenseAsync(CancellationToken cancellationToken = default)
```

### GetLogAsync(name, tailBytes)

Read a log file tail

Parameters:

- `name`: The name.
- `tailBytes`: The tailBytes.

```csharp
Task<M.LogContent> GetLogAsync(string name, long? tailBytes = null, CancellationToken cancellationToken = default)
```

### GetMCPPromptAsync(id, name, body)

Fill a prompt; returns its text

Parameters:

- `id`: The id.
- `name`: The name.
- `body`: The request.

```csharp
Task GetMCPPromptAsync(string id, string name, M.GetMCPPromptRequest? body = null, CancellationToken cancellationToken = default)
```

### GetMCPServerAsync(id)

One tool source

Parameters:

- `id`: The id.

```csharp
Task GetMCPServerAsync(string id, CancellationToken cancellationToken = default)
```

### GetMeAsync()

Who the request is from (#206)

The person, their role, and how Toskar knows. A request from this computer is the Owner's; one with an API key is its person's.

```csharp
Task<M.Me> GetMeAsync(CancellationToken cancellationToken = default)
```

### GetModelPlacementAsync(id)

Which computers can run an installed model

Parameters:

- `id`: The id.

```csharp
Task<M.ModelPlacement> GetModelPlacementAsync(string id, CancellationToken cancellationToken = default)
```

### GetModelRatingAsync(id)

This person's rating of a model, and exactly what sharing it would send

Parameters:

- `id`: The id.

```csharp
Task<M.ModelRating> GetModelRatingAsync(string id, CancellationToken cancellationToken = default)
```

### GetNetworkAsync()

This computer's network, its Bifrost address and fingerprint, and the computers it trusts

```csharp
Task<M.NetworkStatus> GetNetworkAsync(CancellationToken cancellationToken = default)
```

### GetNewsAsync()

The AI news from toskar.ai

New open models, runtime releases, and AI labs' announcements, a few lines each, from https://toskar.ai/news.json (#750). Read when asked, at most every six hours, and kept in the data folder so it shows offline; each read is listed in What left this computer as `news`. With the `ai_news` setting off, nothing is read and `enabled` is false. Members and Admins.

```csharp
Task<M.News> GetNewsAsync(CancellationToken cancellationToken = default)
```

### GetNotificationAsync(id)

One notification with each channel's delivery

Parameters:

- `id`: The id.

```csharp
Task<M.Notification> GetNotificationAsync(string id, CancellationToken cancellationToken = default)
```

### GetNotificationDestinationAsync(id)

One destination

Parameters:

- `id`: The id.

```csharp
Task<M.NotificationDestination> GetNotificationDestinationAsync(string id, CancellationToken cancellationToken = default)
```

### GetOIDCAsync()

Whether sign-in with an OpenID Connect provider is offered (#206)

```csharp
Task<M.OIDCInfo> GetOIDCAsync(CancellationToken cancellationToken = default)
```

### GetPersonalizationAsync()

How the person likes answers

```csharp
Task<M.PersonalStyle> GetPersonalizationAsync(CancellationToken cancellationToken = default)
```

### GetPersonAsync(id)

One person (#592)

Parameters:

- `id`: The id.

```csharp
Task<M.Person> GetPersonAsync(string id, CancellationToken cancellationToken = default)
```

### GetPortalAsync(id)

One chat portal (#205)

Parameters:

- `id`: The id.

```csharp
Task<M.Portal> GetPortalAsync(string id, CancellationToken cancellationToken = default)
```

### GetPortalPageAsync(slug)

What a portal's page shows (#205)

Its name, access, language, and branding, and whether this browser is already its guest. Answers without signing in.

Parameters:

- `slug`: The slug.

```csharp
Task<M.PortalPage> GetPortalPageAsync(string slug, CancellationToken cancellationToken = default)
```

### GetPortalUsageAsync(id)

How much a portal is used (#205)

Visitors who wrote, conversations, and messages they sent, over the last 7 and 30 days.

Parameters:

- `id`: The id.

```csharp
Task<M.PortalUsage> GetPortalUsageAsync(string id, CancellationToken cancellationToken = default)
```

### GetPrivacyAsync()

Run record retention and a 30-day summary of what left this computer

```csharp
Task GetPrivacyAsync(CancellationToken cancellationToken = default)
```

### GetProfileAsync(id)

One profile

Parameters:

- `id`: The id.

```csharp
Task<JsonObject> GetProfileAsync(string id, CancellationToken cancellationToken = default)
```

### GetProfilePinsAsync()

The profiles each pinnable role is kept to (#345)

```csharp
Task<M.ProfilePins> GetProfilePinsAsync(CancellationToken cancellationToken = default)
```

### GetPushStatusAsync()

Push to the Toskar app on this device (#460)

What a paired phone or tablet needs to register with the push relay (the relay and this computer's key, which the relay seals into the device's handle), and whether this device has registered. See docs/push.md.

```csharp
Task<M.PushStatus> GetPushStatusAsync(CancellationToken cancellationToken = default)
```

### GetQuietHoursAsync()

Quiet hours

```csharp
Task<M.QuietHours> GetQuietHoursAsync(CancellationToken cancellationToken = default)
```

### GetRemoteAccessAsync()

Access from anywhere's setting and its listener (#456)

enabled, port, address (a forwarded address, when set), listening (the address it listens on) or error, port_mapping, mapped and mapped_by (pcp, nat-pmp, or upnp) for the router port it opened, map_error, ipv6, reachable (direct, ipv6, manual, relay, or none) with reason (off, not_listening, carrier_nat, or no_port), relay (name, state: no_token, ended (contract 1.41: the token ran out with nothing to renew it, so it isn't sent; a new one takes over within a minute), connecting, connected, or error, and error, its code) while the relay client runs, and check, the last outside check (#546, contract 1.28): at, relay and direct (each way in with address, ok, reason, and ms), tried, and error when the last attempt didn't reach the relay (CHECK_UNSUPPORTED, CHECK_TOO_SOON, NO_TOKEN, RELAY_UNREACHABLE). With Toskar's relay, subscription (#639, contract 1.38): state (none, pending, active, or ended; contract 1.41: ended also when the token from the app's store or a subscription ran out, with expires the day it did), store (stripe when bought here in Settings, app when bought in the Toskar app), expires, open (whether Toskar's relay takes new subscriptions now, when known), checkout (the open checkout's page while pending), error (the last exchange's code when it didn't reach the relay), and in_app_only (contract 1.39: this copy is the Mac App Store's, which neither sells nor manages it; the Toskar app on a phone or tablet does). Set it with PATCH /api/v1/settings: remote_access_enabled, remote_access_port, remote_access_address, remote_access_port_mapping, remote_access_relay (an organization's relay, empty for Toskar's), and remote_access_relay_secret (its enrollment secret; write-only, empty clears it).

```csharp
Task GetRemoteAccessAsync(CancellationToken cancellationToken = default)
```

### GetReportAsync()

What a problem report sends, scrubbed

Versions and the kind of computer, and for an Admin Core's last 40 warnings and errors. Email addresses, keys, tokens, home folder names, the computer's name, and internet addresses are taken out first. Members and paired devices may call it.

```csharp
Task<M.DiagnosticsReport> GetReportAsync(CancellationToken cancellationToken = default)
```

### GetRouteSecretAsync()

The route secret, for a paired device on the home network (#456)

route_secret (base64url, 32 bytes), route_id, relay (the relay this computer uses away from home), and token, the computer's current token for Toskar's relay when it has one (contract 1.27), so each paired device can look it up away from home. Given only on the home network, never through the remote listener; pairing (POST /api/v1/devices/pair) returns them too.

```csharp
Task<M.DeviceRoute> GetRouteSecretAsync(CancellationToken cancellationToken = default)
```

### GetRunAsync(id)

One run trace

Parameters:

- `id`: The id.

```csharp
Task GetRunAsync(string id, CancellationToken cancellationToken = default)
```

### GetRuntimeHistoryAsync()

The daemon's memory and goroutines now and over the last day

Sampled every five minutes and kept for a day, so a slow leak shows on the Diagnostics page. Resets when the daemon restarts.

```csharp
Task<M.RuntimeHistory> GetRuntimeHistoryAsync(CancellationToken cancellationToken = default)
```

### GetSettingsAsync()

Get settings

```csharp
Task<JsonObject> GetSettingsAsync(CancellationToken cancellationToken = default)
```

### GetSourceAsync()

AGPL corresponding-source offer

```csharp
Task<M.SourceOffer> GetSourceAsync(CancellationToken cancellationToken = default)
```

### GetTaskAsync(id)

One task

Parameters:

- `id`: The id.

```csharp
Task<M.ToskarTask> GetTaskAsync(string id, CancellationToken cancellationToken = default)
```

### GetTopicAttemptsAsync(id, days)

A profile's off-topic attempts (#345)

What an Enforce profile held, or whose answer it replaced, over the last days (30 by default, up to 365), kept as run records are.

Parameters:

- `id`: The id.
- `days`: The days.

```csharp
Task GetTopicAttemptsAsync(string id, long? days = null, CancellationToken cancellationToken = default)
```

### GetTrainingJobAsync(id)

One training job

Parameters:

- `id`: The id.

```csharp
Task<M.TrainingJob> GetTrainingJobAsync(string id, CancellationToken cancellationToken = default)
```

### GetUpdatesAsync()

Whether a newer Toskar is out, from the daily check of toskar.ai

Release builds installed from a download check https://toskar.ai/releases/latest.json once a day, while the `update_check` setting is on. The App Store edition, the copy the desktop app runs (`TOSKAR_UPDATE_CHECK=off`), and development builds don't check, and say `supported` false.

```csharp
Task<M.UpdateStatus> GetUpdatesAsync(CancellationToken cancellationToken = default)
```

### GetVersionAsync()

Application version

```csharp
Task<M.VersionResponse> GetVersionAsync(CancellationToken cancellationToken = default)
```

### GetVideoSetupAsync()

What video generation has installed, the models on offer, and any setup in progress

```csharp
Task<M.ImageSetup> GetVideoSetupAsync(CancellationToken cancellationToken = default)
```

### ImportModelAsync(body, filename, displayName, id)

Add a model from a GGUF file

A path on this computer as JSON, copied into the models folder (the default; progress comes as model.download events) or used in place with in_place, or the file itself as an application/octet-stream body with filename in the query. The header and tensor bounds are checked first (#467).

Parameters:

- `body`: The request.
- `filename`: For an upload, the file's name, ending in .gguf
- `displayName`: The displayName.
- `id`: The id.

```csharp
Task<M.ImportedModel> ImportModelAsync(M.ImportModelRequest body, string? filename = null, string? displayName = null, string? id = null, CancellationToken cancellationToken = default)
```

### InstallModelAsync(id, body, wait, nodeId)

Download a catalog model, here or on a paired computer

Parameters:

- `id`: The id.
- `body`: The request.
- `wait`: The wait.
- `nodeId`: The nodeId.

```csharp
Task<M.ModelInstall> InstallModelAsync(string id, M.InstallModelRequest? body = null, string? wait = null, string? nodeId = null, CancellationToken cancellationToken = default)
```

### InstallModelFromURLAsync(body, wait)

Download a GGUF from a URL

Parameters:

- `body`: The request.
- `wait`: true waits for the download to finish

```csharp
Task<M.ModelInstall> InstallModelFromURLAsync(M.InstallFromURLRequest body, string? wait = null, CancellationToken cancellationToken = default)
```

### InstallRuntimeAsync(id)

Install a runtime, such as llamacpp

Parameters:

- `id`: The id.

```csharp
Task<M.RuntimeInstall> InstallRuntimeAsync(string id, CancellationToken cancellationToken = default)
```

### InvitePortalVisitorAsync(id, body)

Invite a visitor to a portal by name (#205)

Answers with the visitor and their one-time link (path /p/<slug>?invite=<token>, good for a week).

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.InvitedVisitor> InvitePortalVisitorAsync(string id, M.InvitePortalVisitorRequest body, CancellationToken cancellationToken = default)
```

### JoinNetworkAsync(body)

Join this computer to the network of the computer that made a join token

Verifies the server's key against the fingerprint before proving the token, which never leaves this computer. Safe to repeat; refuses to switch networks while paired.

Parameters:

- `body`: The request.

```csharp
Task<M.JoinResult> JoinNetworkAsync(M.JoinNetworkRequest body, CancellationToken cancellationToken = default)
```

### LeaveNetworkAsync()

Leave the network, telling each paired computer, and forget them all

Models, settings, and this computer's identity stay.

```csharp
Task<M.LeaveResult> LeaveNetworkAsync(CancellationToken cancellationToken = default)
```

### ListAIsAsync()

Specialized AIs

```csharp
Task<List<M.SpecializedAI>> ListAIsAsync(CancellationToken cancellationToken = default)
```

### ListAPIKeysAsync()

API keys, without their secrets

```csharp
Task<List<M.APIKey>> ListAPIKeysAsync(CancellationToken cancellationToken = default)
```

### ListAutomationRunsAsync(id, before, limit)

A page of an automation's runs, newest first

Parameters:

- `id`: The id.
- `before`: The id of the last run already shown; the page starts after it
- `limit`: Runs per page, 1 to 100 (default 20)

```csharp
Task<M.AutomationRunsPage> ListAutomationRunsAsync(string id, string? before = null, long? limit = null, CancellationToken cancellationToken = default)
```

### ListAutomationsAsync()

Automations with their last result

```csharp
Task<List<M.Automation>> ListAutomationsAsync(CancellationToken cancellationToken = default)
```

### ListBenchmarksAsync()

List recent benchmark jobs

```csharp
Task<List<JsonObject>> ListBenchmarksAsync(CancellationToken cancellationToken = default)
```

### ListBenchmarkWorkloadsAsync()

List benchmark workload categories

```csharp
Task<List<JsonObject>> ListBenchmarkWorkloadsAsync(CancellationToken cancellationToken = default)
```

### ListCachesAsync()

Caches with their declared policies and sizes

```csharp
Task<List<M.CacheInfo>> ListCachesAsync(CancellationToken cancellationToken = default)
```

### ListConnectorsAsync()

List connected services and their status. Secret values are never returned.

```csharp
Task<List<M.ConnectorStatus>> ListConnectorsAsync(CancellationToken cancellationToken = default)
```

### ListConversationArtifactsAsync(id)

Files attached to or made in a conversation

Parameters:

- `id`: The id.

```csharp
Task<List<M.Artifact>> ListConversationArtifactsAsync(string id, CancellationToken cancellationToken = default)
```

### ListConversationMessagesAsync(id)

Messages of a conversation, with sources, steps, and files

Parameters:

- `id`: The id.

```csharp
Task<List<M.Message>> ListConversationMessagesAsync(string id, CancellationToken cancellationToken = default)
```

### ListConversationsAsync()

List conversations

```csharp
Task<List<M.Conversation>> ListConversationsAsync(CancellationToken cancellationToken = default)
```

### ListDevicesAsync(kind)

The connected services' devices, by kind (#586)

Parameters:

- `kind`: The kind.

```csharp
Task ListDevicesAsync(string? kind = null, CancellationToken cancellationToken = default)
```

### ListEgressAsync(conversationId, limit)

What left this computer, newest first

Parameters:

- `conversationId`: The conversationId.
- `limit`: The limit.

```csharp
Task<List<M.EgressRecord>> ListEgressAsync(string? conversationId = null, long? limit = null, CancellationToken cancellationToken = default)
```

### ListExamplesAsync(id)

Training examples and their statistics

Parameters:

- `id`: Specialized AI id

```csharp
Task<M.TrainingExamples> ListExamplesAsync(string id, CancellationToken cancellationToken = default)
```

### ListJoinTokensAsync()

Join tokens, active and from the last week, without their secrets

```csharp
Task<List<M.JoinToken>> ListJoinTokensAsync(CancellationToken cancellationToken = default)
```

### ListKnowledgeSourcesAsync()

Connected knowledge sources

```csharp
Task<List<M.KnowledgeSource>> ListKnowledgeSourcesAsync(CancellationToken cancellationToken = default)
```

### ListLiveFiguresAsync()

Live CPU, memory, and GPU figures for this and paired computers

Each computer's figures now, every few seconds over the last hour (every minute when no model is loaded), and per-minute averages over the last day. A figure a computer can't give, such as GPU temperature on a Mac, is left out rather than reported as 0. A paired computer that doesn't answer within 5 seconds is left out.

```csharp
Task<List<M.LiveFigures>> ListLiveFiguresAsync(CancellationToken cancellationToken = default)
```

### ListLogsAsync()

List diagnostic log files

```csharp
Task<List<M.LogFile>> ListLogsAsync(CancellationToken cancellationToken = default)
```

### ListMCPServersAsync()

List MCP tool sources with status, tools, and masked values. Secret values are never returned.

```csharp
Task<List<M.MCPServer>> ListMCPServersAsync(CancellationToken cancellationToken = default)
```

### ListMemoriesAsync()

Memories and the categories they can have

```csharp
Task<M.MemoryList> ListMemoriesAsync(CancellationToken cancellationToken = default)
```

### ListModelsAsync()

List catalog and installed models

```csharp
Task<List<M.Model>> ListModelsAsync(CancellationToken cancellationToken = default)
```

### ListMyDevicesAsync()

Your connected devices (#206)

The phones, tablets, and TVs connected as the request's person, whatever their role.

```csharp
Task<List<M.MyDevice>> ListMyDevicesAsync(CancellationToken cancellationToken = default)
```

### ListNodesAsync()

List local and discovered computers

```csharp
Task<List<JsonObject>> ListNodesAsync(CancellationToken cancellationToken = default)
```

### ListNotificationDestinationsAsync()

Email and webhook destinations. Passwords and signing secrets are never returned.

```csharp
Task<List<M.NotificationDestination>> ListNotificationDestinationsAsync(CancellationToken cancellationToken = default)
```

### ListNotificationsAsync(unread, limit, category)

List notifications that were not dismissed, newest first

Parameters:

- `unread`: 1 lists unread notifications only
- `limit`: The limit.
- `category`: automation, approval, model, training, health, or system

```csharp
Task<M.NotificationList> ListNotificationsAsync(string? unread = null, long? limit = null, string? category = null, CancellationToken cancellationToken = default)
```

### ListPeopleAsync(role, disabled)

Everyone who uses this Toskar (Admins and the Owner)

Parameters:

- `role`: Only people with this role (#592).
- `disabled`: true for only disabled people, false for only active ones.

```csharp
Task<List<M.Person>> ListPeopleAsync(string? role = null, bool? disabled = null, CancellationToken cancellationToken = default)
```

### ListPerformanceAsync(sort, order, limit)

List generation performance samples

Parameters:

- `sort`: The sort.
- `order`: The order.
- `limit`: The limit.

```csharp
Task<List<JsonObject>> ListPerformanceAsync(string? sort = null, string? order = null, long? limit = null, CancellationToken cancellationToken = default)
```

### ListPortalConversationsAsync(id)

A portal's visitors' conversations (#205)

Newest first, for Admins. A Members only portal's chats are each Member's own, so they aren't here.

Parameters:

- `id`: The id.

```csharp
Task<List<M.PortalConversation>> ListPortalConversationsAsync(string id, CancellationToken cancellationToken = default)
```

### ListPortalMessagesAsync(id, cid)

One visitor's conversation, to read (#205)

Parameters:

- `id`: The id.
- `cid`: The cid.

```csharp
Task<List<M.PortalMessage>> ListPortalMessagesAsync(string id, string cid, CancellationToken cancellationToken = default)
```

### ListPortalsAsync()

Chat portals (#205)

Every portal, for Admins and the Owner.

```csharp
Task<List<M.Portal>> ListPortalsAsync(CancellationToken cancellationToken = default)
```

### ListPortalVisitorsAsync(id)

A portal's invited visitors (#205)

Parameters:

- `id`: The id.

```csharp
Task<List<M.Person>> ListPortalVisitorsAsync(string id, CancellationToken cancellationToken = default)
```

### ListProfilesAsync()

List AI profiles

```csharp
Task<List<JsonObject>> ListProfilesAsync(CancellationToken cancellationToken = default)
```

### ListRunningModelsAsync()

Loaded model instances on this and paired computers

```csharp
Task<List<M.RunningModelView>> ListRunningModelsAsync(CancellationToken cancellationToken = default)
```

### ListRunsAsync(conversationId, limit)

Recent run traces, newest first

Parameters:

- `conversationId`: The conversationId.
- `limit`: The limit.

```csharp
Task ListRunsAsync(string? conversationId = null, long? limit = null, CancellationToken cancellationToken = default)
```

### ListRuntimesAsync()

Runtimes and whether each is installed

```csharp
Task<List<M.RuntimeInfo>> ListRuntimesAsync(CancellationToken cancellationToken = default)
```

### ListTasksAsync()

Recent tasks

```csharp
Task<List<M.ToskarTask>> ListTasksAsync(CancellationToken cancellationToken = default)
```

### ListToolRunsAsync(toolId, conversationId, limit)

Audited tool calls, newest first; records expire with run records

Parameters:

- `toolId`: The toolId.
- `conversationId`: The conversationId.
- `limit`: The limit.

```csharp
Task<List<M.ToolRun>> ListToolRunsAsync(string? toolId = null, string? conversationId = null, long? limit = null, CancellationToken cancellationToken = default)
```

### ListToolsAsync()

Every tool's descriptor, with whether it is on, its health, and the profiles that allow it

```csharp
Task<List<M.ToolDescriptor>> ListToolsAsync(CancellationToken cancellationToken = default)
```

### ListTrainingJobsAsync(aiId)

Training jobs

Parameters:

- `aiId`: The aiId.

```csharp
Task<List<M.TrainingJob>> ListTrainingJobsAsync(string? aiId = null, CancellationToken cancellationToken = default)
```

### MakeAutomationHookAsync(id)

Make a webhook trigger's link

Returns a new token, the only time it's shown; only its hash is kept. The old link stops working.

Parameters:

- `id`: The id.

```csharp
Task<M.HookLink> MakeAutomationHookAsync(string id, CancellationToken cancellationToken = default)
```

### ManageSubscriptionAsync()

The billing page for the subscription bought here (#639)

Answers {url}, Stripe's billing page for the subscription bought in Settings: change the card, download receipts, cancel. Admins only. 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy; 404 SUBSCRIPTION_NONE when none was bought here (one bought in the Toskar app is managed in the device's store); 502 BILLING_UNAVAILABLE.

```csharp
Task ManageSubscriptionAsync(CancellationToken cancellationToken = default)
```

### MarkNotificationsReadAsync(body)

Mark notifications read; no ids marks all of them

Parameters:

- `body`: The request.

```csharp
Task MarkNotificationsReadAsync(M.MarkNotificationsReadRequest? body = null, CancellationToken cancellationToken = default)
```

### MarkOnTopicAsync(id, aid)

Mark an off-topic attempt as on topic (#345)

Adds its message to the profile's example questions and forgets the attempts with that message.

Parameters:

- `id`: The id.
- `aid`: The aid.

```csharp
Task MarkOnTopicAsync(string id, string aid, CancellationToken cancellationToken = default)
```

### McpGalleryAsync()

Gallery entries, with programs that are missing and sources already added

```csharp
Task McpGalleryAsync(CancellationToken cancellationToken = default)
```

### McpImportCandidatesAsync()

MCP servers set up in other apps on this computer, with secret values hidden

```csharp
Task McpImportCandidatesAsync(CancellationToken cancellationToken = default)
```

### McpOAuthCallbackAsync()

Where a tool source's sign-in returns; shows a page that says how it went

```csharp
Task McpOAuthCallbackAsync(CancellationToken cancellationToken = default)
```

### McpServerAsync(body)

Toskar's MCP server (Streamable HTTP, JSON-RPC). Tools ask_local_ai, list_local_models, search_my_knowledge.

Checked like /v1. A request with an Origin header from another site is refused.

Parameters:

- `body`: The request.

```csharp
Task McpServerAsync(JsonObject? body = null, CancellationToken cancellationToken = default)
```

### McpServerDeleteAsync()

End an MCP session

```csharp
Task McpServerDeleteAsync(CancellationToken cancellationToken = default)
```

### McpServerGetAsync()

Not supported; the server does not open a stream

```csharp
Task McpServerGetAsync(CancellationToken cancellationToken = default)
```

### McpServerLogsAsync(id)

Recent log lines of a tool source

Parameters:

- `id`: The id.

```csharp
Task McpServerLogsAsync(string id, CancellationToken cancellationToken = default)
```

### McpServerPromptsAsync(id)

The tool source's ready-made prompts

Parameters:

- `id`: The id.

```csharp
Task McpServerPromptsAsync(string id, CancellationToken cancellationToken = default)
```

### McpServerResourcesAsync(id)

The tool source's resources

Parameters:

- `id`: The id.

```csharp
Task McpServerResourcesAsync(string id, CancellationToken cancellationToken = default)
```

### McpShareAsync()

The address and command other apps use to reach Toskar's MCP server

```csharp
Task McpShareAsync(CancellationToken cancellationToken = default)
```

### ModelsFitAsync()

How well each catalog model fits this computer

```csharp
Task<List<M.ModelsFit>> ModelsFitAsync(CancellationToken cancellationToken = default)
```

### OidcCallbackAsync(state, code)

Where the provider sends people back (#206)

Checks the state against this browser's cookie, swaps the code for an ID token and checks it, signs the browser in, and redirects to the path it started from. A failure redirects to /?oidc_error= failed, refused, disabled, or unavailable.

Parameters:

- `state`: The state.
- `code`: The code.

```csharp
Task OidcCallbackAsync(string? state = null, string? code = null, CancellationToken cancellationToken = default)
```

### OpenaiChatCompletionsAsync(body)

OpenAI-compatible chat completions

temperature and max_tokens apply to the calls that write the answer (#70). The toskar object asks for memory, knowledge, tools, effort, and placement, within what the API key allows. yggdrasil, its name from before the rename, works too; toskar wins when both are sent. Responses carry the answer's extension fields under both names.

Parameters:

- `body`: The request.

```csharp
Task<M.OpenAIChatCompletion> OpenaiChatCompletionsAsync(M.OpenaiChatCompletionsRequest body, CancellationToken cancellationToken = default)
```

### OpenaiListModelsAsync()

OpenAI-compatible model list

auto, each profile as profile:<id>, and each deployed specialized AI as sai:<slug>.

```csharp
Task<M.OpenAIModelList> OpenaiListModelsAsync(CancellationToken cancellationToken = default)
```

### OutboundPairingAsync(code)

The offer this computer made for a code

Parameters:

- `code`: The code.

```csharp
Task<M.PairingOffer> OutboundPairingAsync(string code, CancellationToken cancellationToken = default)
```

### PairDeviceAsync(body)

A phone exchanges the code for its own key (no key needed; local network only)

Parameters:

- `body`: The request.

```csharp
Task<M.PairedDevice> PairDeviceAsync(M.PairDeviceRequest body, CancellationToken cancellationToken = default)
```

### PairNodeAsync(body)

Offer to pair with a discovered computer

Parameters:

- `body`: The request.

```csharp
Task<M.PairingSession> PairNodeAsync(M.PairNodeRequest body, CancellationToken cancellationToken = default)
```

### ParseAutomationAsync(body)

Read a request such as "every morning at 8, tell me if the price is below $500" into an automation

Parameters:

- `body`: The request.

```csharp
Task<M.AutomationRequest> ParseAutomationAsync(M.ParseAutomationRequest body, CancellationToken cancellationToken = default)
```

### ParseMCPAsync(body)

Read pasted settings, a web address, or a command line into server specs and what each still needs

Parameters:

- `body`: The request.

```csharp
Task ParseMCPAsync(M.ParseMCPRequest? body = null, CancellationToken cancellationToken = default)
```

### PauseAutomationAsync(id)

Pause an automation

Parameters:

- `id`: The id.

```csharp
Task<M.Automation> PauseAutomationAsync(string id, CancellationToken cancellationToken = default)
```

### PeekInviteAsync(token)

What a one-time sign-in link is for (#206)

Parameters:

- `token`: The token.

```csharp
Task<M.Invite> PeekInviteAsync(string token, CancellationToken cancellationToken = default)
```

### PendingPairingsAsync()

Pairing offers waiting for approval on this computer

```csharp
Task<List<M.PairingOffer>> PendingPairingsAsync(CancellationToken cancellationToken = default)
```

### PeopleActivityAsync(person, limit)

Who changed whom (#592)

Newest first. Adding, changing, disabling, removing, setting passwords, making links, and revoking keys and devices; never a password.

Parameters:

- `person`: Only entries by or about this person.
- `limit`: At most this many, 100 by default and 500 at most.

```csharp
Task<List<M.ActivityEntry>> PeopleActivityAsync(string? person = null, long? limit = null, CancellationToken cancellationToken = default)
```

### PersonCapabilitiesAsync(id)

What one person may use (#589)

Parameters:

- `id`: The id.

```csharp
Task<M.PersonCapabilities> PersonCapabilitiesAsync(string id, CancellationToken cancellationToken = default)
```

### PersonDevicesAsync(id)

A person's connected devices (#592)

Parameters:

- `id`: The id.

```csharp
Task<List<M.APIKey>> PersonDevicesAsync(string id, CancellationToken cancellationToken = default)
```

### PersonKeysAsync(id)

A person's API keys, other than their devices (#592)

Parameters:

- `id`: The id.

```csharp
Task<List<M.APIKey>> PersonKeysAsync(string id, CancellationToken cancellationToken = default)
```

### PersonLinkAsync(id)

A new one-time link for a person; a reset link once they have a sign-in

Parameters:

- `id`: The id.

```csharp
Task<M.InviteLink> PersonLinkAsync(string id, CancellationToken cancellationToken = default)
```

### PortalVisitorLinkAsync(id, vid)

A new link for an invited visitor (#205)

Replaces any link they haven't used.

Parameters:

- `id`: The id.
- `vid`: The vid.

```csharp
Task<M.VisitorLink> PortalVisitorLinkAsync(string id, string vid, CancellationToken cancellationToken = default)
```

### PreviewAutomationAsync(body)

Check an automation and show its next runs without saving it

Parameters:

- `body`: The request.

```csharp
Task<M.AutomationPreview> PreviewAutomationAsync(M.AutomationInput body, CancellationToken cancellationToken = default)
```

### PreviewModelFromURLAsync(body)

What a download from a URL would bring, without downloading it

The file and its size (and its vision projector's) from the repository, the free space where models are kept, whether it's already a model here, and copies of the same file other apps have (by name, Ollama's SHA-256 blob, or a large file's exact size), which can be added where they are instead (#611).

Parameters:

- `body`: The request.

```csharp
Task<M.URLPreview> PreviewModelFromURLAsync(M.InstallFromURLRequest body, CancellationToken cancellationToken = default)
```

### PutLicenseAsync(xToskarShell, body)

Set Toskar Pro's trial or Unlock (the desktop app only)

Only the Toskar Pro desktop app on this computer, with the `X-Toskar-Shell` secret it started Core with (`TOSKAR_SHELL_SECRET`). Anything else gets 403 `SHELL_ONLY`.

Parameters:

- `xToskarShell`: The xToskarShell.
- `body`: The request.

```csharp
Task<M.License> PutLicenseAsync(string xToskarShell, M.PutLicenseRequest body, CancellationToken cancellationToken = default)
```

### PutModelRatingAsync(id, body)

Rate a model 1–5 stars, and share the rating with the community or keep it on this computer

Sharing sends the stars, tags, model identity, hardware class, a random rating ID, and the app version to the ratings service. `share` false withdraws a rating that was shared. A 502 means the rating was saved here but the service could not be reached.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.ModelRating> PutModelRatingAsync(string id, M.PutModelRatingRequest body, CancellationToken cancellationToken = default)
```

### PutRelayTokenAsync()

Hand over a subscription's relay token (#456)

Body {token, enable}. token is the route token the app got for this computer by exchanging a store receipt with Toskar's relay; the computer keeps it and registers and keeps its tunnel there. A paired device may send it, from home or through the remote listener. enable also turns access from anywhere on, and needs an Admin (403 ROLE_REQUIRED). Answers state: the relay client's state, or off. 400 RELAY_TOKEN_INVALID for a token that isn't for this computer's route or has expired, RELAY_TOKEN_NOT_NEEDED when an organization's relay is set.

```csharp
Task PutRelayTokenAsync(CancellationToken cancellationToken = default)
```

### PutSettingsAsync(body)

Update settings (same as PATCH)

Parameters:

- `body`: The request.

```csharp
Task<JsonObject> PutSettingsAsync(JsonObject body, CancellationToken cancellationToken = default)
```

### ReadAloudAsync(body)

Read text aloud on this computer; the audio is kept as a file in the chat

Parameters:

- `body`: The request.

```csharp
Task<M.SpokenText> ReadAloudAsync(M.ReadAloudRequest body, CancellationToken cancellationToken = default)
```

### ReceivePairingOfferAsync(body)

Receive a pairing offer from another computer

Parameters:

- `body`: The request.

```csharp
Task<M.PairingSession> ReceivePairingOfferAsync(M.PairingOffer body, CancellationToken cancellationToken = default)
```

### RecommendModelsAsync(purpose)

Recommended models for this computer

Parameters:

- `purpose`: What the model is for, such as chat or coding

```csharp
Task<M.Recommendation> RecommendModelsAsync(string? purpose = null, CancellationToken cancellationToken = default)
```

### RefreshKnowledgeSourceAsync(id)

Reindex a source; a failure is recorded on the source

Parameters:

- `id`: The id.

```csharp
Task<M.KnowledgeSource> RefreshKnowledgeSourceAsync(string id, CancellationToken cancellationToken = default)
```

### RefreshNodesAsync()

Look for computers again

```csharp
Task<M.OK> RefreshNodesAsync(CancellationToken cancellationToken = default)
```

### RegisterPushAsync(body)

Register this device's push handle

A paired phone or tablet gives the sealed handle the push relay made from its push token. Only a paired device's key may; another gets PUSH_DEVICE_ONLY. The computer never sees the token. Disconnecting the device ends its pushes.

Parameters:

- `body`: The request.

```csharp
Task<M.PushStatus> RegisterPushAsync(M.RegisterPushRequest body, CancellationToken cancellationToken = default)
```

### RemoveImageModelAsync(id)

Delete an installed image model to free its space

Parameters:

- `id`: The id.

```csharp
Task<M.ImageSetup> RemoveImageModelAsync(string id, CancellationToken cancellationToken = default)
```

### RemoveMCPServerAsync(id)

Stop a tool source, remove its tools, and delete its stored secrets

Parameters:

- `id`: The id.

```csharp
Task RemoveMCPServerAsync(string id, CancellationToken cancellationToken = default)
```

### RemovePersonAsync(id, body, transferTo)

Remove a person (#592)

Revokes their keys and devices, signs them out, and deletes their data or gives it to transfer_to. Nobody removes themselves or the Owner, and only the Owner removes Admins. The body's confirm must be their name.

Parameters:

- `id`: The id.
- `body`: The request.
- `transferTo`: A person to give their chats, memories, automations, files, and notifications to, instead of deleting them.

```csharp
Task RemovePersonAsync(string id, M.RemovePersonRequest body, string? transferTo = null, CancellationToken cancellationToken = default)
```

### RemovePortalVisitorAsync(id, vid)

Remove an invited visitor (#205)

They're disabled and signed out at once.

Parameters:

- `id`: The id.
- `vid`: The vid.

```csharp
Task RemovePortalVisitorAsync(string id, string vid, CancellationToken cancellationToken = default)
```

### RemoveVideoModelAsync(id)

Delete an installed video model to free its space

Parameters:

- `id`: The id.

```csharp
Task<M.ImageSetup> RemoveVideoModelAsync(string id, CancellationToken cancellationToken = default)
```

### ReplaceMCPServerAsync(id, body)

Change how a tool source is reached, then check it. Blank secret values keep the stored ones.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task ReplaceMCPServerAsync(string id, M.ReplaceMCPServerRequest? body = null, CancellationToken cancellationToken = default)
```

### ResetAppAsync(body, deleteModels)

Reset application to defaults

Clears chats, custom profiles, tasks, and API keys; restores settings and built-in profiles. Downloaded models and runtimes are kept unless delete_models is true. The client should clear local UI state and restart onboarding. Not reversible.

Parameters:

- `body`: The request.
- `deleteModels`: The deleteModels.

```csharp
Task<JsonObject> ResetAppAsync(M.ResetAppRequest? body = null, string? deleteModels = null, CancellationToken cancellationToken = default)
```

### ResetProfileAsync(id)

Put a built-in profile back to how Toskar ships it

Parameters:

- `id`: The id.

```csharp
Task<JsonObject> ResetProfileAsync(string id, CancellationToken cancellationToken = default)
```

### ResumeAutomationAsync(id)

Resume an automation

Parameters:

- `id`: The id.

```csharp
Task<M.Automation> ResumeAutomationAsync(string id, CancellationToken cancellationToken = default)
```

### RevokeJoinTokenAsync(id)

Revoke an unused join token

Parameters:

- `id`: The id.

```csharp
Task<M.JoinToken> RevokeJoinTokenAsync(string id, CancellationToken cancellationToken = default)
```

### RevokeNodeAsync(id)

Stop trusting a paired computer

Parameters:

- `id`: The id.

```csharp
Task RevokeNodeAsync(string id, CancellationToken cancellationToken = default)
```

### RevokePersonDeviceAsync(id, key)

Disconnect one of a person's devices (#592)

Parameters:

- `id`: The id.
- `key`: The key.

```csharp
Task RevokePersonDeviceAsync(string id, string key, CancellationToken cancellationToken = default)
```

### RevokePersonKeyAsync(id, key)

Revoke one of a person's keys (#592)

Parameters:

- `id`: The id.
- `key`: The key.

```csharp
Task RevokePersonKeyAsync(string id, string key, CancellationToken cancellationToken = default)
```

### RoleCapabilitiesAsync()

What each role may use (#589)

Every capability in order, each role's, and the defaults each role ships with. The Owner always has everything.

```csharp
Task<M.RoleCapabilities> RoleCapabilitiesAsync(CancellationToken cancellationToken = default)
```

### RotateAPIKeyAsync(id)

Replace a key's secret; the old one stops working

Parameters:

- `id`: The id.

```csharp
Task<M.NewAPIKey> RotateAPIKeyAsync(string id, CancellationToken cancellationToken = default)
```

### RotateNotificationSecretAsync(id)

Replace a webhook's signing secret; the old one stops working

Parameters:

- `id`: The id.

```csharp
Task<M.DestinationSecret> RotateNotificationSecretAsync(string id, CancellationToken cancellationToken = default)
```

### RunAutomationAsync(id)

Run an automation now

Parameters:

- `id`: The id.

```csharp
Task<M.AutomationRunInfo> RunAutomationAsync(string id, CancellationToken cancellationToken = default)
```

### RunHookAsync(token, body)

Start the automation a webhook link belongs to

The token in the link is the only proof, so this needs no API key. The request body (up to 64 KB, any type) goes to the run as data from the caller, never as instructions. One automation's link takes a call at most every 10 seconds.

Parameters:

- `token`: The token.
- `body`: The request.

```csharp
Task<M.HookRun> RunHookAsync(string token, string? body = null, CancellationToken cancellationToken = default)
```

### SearchKnowledgeAsync(body)

Search connected knowledge

Parameters:

- `body`: The request.

```csharp
Task<List<M.KnowledgeHit>> SearchKnowledgeAsync(M.SearchKnowledgeRequest body, CancellationToken cancellationToken = default)
```

### SendReportAsync()

Send a problem report to Toskar (#588)

Body {product (core, the default, or apps), app, where, code, error, note, email, details}. Core scrubs the error and note as it scrubs its own report, adds that report when details is true, and sends it to Toskar's report service (https://toskar.ai/api/report, or TOSKAR_REPORT_URL), which files it as an issue in a private repository, grouped with others for the same error and version. A reply address goes to the Toskar team by email, never into the issue. Answers {status: created or added, number}. Each one is listed in What left this computer as problem_report. Members and paired devices may send. 400 REPORT_INVALID; 403 REPORTS_OFF when an Admin turned problem_reports off; 429 REPORT_RATE_LIMITED; 502 REPORTS_UNAVAILABLE when the service can't be reached or isn't set up, for the client to send by email instead (contract 1.40).

```csharp
Task SendReportAsync(CancellationToken cancellationToken = default)
```

### SetAPIKeyPermissionsAsync(id, body)

Change what an API key may ask of the assistant

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task SetAPIKeyPermissionsAsync(string id, M.SetAPIKeyPermissionsRequest? body = null, CancellationToken cancellationToken = default)
```

### SetExternalServerAsync(body)

Set the external server's base URL and API key

The key is stored in the secrets folder and never returned. An empty api_key keeps the stored one; clear_key removes it; an empty base_url turns the server off.

Parameters:

- `body`: The request.

```csharp
Task<M.ExternalServer> SetExternalServerAsync(M.SetExternalServerRequest body, CancellationToken cancellationToken = default)
```

### SetModelProjectorAsync(id, body)

Give an added model its vision projector

A GGUF vision projector (mmproj) on this computer, copied beside the model so it can see pictures (#467).

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.ModelVision> SetModelProjectorAsync(string id, M.SetModelProjectorRequest body, CancellationToken cancellationToken = default)
```

### SetMyPreferencesAsync(body)

Save your own languages (#206)

The request's person's App language and assistant language, whatever their role. The Owner's are the install's, which others start from until they choose. Answers with the person's settings.

Parameters:

- `body`: The request.

```csharp
Task<JsonObject> SetMyPreferencesAsync(M.SetMyPreferencesRequest body, CancellationToken cancellationToken = default)
```

### SetPersonalizationAsync(body)

Save how the person likes answers. Style only; it cannot grant a permission.

Parameters:

- `body`: The request.

```csharp
Task SetPersonalizationAsync(M.PersonalStyle? body = null, CancellationToken cancellationToken = default)
```

### SetPersonCapabilitiesAsync(id, body)

Allow or Block something for one person (#589)

true allows, false blocks, and null is as their role's. The Owner's are fixed.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.PersonCapabilities> SetPersonCapabilitiesAsync(string id, Dictionary<string, bool?> body, CancellationToken cancellationToken = default)
```

### SetPersonProfilesAsync(id, body)

Pin a Member or Visitor to profiles (#345)

profiles: a list replaces their role's pin, [] is any profile, and null is their role's again. The Owner and Admins can't be pinned.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Person> SetPersonProfilesAsync(string id, M.SetPersonProfilesRequest body, CancellationToken cancellationToken = default)
```

### SetQuietHoursAsync(body)

Set quiet hours

Parameters:

- `body`: The request.

```csharp
Task<M.QuietHours> SetQuietHoursAsync(M.QuietHours body, CancellationToken cancellationToken = default)
```

### SetRoleCapabilitiesAsync(role, body)

Change what a role may use (#589)

Only the Owner changes the Admins'. The Owner's are fixed.

Parameters:

- `role`: The role.
- `body`: The request.

```csharp
Task<Dictionary<string, bool>> SetRoleCapabilitiesAsync(string role, Dictionary<string, bool> body, CancellationToken cancellationToken = default)
```

### SetRoleProfilesAsync(role, body)

Pin a role to profiles (#345)

Parameters:

- `role`: The role.
- `body`: The request.

```csharp
Task<M.ProfilePins> SetRoleProfilesAsync(string role, M.SetRoleProfilesRequest body, CancellationToken cancellationToken = default)
```

### SetRunRetentionAsync(body)

Set how long run records are kept; 0 keeps them

Parameters:

- `body`: The request.

```csharp
Task SetRunRetentionAsync(M.SetRunRetentionRequest? body = null, CancellationToken cancellationToken = default)
```

### SetTestPromptsAsync(id, body)

Set the prompts evaluation compares

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task<List<M.EvalPrompt>> SetTestPromptsAsync(string id, M.SetTestPromptsRequest body, CancellationToken cancellationToken = default)
```

### SetToolEnabledAsync(id, body)

Turn a tool on or off

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.ToolEnabled> SetToolEnabledAsync(string id, M.SetToolEnabledRequest body, CancellationToken cancellationToken = default)
```

### ShowMessageVersionAsync(id, mid)

Show a version of its point in the chat, with what followed it (#447)

Parameters:

- `id`: The id.
- `mid`: The mid.

```csharp
Task<List<M.Message>> ShowMessageVersionAsync(string id, string mid, CancellationToken cancellationToken = default)
```

### SignInAsync(body)

Sign in with a username and password (#206)

Sets the session cookie. Five failures for a username in 15 minutes, or twenty from an address in ten, answer 429 SIGN_IN_THROTTLED for a while.

Parameters:

- `body`: The request.

```csharp
Task<M.Principal> SignInAsync(M.SignInRequest body, CancellationToken cancellationToken = default)
```

### SignInMCPServerAsync(id, body)

Start signing in to the tool source's service; returns the address to open

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task SignInMCPServerAsync(string id, M.SignInMCPServerRequest? body = null, CancellationToken cancellationToken = default)
```

### SignOutAsync()

Sign out this browser

```csharp
Task SignOutAsync(CancellationToken cancellationToken = default)
```

### SignOutMCPServerAsync(id)

Forget the tool source's sign-in

Parameters:

- `id`: The id.

```csharp
Task SignOutMCPServerAsync(string id, CancellationToken cancellationToken = default)
```

### StartBenchmarkAsync(body)

Start a multi-model benchmark

Parameters:

- `body`: The request.

```csharp
Task<JsonObject> StartBenchmarkAsync(JsonObject body, CancellationToken cancellationToken = default)
```

### StartDevicePairingAsync(body)

Show a 6-digit code a phone connects with, replacing any other

Parameters:

- `body`: The request.

```csharp
Task<M.DevicePairing> StartDevicePairingAsync(M.StartDevicePairingRequest? body = null, CancellationToken cancellationToken = default)
```

### StartImageSetupAsync(body)

Install stable-diffusion.cpp and an image model in the background

Parameters:

- `body`: The request.

```csharp
Task<M.ImageSetup> StartImageSetupAsync(M.StartImageSetupRequest body, CancellationToken cancellationToken = default)
```

### StartModelAsync(id, body)

Load a model

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.RunningModelView> StartModelAsync(string id, M.StartModelRequest? body = null, CancellationToken cancellationToken = default)
```

### StartOIDCAsync(return)

Go to the provider to sign in (#206)

Redirects to the provider with PKCE, and sets a short-lived cookie with the sign-in's state. return is the path in Toskar to go to afterwards.

Parameters:

- `return`: The return.

```csharp
Task StartOIDCAsync(string? @return = null, CancellationToken cancellationToken = default)
```

### StartSubscriptionCheckoutAsync()

Subscribe to access from anywhere here, with Stripe (#639)

Body {plan}: monthly or yearly. Opens a Stripe checkout at yeix.io, which bills for Toskar, for this computer's route on Toskar's relay, and answers {url}, its page, for the person to open. Toskar then asks the relay every few seconds whether it's paid; once it is, it keeps the relay token, turns access from anywhere on, and renews the token as the subscription does. Admins only. 400 SUBSCRIPTION_PLAN_INVALID; 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy, SUBSCRIPTION_OWN_RELAY with an organization's relay, SUBSCRIPTION_ACTIVE when this computer already has a current token; 503 RELAY_SOLD_OUT when Toskar's relay takes no new subscriptions; 502 BILLING_UNAVAILABLE.

```csharp
Task StartSubscriptionCheckoutAsync(CancellationToken cancellationToken = default)
```

### StartTrainingAsync(id, body)

Start training

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task<M.TrainingJob> StartTrainingAsync(string id, M.StartTrainingRequest? body = null, CancellationToken cancellationToken = default)
```

### StartVideoSetupAsync(body)

Install stable-diffusion.cpp and a video model in the background

Parameters:

- `body`: The request.

```csharp
Task<M.ImageSetup> StartVideoSetupAsync(M.StartVideoSetupRequest body, CancellationToken cancellationToken = default)
```

### StopChatAsync(body)

Stop a conversation's running turn

Parameters:

- `body`: The request.

```csharp
Task<M.ChatStopped> StopChatAsync(M.StopChatRequest body, CancellationToken cancellationToken = default)
```

### StopModelAsync(id, body)

Unload a model instance

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.OK> StopModelAsync(string id, M.StopModelRequest? body = null, CancellationToken cancellationToken = default)
```

### TestNotificationDestinationAsync(id)

Send a test notification now

Parameters:

- `id`: The id.

```csharp
Task<M.OK> TestNotificationDestinationAsync(string id, CancellationToken cancellationToken = default)
```

### TestToolAsync(id, body)

Run a tool once with the given arguments

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<JsonObject> TestToolAsync(string id, M.TestToolRequest body, CancellationToken cancellationToken = default)
```

### ToolActivityAsync()

Recent tool calls and pending approvals

```csharp
Task<List<M.ToolActivity>> ToolActivityAsync(CancellationToken cancellationToken = default)
```

### ToolProvidersAsync()

Each computer's providers for tools that can run on any paired computer, and their state

```csharp
Task<List<M.NodeToolProviders>> ToolProvidersAsync(CancellationToken cancellationToken = default)
```

### TrainingBackendsAsync()

Trainers on this computer and whether each can run

```csharp
Task<List<M.TrainingBackend>> TrainingBackendsAsync(CancellationToken cancellationToken = default)
```

### TrainingBaseModelsAsync(goal)

Trainable base models, ranked for a goal

Parameters:

- `goal`: The goal.

```csharp
Task<List<M.TrainingBaseModel>> TrainingBaseModelsAsync(string? goal = null, CancellationToken cancellationToken = default)
```

### TrainingPlanAsync(id)

Training plan: fit, downloads, disk, time, and the computer to train on

Parameters:

- `id`: Specialized AI id

```csharp
Task<M.TrainingPlan> TrainingPlanAsync(string id, CancellationToken cancellationToken = default)
```

### TrainingSamplesAsync()

Sample material files

```csharp
Task<List<M.TrainingSample>> TrainingSamplesAsync(CancellationToken cancellationToken = default)
```

### TranscribeRecordingAsync(body)

A recording's text, for speaking a message instead of typing it (yeixio/toskar-apps#155)

The recording is attached first with POST /api/v1/artifacts (audio). Runs speech.transcribe (Whisper) on this computer or a paired one that has it, and answers the text for the person to check before sending. Visitors and paired devices may use it.

Parameters:

- `body`: The request.

```csharp
Task<M.Transcription> TranscribeRecordingAsync(M.TranscribeRecordingRequest body, CancellationToken cancellationToken = default)
```

### TryTopicsAsync(id, body)

Try one message against a profile's topic controls (#345)

message (up to 2000 characters), and optional topics: draft topic controls used in place of the saved ones. Nothing is saved. The answer is a quick one, without tools, knowledge, or memories.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task TryTopicsAsync(string id, M.TryTopicsRequest body, CancellationToken cancellationToken = default)
```

### UndeployAIAsync(id)

Stop serving a specialized AI

Parameters:

- `id`: Specialized AI id

```csharp
Task<M.SpecializedAI> UndeployAIAsync(string id, CancellationToken cancellationToken = default)
```

### UnregisterPushAsync()

Stop pushes to this device

```csharp
Task UnregisterPushAsync(CancellationToken cancellationToken = default)
```

### UpdateAddedModelAsync(id, body)

Rename or retag an added model

For a model added from a file or a link; catalog models keep their own (#467). Tags are general, coding, reasoning, and writing; vision comes with a projector.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.AddedModel> UpdateAddedModelAsync(string id, M.UpdateAddedModelRequest body, CancellationToken cancellationToken = default)
```

### UpdateAIAsync(id, body)

Update a specialized AI

Parameters:

- `id`: Specialized AI id
- `body`: The request.

```csharp
Task<M.SpecializedAI> UpdateAIAsync(string id, M.UpdateAIRequest body, CancellationToken cancellationToken = default)
```

### UpdateAutomationAsync(id, body)

Change only the fields given

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Automation> UpdateAutomationAsync(string id, M.AutomationInput body, CancellationToken cancellationToken = default)
```

### UpdateConversationAsync(id, body)

Update conversation

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Conversation> UpdateConversationAsync(string id, M.UpdateConversationRequest? body = null, CancellationToken cancellationToken = default)
```

### UpdateExampleAsync(id, eid, body)

Edit or exclude an example

Parameters:

- `id`: Specialized AI id
- `eid`: The eid.
- `body`: The request.

```csharp
Task UpdateExampleAsync(string id, string eid, M.UpdateExampleRequest body, CancellationToken cancellationToken = default)
```

### UpdateKnowledgeSourceAsync(id, body)

Rename a source, replace a text source's content, or change its connection

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.KnowledgeSource> UpdateKnowledgeSourceAsync(string id, M.UpdateKnowledgeSourceRequest body, CancellationToken cancellationToken = default)
```

### UpdateMCPServerAsync(id, body)

Change enabled, allow_sampling, always_offer, keywords, or per-tool policies (allow, ask, default)

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task UpdateMCPServerAsync(string id, JsonObject? body = null, CancellationToken cancellationToken = default)
```

### UpdateMemoryAsync(id, body)

Edit, turn off, or keep a memory on this computer only

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Memory> UpdateMemoryAsync(string id, M.UpdateMemoryRequest body, CancellationToken cancellationToken = default)
```

### UpdateNotificationDestinationAsync(id, body)

Change a destination; an empty password keeps the stored one

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.NotificationDestination> UpdateNotificationDestinationAsync(string id, M.NotificationDestinationInput body, CancellationToken cancellationToken = default)
```

### UpdatePortalAsync(id, body)

Change a chat portal (#205)

Any of slug, name, profile_id, tools (none, read_only, profile), memory, language, access (open, passcode), passcode (empty removes it), branding (a JSON object), and enabled. Turning it off stops its visitors at once.

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<M.Portal> UpdatePortalAsync(string id, JsonObject body, CancellationToken cancellationToken = default)
```

### UpdateProfileAsync(id, body)

Update a profile, including its orchestration controls

Parameters:

- `id`: The id.
- `body`: The request.

```csharp
Task<JsonObject> UpdateProfileAsync(string id, JsonObject body, CancellationToken cancellationToken = default)
```

### UpdateSettingsAsync(body)

Update settings

Parameters:

- `body`: The request.

```csharp
Task<JsonObject> UpdateSettingsAsync(JsonObject body, CancellationToken cancellationToken = default)
```

### UploadArtifactAsync(body)

Upload a file to attach to a chat (up to 25 MB)

Parameters:

- `body`: The request.

```csharp
Task<M.Artifact> UploadArtifactAsync(M.UploadArtifactRequest body, CancellationToken cancellationToken = default)
```

### UseImageBuildAsync(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

Parameters:

- `body`: The request.

```csharp
Task<M.ImageSetup> UseImageBuildAsync(M.UseImageBuildRequest body, CancellationToken cancellationToken = default)
```

### UseVideoBuildAsync(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

Parameters:

- `body`: The request.

```csharp
Task<M.ImageSetup> UseVideoBuildAsync(M.UseVideoBuildRequest body, CancellationToken cancellationToken = default)
```

### WarmModelAsync(body)

Start loading the model a chat would use

Starts loading, in the background, the model a chat on the profile would use, and answers at once (#498), so it loads while someone types or speaks. Never loads beside a model that is answering, nor one that wouldn't fit beside those already loaded.

Parameters:

- `body`: The request.

```csharp
Task<M.ModelWarmResponse> WarmModelAsync(M.WarmModelRequest? body = null, CancellationToken cancellationToken = default)
```
