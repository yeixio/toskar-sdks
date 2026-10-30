# Swift error codes

*Generated from the codes' declarations by `swift/scripts/reference.py`: Toskar Core's error catalog, by way of `swift/scripts/codes.swift`, and the SDK's own.*

The codes Toskar Core and the SDK answer errors with, as `ToskarError.Code`, with each one's English text. A newer Core may answer with a code this list doesn't have yet.

| Code | Value | Text |
| --- | --- | --- |
| `.apiKeyInUrl` | `API_KEY_IN_URL` | Send the API key in the Authorization header, not in the address. |
| `.apiKeyRequired` | `API_KEY_REQUIRED` | Create an API key or add a person before allowing access from other devices. |
| `.apiKeysListFailed` | `API_KEYS_LIST_FAILED` | {{detail}} |
| `.approveFailed` | `APPROVE_FAILED` | {{detail}} |
| `.attemptNotFound` | `ATTEMPT_NOT_FOUND` | That attempt is gone. |
| `.automationFailed` | `AUTOMATION_FAILED` | {{detail}} |
| `.automationInterrupted` | `AUTOMATION_INTERRUPTED` | The run didn't finish because Toskar stopped while it ran. It runs again at its next time. |
| `.automationInvalid` | `AUTOMATION_INVALID` | {{detail}} |
| `.automationNoResult` | `AUTOMATION_NO_RESULT` | This run has no result to continue in chat. |
| `.automationNotWebhook` | `AUTOMATION_NOT_WEBHOOK` | This automation doesn't run from a webhook. |
| `.automationPaused` | `AUTOMATION_PAUSED` | This automation is paused. |
| `.automationRunning` | `AUTOMATION_RUNNING` | This automation is already running. Its result will appear here when it finishes. |
| `.automationTimeout` | `AUTOMATION_TIMEOUT` | The run took longer than {{minutes}} minutes and was stopped. Try a faster model or a shorter prompt. |
| `.badRequest` | `BAD_REQUEST` | {{detail}} |
| `.badResponse` | `BAD_RESPONSE` | The Toskar service sent an answer the app couldn't read (HTTP {{status}}). Try again; if it keeps happening, report it. |
| `.benchmarkListFailed` | `BENCHMARK_LIST_FAILED` | Couldn't list benchmarks. |
| `.benchmarkStartFailed` | `BENCHMARK_START_FAILED` | {{detail}} |
| `.benchmarkUnsupported` | `BENCHMARK_UNSUPPORTED` | Benchmarks aren't available on this computer. |
| `.billingUnavailable` | `BILLING_UNAVAILABLE` | Billing couldn't be reached. Try again in a minute. |
| `.browseFailed` | `BROWSE_FAILED` | {{detail}} |
| `.cacheNotFound` | `CACHE_NOT_FOUND` | No cache has that name. |
| `.capabilityOff` | `CAPABILITY_OFF` | This is turned off for your account. Ask {{admin}} or another Admin to turn it on. |
| `.capabilityUnknown` | `CAPABILITY_UNKNOWN` | Toskar doesn't know that capability. |
| `.chatFailed` | `CHAT_FAILED` | {{detail}} |
| `.claimFailed` | `CLAIM_FAILED` | {{detail}} |
| `.compactFailed` | `COMPACT_FAILED` | The chat couldn't be compacted: {{detail}} |
| `.computerOffline` | `COMPUTER_OFFLINE` | The computer running this model is offline. |
| `.confirmName` | `CONFIRM_NAME` | To remove {{name}}, type their name to confirm. |
| `.conflict` | `CONFLICT` | {{detail}} |
| `.connectionLost` | `CONNECTION_LOST` | The connection to the model was lost. |
| `.connectorFailed` | `CONNECTOR_FAILED` | {{detail}} |
| `.connectorNotFound` | `CONNECTOR_NOT_FOUND` | Toskar doesn't know that service. |
| `.connectorsFailed` | `CONNECTORS_FAILED` | {{detail}} |
| `.contextTooLong` | `CONTEXT_TOO_LONG` | This chat is too long for the model. |
| `.contractMismatch` | `CONTRACT_MISMATCH` | {{detail}} |
| `.conversationCreateFailed` | `CONVERSATION_CREATE_FAILED` | Couldn't start a new chat. |
| `.conversationDeleteFailed` | `CONVERSATION_DELETE_FAILED` | {{detail}} |
| `.conversationUpdateFailed` | `CONVERSATION_UPDATE_FAILED` | {{detail}} |
| `.conversationsListFailed` | `CONVERSATIONS_LIST_FAILED` | Couldn't list your chats. |
| `.createFailed` | `CREATE_FAILED` | {{detail}} |
| `.crossSite` | `CROSS_SITE` | That change didn't come from Toskar's own pages, so it was refused. |
| `.decideFailed` | `DECIDE_FAILED` | {{detail}} |
| `.deleteFailed` | `DELETE_FAILED` | {{detail}} |
| `.destinationNotFound` | `DESTINATION_NOT_FOUND` | That notification destination was removed. |
| `.deviceLimit` | `DEVICE_LIMIT` | You have {{limit}} connected devices, the most you can. Disconnect one first. |
| `.deviceNotAllowed` | `DEVICE_NOT_ALLOWED` | A device's key can't do this. Use a key from API Access. |
| `.deviceNotFound` | `DEVICE_NOT_FOUND` | No device of yours has that id. |
| `.devicesFailed` | `DEVICES_FAILED` | Couldn't read or change your devices. |
| `.diagnosticsFailed` | `DIAGNOSTICS_FAILED` | Couldn't create a diagnostics bundle. |
| `.egressFailed` | `EGRESS_FAILED` | {{detail}} |
| `.emailInvalid` | `EMAIL_INVALID` | That isn't an email address. |
| `.emailTaken` | `EMAIL_TAKEN` | Someone else has that email address. |
| `.emptyAnswer` | `EMPTY_ANSWER` | The model didn't write an answer. Try again, or choose another model. |
| `.examplesFull` | `EXAMPLES_FULL` | The profile has 20 example questions. Remove one to add this. |
| `.externalBadUrl` | `EXTERNAL_BAD_URL` | The base URL must start with http:// or https://, such as https://api.openai.com/v1. |
| `.externalFailed` | `EXTERNAL_FAILED` | {{detail}} |
| `.externalLocalOnly` | `EXTERNAL_LOCAL_ONLY` | This chat uses memories or knowledge marked This computer only, so it can't go to the external server. Choose a model on this computer. |
| `.externalOfflineProfile` | `EXTERNAL_OFFLINE_PROFILE` | This profile keeps work on this computer, so it doesn't use the external server. Choose a model on this computer or another profile. |
| `.fileNotFound` | `FILE_NOT_FOUND` | That file isn't here anymore. |
| `.fitFailed` | `FIT_FAILED` | {{detail}} |
| `.gpuSetupFailed` | `GPU_SETUP_FAILED` | Couldn't check this computer's GPU setup. |
| `.hardwareDetectFailed` | `HARDWARE_DETECT_FAILED` | Toskar couldn't fully detect this computer's hardware. Some details may be missing. |
| `.hardwareUnavailable` | `HARDWARE_UNAVAILABLE` | Hardware detection isn't available. |
| `.hookTooLarge` | `HOOK_TOO_LARGE` | The request body is larger than 64 KB. |
| `.hookTooSoon` | `HOOK_TOO_SOON` | This webhook was called a moment ago. Try again in a few seconds. |
| `.hostNotAllowed` | `HOST_NOT_ALLOWED` | This address is not one of this computer's. Open Toskar at http://127.0.0.1 or http://localhost, or send an API key. |
| `.huggingfaceTokenInvalid` | `HUGGINGFACE_TOKEN_INVALID` | That isn't a Hugging Face token. Copy a read token from huggingface.co/settings/tokens; it starts with hf_. |
| `.installFailed` | `INSTALL_FAILED` | {{detail}} |
| `.internalError` | `INTERNAL_ERROR` | {{detail}} |
| `.invalidBody` | `INVALID_BODY` | {{detail}} |
| `.invalidBranch` | `INVALID_BRANCH` | Send one of parent_id, retry_of, or edit_of, with the chat's conversation_id. |
| `.invalidConversationIds` | `INVALID_CONVERSATION_IDS` | Name 1 to {{max}} chats to delete. |
| `.invalidJson` | `INVALID_JSON` | {{detail}} |
| `.invalidLocale` | `INVALID_LOCALE` | That isn't a language Toskar recognizes. |
| `.invalidPersonalization` | `INVALID_PERSONALIZATION` | {{detail}} |
| `.invalidRating` | `INVALID_RATING` | A rating is 1 to 5 stars, with reasons from the list. |
| `.invalidRetention` | `INVALID_RETENTION` | {{detail}} |
| `.invalidSetting` | `INVALID_SETTING` | “{{value}}” isn't a valid value for {{setting}}. |
| `.inviteInvalid` | `INVITE_INVALID` | This link has expired or was already used. Ask for a new one. |
| `.joinBadRequest` | `JOIN_BAD_REQUEST` | {{detail}} |
| `.joinFailed` | `JOIN_FAILED` | {{detail}} |
| `.joinNotReachable` | `JOIN_NOT_REACHABLE` | Other computers can't reach this one. Turn on Find other computers, then restart Toskar. |
| `.joinOtherNetwork` | `JOIN_OTHER_NETWORK` | This computer is already in another Toskar network. Run toskarctl leave first to join this one. |
| `.joinRateLimited` | `JOIN_RATE_LIMITED` | Too many join attempts from this address. Wait a few minutes and try again. |
| `.joinTokenExpired` | `JOIN_TOKEN_EXPIRED` | This join token has expired. Make a new join command on a computer in the network. |
| `.joinTokenFailed` | `JOIN_TOKEN_FAILED` | {{detail}} |
| `.joinTokenInvalid` | `JOIN_TOKEN_INVALID` | This join token isn't valid. Make a new join command on a computer in the network. |
| `.joinTokenNotActive` | `JOIN_TOKEN_NOT_ACTIVE` | That join token can't be revoked: it was already used, revoked, or expired. |
| `.joinTokenNotFound` | `JOIN_TOKEN_NOT_FOUND` | No join token has that ID. |
| `.joinTokenRevoked` | `JOIN_TOKEN_REVOKED` | This join token was revoked. Make a new join command on a computer in the network. |
| `.joinTokenUsed` | `JOIN_TOKEN_USED` | This join token has already been used. Make a new join command for each computer. |
| `.joinUnreachable` | `JOIN_UNREACHABLE` | Couldn't reach Toskar at {{server}}. Check the address, the firewall, and that Toskar is running there. |
| `.joinWrongServer` | `JOIN_WRONG_SERVER` | The computer at that address isn't the one the join command was made on. Nothing that proves the token was sent. |
| `.keyChatOnly` | `KEY_CHAT_ONLY` | This key is for chat only, so it can't do this. Use another key from API Access. |
| `.keyNotFound` | `KEY_NOT_FOUND` | They have no key with that id. |
| `.keysFailed` | `KEYS_FAILED` | Their keys couldn't be read: {{detail}} |
| `.knowledgeSourceNotFound` | `KNOWLEDGE_SOURCE_NOT_FOUND` | That knowledge source was removed. |
| `.knowledgeSyncFailed` | `KNOWLEDGE_SYNC_FAILED` | {{detail}} |
| `.lanAccessFailed` | `LAN_ACCESS_FAILED` | Local network access couldn't be turned on. |
| `.lanAccessOff` | `LAN_ACCESS_OFF` | Local network access is off on this computer, so it only answers apps on it. |
| `.liveFiguresFailed` | `LIVE_FIGURES_FAILED` | Couldn't read this computer's CPU, memory, and GPU figures. |
| `.logNotFound` | `LOG_NOT_FOUND` | That log file couldn't be opened. |
| `.logsListFailed` | `LOGS_LIST_FAILED` | Couldn't list the log files. |
| `.markFailed` | `MARK_FAILED` | Couldn't mark that as on topic. |
| `.mcpFailed` | `MCP_FAILED` | {{detail}} |
| `.mcpNotFound` | `MCP_NOT_FOUND` | There's no tool source with that name. |
| `.memoryLooksSecret` | `MEMORY_LOOKS_SECRET` | That looks like a password, key, or token, so Toskar didn't save it. |
| `.memoryNotFound` | `MEMORY_NOT_FOUND` | That memory was removed. |
| `.messageNotFound` | `MESSAGE_NOT_FOUND` | That message isn't in this chat anymore. Reload the chat and try again. |
| `.messagesListFailed` | `MESSAGES_LIST_FAILED` | {{detail}} |
| `.methodNotAllowed` | `METHOD_NOT_ALLOWED` | The Toskar service doesn't take that request ({{route}}). Update the app and the service to the same version. |
| `.modelBusy` | `MODEL_BUSY` | {{detail}} |
| `.modelFileInvalid` | `MODEL_FILE_INVALID` | This isn't a model Toskar can use: {{detail}}. |
| `.modelFileNotFound` | `MODEL_FILE_NOT_FOUND` | There's no file at {{path}}. |
| `.modelFileNotProjector` | `MODEL_FILE_NOT_PROJECTOR` | This is a model, not a vision projector. |
| `.modelFileProjector` | `MODEL_FILE_PROJECTOR` | This is a vision projector, which helps a model see pictures. Add the model it belongs to. |
| `.modelImportFailed` | `MODEL_IMPORT_FAILED` | {{detail}} |
| `.modelNameInvalid` | `MODEL_NAME_INVALID` | Give the model a name of 1 to 120 characters. |
| `.modelNotEditable` | `MODEL_NOT_EDITABLE` | Only a model you added can be renamed or tagged. |
| `.modelNotFound` | `MODEL_NOT_FOUND` | No model has that ID. |
| `.modelNotInstalled` | `MODEL_NOT_INSTALLED` | {{model_id}} isn't installed. |
| `.modelUnhealthy` | `MODEL_UNHEALTHY` | The model stopped working. |
| `.modelUpdateFailed` | `MODEL_UPDATE_FAILED` | {{detail}} |
| `.modelsListFailed` | `MODELS_LIST_FAILED` | Couldn't list models. |
| `.nameInvalid` | `NAME_INVALID` | A name is 1 to 80 characters. |
| `.needsApproval` | `NEEDS_APPROVAL` | This needs your approval before the automation can go on. |
| `.newsUnavailable` | `NEWS_UNAVAILABLE` | The AI news couldn't be read from toskar.ai. Check the internet connection and try again. |
| `.noModelAssigned` | `NO_MODEL_ASSIGNED` | No model is chosen for this. Install one in Models, or choose one in the profile. |
| `.noModelInstalled` | `NO_MODEL_INSTALLED` | No model is installed yet. Install one in Models to start chatting. |
| `.noPassword` | `NO_PASSWORD` | You don't sign in with a password here. |
| `.noRecord` | `NO_RECORD` | No address record to find the computer away from home: it may be off or asleep, or have no access from anywhere. |
| `.noTextFound` | `NO_TEXT_FOUND` | No text found. Scanned PDFs need text recognition (OCR) before Toskar can read them. |
| `.nodesListFailed` | `NODES_LIST_FAILED` | Couldn't list computers. |
| `.notADevice` | `NOT_A_DEVICE` | Only a connected device can disconnect itself. |
| `.notConfirmed` | `NOT_CONFIRMED` | Pairing that the person stopped at the short pin. |
| `.notFound` | `NOT_FOUND` | {{detail}} |
| `.notImplemented` | `NOT_IMPLEMENTED` | {{detail}} |
| `.nothingToCompact` | `NOTHING_TO_COMPACT` | This chat is too short to compact. |
| `.notificationNotFound` | `NOTIFICATION_NOT_FOUND` | That notification was removed. |
| `.notificationsDisabled` | `NOTIFICATIONS_DISABLED` | Notifications are turned off. |
| `.notificationsFailed` | `NOTIFICATIONS_FAILED` | {{detail}} |
| `.offerFailed` | `OFFER_FAILED` | {{detail}} |
| `.originNotAllowed` | `ORIGIN_NOT_ALLOWED` | Websites cannot use Toskar without an API key. |
| `.outOfMemory` | `OUT_OF_MEMORY` | The model ran out of memory. |
| `.ownerFixed` | `OWNER_FIXED` | The Owner's role can't change, and nobody changes their own role or disables themselves. |
| `.pairFailed` | `PAIR_FAILED` | {{detail}} |
| `.pairingExpired` | `PAIRING_EXPIRED` | That code has expired. Choose Connect a device on the computer again. |
| `.pairingFailed` | `PAIRING_FAILED` | The device couldn't be connected. |
| `.pairingNotLocal` | `PAIRING_NOT_LOCAL` | A device can connect only from the computer's own network. |
| `.pairingNotStarted` | `PAIRING_NOT_STARTED` | That computer isn't showing a code. Choose Connect a device on it first. |
| `.pairingRateLimited` | `PAIRING_RATE_LIMITED` | Too many pairing attempts from this address. Wait a few minutes and start pairing again. |
| `.pairingThrottled` | `PAIRING_THROTTLED` | Too many tries. Wait a few minutes, then try again. |
| `.pairingWrongCode` | `PAIRING_WRONG_CODE` | That isn't the code the computer shows. Check it and try again. |
| `.passwordChangeRequired` | `PASSWORD_CHANGE_REQUIRED` | Change the password you were given first. |
| `.passwordSame` | `PASSWORD_SAME` | Choose a password other than your current one. |
| `.passwordTooShort` | `PASSWORD_TOO_SHORT` | A password needs at least 10 characters. |
| `.passwordWrong` | `PASSWORD_WRONG` | That isn't your current password. |
| `.peerFailed` | `PEER_FAILED` | {{detail}} |
| `.peerTooOld` | `PEER_TOO_OLD` | That computer needs a newer Toskar to run tools for others. |
| `.peerUnauthorized` | `PEER_UNAUTHORIZED` | That computer didn't accept this one's sign-in ({{detail}}). If it keeps happening, pair the two computers again in Computers. |
| `.peerUnavailable` | `PEER_UNAVAILABLE` | That computer doesn't offer this right now. It may still be starting, or need a newer Toskar. |
| `.performanceListFailed` | `PERFORMANCE_LIST_FAILED` | Couldn't list performance measurements. |
| `.permissionsFailed` | `PERMISSIONS_FAILED` | {{detail}} |
| `.personNotFound` | `PERSON_NOT_FOUND` | That person isn't here. |
| `.personalizationFailed` | `PERSONALIZATION_FAILED` | {{detail}} |
| `.pinInvalid` | `PIN_INVALID` | That pin can't be saved. Only Members and Visitors are pinned, and only to profiles that exist. |
| `.pinMismatch` | `PIN_MISMATCH` | The computer's certificate isn't the one paired with: stop, and pair again to trust a new certificate. |
| `.pinsFailed` | `PINS_FAILED` | Couldn't read which profiles people are pinned to. |
| `.portalBusy` | `PORTAL_BUSY` | This chat is busy. Try again in a moment. |
| `.portalInvalid` | `PORTAL_INVALID` | That portal setting can't be used. |
| `.portalInvite` | `PORTAL_INVITE` | This chat is by invitation. Open the link you were sent, or ask for a new one. |
| `.portalMembers` | `PORTAL_MEMBERS` | This chat is for the people who sign in to this Toskar. |
| `.portalNotFound` | `PORTAL_NOT_FOUND` | There's no portal at this address, or it's turned off. |
| `.portalOff` | `PORTAL_OFF` | This portal is turned off. |
| `.portalOnly` | `PORTAL_ONLY` | A portal's visitor can only chat in the portal. |
| `.portalPasscode` | `PORTAL_PASSCODE` | That passcode isn't right. |
| `.portalRate` | `PORTAL_RATE` | You've sent a lot of messages. Try again later. |
| `.portalSlugTaken` | `PORTAL_SLUG_TAKEN` | Another portal has that address. |
| `.portalTooLong` | `PORTAL_TOO_LONG` | A message here can be {{max}} characters at most. |
| `.preferenceCannotGrantTools` | `PREFERENCE_CANNOT_GRANT_TOOLS` | Preferences and memories can't give permission to use tools. Change what tools may do in Settings → Tool permissions or in a profile. |
| `.privacyFailed` | `PRIVACY_FAILED` | {{detail}} |
| `.profileCreateFailed` | `PROFILE_CREATE_FAILED` | {{detail}} |
| `.profileNotFound` | `PROFILE_NOT_FOUND` | There's no such profile. |
| `.profilePinned` | `PROFILE_PINNED` | This key answers only with its own profile. Leave out the profile and model, or name that profile. |
| `.profileUpdateFailed` | `PROFILE_UPDATE_FAILED` | {{detail}} |
| `.profilesListFailed` | `PROFILES_LIST_FAILED` | Couldn't list profiles. |
| `.proxyRefused` | `PROXY_REFUSED` | Your sign-in doesn't give you a role on this Toskar. Ask its Owner to add you to a group that does. |
| `.pushDeviceOnly` | `PUSH_DEVICE_ONLY` | Only a paired phone or tablet can turn on notifications. |
| `.pushFailed` | `PUSH_FAILED` | {{detail}} |
| `.pushInvalid` | `PUSH_INVALID` | {{detail}} |
| `.pushUnavailable` | `PUSH_UNAVAILABLE` | Notifications in the Toskar app aren't available on this computer. |
| `.ratingFailed` | `RATING_FAILED` | {{detail}} |
| `.ratingNotShareable` | `RATING_NOT_SHAREABLE` | This model can't be compared with others' ratings, so its rating stays on this computer. |
| `.ratingsUnreachable` | `RATINGS_UNREACHABLE` | Your rating is saved on this computer, but the ratings service couldn't be reached. Try again later. |
| `.recommendFailed` | `RECOMMEND_FAILED` | {{detail}} |
| `.recordPin` | `RECORD_PIN` | An address record that isn't from the pinned computer, or is for another route. |
| `.recordSealed` | `RECORD_SEALED` | An address record that doesn't open with the route secret. |
| `.recordStale` | `RECORD_STALE` | An address record too old, or from too far in the future. |
| `.refreshFailed` | `REFRESH_FAILED` | {{detail}} |
| `.relayInvalid` | `RELAY_INVALID` | Enter the relay's name, such as relay.example.com, with a port only when it isn't 443. |
| `.relaySecretInvalid` | `RELAY_SECRET_INVALID` | That isn't an enrollment secret. Copy it from the relay's enroll.secret file. |
| `.relaySoldOut` | `RELAY_SOLD_OUT` | Toskar's relay isn't taking new subscriptions right now. Try again in a few days. |
| `.relayTokenFailed` | `RELAY_TOKEN_FAILED` | Couldn't save the relay token on this computer. |
| `.relayTokenInvalid` | `RELAY_TOKEN_INVALID` | That relay token isn't for this computer, or it has run out. Subscribe again from this device. |
| `.relayTokenNotNeeded` | `RELAY_TOKEN_NOT_NEEDED` | This computer uses your organization's relay, so it doesn't need a subscription. |
| `.remoteAccessOff` | `REMOTE_ACCESS_OFF` | Access from anywhere is off, so there's nothing to check. Turn it on first. |
| `.remoteAddressInvalid` | `REMOTE_ADDRESS_INVALID` | Enter a host name or IP, with a port when it differs, such as home.example.com or 203.0.113.7:7333. |
| `.remoteDevicesOnly` | `REMOTE_DEVICES_ONLY` | From outside the home network, only paired devices can connect. |
| `.remoteListenFailed` | `REMOTE_LISTEN_FAILED` | Access from anywhere can't listen on port {{port}}. Another program may be using it. |
| `.remotePortInvalid` | `REMOTE_PORT_INVALID` | The port is 1024 to 65535, and not the one the app or the computers use. |
| `.remoteThrottled` | `REMOTE_THROTTLED` | Too many wrong keys came from this address. Try again later. |
| `.remoteTrainingFailed` | `REMOTE_TRAINING_FAILED` | {{detail}} |
| `.replyInterrupted` | `REPLY_INTERRUPTED` | The reply stopped before it finished because the connection to the Toskar service was lost. Try again. |
| `.reportInvalid` | `REPORT_INVALID` | That report can't be sent: it needs the error, and any email address has to be complete. |
| `.reportRateLimited` | `REPORT_RATE_LIMITED` | Too many reports were sent from here. Try again later, or send it by email. |
| `.reportsOff` | `REPORTS_OFF` | An Admin turned off sending problem reports to Toskar. Copy the report and give it to whoever runs Toskar here. |
| `.reportsUnavailable` | `REPORTS_UNAVAILABLE` | The report couldn't be sent to Toskar right now. Send it by email instead. |
| `.requestBadTime` | `REQUEST_BAD_TIME` | That time is not valid. |
| `.requestEmpty` | `REQUEST_EMPTY` | Describe the automation. |
| `.requestNoSchedule` | `REQUEST_NO_SCHEDULE` | Describe when it should run, for example “every morning at 8:00 AM”. |
| `.requestTimeZone` | `REQUEST_TIME_ZONE` | A time zone is required. |
| `.resetFailed` | `RESET_FAILED` | {{detail}} |
| `.resetUnsupported` | `RESET_UNSUPPORTED` | Resetting isn't available here. |
| `.revokeFailed` | `REVOKE_FAILED` | {{detail}} |
| `.roleInvalid` | `ROLE_INVALID` | That isn't a role. |
| `.roleRequired` | `ROLE_REQUIRED` | This needs the {{role}} role. |
| `.rotateFailed` | `ROTATE_FAILED` | {{detail}} |
| `.routeFailed` | `ROUTE_FAILED` | Couldn't set up access from anywhere on this computer. |
| `.routeNotFound` | `ROUTE_NOT_FOUND` | This version of the Toskar service doesn't know that request ({{route}}). Update the app and the service to the same version. |
| `.routeNotLocal` | `ROUTE_NOT_LOCAL` | Connect at home once to set up access from anywhere on this device. |
| `.runNotFound` | `RUN_NOT_FOUND` | That run isn't recorded, or its record was removed. |
| `.runningListFailed` | `RUNNING_LIST_FAILED` | {{detail}} |
| `.runsFailed` | `RUNS_FAILED` | {{detail}} |
| `.runtimeError` | `RUNTIME_ERROR` | The model's engine ran into an error. |
| `.runtimeNotInstalled` | `RUNTIME_NOT_INSTALLED` | {{runtime}} isn't set up yet. Choose Start on a model in Models, and Toskar sets it up. |
| `.runtimeSetupFailed` | `RUNTIME_SETUP_FAILED` | {{runtime}} couldn't be set up, so the model can't start ({{reason}}). Check this computer's internet connection, then choose Start again. |
| `.runtimesListFailed` | `RUNTIMES_LIST_FAILED` | {{detail}} |
| `.sandboxed` | `SANDBOXED` | This copy of Toskar runs in the macOS App Sandbox, which can't run a Python environment it downloads. |
| `.serviceUnreachable` | `SERVICE_UNREACHABLE` | Couldn't reach the local Toskar service ({{detail}}). If this is the desktop app, quit and reopen it so the service restarts. |
| `.settingsReadFailed` | `SETTINGS_READ_FAILED` | Couldn't read settings. |
| `.settingsUpdateFailed` | `SETTINGS_UPDATE_FAILED` | Couldn't update settings. |
| `.setupRefused` | `SETUP_REFUSED` | {{detail}} |
| `.shellOnly` | `SHELL_ONLY` | Only the Toskar Pro app on this computer can change this. |
| `.signInFailed` | `SIGN_IN_FAILED` | That username and password don't match. |
| `.signInThrottled` | `SIGN_IN_THROTTLED` | Too many tries. Wait 15 minutes and try again. |
| `.speechFailed` | `SPEECH_FAILED` | {{detail}} |
| `.speechNoVoice` | `SPEECH_NO_VOICE` | There is no voice to read {{language}} aloud yet. |
| `.speechSetupFailed` | `SPEECH_SETUP_FAILED` | Speech (reading aloud and turning speech into text) couldn't be set up on this computer. Diagnostics shows what's missing. |
| `.speechUnavailable` | `SPEECH_UNAVAILABLE` | {{detail}} |
| `.sseUnsupported` | `SSE_UNSUPPORTED` | Streaming isn't supported here. |
| `.startFailed` | `START_FAILED` | {{detail}} |
| `.stopFailed` | `STOP_FAILED` | {{detail}} |
| `.subscriptionActive` | `SUBSCRIPTION_ACTIVE` | This computer already has access from anywhere. |
| `.subscriptionFailed` | `SUBSCRIPTION_FAILED` | Couldn't start the subscription. |
| `.subscriptionInAppOnly` | `SUBSCRIPTION_IN_APP_ONLY` | This copy of Toskar is from the App Store, so access from anywhere is sold in the Toskar app on your phone or tablet. |
| `.subscriptionNone` | `SUBSCRIPTION_NONE` | This computer has no subscription bought in its settings. One bought in the Toskar app is managed in your phone's or tablet's store. |
| `.subscriptionOwnRelay` | `SUBSCRIPTION_OWN_RELAY` | This computer uses your organization's relay, so it doesn't need a subscription to Toskar's. |
| `.subscriptionPlanInvalid` | `SUBSCRIPTION_PLAN_INVALID` | Choose monthly or yearly. |
| `.summaryEmpty` | `SUMMARY_EMPTY` | A summary can't be empty. |
| `.summaryFailed` | `SUMMARY_FAILED` | The summary couldn't be read or saved: {{detail}} |
| `.summaryNotFound` | `SUMMARY_NOT_FOUND` | This chat hasn't been compacted yet. |
| `.supportModelBusy` | `SUPPORT_MODEL_BUSY` | The supporting model can't run right now. |
| `.taskCreateFailed` | `TASK_CREATE_FAILED` | {{detail}} |
| `.taskFailed` | `TASK_FAILED` | {{detail}} |
| `.taskInterrupted` | `TASK_INTERRUPTED` | Toskar stopped before this finished. |
| `.tasksListFailed` | `TASKS_LIST_FAILED` | {{detail}} |
| `.toolSourceEntryNotFound` | `TOOL_SOURCE_ENTRY_NOT_FOUND` | That gallery entry or app setting wasn't found. |
| `.toolTestFailed` | `TOOL_TEST_FAILED` | {{detail}} |
| `.toolUpdateFailed` | `TOOL_UPDATE_FAILED` | {{detail}} |
| `.toolsFailed` | `TOOLS_FAILED` | {{detail}} |
| `.trainingCancelled` | `TRAINING_CANCELLED` | Training was cancelled. |
| `.transferInvalid` | `TRANSFER_INVALID` | There's no active person to give their data to. |
| `.trialFailed` | `TRIAL_FAILED` | Couldn't try that message. Check the topic controls and that a model is ready. |
| `.trialNotStarted` | `TRIAL_NOT_STARTED` | Start Toskar Pro's free 14-day trial to add models, automations, or people. |
| `.unauthorized` | `UNAUTHORIZED` | This Toskar needs an API key. |
| `.unlockRequired` | `UNLOCK_REQUIRED` | Your Toskar Pro trial has ended. Unlock Toskar Pro to add models, automations, or people. |
| `.unreachable` | `UNREACHABLE` | No way in answered, at home or away. |
| `.unreadableFile` | `UNREADABLE_FILE` | Toskar can't read {{name}}: {{cause}} |
| `.unsupportedFile` | `UNSUPPORTED_FILE` | Toskar can't read {{name}} yet. Attach a document, spreadsheet, PDF, code file, audio, video, or a PNG or JPEG image. |
| `.usernameInvalid` | `USERNAME_INVALID` | A username is 3 to 32 letters, digits, dots, dashes, or underscores. |
| `.usernameTaken` | `USERNAME_TAKEN` | That username is taken. |
| `.warmFailed` | `WARM_FAILED` | {{detail}} |
