# Every route on `toskar.api()`

*Generated from `src/generated/api.rs`, which `rust/scripts/generate.py` writes from Toskar Core's API spec.*

One async method for each operation, named after its operationId in snake case. An error answer is a `toskar::Error`. The models are in `toskar::models`, and every field is described at [toskar.ai/developers/api](https://toskar.ai/developers/api).

### accept_invite(token, body)

Use a one-time link to set a username and password, or a new password, and sign in

```rust
pub async fn accept_invite(&self, token: &str, body: &models::AcceptInviteRequest) -> Result<models::Principal>
```

### add_companion_device(body)

Connect a companion device, such as a watch with its phone

A connected device asks for a key of its own for a device that goes along with it (yeixio/toskar-apps#213), for the same person, so it shows in Devices and can be disconnected on its own. It works from anywhere, as no code is typed. The answer is the same as POST /devices/pair's. A person may have 20 connected devices.

```rust
pub async fn add_companion_device(&self, body: &models::AddCompanionDeviceRequest) -> Result<models::PairedDevice>
```

### add_conversations(id, body)

Add chats as training material

- `id`: Specialized AI id

```rust
pub async fn add_conversations(&self, id: &str, body: &models::AddConversationsRequest) -> Result<models::TrainingMaterial>
```

### add_example(id, body)

Add an example

- `id`: Specialized AI id

```rust
pub async fn add_example(&self, id: &str, body: &models::AddExampleRequest) -> Result<()>
```

### add_material(id, body)

Add material

- `id`: Specialized AI id

```rust
pub async fn add_material(&self, id: &str, body: &models::AddMaterialRequest) -> Result<models::TrainingMaterial>
```

### add_mcp_server(body)

Check a tool source connects and list its tools, then store it and add the tools

Send a gallery entry ({"preset", "values"}), a spec ({"spec", "values"}), or a server from another app ({"import": {"app", "name"}}). redirect_base is the address the browser uses, for a sign-in. When the service needs a sign-in, the source is stored and sign_in_url is returned.

```rust
pub async fn add_mcp_server(&self, body: Option<&models::AddMCPServerRequest>) -> Result<()>
```

### add_memory(body)

Add a memory; an existing equal memory is returned instead

```rust
pub async fn add_memory(&self, body: &models::AddMemoryRequest) -> Result<models::Memory>
```

### add_person(body)

Add a person and make their invite link (Admins add Members and Visitors; the Owner adds Admins too)

```rust
pub async fn add_person(&self, body: &models::AddPersonRequest) -> Result<models::AddedPerson>
```

### approve_pairing(id, body)

Approve a pairing offer

```rust
pub async fn approve_pairing(&self, id: &str, body: Option<&models::ApprovePairingRequest>) -> Result<models::PairingSession>
```

### browse_models(q, limit)

Search Hugging Face for GGUF models

```rust
pub async fn browse_models(&self, q: Option<&str>, limit: Option<i64>) -> Result<Vec<models::BrowseModel>>
```

### cancel_benchmark(id)

Cancel a running benchmark

```rust
pub async fn cancel_benchmark(&self, id: &str) -> Result<models::OK>
```

### cancel_device_pairing()

Stop showing the code

```rust
pub async fn cancel_device_pairing(&self) -> Result<()>
```

### cancel_image_setup()

Stop the setup in progress; what was downloaded is kept and resumed next time

```rust
pub async fn cancel_image_setup(&self) -> Result<models::ImageSetup>
```

### cancel_training_job(id)

Cancel a training job

```rust
pub async fn cancel_training_job(&self, id: &str) -> Result<models::TrainingJob>
```

### cancel_video_setup()

Stop the setup in progress; what was downloaded is kept and resumed next time

```rust
pub async fn cancel_video_setup(&self) -> Result<models::ImageSetup>
```

### change_my_password(body)

Change your own password (#592)

With your current one. A password an Admin set with must_change is changed here before anything else works; until then other routes answer PASSWORD_CHANGE_REQUIRED. You're signed out everywhere else.

```rust
pub async fn change_my_password(&self, body: &models::ChangeMyPasswordRequest) -> Result<models::Principal>
```

### change_person(id, body)

Rename, change the role of, disable, or enable a person

The Owner's role is fixed and they can't be disabled; nobody changes their own role or disables themselves. Disabling signs the person out everywhere and stops their keys.

```rust
pub async fn change_person(&self, id: &str, body: &models::ChangePersonRequest) -> Result<models::Person>
```

### chat(body)

Send a chat message

Without stream, returns {content, metrics}. With stream, a server-sent event stream of token events, then done; an error event ends it early.

```rust
pub async fn chat(&self, body: &models::ChatRequest) -> Result<models::ChatAnswer>
```

### check_connector(id)

Check the stored credential again

```rust
pub async fn check_connector(&self, id: &str) -> Result<()>
```

### check_mcp_server(id)

Connect again and list the tools

```rust
pub async fn check_mcp_server(&self, id: &str) -> Result<()>
```

### check_remote_access()

Check access from anywhere from outside, now (#546)

The relay reaches this computer from the internet, through its tunnel and each direct way in, as a paired device away from home does: TLS to this computer's certificate and GET /api/v1/health. It also runs on its own every 30 minutes and after the relay connects or the ways in change. Answers what GET /api/v1/remote-access does, with check updated. Admins only. 409 REMOTE_ACCESS_OFF when access from anywhere is off or its listener isn't up.

```rust
pub async fn check_remote_access(&self) -> Result<()>
```

### claim_pairing(body)

Pair using the code shown on the other computer

```rust
pub async fn claim_pairing(&self, body: &models::ClaimPairingRequest) -> Result<models::PairingSession>
```

### classify_material(body)

Recommend whether material is for training, knowledge, or both

```rust
pub async fn classify_material(&self, body: &models::ClassifyMaterialRequest) -> Result<models::ClassifiedMaterial>
```

### clear_cache(name)

Clear one cache

```rust
pub async fn clear_cache(&self, name: &str) -> Result<()>
```

### compact_conversation(id)

Compact a chat now (#342)

Summarizes its older messages whatever its size, keeping the newest verbatim. NOTHING_TO_COMPACT for a chat too short.

```rust
pub async fn compact_conversation(&self, id: &str) -> Result<models::ConversationSummary>
```

### connect_service(id, body)

Check values with the service, then store them and add its tools

```rust
pub async fn connect_service(&self, id: &str, body: Option<&models::ConnectServiceRequest>) -> Result<()>
```

### continue_automation_run(id, run_id)

Open a run's result in a chat to reply to

Returns the chat the result was already posted to, or makes one with the result as its first answer, marked with meta.automation_run.

```rust
pub async fn continue_automation_run(&self, id: &str, run_id: &str) -> Result<models::ContinuedRun>
```

### conversation_from_summary(id)

A new chat that begins with this chat's summary (#342)

```rust
pub async fn conversation_from_summary(&self, id: &str) -> Result<models::Conversation>
```

### create_ai(body)

Create a specialized AI

```rust
pub async fn create_ai(&self, body: &models::CreateAIRequest) -> Result<models::SpecializedAI>
```

### create_api_key(body)

Create an API key; the secret is shown only in this response

```rust
pub async fn create_api_key(&self, body: &models::CreateAPIKeyRequest) -> Result<models::NewAPIKey>
```

### create_automation(body)

Create an automation

```rust
pub async fn create_automation(&self, body: &models::AutomationInput) -> Result<models::Automation>
```

### create_conversation(body)

Create conversation

```rust
pub async fn create_conversation(&self, body: Option<&models::CreateConversationRequest>) -> Result<models::Conversation>
```

### create_diagnostics(body)

Create a diagnostics bundle

```rust
pub async fn create_diagnostics(&self, body: Option<&models::CreateDiagnosticsRequest>) -> Result<models::DiagnosticsBundle>
```

### create_example_ai()

Create the example specialized AI

```rust
pub async fn create_example_ai(&self) -> Result<models::SpecializedAI>
```

### create_join_token(body)

Make a one-time join token and the command that adds a computer to this network

The token is shown once and only its proof key is kept. It lasts `ttl_minutes` (15 by default, at most 1440) and can be used once. Refused with 409 when other computers can't reach this one's Bifrost.

```rust
pub async fn create_join_token(&self, body: Option<&models::CreateJoinTokenRequest>) -> Result<models::JoinTokenCreated>
```

### create_knowledge_source(body)

Connect a file, folder, upload, pasted text, database, or web API

```rust
pub async fn create_knowledge_source(&self, body: &models::CreateKnowledgeSourceRequest) -> Result<models::KnowledgeSource>
```

### create_notification_destination(body)

Add an email or webhook destination; a webhook's signing secret is returned this once

```rust
pub async fn create_notification_destination(&self, body: &models::NotificationDestinationInput) -> Result<models::CreatedDestination>
```

### create_portal(body)

Add a chat portal (#205)

slug (2 to 40 lowercase letters, digits, or dashes) and name are required. It starts with no tools, no memory, passcode access (passcode required), and on.

```rust
pub async fn create_portal(&self, body: &Map<String, Value>) -> Result<models::Portal>
```

### create_profile(body)

Create a profile

```rust
pub async fn create_profile(&self, body: &Map<String, Value>) -> Result<Map<String, Value>>
```

### create_task(body)

Run a prompt as a task

```rust
pub async fn create_task(&self, body: &models::CreateTaskRequest) -> Result<models::Task>
```

### decide_tool(body)

Answer a tool approval request

```rust
pub async fn decide_tool(&self, body: &models::DecideToolRequest) -> Result<models::Status>
```

### delete_ai(id)

Delete a specialized AI

- `id`: Specialized AI id

```rust
pub async fn delete_ai(&self, id: &str) -> Result<()>
```

### delete_api_key(id)

Delete an API key

```rust
pub async fn delete_api_key(&self, id: &str) -> Result<()>
```

### delete_artifact(id)

Delete a file

```rust
pub async fn delete_artifact(&self, id: &str) -> Result<()>
```

### delete_automation(id)

Delete an automation

```rust
pub async fn delete_automation(&self, id: &str) -> Result<()>
```

### delete_conversation(id)

Delete conversation

```rust
pub async fn delete_conversation(&self, id: &str) -> Result<()>
```

### delete_conversations(body)

Delete several conversations

Deletes the caller's chats among ids, with their messages and files, in one request (#452, contract 1.25). Another person's chat, or one that doesn't exist, is skipped as not_found.

```rust
pub async fn delete_conversations(&self, body: &models::DeleteConversationsRequest) -> Result<models::ConversationsDeleted>
```

### delete_example(id, eid)

Delete an example

- `id`: Specialized AI id

```rust
pub async fn delete_example(&self, id: &str, eid: &str) -> Result<()>
```

### delete_export(id, rev)

Delete an exported file

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn delete_export(&self, id: &str, rev: &str) -> Result<()>
```

### delete_knowledge_source(id)

Remove a source and its index

```rust
pub async fn delete_knowledge_source(&self, id: &str) -> Result<()>
```

### delete_material(id, mid)

Remove material

- `id`: Specialized AI id

```rust
pub async fn delete_material(&self, id: &str, mid: &str) -> Result<()>
```

### delete_memory(id)

Delete a memory

```rust
pub async fn delete_memory(&self, id: &str) -> Result<()>
```

### delete_model(id, body, node_id)

Delete a model file

```rust
pub async fn delete_model(&self, id: &str, body: Option<&models::DeleteModelRequest>, node_id: Option<&str>) -> Result<()>
```

### delete_model_rating(id)

Remove this person's rating, withdrawing it first if it was shared

```rust
pub async fn delete_model_rating(&self, id: &str) -> Result<()>
```

### delete_notification_destination(id)

Remove a destination, its stored secret, and its waiting deliveries

```rust
pub async fn delete_notification_destination(&self, id: &str) -> Result<()>
```

### delete_portal(id)

Remove a chat portal (#205)

Its guests can no longer chat.

```rust
pub async fn delete_portal(&self, id: &str) -> Result<()>
```

### delete_profile(id)

Delete a custom profile

```rust
pub async fn delete_profile(&self, id: &str) -> Result<()>
```

### delete_run_records()

Delete run records now

```rust
pub async fn delete_run_records(&self) -> Result<()>
```

### deploy_revision(id, rev)

Deploy an evaluated revision

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn deploy_revision(&self, id: &str, rev: &str) -> Result<models::SpecializedAI>
```

### deployed_a_is()

Deployed specialized AIs, as model ids sai:&lt;slug&gt;

```rust
pub async fn deployed_a_is(&self) -> Result<Vec<models::Model>>
```

### describe_tool(id)

One tool's descriptor

```rust
pub async fn describe_tool(&self, id: &str) -> Result<models::ToolDescriptor>
```

### disconnect_my_device(id)

Disconnect one of your devices (#206)

```rust
pub async fn disconnect_my_device(&self, id: &str) -> Result<()>
```

### disconnect_service(id)

Delete the stored credential and remove the service's tools

```rust
pub async fn disconnect_service(&self, id: &str) -> Result<()>
```

### disconnect_this_device()

Disconnect this device, with its companions (#766)

A device's own key disconnects it, as the apps do when the person removes this computer. Its key and its companions' keys, such as its watch's, are revoked, and their notifications stop.

```rust
pub async fn disconnect_this_device(&self) -> Result<()>
```

### dismiss_model_rating(id)

Stop asking for a rating of a model

```rust
pub async fn dismiss_model_rating(&self, id: &str) -> Result<()>
```

### dismiss_notification(id)

Hide a notification from the notification center

```rust
pub async fn dismiss_notification(&self, id: &str) -> Result<()>
```

### download_export(id, rev)

Download the exported GGUF

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn download_export(&self, id: &str, rev: &str) -> Result<Vec<u8>>
```

### edit_conversation_summary(id, body)

Correct a chat's summary (#342)

Later summaries keep the correction.

```rust
pub async fn edit_conversation_summary(&self, id: &str, body: &models::EditConversationSummaryRequest) -> Result<models::ConversationSummary>
```

### enter_portal(slug)

Enter a portal as its guest (#205)

With passcode when the portal has one. Makes this browser the portal's guest, signed in by a toskar_portal_&lt;slug&gt; cookie that counts only on requests carrying X-Toskar-Portal. A guest reaches only the portal's chat, with the portal's profile, tools, memory, and language.

```rust
pub async fn enter_portal(&self, slug: &str) -> Result<models::EnteredPortal>
```

### evaluate_revision(id, rev)

Compare a revision with the base model

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn evaluate_revision(&self, id: &str, rev: &str) -> Result<models::Evaluation>
```

### export_diagnostics(include_conversations)

Create a diagnostics bundle (a zip without secrets or private keys)

```rust
pub async fn export_diagnostics(&self, include_conversations: Option<&str>) -> Result<models::DiagnosticsBundle>
```

### export_revision(id, rev)

Export a revision as one GGUF file

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn export_revision(&self, id: &str, rev: &str) -> Result<models::ExportStatus>
```

### export_status(id, rev)

Export status of a revision

- `id`: Specialized AI id
- `rev`: Revision number

```rust
pub async fn export_status(&self, id: &str, rev: &str) -> Result<models::ExportStatus>
```

### find_models_in_other_apps()

Models other local AI apps keep on this computer

GGUF models LM Studio, Ollama (through its manifests), llama.cpp, and GPT4All already downloaded, to add with POST /api/v1/models/import without downloading them again. Only headers and Ollama's manifests are read; incomplete files and vision projectors are left out (#467). GGUF files put in Toskar's own models folder by hand that aren't models yet come first, as app toskar; one is always added in place (#763).

```rust
pub async fn find_models_in_other_apps(&self) -> Result<models::FoundModels>
```

### get_about()

AGPL corresponding-source offer

```rust
pub async fn get_about(&self) -> Result<models::SourceOffer>
```

### get_ai(id)

A specialized AI with its materials, revisions, and jobs

- `id`: Specialized AI id

```rust
pub async fn get_ai(&self, id: &str) -> Result<models::SpecializedAI>
```

### get_api_tls()

How the API speaks HTTPS on the local network (#213)

```rust
pub async fn get_api_tls(&self) -> Result<models::TLSInfo>
```

### get_artifact(id)

One file

```rust
pub async fn get_artifact(&self, id: &str) -> Result<models::Artifact>
```

### get_artifact_content(id, inline)

A file's content

- `inline`: 1 shows a PDF or image in the browser instead of downloading it

```rust
pub async fn get_artifact_content(&self, id: &str, inline: Option<&str>) -> Result<Vec<u8>>
```

### get_automation(id)

An automation with its run history

```rust
pub async fn get_automation(&self, id: &str) -> Result<models::AutomationDetail>
```

### get_benchmark(id)

Get benchmark job status and results

```rust
pub async fn get_benchmark(&self, id: &str) -> Result<Map<String, Value>>
```

### get_capabilities(ask)

Capability inventory: what Toskar can do right now

- `ask`: A question such as "Can you generate an image?"; returns the abilities that answer it

```rust
pub async fn get_capabilities(&self, ask: Option<&str>) -> Result<Value>
```

### get_community_ratings()

Everyone's ratings of the models here, from hardware like this computer's and overall

Empty unless `community_ratings` is on. The public summary is downloaded at most once a day; when that fails, the last one is used and `error` says why.

```rust
pub async fn get_community_ratings(&self) -> Result<models::CommunityRatings>
```

### get_conversation_summary(id)

A chat's auto-compact summary (#342)

What the model sees in place of the chat's older messages, through which message. Every message stays saved.

```rust
pub async fn get_conversation_summary(&self, id: &str) -> Result<models::ConversationSummary>
```

### get_device_pairing()

Whether a phone has connected with the code shown

```rust
pub async fn get_device_pairing(&self) -> Result<models::DevicePairing>
```

### get_external_server()

The OpenAI-compatible server whose models can be chosen for a chat, and the models it offers

```rust
pub async fn get_external_server(&self) -> Result<models::ExternalServer>
```

### get_first_answers(days)

How long answers took to start, by app, cold or warm

Chat runs that reached a first token, grouped by the app that asked (the chat request's client) and by whether a model had to load first. Automations are left out.

- `days`: How many days back to look; 7 by default, 90 at most.

```rust
pub async fn get_first_answers(&self, days: Option<i64>) -> Result<models::FirstAnswers>
```

### get_gpu_setup()

What this computer still needs for Toskar to use its GPU

The graphics card found and each missing piece, most basic first, with a fix written for this computer: the Vulkan loader or drivers, permission to open the card's render device, NVIDIA's driver, a Windows card's driver, or the CPU-only llama.cpp build. No problems when the GPU is ready, when there is no GPU, and on macOS.

```rust
pub async fn get_gpu_setup(&self) -> Result<models::GPUSetup>
```

### get_hardware()

Local hardware inventory

```rust
pub async fn get_hardware(&self) -> Result<Map<String, Value>>
```

### get_health()

Health check

```rust
pub async fn get_health(&self) -> Result<models::HealthResponse>
```

### get_image_setup()

What image generation has installed, the models on offer, and any setup in progress

```rust
pub async fn get_image_setup(&self) -> Result<models::ImageSetup>
```

### get_knowledge_content(id)

The text of a pasted or uploaded source

```rust
pub async fn get_knowledge_content(&self, id: &str) -> Result<models::SourceText>
```

### get_knowledge_source(id)

One source

```rust
pub async fn get_knowledge_source(&self, id: &str) -> Result<models::KnowledgeSource>
```

### get_license()

Toskar Pro's trial or Unlock, as its desktop app last said

Core on its own has no license (`kind` empty) and nothing is limited. The Toskar Pro desktop app from the Mac App Store or the Microsoft Store sets a 14-day trial, unlocked, or ended (yeixio/toskar-apps#336). While `limited`, installing models, creating automations, and adding people answer 403 `UNLOCK_REQUIRED`; what's set up keeps working.

```rust
pub async fn get_license(&self) -> Result<models::License>
```

### get_log(name, tail_bytes)

Read a log file tail

```rust
pub async fn get_log(&self, name: &str, tail_bytes: Option<i64>) -> Result<models::LogContent>
```

### get_mcp_prompt(id, name, body)

Fill a prompt; returns its text

```rust
pub async fn get_mcp_prompt(&self, id: &str, name: &str, body: Option<&models::GetMCPPromptRequest>) -> Result<()>
```

### get_mcp_server(id)

One tool source

```rust
pub async fn get_mcp_server(&self, id: &str) -> Result<()>
```

### get_me()

Who the request is from (#206)

The person, their role, and how Toskar knows. A request from this computer is the Owner's; one with an API key is its person's.

```rust
pub async fn get_me(&self) -> Result<models::Me>
```

### get_model_placement(id)

Which computers can run an installed model

```rust
pub async fn get_model_placement(&self, id: &str) -> Result<models::ModelPlacement>
```

### get_model_rating(id)

This person's rating of a model, and exactly what sharing it would send

```rust
pub async fn get_model_rating(&self, id: &str) -> Result<models::ModelRating>
```

### get_network()

This computer's network, its Bifrost address and fingerprint, and the computers it trusts

```rust
pub async fn get_network(&self) -> Result<models::NetworkStatus>
```

### get_news()

The AI news from toskar.ai

New open models, runtime releases, and AI labs' announcements, a few lines each, from https://toskar.ai/news.json (#750). Read when asked, at most every six hours, and kept in the data folder so it shows offline; each read is listed in What left this computer as `news`. With the `ai_news` setting off, nothing is read and `enabled` is false. Members and Admins.

```rust
pub async fn get_news(&self) -> Result<models::News>
```

### get_notification(id)

One notification with each channel's delivery

```rust
pub async fn get_notification(&self, id: &str) -> Result<models::Notification>
```

### get_notification_destination(id)

One destination

```rust
pub async fn get_notification_destination(&self, id: &str) -> Result<models::NotificationDestination>
```

### get_oidc()

Whether sign-in with an OpenID Connect provider is offered (#206)

```rust
pub async fn get_oidc(&self) -> Result<models::OIDCInfo>
```

### get_person(id)

One person (#592)

```rust
pub async fn get_person(&self, id: &str) -> Result<models::Person>
```

### get_personalization()

How the person likes answers

```rust
pub async fn get_personalization(&self) -> Result<models::PersonalStyle>
```

### get_portal(id)

One chat portal (#205)

```rust
pub async fn get_portal(&self, id: &str) -> Result<models::Portal>
```

### get_portal_page(slug)

What a portal's page shows (#205)

Its name, access, language, and branding, and whether this browser is already its guest. Answers without signing in.

```rust
pub async fn get_portal_page(&self, slug: &str) -> Result<models::PortalPage>
```

### get_portal_usage(id)

How much a portal is used (#205)

Visitors who wrote, conversations, and messages they sent, over the last 7 and 30 days.

```rust
pub async fn get_portal_usage(&self, id: &str) -> Result<models::PortalUsage>
```

### get_privacy()

Run record retention and a 30-day summary of what left this computer

```rust
pub async fn get_privacy(&self) -> Result<()>
```

### get_profile(id)

One profile

```rust
pub async fn get_profile(&self, id: &str) -> Result<Map<String, Value>>
```

### get_profile_pins()

The profiles each pinnable role is kept to (#345)

```rust
pub async fn get_profile_pins(&self) -> Result<models::ProfilePins>
```

### get_push_status()

Push to the Toskar app on this device (#460)

What a paired phone or tablet needs to register with the push relay (the relay and this computer's key, which the relay seals into the device's handle), and whether this device has registered. See docs/push.md.

```rust
pub async fn get_push_status(&self) -> Result<models::PushStatus>
```

### get_quiet_hours()

Quiet hours

```rust
pub async fn get_quiet_hours(&self) -> Result<models::QuietHours>
```

### get_remote_access()

Access from anywhere's setting and its listener (#456)

enabled, port, address (a forwarded address, when set), listening (the address it listens on) or error, port_mapping, mapped and mapped_by (pcp, nat-pmp, or upnp) for the router port it opened, map_error, ipv6, reachable (direct, ipv6, manual, relay, or none) with reason (off, not_listening, carrier_nat, or no_port), relay (name, state: no_token, ended (contract 1.41: the token ran out with nothing to renew it, so it isn't sent; a new one takes over within a minute), connecting, connected, or error, and error, its code) while the relay client runs, and check, the last outside check (#546, contract 1.28): at, relay and direct (each way in with address, ok, reason, and ms), tried, and error when the last attempt didn't reach the relay (CHECK_UNSUPPORTED, CHECK_TOO_SOON, NO_TOKEN, RELAY_UNREACHABLE). With Toskar's relay, subscription (#639, contract 1.38): state (none, pending, active, or ended; contract 1.41: ended also when the token from the app's store or a subscription ran out, with expires the day it did), store (stripe when bought here in Settings, app when bought in the Toskar app), expires, open (whether Toskar's relay takes new subscriptions now, when known), checkout (the open checkout's page while pending), error (the last exchange's code when it didn't reach the relay), and in_app_only (contract 1.39: this copy is the Mac App Store's, which neither sells nor manages it; the Toskar app on a phone or tablet does). Set it with PATCH /api/v1/settings: remote_access_enabled, remote_access_port, remote_access_address, remote_access_port_mapping, remote_access_relay (an organization's relay, empty for Toskar's), and remote_access_relay_secret (its enrollment secret; write-only, empty clears it).

```rust
pub async fn get_remote_access(&self) -> Result<()>
```

### get_report()

What a problem report sends, scrubbed

Versions and the kind of computer, and for an Admin Core's last 40 warnings and errors. Email addresses, keys, tokens, home folder names, the computer's name, and internet addresses are taken out first. Members and paired devices may call it.

```rust
pub async fn get_report(&self) -> Result<models::DiagnosticsReport>
```

### get_route_secret()

The route secret, for a paired device on the home network (#456)

route_secret (base64url, 32 bytes), route_id, relay (the relay this computer uses away from home), and token, the computer's current token for Toskar's relay when it has one (contract 1.27), so each paired device can look it up away from home. Given only on the home network, never through the remote listener; pairing (POST /api/v1/devices/pair) returns them too.

```rust
pub async fn get_route_secret(&self) -> Result<models::DeviceRoute>
```

### get_run(id)

One run trace

```rust
pub async fn get_run(&self, id: &str) -> Result<()>
```

### get_runtime_history()

The daemon's memory and goroutines now and over the last day

Sampled every five minutes and kept for a day, so a slow leak shows on the Diagnostics page. Resets when the daemon restarts.

```rust
pub async fn get_runtime_history(&self) -> Result<models::RuntimeHistory>
```

### get_settings()

Get settings

```rust
pub async fn get_settings(&self) -> Result<Map<String, Value>>
```

### get_source()

AGPL corresponding-source offer

```rust
pub async fn get_source(&self) -> Result<models::SourceOffer>
```

### get_task(id)

One task

```rust
pub async fn get_task(&self, id: &str) -> Result<models::Task>
```

### get_topic_attempts(id, days)

A profile's off-topic attempts (#345)

What an Enforce profile held, or whose answer it replaced, over the last days (30 by default, up to 365), kept as run records are.

```rust
pub async fn get_topic_attempts(&self, id: &str, days: Option<i64>) -> Result<()>
```

### get_training_job(id)

One training job

```rust
pub async fn get_training_job(&self, id: &str) -> Result<models::TrainingJob>
```

### get_updates()

Whether a newer Toskar is out, from the daily check of toskar.ai

Release builds installed from a download check https://toskar.ai/releases/latest.json once a day, while the `update_check` setting is on. The App Store edition, the copy the desktop app runs (`TOSKAR_UPDATE_CHECK=off`), and development builds don't check, and say `supported` false.

```rust
pub async fn get_updates(&self) -> Result<models::UpdateStatus>
```

### get_version()

Application version

```rust
pub async fn get_version(&self) -> Result<models::VersionResponse>
```

### get_video_setup()

What video generation has installed, the models on offer, and any setup in progress

```rust
pub async fn get_video_setup(&self) -> Result<models::ImageSetup>
```

### import_model(body, filename, display_name, id)

Add a model from a GGUF file

A path on this computer as JSON, copied into the models folder (the default; progress comes as model.download events) or used in place with in_place, or the file itself as an application/octet-stream body with filename in the query. The header and tensor bounds are checked first (#467).

- `filename`: For an upload, the file's name, ending in .gguf

```rust
pub async fn import_model(&self, body: &models::ImportModelRequest, filename: Option<&str>, display_name: Option<&str>, id: Option<&str>) -> Result<models::ImportedModel>
```

### install_model(id, body, wait, node_id)

Download a catalog model, here or on a paired computer

```rust
pub async fn install_model(&self, id: &str, body: Option<&models::InstallModelRequest>, wait: Option<&str>, node_id: Option<&str>) -> Result<models::ModelInstall>
```

### install_model_from_url(body, wait)

Download a GGUF from a URL

- `wait`: true waits for the download to finish

```rust
pub async fn install_model_from_url(&self, body: &models::InstallFromURLRequest, wait: Option<&str>) -> Result<models::ModelInstall>
```

### install_runtime(id)

Install a runtime, such as llamacpp

```rust
pub async fn install_runtime(&self, id: &str) -> Result<models::RuntimeInstall>
```

### invite_portal_visitor(id, body)

Invite a visitor to a portal by name (#205)

Answers with the visitor and their one-time link (path /p/&lt;slug&gt;?invite=&lt;token&gt;, good for a week).

```rust
pub async fn invite_portal_visitor(&self, id: &str, body: &models::InvitePortalVisitorRequest) -> Result<models::InvitedVisitor>
```

### join_network(body)

Join this computer to the network of the computer that made a join token

Verifies the server's key against the fingerprint before proving the token, which never leaves this computer. Safe to repeat; refuses to switch networks while paired.

```rust
pub async fn join_network(&self, body: &models::JoinNetworkRequest) -> Result<models::JoinResult>
```

### leave_network()

Leave the network, telling each paired computer, and forget them all

Models, settings, and this computer's identity stay.

```rust
pub async fn leave_network(&self) -> Result<models::LeaveResult>
```

### list_a_is()

Specialized AIs

```rust
pub async fn list_a_is(&self) -> Result<Vec<models::SpecializedAI>>
```

### list_api_keys()

API keys, without their secrets

```rust
pub async fn list_api_keys(&self) -> Result<Vec<models::APIKey>>
```

### list_automation_runs(id, before, limit)

A page of an automation's runs, newest first

- `before`: The id of the last run already shown; the page starts after it
- `limit`: Runs per page, 1 to 100 (default 20)

```rust
pub async fn list_automation_runs(&self, id: &str, before: Option<&str>, limit: Option<i64>) -> Result<models::AutomationRunsPage>
```

### list_automations()

Automations with their last result

```rust
pub async fn list_automations(&self) -> Result<Vec<models::Automation>>
```

### list_benchmark_workloads()

List benchmark workload categories

```rust
pub async fn list_benchmark_workloads(&self) -> Result<Vec<Map<String, Value>>>
```

### list_benchmarks()

List recent benchmark jobs

```rust
pub async fn list_benchmarks(&self) -> Result<Vec<Map<String, Value>>>
```

### list_caches()

Caches with their declared policies and sizes

```rust
pub async fn list_caches(&self) -> Result<Vec<models::CacheInfo>>
```

### list_connectors()

List connected services and their status. Secret values are never returned.

```rust
pub async fn list_connectors(&self) -> Result<Vec<models::ConnectorStatus>>
```

### list_conversation_artifacts(id)

Files attached to or made in a conversation

```rust
pub async fn list_conversation_artifacts(&self, id: &str) -> Result<Vec<models::Artifact>>
```

### list_conversation_messages(id)

Messages of a conversation, with sources, steps, and files

```rust
pub async fn list_conversation_messages(&self, id: &str) -> Result<Vec<models::Message>>
```

### list_conversations()

List conversations

```rust
pub async fn list_conversations(&self) -> Result<Vec<models::Conversation>>
```

### list_devices(kind)

The connected services' devices, by kind (#586)

```rust
pub async fn list_devices(&self, kind: Option<&str>) -> Result<()>
```

### list_egress(conversation_id, limit)

What left this computer, newest first

```rust
pub async fn list_egress(&self, conversation_id: Option<&str>, limit: Option<i64>) -> Result<Vec<models::EgressRecord>>
```

### list_examples(id)

Training examples and their statistics

- `id`: Specialized AI id

```rust
pub async fn list_examples(&self, id: &str) -> Result<models::TrainingExamples>
```

### list_join_tokens()

Join tokens, active and from the last week, without their secrets

```rust
pub async fn list_join_tokens(&self) -> Result<Vec<models::JoinToken>>
```

### list_knowledge_sources()

Connected knowledge sources

```rust
pub async fn list_knowledge_sources(&self) -> Result<Vec<models::KnowledgeSource>>
```

### list_live_figures()

Live CPU, memory, and GPU figures for this and paired computers

Each computer's figures now, every few seconds over the last hour (every minute when no model is loaded), and per-minute averages over the last day. A figure a computer can't give, such as GPU temperature on a Mac, is left out rather than reported as 0. A paired computer that doesn't answer within 5 seconds is left out.

```rust
pub async fn list_live_figures(&self) -> Result<Vec<models::LiveFigures>>
```

### list_logs()

List diagnostic log files

```rust
pub async fn list_logs(&self) -> Result<Vec<models::LogFile>>
```

### list_mcp_servers()

List MCP tool sources with status, tools, and masked values. Secret values are never returned.

```rust
pub async fn list_mcp_servers(&self) -> Result<Vec<models::MCPServer>>
```

### list_memories()

Memories and the categories they can have

```rust
pub async fn list_memories(&self) -> Result<models::MemoryList>
```

### list_models()

List catalog and installed models

```rust
pub async fn list_models(&self) -> Result<Vec<models::Model>>
```

### list_my_devices()

Your connected devices (#206)

The phones, tablets, and TVs connected as the request's person, whatever their role.

```rust
pub async fn list_my_devices(&self) -> Result<Vec<models::MyDevice>>
```

### list_nodes()

List local and discovered computers

```rust
pub async fn list_nodes(&self) -> Result<Vec<Map<String, Value>>>
```

### list_notification_destinations()

Email and webhook destinations. Passwords and signing secrets are never returned.

```rust
pub async fn list_notification_destinations(&self) -> Result<Vec<models::NotificationDestination>>
```

### list_notifications(unread, limit, category)

List notifications that were not dismissed, newest first

- `unread`: 1 lists unread notifications only
- `category`: automation, approval, model, training, health, or system

```rust
pub async fn list_notifications(&self, unread: Option<&str>, limit: Option<i64>, category: Option<&str>) -> Result<models::NotificationList>
```

### list_people(role, disabled)

Everyone who uses this Toskar (Admins and the Owner)

- `role`: Only people with this role (#592).
- `disabled`: true for only disabled people, false for only active ones.

```rust
pub async fn list_people(&self, role: Option<&str>, disabled: Option<bool>) -> Result<Vec<models::Person>>
```

### list_performance(sort, order, limit)

List generation performance samples

```rust
pub async fn list_performance(&self, sort: Option<&str>, order: Option<&str>, limit: Option<i64>) -> Result<Vec<Map<String, Value>>>
```

### list_portal_conversations(id)

A portal's visitors' conversations (#205)

Newest first, for Admins. A Members only portal's chats are each Member's own, so they aren't here.

```rust
pub async fn list_portal_conversations(&self, id: &str) -> Result<Vec<models::PortalConversation>>
```

### list_portal_messages(id, cid)

One visitor's conversation, to read (#205)

```rust
pub async fn list_portal_messages(&self, id: &str, cid: &str) -> Result<Vec<models::PortalMessage>>
```

### list_portal_visitors(id)

A portal's invited visitors (#205)

```rust
pub async fn list_portal_visitors(&self, id: &str) -> Result<Vec<models::Person>>
```

### list_portals()

Chat portals (#205)

Every portal, for Admins and the Owner.

```rust
pub async fn list_portals(&self) -> Result<Vec<models::Portal>>
```

### list_profiles()

List AI profiles

```rust
pub async fn list_profiles(&self) -> Result<Vec<Map<String, Value>>>
```

### list_running_models()

Loaded model instances on this and paired computers

```rust
pub async fn list_running_models(&self) -> Result<Vec<models::RunningModelView>>
```

### list_runs(conversation_id, limit)

Recent run traces, newest first

```rust
pub async fn list_runs(&self, conversation_id: Option<&str>, limit: Option<i64>) -> Result<()>
```

### list_runtimes()

Runtimes and whether each is installed

```rust
pub async fn list_runtimes(&self) -> Result<Vec<models::RuntimeInfo>>
```

### list_tasks()

Recent tasks

```rust
pub async fn list_tasks(&self) -> Result<Vec<models::Task>>
```

### list_tool_runs(tool_id, conversation_id, limit)

Audited tool calls, newest first; records expire with run records

```rust
pub async fn list_tool_runs(&self, tool_id: Option<&str>, conversation_id: Option<&str>, limit: Option<i64>) -> Result<Vec<models::ToolRun>>
```

### list_tools()

Every tool's descriptor, with whether it is on, its health, and the profiles that allow it

```rust
pub async fn list_tools(&self) -> Result<Vec<models::ToolDescriptor>>
```

### list_training_jobs(ai_id)

Training jobs

```rust
pub async fn list_training_jobs(&self, ai_id: Option<&str>) -> Result<Vec<models::TrainingJob>>
```

### make_automation_hook(id)

Make a webhook trigger's link

Returns a new token, the only time it's shown; only its hash is kept. The old link stops working.

```rust
pub async fn make_automation_hook(&self, id: &str) -> Result<models::HookLink>
```

### manage_subscription()

The billing page for the subscription bought here (#639)

Answers {url}, Stripe's billing page for the subscription bought in Settings: change the card, download receipts, cancel. Admins only. 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy; 404 SUBSCRIPTION_NONE when none was bought here (one bought in the Toskar app is managed in the device's store); 502 BILLING_UNAVAILABLE.

```rust
pub async fn manage_subscription(&self) -> Result<()>
```

### mark_notifications_read(body)

Mark notifications read; no ids marks all of them

```rust
pub async fn mark_notifications_read(&self, body: Option<&models::MarkNotificationsReadRequest>) -> Result<()>
```

### mark_on_topic(id, aid)

Mark an off-topic attempt as on topic (#345)

Adds its message to the profile's example questions and forgets the attempts with that message.

```rust
pub async fn mark_on_topic(&self, id: &str, aid: &str) -> Result<()>
```

### mcp_gallery()

Gallery entries, with programs that are missing and sources already added

```rust
pub async fn mcp_gallery(&self) -> Result<()>
```

### mcp_import_candidates()

MCP servers set up in other apps on this computer, with secret values hidden

```rust
pub async fn mcp_import_candidates(&self) -> Result<()>
```

### mcp_o_auth_callback()

Where a tool source's sign-in returns; shows a page that says how it went

```rust
pub async fn mcp_o_auth_callback(&self) -> Result<()>
```

### mcp_server(body)

Toskar's MCP server (Streamable HTTP, JSON-RPC). Tools ask_local_ai, list_local_models, search_my_knowledge.

Checked like /v1. A request with an Origin header from another site is refused.

```rust
pub async fn mcp_server(&self, body: Option<&Map<String, Value>>) -> Result<()>
```

### mcp_server_delete()

End an MCP session

```rust
pub async fn mcp_server_delete(&self) -> Result<()>
```

### mcp_server_get()

Not supported; the server does not open a stream

```rust
pub async fn mcp_server_get(&self) -> Result<()>
```

### mcp_server_logs(id)

Recent log lines of a tool source

```rust
pub async fn mcp_server_logs(&self, id: &str) -> Result<()>
```

### mcp_server_prompts(id)

The tool source's ready-made prompts

```rust
pub async fn mcp_server_prompts(&self, id: &str) -> Result<()>
```

### mcp_server_resources(id)

The tool source's resources

```rust
pub async fn mcp_server_resources(&self, id: &str) -> Result<()>
```

### mcp_share()

The address and command other apps use to reach Toskar's MCP server

```rust
pub async fn mcp_share(&self) -> Result<()>
```

### models_fit()

How well each catalog model fits this computer

```rust
pub async fn models_fit(&self) -> Result<Vec<models::ModelsFit>>
```

### oidc_callback(state, code)

Where the provider sends people back (#206)

Checks the state against this browser's cookie, swaps the code for an ID token and checks it, signs the browser in, and redirects to the path it started from. A failure redirects to /?oidc_error= failed, refused, disabled, or unavailable.

```rust
pub async fn oidc_callback(&self, state: Option<&str>, code: Option<&str>) -> Result<()>
```

### openai_chat_completions(body)

OpenAI-compatible chat completions

temperature and max_tokens apply to the calls that write the answer (#70). The toskar object asks for memory, knowledge, tools, effort, and placement, within what the API key allows. yggdrasil, its name from before the rename, works too; toskar wins when both are sent. Responses carry the answer's extension fields under both names.

```rust
pub async fn openai_chat_completions(&self, body: &models::OpenaiChatCompletionsRequest) -> Result<models::OpenAIChatCompletion>
```

### openai_list_models()

OpenAI-compatible model list

auto, each profile as profile:&lt;id&gt;, and each deployed specialized AI as sai:&lt;slug&gt;.

```rust
pub async fn openai_list_models(&self) -> Result<models::OpenAIModelList>
```

### outbound_pairing(code)

The offer this computer made for a code

```rust
pub async fn outbound_pairing(&self, code: &str) -> Result<models::PairingOffer>
```

### pair_device(body)

A phone exchanges the code for its own key (no key needed; local network only)

```rust
pub async fn pair_device(&self, body: &models::PairDeviceRequest) -> Result<models::PairedDevice>
```

### pair_node(body)

Offer to pair with a discovered computer

```rust
pub async fn pair_node(&self, body: &models::PairNodeRequest) -> Result<models::PairingSession>
```

### parse_automation(body)

Read a request such as "every morning at 8, tell me if the price is below $500" into an automation

```rust
pub async fn parse_automation(&self, body: &models::ParseAutomationRequest) -> Result<models::AutomationRequest>
```

### parse_mcp(body)

Read pasted settings, a web address, or a command line into server specs and what each still needs

```rust
pub async fn parse_mcp(&self, body: Option<&models::ParseMCPRequest>) -> Result<()>
```

### pause_automation(id)

Pause an automation

```rust
pub async fn pause_automation(&self, id: &str) -> Result<models::Automation>
```

### peek_invite(token)

What a one-time sign-in link is for (#206)

```rust
pub async fn peek_invite(&self, token: &str) -> Result<models::Invite>
```

### pending_pairings()

Pairing offers waiting for approval on this computer

```rust
pub async fn pending_pairings(&self) -> Result<Vec<models::PairingOffer>>
```

### people_activity(person, limit)

Who changed whom (#592)

Newest first. Adding, changing, disabling, removing, setting passwords, making links, and revoking keys and devices; never a password.

- `person`: Only entries by or about this person.
- `limit`: At most this many, 100 by default and 500 at most.

```rust
pub async fn people_activity(&self, person: Option<&str>, limit: Option<i64>) -> Result<Vec<models::ActivityEntry>>
```

### person_capabilities(id)

What one person may use (#589)

```rust
pub async fn person_capabilities(&self, id: &str) -> Result<models::PersonCapabilities>
```

### person_devices(id)

A person's connected devices (#592)

```rust
pub async fn person_devices(&self, id: &str) -> Result<Vec<models::APIKey>>
```

### person_keys(id)

A person's API keys, other than their devices (#592)

```rust
pub async fn person_keys(&self, id: &str) -> Result<Vec<models::APIKey>>
```

### person_link(id)

A new one-time link for a person; a reset link once they have a sign-in

```rust
pub async fn person_link(&self, id: &str) -> Result<models::InviteLink>
```

### portal_visitor_link(id, vid)

A new link for an invited visitor (#205)

Replaces any link they haven't used.

```rust
pub async fn portal_visitor_link(&self, id: &str, vid: &str) -> Result<models::VisitorLink>
```

### preview_automation(body)

Check an automation and show its next runs without saving it

```rust
pub async fn preview_automation(&self, body: &models::AutomationInput) -> Result<models::AutomationPreview>
```

### preview_model_from_url(body)

What a download from a URL would bring, without downloading it

The file and its size (and its vision projector's) from the repository, the free space where models are kept, whether it's already a model here, and copies of the same file other apps have (by name, Ollama's SHA-256 blob, or a large file's exact size), which can be added where they are instead (#611).

```rust
pub async fn preview_model_from_url(&self, body: &models::InstallFromURLRequest) -> Result<models::URLPreview>
```

### put_license(x_toskar_shell, body)

Set Toskar Pro's trial or Unlock (the desktop app only)

Only the Toskar Pro desktop app on this computer, with the `X-Toskar-Shell` secret it started Core with (`TOSKAR_SHELL_SECRET`). Anything else gets 403 `SHELL_ONLY`.

```rust
pub async fn put_license(&self, x_toskar_shell: &str, body: &models::PutLicenseRequest) -> Result<models::License>
```

### put_model_rating(id, body)

Rate a model 1–5 stars, and share the rating with the community or keep it on this computer

Sharing sends the stars, tags, model identity, hardware class, a random rating ID, and the app version to the ratings service. `share` false withdraws a rating that was shared. A 502 means the rating was saved here but the service could not be reached.

```rust
pub async fn put_model_rating(&self, id: &str, body: &models::PutModelRatingRequest) -> Result<models::ModelRating>
```

### put_relay_token()

Hand over a subscription's relay token (#456)

Body {token, enable}. token is the route token the app got for this computer by exchanging a store receipt with Toskar's relay; the computer keeps it and registers and keeps its tunnel there. A paired device may send it, from home or through the remote listener. enable also turns access from anywhere on, and needs an Admin (403 ROLE_REQUIRED). Answers state: the relay client's state, or off. 400 RELAY_TOKEN_INVALID for a token that isn't for this computer's route or has expired, RELAY_TOKEN_NOT_NEEDED when an organization's relay is set.

```rust
pub async fn put_relay_token(&self) -> Result<()>
```

### put_settings(body)

Update settings (same as PATCH)

```rust
pub async fn put_settings(&self, body: &Map<String, Value>) -> Result<Map<String, Value>>
```

### read_aloud(body)

Read text aloud on this computer; the audio is kept as a file in the chat

```rust
pub async fn read_aloud(&self, body: &models::ReadAloudRequest) -> Result<models::SpokenText>
```

### receive_pairing_offer(body)

Receive a pairing offer from another computer

```rust
pub async fn receive_pairing_offer(&self, body: &models::PairingOffer) -> Result<models::PairingSession>
```

### recommend_models(purpose)

Recommended models for this computer

- `purpose`: What the model is for, such as chat or coding

```rust
pub async fn recommend_models(&self, purpose: Option<&str>) -> Result<models::Recommendation>
```

### refresh_knowledge_source(id)

Reindex a source; a failure is recorded on the source

```rust
pub async fn refresh_knowledge_source(&self, id: &str) -> Result<models::KnowledgeSource>
```

### refresh_nodes()

Look for computers again

```rust
pub async fn refresh_nodes(&self) -> Result<models::OK>
```

### register_push(body)

Register this device's push handle

A paired phone or tablet gives the sealed handle the push relay made from its push token. Only a paired device's key may; another gets PUSH_DEVICE_ONLY. The computer never sees the token. Disconnecting the device ends its pushes.

```rust
pub async fn register_push(&self, body: &models::RegisterPushRequest) -> Result<models::PushStatus>
```

### remove_image_model(id)

Delete an installed image model to free its space

```rust
pub async fn remove_image_model(&self, id: &str) -> Result<models::ImageSetup>
```

### remove_mcp_server(id)

Stop a tool source, remove its tools, and delete its stored secrets

```rust
pub async fn remove_mcp_server(&self, id: &str) -> Result<()>
```

### remove_person(id, body, transfer_to)

Remove a person (#592)

Revokes their keys and devices, signs them out, and deletes their data or gives it to transfer_to. Nobody removes themselves or the Owner, and only the Owner removes Admins. The body's confirm must be their name.

- `transfer_to`: A person to give their chats, memories, automations, files, and notifications to, instead of deleting them.

```rust
pub async fn remove_person(&self, id: &str, body: &models::RemovePersonRequest, transfer_to: Option<&str>) -> Result<()>
```

### remove_portal_visitor(id, vid)

Remove an invited visitor (#205)

They're disabled and signed out at once.

```rust
pub async fn remove_portal_visitor(&self, id: &str, vid: &str) -> Result<()>
```

### remove_video_model(id)

Delete an installed video model to free its space

```rust
pub async fn remove_video_model(&self, id: &str) -> Result<models::ImageSetup>
```

### replace_mcp_server(id, body)

Change how a tool source is reached, then check it. Blank secret values keep the stored ones.

```rust
pub async fn replace_mcp_server(&self, id: &str, body: Option<&models::ReplaceMCPServerRequest>) -> Result<()>
```

### reset_app(body, delete_models)

Reset application to defaults

Clears chats, custom profiles, tasks, and API keys; restores settings and built-in profiles. Downloaded models and runtimes are kept unless delete_models is true. The client should clear local UI state and restart onboarding. Not reversible.

```rust
pub async fn reset_app(&self, body: Option<&models::ResetAppRequest>, delete_models: Option<&str>) -> Result<Map<String, Value>>
```

### reset_profile(id)

Put a built-in profile back to how Toskar ships it

```rust
pub async fn reset_profile(&self, id: &str) -> Result<Map<String, Value>>
```

### resume_automation(id)

Resume an automation

```rust
pub async fn resume_automation(&self, id: &str) -> Result<models::Automation>
```

### revoke_join_token(id)

Revoke an unused join token

```rust
pub async fn revoke_join_token(&self, id: &str) -> Result<models::JoinToken>
```

### revoke_node(id)

Stop trusting a paired computer

```rust
pub async fn revoke_node(&self, id: &str) -> Result<()>
```

### revoke_person_device(id, key)

Disconnect one of a person's devices (#592)

```rust
pub async fn revoke_person_device(&self, id: &str, key: &str) -> Result<()>
```

### revoke_person_key(id, key)

Revoke one of a person's keys (#592)

```rust
pub async fn revoke_person_key(&self, id: &str, key: &str) -> Result<()>
```

### role_capabilities()

What each role may use (#589)

Every capability in order, each role's, and the defaults each role ships with. The Owner always has everything.

```rust
pub async fn role_capabilities(&self) -> Result<models::RoleCapabilities>
```

### rotate_api_key(id)

Replace a key's secret; the old one stops working

```rust
pub async fn rotate_api_key(&self, id: &str) -> Result<models::NewAPIKey>
```

### rotate_notification_secret(id)

Replace a webhook's signing secret; the old one stops working

```rust
pub async fn rotate_notification_secret(&self, id: &str) -> Result<models::DestinationSecret>
```

### run_automation(id)

Run an automation now

```rust
pub async fn run_automation(&self, id: &str) -> Result<models::AutomationRunInfo>
```

### run_hook(token, body)

Start the automation a webhook link belongs to

The token in the link is the only proof, so this needs no API key. The request body (up to 64 KB, any type) goes to the run as data from the caller, never as instructions. One automation's link takes a call at most every 10 seconds.

```rust
pub async fn run_hook(&self, token: &str, body: Option<String>) -> Result<models::HookRun>
```

### search_knowledge(body)

Search connected knowledge

```rust
pub async fn search_knowledge(&self, body: &models::SearchKnowledgeRequest) -> Result<Vec<models::KnowledgeHit>>
```

### send_report()

Send a problem report to Toskar (#588)

Body {product (core, the default, or apps), app, where, code, error, note, email, details}. Core scrubs the error and note as it scrubs its own report, adds that report when details is true, and sends it to Toskar's report service (https://toskar.ai/api/report, or TOSKAR_REPORT_URL), which files it as an issue in a private repository, grouped with others for the same error and version. A reply address goes to the Toskar team by email, never into the issue. Answers {status: created or added, number}. Each one is listed in What left this computer as problem_report. Members and paired devices may send. 400 REPORT_INVALID; 403 REPORTS_OFF when an Admin turned problem_reports off; 429 REPORT_RATE_LIMITED; 502 REPORTS_UNAVAILABLE when the service can't be reached or isn't set up, for the client to send by email instead (contract 1.40).

```rust
pub async fn send_report(&self) -> Result<()>
```

### set_api_key_permissions(id, body)

Change what an API key may ask of the assistant

```rust
pub async fn set_api_key_permissions(&self, id: &str, body: Option<&models::SetAPIKeyPermissionsRequest>) -> Result<()>
```

### set_external_server(body)

Set the external server's base URL and API key

The key is stored in the secrets folder and never returned. An empty api_key keeps the stored one; clear_key removes it; an empty base_url turns the server off.

```rust
pub async fn set_external_server(&self, body: &models::SetExternalServerRequest) -> Result<models::ExternalServer>
```

### set_model_projector(id, body)

Give an added model its vision projector

A GGUF vision projector (mmproj) on this computer, copied beside the model so it can see pictures (#467).

```rust
pub async fn set_model_projector(&self, id: &str, body: &models::SetModelProjectorRequest) -> Result<models::ModelVision>
```

### set_my_preferences(body)

Save your own languages (#206)

The request's person's App language and assistant language, whatever their role. The Owner's are the install's, which others start from until they choose. Answers with the person's settings.

```rust
pub async fn set_my_preferences(&self, body: &models::SetMyPreferencesRequest) -> Result<Map<String, Value>>
```

### set_person_capabilities(id, body)

Allow or Block something for one person (#589)

true allows, false blocks, and null is as their role's. The Owner's are fixed.

```rust
pub async fn set_person_capabilities(&self, id: &str, body: &BTreeMap<String, Option<bool>>) -> Result<models::PersonCapabilities>
```

### set_person_profiles(id, body)

Pin a Member or Visitor to profiles (#345)

profiles: a list replaces their role's pin, \[\] is any profile, and null is their role's again. The Owner and Admins can't be pinned.

```rust
pub async fn set_person_profiles(&self, id: &str, body: &models::SetPersonProfilesRequest) -> Result<models::Person>
```

### set_personalization(body)

Save how the person likes answers. Style only; it cannot grant a permission.

```rust
pub async fn set_personalization(&self, body: Option<&models::PersonalStyle>) -> Result<()>
```

### set_quiet_hours(body)

Set quiet hours

```rust
pub async fn set_quiet_hours(&self, body: &models::QuietHours) -> Result<models::QuietHours>
```

### set_role_capabilities(role, body)

Change what a role may use (#589)

Only the Owner changes the Admins'. The Owner's are fixed.

```rust
pub async fn set_role_capabilities(&self, role: &str, body: &BTreeMap<String, bool>) -> Result<BTreeMap<String, bool>>
```

### set_role_profiles(role, body)

Pin a role to profiles (#345)

```rust
pub async fn set_role_profiles(&self, role: &str, body: &models::SetRoleProfilesRequest) -> Result<models::ProfilePins>
```

### set_run_retention(body)

Set how long run records are kept; 0 keeps them

```rust
pub async fn set_run_retention(&self, body: Option<&models::SetRunRetentionRequest>) -> Result<()>
```

### set_test_prompts(id, body)

Set the prompts evaluation compares

- `id`: Specialized AI id

```rust
pub async fn set_test_prompts(&self, id: &str, body: &models::SetTestPromptsRequest) -> Result<Vec<models::EvalPrompt>>
```

### set_tool_enabled(id, body)

Turn a tool on or off

```rust
pub async fn set_tool_enabled(&self, id: &str, body: &models::SetToolEnabledRequest) -> Result<models::ToolEnabled>
```

### show_message_version(id, mid)

Show a version of its point in the chat, with what followed it (#447)

```rust
pub async fn show_message_version(&self, id: &str, mid: &str) -> Result<Vec<models::Message>>
```

### sign_in(body)

Sign in with a username and password (#206)

Sets the session cookie. Five failures for a username in 15 minutes, or twenty from an address in ten, answer 429 SIGN_IN_THROTTLED for a while.

```rust
pub async fn sign_in(&self, body: &models::SignInRequest) -> Result<models::Principal>
```

### sign_in_mcp_server(id, body)

Start signing in to the tool source's service; returns the address to open

```rust
pub async fn sign_in_mcp_server(&self, id: &str, body: Option<&models::SignInMCPServerRequest>) -> Result<()>
```

### sign_out()

Sign out this browser

```rust
pub async fn sign_out(&self) -> Result<()>
```

### sign_out_mcp_server(id)

Forget the tool source's sign-in

```rust
pub async fn sign_out_mcp_server(&self, id: &str) -> Result<()>
```

### start_benchmark(body)

Start a multi-model benchmark

```rust
pub async fn start_benchmark(&self, body: &Map<String, Value>) -> Result<Map<String, Value>>
```

### start_device_pairing(body)

Show a 6-digit code a phone connects with, replacing any other

```rust
pub async fn start_device_pairing(&self, body: Option<&models::StartDevicePairingRequest>) -> Result<models::DevicePairing>
```

### start_image_setup(body)

Install stable-diffusion.cpp and an image model in the background

```rust
pub async fn start_image_setup(&self, body: &models::StartImageSetupRequest) -> Result<models::ImageSetup>
```

### start_model(id, body)

Load a model

```rust
pub async fn start_model(&self, id: &str, body: Option<&models::StartModelRequest>) -> Result<models::RunningModelView>
```

### start_oidc(r#return)

Go to the provider to sign in (#206)

Redirects to the provider with PKCE, and sets a short-lived cookie with the sign-in's state. return is the path in Toskar to go to afterwards.

```rust
pub async fn start_oidc(&self, r#return: Option<&str>) -> Result<()>
```

### start_subscription_checkout()

Subscribe to access from anywhere here, with Stripe (#639)

Body {plan}: monthly or yearly. Opens a Stripe checkout at yeix.io, which bills for Toskar, for this computer's route on Toskar's relay, and answers {url}, its page, for the person to open. Toskar then asks the relay every few seconds whether it's paid; once it is, it keeps the relay token, turns access from anywhere on, and renews the token as the subscription does. Admins only. 400 SUBSCRIPTION_PLAN_INVALID; 409 SUBSCRIPTION_IN_APP_ONLY in the Mac App Store's copy, SUBSCRIPTION_OWN_RELAY with an organization's relay, SUBSCRIPTION_ACTIVE when this computer already has a current token; 503 RELAY_SOLD_OUT when Toskar's relay takes no new subscriptions; 502 BILLING_UNAVAILABLE.

```rust
pub async fn start_subscription_checkout(&self) -> Result<()>
```

### start_training(id, body)

Start training

- `id`: Specialized AI id

```rust
pub async fn start_training(&self, id: &str, body: Option<&models::StartTrainingRequest>) -> Result<models::TrainingJob>
```

### start_video_setup(body)

Install stable-diffusion.cpp and a video model in the background

```rust
pub async fn start_video_setup(&self, body: &models::StartVideoSetupRequest) -> Result<models::ImageSetup>
```

### stop_chat(body)

Stop a conversation's running turn

```rust
pub async fn stop_chat(&self, body: &models::StopChatRequest) -> Result<models::ChatStopped>
```

### stop_model(id, body)

Unload a model instance

```rust
pub async fn stop_model(&self, id: &str, body: Option<&models::StopModelRequest>) -> Result<models::OK>
```

### test_notification_destination(id)

Send a test notification now

```rust
pub async fn test_notification_destination(&self, id: &str) -> Result<models::OK>
```

### test_tool(id, body)

Run a tool once with the given arguments

```rust
pub async fn test_tool(&self, id: &str, body: &models::TestToolRequest) -> Result<Map<String, Value>>
```

### tool_activity()

Recent tool calls and pending approvals

```rust
pub async fn tool_activity(&self) -> Result<Vec<models::ToolActivity>>
```

### tool_providers()

Each computer's providers for tools that can run on any paired computer, and their state

```rust
pub async fn tool_providers(&self) -> Result<Vec<models::NodeToolProviders>>
```

### training_backends()

Trainers on this computer and whether each can run

```rust
pub async fn training_backends(&self) -> Result<Vec<models::TrainingBackend>>
```

### training_base_models(goal)

Trainable base models, ranked for a goal

```rust
pub async fn training_base_models(&self, goal: Option<&str>) -> Result<Vec<models::TrainingBaseModel>>
```

### training_plan(id)

Training plan: fit, downloads, disk, time, and the computer to train on

- `id`: Specialized AI id

```rust
pub async fn training_plan(&self, id: &str) -> Result<models::TrainingPlan>
```

### training_samples()

Sample material files

```rust
pub async fn training_samples(&self) -> Result<Vec<models::TrainingSample>>
```

### transcribe_recording(body)

A recording's text, for speaking a message instead of typing it (yeixio/toskar-apps#155)

The recording is attached first with POST /api/v1/artifacts (audio). Runs speech.transcribe (Whisper) on this computer or a paired one that has it, and answers the text for the person to check before sending. Visitors and paired devices may use it.

```rust
pub async fn transcribe_recording(&self, body: &models::TranscribeRecordingRequest) -> Result<models::Transcription>
```

### try_topics(id, body)

Try one message against a profile's topic controls (#345)

message (up to 2000 characters), and optional topics: draft topic controls used in place of the saved ones. Nothing is saved. The answer is a quick one, without tools, knowledge, or memories.

```rust
pub async fn try_topics(&self, id: &str, body: &models::TryTopicsRequest) -> Result<()>
```

### undeploy_ai(id)

Stop serving a specialized AI

- `id`: Specialized AI id

```rust
pub async fn undeploy_ai(&self, id: &str) -> Result<models::SpecializedAI>
```

### unregister_push()

Stop pushes to this device

```rust
pub async fn unregister_push(&self) -> Result<()>
```

### update_added_model(id, body)

Rename or retag an added model

For a model added from a file or a link; catalog models keep their own (#467). Tags are general, coding, reasoning, and writing; vision comes with a projector.

```rust
pub async fn update_added_model(&self, id: &str, body: &models::UpdateAddedModelRequest) -> Result<models::AddedModel>
```

### update_ai(id, body)

Update a specialized AI

- `id`: Specialized AI id

```rust
pub async fn update_ai(&self, id: &str, body: &models::UpdateAIRequest) -> Result<models::SpecializedAI>
```

### update_automation(id, body)

Change only the fields given

```rust
pub async fn update_automation(&self, id: &str, body: &models::AutomationInput) -> Result<models::Automation>
```

### update_conversation(id, body)

Update conversation

```rust
pub async fn update_conversation(&self, id: &str, body: Option<&models::UpdateConversationRequest>) -> Result<models::Conversation>
```

### update_example(id, eid, body)

Edit or exclude an example

- `id`: Specialized AI id

```rust
pub async fn update_example(&self, id: &str, eid: &str, body: &models::UpdateExampleRequest) -> Result<()>
```

### update_knowledge_source(id, body)

Rename a source, replace a text source's content, or change its connection

```rust
pub async fn update_knowledge_source(&self, id: &str, body: &models::UpdateKnowledgeSourceRequest) -> Result<models::KnowledgeSource>
```

### update_mcp_server(id, body)

Change enabled, allow_sampling, always_offer, keywords, or per-tool policies (allow, ask, default)

```rust
pub async fn update_mcp_server(&self, id: &str, body: Option<&Map<String, Value>>) -> Result<()>
```

### update_memory(id, body)

Edit, turn off, or keep a memory on this computer only

```rust
pub async fn update_memory(&self, id: &str, body: &models::UpdateMemoryRequest) -> Result<models::Memory>
```

### update_notification_destination(id, body)

Change a destination; an empty password keeps the stored one

```rust
pub async fn update_notification_destination(&self, id: &str, body: &models::NotificationDestinationInput) -> Result<models::NotificationDestination>
```

### update_portal(id, body)

Change a chat portal (#205)

Any of slug, name, profile_id, tools (none, read_only, profile), memory, language, access (open, passcode), passcode (empty removes it), branding (a JSON object), and enabled. Turning it off stops its visitors at once.

```rust
pub async fn update_portal(&self, id: &str, body: &Map<String, Value>) -> Result<models::Portal>
```

### update_profile(id, body)

Update a profile, including its orchestration controls

```rust
pub async fn update_profile(&self, id: &str, body: &Map<String, Value>) -> Result<Map<String, Value>>
```

### update_settings(body)

Update settings

```rust
pub async fn update_settings(&self, body: &Map<String, Value>) -> Result<Map<String, Value>>
```

### upload_artifact(body)

Upload a file to attach to a chat (up to 25 MB)

```rust
pub async fn upload_artifact(&self, body: &models::UploadArtifactRequest) -> Result<models::Artifact>
```

### use_image_build(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

```rust
pub async fn use_image_build(&self, body: &models::UseImageBuildRequest) -> Result<models::ImageSetup>
```

### use_video_build(body)

Switch stable-diffusion.cpp to its CPU build, or back to its GPU build

Images and video share the program, so this switches both. The GPU build is Metal on macOS and Vulkan on Linux and Windows, used when a GPU with a Vulkan driver is found; a Vulkan build that can't start on the GPU falls back to the CPU build by itself.

```rust
pub async fn use_video_build(&self, body: &models::UseVideoBuildRequest) -> Result<models::ImageSetup>
```

### warm_model(body)

Start loading the model a chat would use

Starts loading, in the background, the model a chat on the profile would use, and answers at once (#498), so it loads while someone types or speaks. Never loads beside a model that is answering, nor one that wouldn't fit beside those already loaded.

```rust
pub async fn warm_model(&self, body: Option<&models::WarmModelRequest>) -> Result<models::ModelWarmResponse>
```
