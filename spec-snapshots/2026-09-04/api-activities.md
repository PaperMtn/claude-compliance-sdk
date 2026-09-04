# Query compliance activities

**GET** `/v1/compliance/activities`

List compliance activities for the authenticated tenant.

The tenant is the caller's parent organization, or — for an organization
with no parent — the organization itself. Returns a paginated list of
compliance activities that can be filtered by various criteria.

## Query parameters

- `activity_types: optional array of "abuse_decision_received" or "account_deleted" or "admin_api_key_created" or 480 more`

  Filter activities by type. See the response `data` schema for the additional fields each type returns. Cannot be combined with `exclude_activity_types[]`.

  - `"abuse_decision_received"`

    An external anti-abuse service reported a consequential decision about a sign-in or sign-up attempt.

  - `"account_deleted"`

    User-initiated self-service account deletion.

  - `"admin_api_key_created"`

    An admin API key was created.

  - `"admin_api_key_deleted"`

    An admin API key was deleted.

  - `"admin_api_key_updated"`

    An admin API key was updated (renamed or activated/deactivated).

  - `"admin_connector_request_resolved"`

    Admin approved or dismissed pending member requests to enable an MCP connector.

  - `"admin_request_created"`

    Admin request created by an org member (seat upgrade, limit increase, join org, end-user invite).

  - `"age_verified"`

    User age was verified.

  - `"anonymous_mobile_login_attempted"`

    Anonymous mobile login was attempted.

  - `"api_key_created"`

    Activity logged when a new API key is created.

  - `"audit_log_export_accessed"`

    Audit log export file was accessed/downloaded via signed URL.

  - `"audit_log_export_started"`

    Audit log export was initiated.

  - `"billing_emails_updated"`

    The organization's billing email recipients were updated.

  - `"ccr_agent_created"`

    A Claude Code agent was created.

  - `"ccr_agent_deleted"`

    A Claude Code agent was deleted.

  - `"ccr_agent_proxy_credential_created"`

    A Claude Code agent proxy credential was created. Credentials hold the secrets the agent proxy injects into requests Claude Code sessions send to approved external services; each credential belongs to an agent proxy profile. Audit events carry only credential names and settings, never the secret material itself.

  - `"ccr_agent_proxy_credential_deleted"`

    A Claude Code agent proxy credential was deleted. Its secret material was removed and can no longer be sent to any host.

  - `"ccr_agent_proxy_credential_rotated"`

    A Claude Code agent proxy credential's secret material was replaced. The replacement keeps the same name, profile, and allowed hosts under a new credential identifier, and everything that referenced the old credential now uses the replacement.

  - `"ccr_agent_proxy_credential_updated"`

    A Claude Code agent proxy credential's settings were updated. Only the display name and the allowed host patterns can be updated; the secret material can only be replaced through a rotation.

  - `"ccr_agent_proxy_destination_deleted"`

    An agent proxy destination was deleted.

  - `"ccr_agent_proxy_network_events_listed"`

    A Claude Code network activity export was accessed for the given hour.

  - `"ccr_agent_proxy_profile_bound"`

    A Claude Code agent proxy profile was bound to a scope, applying its policy to Claude Code sessions in that scope.

  - `"ccr_agent_proxy_profile_created"`

    A Claude Code agent proxy profile was created. Agent proxy profiles are named, reusable bundles of access policy that administrators bind to parts of the organization.

  - `"ccr_agent_proxy_profile_deleted"`

    A Claude Code agent proxy profile was deleted, removing its policy from everything it was bound to.

  - `"ccr_agent_proxy_profile_unbound"`

    A Claude Code agent proxy profile was unbound from a scope, removing its policy from Claude Code sessions in that scope.

  - `"ccr_agent_proxy_profile_updated"`

    A Claude Code agent proxy profile's configuration was updated.

  - `"ccr_agent_proxy_provisioning_credential_rejected"`

    An organization owner rejected a credential that a teammate submitted via an agent proxy provisioning link: the credential and its disabled rule were deleted and the link was revoked. The actor is the owner; the submitter is recorded for attribution.

  - `"ccr_agent_proxy_provisioning_link_enabled"`

    An organization owner enabled a credential that a teammate submitted via an agent proxy provisioning link: the disabled rule created at submission was switched to enforce, so the credential now takes traffic. The actor is the owner; the submitter is the actor on the prior ccr_agent_proxy_provisioning_link_submitted event.

  - `"ccr_agent_proxy_provisioning_link_generated"`

    An organization owner generated a one-time agent proxy credential provisioning link so a teammate can submit a credential into the target agent proxy profile without holding the owner role.

  - `"ccr_agent_proxy_provisioning_link_revoked"`

    An organization owner revoked an unfilled agent proxy provisioning link.

  - `"ccr_agent_proxy_provisioning_link_submitted"`

    A teammate submitted a credential via an agent proxy provisioning link. The credential and a disabled rule are created; the credential takes traffic only after an organization owner enables the submitted credential. This event records the link-mediated lifecycle; the credential itself additionally emits ccr_agent_proxy_credential_created.

  - `"ccr_agent_proxy_rule_deleted"`

    An agent proxy rule was deleted.

  - `"ccr_agent_slack_access_scope_created"`

    A Claude Code agent was granted access to read or write in an additional Slack channel beyond the one it is assigned to.

  - `"ccr_agent_slack_access_scope_deleted"`

    A Claude Code agent's access to an additional Slack channel was revoked.

  - `"ccr_agent_slack_binding_created"`

    A Claude Code agent was assigned to a Slack channel or workspace as its dedicated agent.

  - `"ccr_agent_slack_binding_deleted"`

    A Claude Code agent's assignment to a Slack channel or workspace was removed.

  - `"ccr_agent_updated"`

    A Claude Code agent's configuration was updated. Also emitted with updated_fields ["is_virtual"] alone when an auto-provisioned agent is promoted to a configured one, whether by an update request targeting it or by binding an agent proxy profile to it.

  - `"ccr_role_channel_assignment_deleted"`

    CcrRoleChannelAssignmentDeleted is emitted when an org owner/admin removes an RBAC role's channel assignment row (the role reverts to granting zero channels).

  - `"ccr_role_channel_assignment_updated"`

    CcrRoleChannelAssignmentUpdated is emitted when an org owner/admin sets or replaces the list of Slack channels an RBAC role's holders may configure via the delegated Claude-in-Slack channel-manage surface.

  - `"ccr_session_created"`

    A Claude Code session was created. A session is one coding interaction with Claude.

  - `"ccr_session_deleted"`

    A Claude Code session was deleted.

  - `"ccr_session_updated"`

    A Claude Code session's settings were updated.

  - `"claude_artifact_access_failed"`

    An attempt to access an artifact failed.

  - `"claude_artifact_commented"`

    Comment activity on a published artifact: a comment was added, a thread's resolved state was changed, or a thread was deleted. The actor is the user who performed the action; the comment text itself is stored with the artifact and is not part of this record.

  - `"claude_artifact_comments_viewed"`

    An artifact's comments were viewed.

  - `"claude_artifact_created"`

    An artifact was created.

  - `"claude_artifact_duplicated"`

    A user duplicated an artifact they could view into a new artifact that they own. The actor is the user who created the copy; the source artifact is not modified.

  - `"claude_artifact_published"`

    A new version of an artifact was published — for an artifact created in a chat this is the action that made it publicly viewable; for an artifact created outside a chat it is recorded on every save, including saves of private artifacts, and changes to who can access the artifact are recorded separately as claude_artifact_sharing_updated.

  - `"claude_artifact_sharing_updated"`

    An artifact's sharing settings were updated.

  - `"claude_artifact_viewed"`

    An artifact was viewed.

  - `"claude_chat_access_failed"`

    A user was denied access to a Claude.ai chat conversation.

  - `"claude_chat_created"`

    User created a chat.

  - `"claude_chat_deleted"`

    A user deleted a Claude.ai chat conversation.

  - `"claude_chat_deletion_failed"`

    A request to delete a Claude.ai chat conversation failed.

  - `"claude_chat_settings_updated"`

    User updated the settings for a conversation.

  - `"claude_chat_snapshot_created"`

    User created/shared a chat snapshot.

  - `"claude_chat_snapshot_deleted"`

    User deleted/unshared a chat snapshot.

  - `"claude_chat_snapshot_viewed"`

    User viewed a chat snapshot (authenticated or public/unauthenticated).

  - `"claude_chat_sync_source_created"`

    A sync source was connected for syncing external content into Claude chats.

  - `"claude_chat_sync_source_deleted"`

    A sync source was disconnected from Claude chats.

  - `"claude_chat_sync_source_updated"`

    A Claude chat sync source's configuration was updated.

  - `"claude_chat_updated"`

    User updated the chat metadata (e.g name, model).

  - `"claude_chat_viewed"`

    A user viewed a Claude.ai chat conversation.

  - `"claude_code_credential_revoked"`

    A Claude Code credential (runner pool key, runner token, or session token) was revoked. The credential itself is never recorded.

  - `"claude_code_review_config_updated"`

    Claude Code Review configuration was enabled/disabled for an org.

  - `"claude_code_review_repository_added"`

    A repository was added to org-level Claude Code Review configuration.

  - `"claude_code_review_repository_removed"`

    A repository was removed from org-level Claude Code Review configuration.

  - `"claude_code_review_repository_updated"`

    A Claude Code Review repository configuration was updated.

  - `"claude_code_runner_deleted"`

    A self-hosted runner was forcibly removed from its pool. Sessions assigned to the runner were returned to the pool queue, unless a session had already been requeued repeatedly, in which case it was marked stuck instead of being requeued again.

  - `"claude_code_runner_pool_created"`

    A self-hosted runner pool for Claude Code was created.

  - `"claude_code_runner_pool_deleted"`

    A self-hosted runner pool was deleted.

  - `"claude_code_runner_pool_secret_minted"`

    A registration key for a self-hosted runner pool was minted. Runners present this key to join the pool. The key itself is never recorded.

  - `"claude_code_runner_pool_session_queue_updated"`

    An admin changed a session's position in its self-hosted runner pool's queue: requeued it onto a different runner, dismissed it from the queue, or re-admitted it for another runner provisioning attempt.

  - `"claude_code_runner_pool_updated"`

    A self-hosted runner pool's settings were updated.

  - `"claude_code_security_center_config_updated"`

    Claude Code Security Center scanning was enabled/disabled for an org.

  - `"claude_code_security_scan_cancelled"`

    In-flight Claude Code Security scans were cancelled for a project.

  - `"claude_code_security_scan_created"`

    A Claude Code Security scan was started.

  - `"claude_code_security_scan_project_member_updated"`

    A person's access to a Claude Code Security scan project was granted, changed, or revoked.

  - `"claude_code_security_scan_project_updated"`

    A Claude Code Security scan project was archived, unarchived, created, or migrated to a new product experience.

  - `"claude_code_security_scan_project_visibility_updated"`

    A Claude Code Security scan project was shared with the organization or made private.

  - `"claude_code_security_scan_run_updated"`

    A single Claude Code Security scan run was archived, unarchived, or resumed after a billing pause.

  - `"claude_code_security_scan_schedule_deleted"`

    A recurring scan schedule was deleted for a Claude Code Security project.

  - `"claude_code_security_scan_schedule_updated"`

    A recurring scan schedule was set or replaced for a Claude Code Security project.

  - `"claude_code_security_vulnerability_fix_session_created"`

    A Claude Code remediation session was created for a Claude Code Security vulnerability finding.

  - `"claude_code_security_vulnerability_updated"`

    A Claude Code Security vulnerability finding was dismissed, restored, marked fixed, or reopened.

  - `"claude_code_security_webhook_created"`

    A Claude Code Security outbound webhook was created.

  - `"claude_code_security_webhook_deleted"`

    A Claude Code Security outbound webhook was deleted.

  - `"claude_code_security_webhook_secret_updated"`

    The HMAC signing secret for a Claude Code Security webhook was rotated.

  - `"claude_code_security_webhook_updated"`

    A Claude Code Security outbound webhook was updated.

  - `"claude_code_team_memory_acl_updated"`

    An RBAC group was added to or removed from the Claude Code team-memory ACL.

  - `"claude_code_team_memory_updated"`

    Claude Code team memory shared with the organization was updated.

  - `"claude_code_team_onboarding_guide_updated"`

    A Claude Code team onboarding guide was created, updated, or deleted.

  - `"claude_code_user_marketplaces_updated"`

    A user's Claude Code plugin marketplace selections were updated on Anthropic servers.

  - `"claude_code_user_memory_updated"`

    A user's synced private Claude Code memory was updated or deleted on Anthropic servers.

  - `"claude_code_user_plugins_updated"`

    A user's Claude Code plugin selections — which plugins are installed and enabled — were updated on Anthropic servers.

  - `"claude_code_user_settings_updated"`

    A user's synced Claude Code settings were updated or deleted on Anthropic servers.

  - `"claude_command_created"`

    Command was created.

  - `"claude_command_deleted"`

    Command was deleted.

  - `"claude_command_replaced"`

    Command was replaced.

  - `"claude_enterprise_upgrade_credit_updated"`

    An organization admin cancelled, or turned back on, the monthly usage credit the organization receives for upgrading from the Team plan to the Enterprise plan, together with the recurring monthly charge that accompanies it.

  - `"claude_file_access_failed"`

    A user was denied access to a file in Claude.ai.

  - `"claude_file_deleted"`

    A file was deleted.

  - `"claude_file_exported"`

    A file was exported from Claude to an external storage destination.

  - `"claude_file_uploaded"`

    A file was uploaded.

  - `"claude_file_viewed"`

    A user viewed a file in Claude.ai.

  - `"claude_gdrive_integration_created"`

    A Google Drive integration was enabled for the organization.

  - `"claude_gdrive_integration_deleted"`

    A Google Drive integration was disabled for the organization.

  - `"claude_gdrive_integration_updated"`

    A Google Drive integration's configuration was updated.

  - `"claude_github_integration_created"`

    A GitHub integration was enabled for the organization.

  - `"claude_github_integration_deleted"`

    A GitHub integration was disabled for the organization.

  - `"claude_github_integration_updated"`

    A GitHub integration's configuration was updated.

  - `"claude_organization_settings_updated"`

    Organization settings were updated.

  - `"claude_plugin_created"`

    Plugin was created.

  - `"claude_plugin_deleted"`

    Plugin was deleted.

  - `"claude_plugin_disabled"`

    User disabled a plugin for their account.

  - `"claude_plugin_enabled"`

    User enabled a plugin for their account.

  - `"claude_plugin_replaced"`

    Plugin was replaced.

  - `"claude_plugin_updated"`

    Plugin was updated.

  - `"claude_project_archived"`

    A Claude project was archived.

  - `"claude_project_created"`

    A Claude project was created.

  - `"claude_project_deleted"`

    A Claude project was deleted.

  - `"claude_project_document_access_failed"`

    An attempt to access a document in a Claude project failed.

  - `"claude_project_document_bulk_deletion_audit_truncated"`

    A bulk request to delete documents from a Claude project failed with more documents requested than were individually recorded in the audit log.

  - `"claude_project_document_deleted"`

    A document was deleted from a Claude project.

  - `"claude_project_document_deletion_failed"`

    A request to delete a document from a Claude project failed.

  - `"claude_project_document_updated"`

    The content of a document in a Claude project was replaced in place.

  - `"claude_project_document_uploaded"`

    A document was uploaded to a Claude project.

  - `"claude_project_document_viewed"`

    A document in a Claude project was viewed.

  - `"claude_project_file_access_failed"`

    An attempt to access a file in a Claude project failed.

  - `"claude_project_file_bulk_deletion_audit_truncated"`

    A bulk request to delete files from a Claude project failed with more files requested than were individually recorded in the audit log.

  - `"claude_project_file_deleted"`

    A file was deleted from a Claude project.

  - `"claude_project_file_deletion_failed"`

    A request to delete a file from a Claude project failed.

  - `"claude_project_file_uploaded"`

    A file was uploaded to a Claude project.

  - `"claude_project_reported"`

    A Claude project was reported.

  - `"claude_project_sharing_updated"`

    A Claude project's sharing settings were updated.

  - `"claude_project_sync_source_created"`

    A sync source was connected to a Claude project's knowledge base.

  - `"claude_project_sync_source_deleted"`

    A sync source was disconnected from a Claude project's knowledge base.

  - `"claude_project_sync_source_updated"`

    A Claude project sync source's configuration was updated.

  - `"claude_project_viewed"`

    A Claude project was viewed.

  - `"claude_published_artifact_deleted"`

    A published artifact was deleted or unpublished — by its creator, by an organization admin, or by Anthropic (for example, when it was removed for a policy violation).

  - `"claude_pubsec_identity_configured"`

    SAML IdP configuration updated for a public sector organization.

  - `"claude_skill_created"`

    Skill was created.

  - `"claude_skill_deleted"`

    Skill was deleted.

  - `"claude_skill_disabled"`

    User disabled a skill for their account.

  - `"claude_skill_enabled"`

    User enabled a skill for their account.

  - `"claude_skill_replaced"`

    Skill was replaced.

  - `"claude_user_role_updated"`

    A user's role within the organization was changed, or the user was added to or removed from the organization.

  - `"claude_user_seat_tier_updated"`

    An organization member's seat tier was changed. A null `previous_seat_tier` means the member previously had no seat assigned; a null `current_seat_tier` means the seat was removed.

  - `"claude_user_settings_updated"`

    User updated their personal settings.

  - `"cli_plugin_exec_policy_updated"`

    Admin set or cleared the per-op permission ceiling for a plugin CLI.

  - `"compliance_api_accessed"`

    Logging event auto-generated for each compliance API request.

  - `"cowork_session_updated"`

    A Cowork session was updated.

  - `"design_project_artifact_published"`

    A Claude Design project's content was published as a claude.ai artifact, making a snapshot of one of its files viewable outside the project's sharing settings.

  - `"design_project_created"`

    A Claude Design project was created.

  - `"design_project_deleted"`

    A Claude Design project was deleted.

  - `"design_project_member_added"`

    A member was granted access to a Claude Design project.

  - `"design_project_member_removed"`

    A member's access to a Claude Design project was revoked.

  - `"design_project_member_role_updated"`

    A Claude Design project member's role was changed.

  - `"design_project_published"`

    A Claude Design template or design system was published, making it discoverable by everyone in its organization.

  - `"design_project_sharing_updated"`

    A Claude Design project's link-sharing settings were changed — who the project's link works for, and what people opening it through the link may do. Access granted to individual members is reported separately (see design_project_member_added).

  - `"design_project_unpublished"`

    A Claude Design template or design system was unpublished, removing it from its organization's shared gallery.

  - `"design_project_updated"`

    A Claude Design project's metadata was updated.

  - `"design_project_version_restored"`

    A Claude Design project's working tree was rolled back to a previously saved version, replacing its current files with that version's files.

  - `"design_project_viewed"`

    A Claude Design project's content was read. The surface field records which kind of read — a project open, a full-content read, a single-file read, a saved-version read, or an export request. The actor is the reader.

    This activity type is retired: project content reads are no longer
    recorded. Events of this type may still appear in feeds for reads that
    occurred while it was active.

  - `"desktop_extension_allowlisted"`

    A desktop extension was added to an org's allowlist.

  - `"desktop_extension_blocklisted"`

    A desktop extension was added to the global blocklist.

  - `"desktop_extension_deleted"`

    A desktop extension was deleted, either globally by an admin or org-scoped by an org owner.

  - `"desktop_extension_removed_from_allowlist"`

    A desktop extension was removed from an org's allowlist.

  - `"desktop_extension_unblocked"`

    A desktop extension was removed from the global blocklist.

  - `"desktop_extension_uploaded"`

    A desktop extension was uploaded, either globally by an admin or org-scoped by an org owner.

  - `"desktop_extension_version_uploaded"`

    A new version of an existing org-owned desktop extension was uploaded.

  - `"domain_claim_initiated"`

    Domain capture claim initiated over personal accounts on verified domains.

  - `"end_user_invite_requested"`

    Non-admin member submitted an invite request for a new org member.

  - `"extra_usage_billing_enabled"`

    Usage credit billing was enabled for an organization.

  - `"extra_usage_credit_granted"`

    A promotional usage credit grant was claimed.

  - `"extra_usage_spend_limit_created"`

    Usage credit spend limit was created.

  - `"extra_usage_spend_limit_deleted"`

    Usage credit spend limit was deleted.

  - `"extra_usage_spend_limit_increase_request_approved"`

    A usage credit spend limit increase request was approved.

  - `"extra_usage_spend_limit_increase_request_denied"`

    A usage credit spend limit increase request was denied.

  - `"extra_usage_spend_limit_updated"`

    Usage credit spend limit was updated.

  - `"ghe_configuration_created"`

    Admin created a GHE configuration.

  - `"ghe_configuration_deleted"`

    Admin deleted a GHE configuration.

  - `"ghe_configuration_updated"`

    Admin updated a GHE configuration. Previous/new field pairs are recorded only for settings that changed in the update; secret credentials are never recorded, only whether they were replaced.

  - `"ghe_user_connected"`

    User connected to a GHE instance.

  - `"ghe_user_disconnected"`

    User disconnected from a GHE instance.

  - `"ghe_webhook_signature_invalid"`

    Webhook signature validation failed.

  - `"github_token_import"`

    A user attempted to import a personal GitHub access token for use with Claude Code. The `result` field indicates the outcome of the import (imported, rejected, or failed).

  - `"group_created"`

    A group was created (RBAC admin or SCIM provisioning).

  - `"group_deleted"`

    A group was deleted (RBAC admin or SCIM provisioning).

  - `"group_list_viewed"`

    Admin viewed the list of RBAC groups.

  - `"group_member_added"`

    One or more members were added to a group.

  - `"group_member_addition_failed"`

    A request to add members to a group failed. Some of the requested members may have been added before the failure.

  - `"group_member_list_viewed"`

    Admin viewed the members of an RBAC group.

  - `"group_member_removal_failed"`

    A request to remove members from a group failed. Some of the requested members may have been removed before the failure.

  - `"group_member_removed"`

    One or more members were removed from a group.

  - `"group_project_shares_revoked"`

    An RBAC group's project shares in one organization were revoked in bulk.

  - `"group_skill_shares_revoked"`

    An RBAC group's skill shares in one organization were revoked in bulk.

  - `"group_updated"`

    A group was updated (RBAC admin or SCIM provisioning).

  - `"group_viewed"`

    A group was viewed.

  - `"group_visibility_updated"`

    An RBAC group's visibility policy was updated.

  - `"inference_hooks_circuit_breaker_tripped"`

    The organization's Inference hooks circuit breaker tripped automatically: calls to the organization's Inference hooks endpoint crossed a failure threshold, and inspection was suspended to protect live traffic. While tripped, requests are handled according to the organization's failure handling setting — allowed through uninspected (fail open) or rejected (fail closed) — and no per-request Inference hooks activities are recorded. The tripped state persists until an administrator re-enables Inference hooks inspection (or explicitly resets the circuit breaker).

  - `"inference_hooks_config_deleted"`

    Inference hooks configuration was removed for the
    organization.

  - `"inference_hooks_config_updated"`

    Inference hooks configuration was created or updated for the
    organization.

  - `"inference_hooks_request_denied"`

    Inference hooks inspection denied a request. The request was blocked and no model response was produced.

  - `"inference_hooks_request_failed_open"`

    A request proceeded without Inference hooks inspection because a verdict could not be obtained and the organization's Inference hooks configuration is set to fail open.

  - `"inference_hooks_signing_secret_generated"`

    A request signing secret was generated for the organization's
    Inference hooks configuration.

  - `"integration_user_connected"`

    User connected to an integration.

  - `"integration_user_disconnected"`

    User disconnected from an integration.

  - `"invoice_collection_method_updated"`

    Invoice collection method was changed.

  - `"lti_launch_initiated"`

    LTI launch was initiated.

  - `"lti_launch_success"`

    LTI launch completed successfully.

  - `"lti_platform_created"`

    Anthropic staff created an LTI platform integration on behalf of an org.

  - `"lti_platform_updated"`

    Anthropic staff updated an LTI platform integration on behalf of an org.

  - `"magic_link_login_failed"`

    A magic link sign-in attempt failed.

  - `"magic_link_login_initiated"`

    A user requested a magic link sign-in email.

  - `"magic_link_login_succeeded"`

    A user successfully signed in with a magic link email.

  - `"managed_organization_setup_completed"`

    Managed (AWS Marketplace) organization setup was completed.

  - `"marketplace_created"`

    Admin created an organization marketplace.

  - `"marketplace_deleted"`

    Admin deleted an organization marketplace.

  - `"marketplace_updated"`

    Admin updated an organization marketplace.

  - `"marketplace_webhook_deleted"`

    Admin removed the GitHub push webhook for a marketplace.

  - `"marketplace_webhook_provisioned"`

    Admin provisioned a GitHub push webhook for a marketplace.

  - `"mcp_directory_server_published"`

    The organization published its approved MCP directory listing.

  - `"mcp_server_created"`

    An MCP server was added to the organization.

  - `"mcp_server_deleted"`

    An MCP server was removed from the organization.

  - `"mcp_server_managed_auth_token_exchanged"`

    A user attempted to obtain an access token for an MCP server via enterprise managed authorization. This event reports the outcomes of attempted token exchanges. Repeated failures with the same cause may be reported once until the cause changes, and requests denied by organization policy before a token exchange is attempted are not reported, with the exception of the "connector_scope_not_granted" failures described under error_type.

  - `"mcp_server_managed_auth_updated"`

    An MCP server's enterprise managed authorization settings were set, changed, or cleared, including when they were supplied while the server was being added or edited. Fields without a "previous_" prefix describe the settings after the change and are null when the server has no managed authorization settings afterwards; "previous_" fields describe the settings before the change and are null when the server had none before (always the case for a newly added server).

  - `"mcp_server_updated"`

    An MCP server's configuration was updated.

  - `"mcp_tool_policy_updated"`

    The permission restriction for an MCP tool was set or cleared.

  - `"org_analytics_api_capability_updated"`

    Organization analytics_api capability was enabled or disabled.

  - `"org_bulk_delete_initiated"`

    Organization bulk deletion was initiated.

  - `"org_capability_grant_added"`

    A capability grant was added to a workspace or role.

  - `"org_capability_grant_removed"`

    A capability grant was removed from a workspace or role.

  - `"org_claude_code_data_sharing_disabled"`

    Organization Claude Code data sharing was disabled.

  - `"org_claude_code_data_sharing_enabled"`

    Organization Claude Code data sharing was enabled.

  - `"org_claude_code_desktop_disabled"`

    Organization Claude Code Desktop was disabled.

  - `"org_claude_code_desktop_enabled"`

    Organization Claude Code Desktop was enabled.

  - `"org_claude_code_zero_data_retention_disabled"`

    A primary owner disabled zero data retention for Claude Code, so Claude
    Code content is retained according to the organization's data retention
    settings.

  - `"org_compliance_api_settings_updated"`

    Organization compliance API settings were updated.

  - `"org_connector_domain_guard_updated"`

    Enterprise admin changed whether connectors are restricted to verified domains.

  - `"org_cowork_act_without_asking_mode_disabled"`

    The "Act without asking" mode in Cowork was disabled for the organization, so members can no longer let Claude act without asking for approval.

  - `"org_cowork_act_without_asking_mode_enabled"`

    The "Act without asking" mode in Cowork was enabled for the organization, allowing members to let Claude act without asking for approval.

  - `"org_cowork_agent_disabled"`

    Organization Cowork Agent was disabled.

  - `"org_cowork_agent_enabled"`

    Organization Cowork Agent was enabled.

  - `"org_cowork_auto_mode_disabled"`

    The "Auto" permission mode in Cowork was disabled for the organization, so members can no longer let Claude approve its own actions after a safety check.

  - `"org_cowork_auto_mode_enabled"`

    The "Auto" permission mode in Cowork was enabled for the organization, allowing members to let Claude approve its own actions after a safety check.

  - `"org_cowork_disabled"`

    Organization cowork was disabled.

  - `"org_cowork_enabled"`

    Organization cowork was enabled.

  - `"org_cowork_mcp_always_allow_disabled"`

    The "Always allow" option for connector tools in Cowork was disabled for the organization, so each use of a connector tool that can make changes requires approval. Read-only connector tools are not affected by this setting.

  - `"org_cowork_mcp_always_allow_enabled"`

    The "Always allow" option for connector tools in Cowork was enabled for the organization, letting members approve a connector tool that can make changes once and allow its later uses automatically. Read-only connector tools are not affected by this setting.

  - `"org_cowork_otlp_settings_updated"`

    The organization's Cowork OpenTelemetry monitoring export settings were updated.

  - `"org_cowork_remote_disabled"`

    Running Cowork in the cloud was disabled for the organization, so members can no longer run Cowork sessions in Anthropic-hosted remote environments.

  - `"org_cowork_remote_enabled"`

    Running Cowork in the cloud was enabled for the organization, allowing members to run Cowork sessions in Anthropic-hosted remote environments.

  - `"org_creation_blocked"`

    Organization creation was blocked.

  - `"org_data_export_accessed"`

    Organization data export file was accessed/downloaded via signed URL.

  - `"org_data_export_completed"`

    Organization data export was completed.

  - `"org_data_export_started"`

    Organization data export was started.

  - `"org_data_residency_updated"`

    The organization's inference data residency settings were updated.

  - `"org_deleted_via_bulk"`

    Organization was deleted via bulk operation.

  - `"org_deletion_requested"`

    Organization deletion was requested.

  - `"org_directory_resync_completed"`

    Organization directory resync completed successfully.

  - `"org_directory_resync_failed"`

    Organization directory resync failed.

  - `"org_directory_resync_started"`

    Organization directory resync was started asynchronously.

  - `"org_directory_sync_activated"`

    Organization directory sync was activated.

  - `"org_directory_sync_add_initiated"`

    Organization directory sync setup was initiated.

  - `"org_directory_sync_deleted"`

    Organization directory sync was deleted.

  - `"org_discoverability_disabled"`

    Admin disabled organization discoverability.

  - `"org_discoverability_enabled"`

    Admin enabled organization discoverability.

  - `"org_discoverability_settings_updated"`

    Admin updated organization discoverability settings.

  - `"org_domain_add_initiated"`

    Organization domain verification was initiated.

  - `"org_domain_removed"`

    Organization domain was removed.

  - `"org_domain_verified"`

    Organization domain was verified.

  - `"org_external_key_created"`

    A CMEK external key config was created.

  - `"org_external_key_deleted"`

    A CMEK external key config was deleted.

  - `"org_external_key_updated"`

    A CMEK external key config was updated.

  - `"org_external_key_validated"`

    A CMEK external key config was validated against the customer's KMS.

  - `"org_hipaa_self_serve_enabled"`

    A primary owner click-accepted the BAA and enabled HIPAA protections
    for the organization via the self-serve flow.

  - `"org_invite_link_disabled"`

    Organization invite link was disabled.

  - `"org_invite_link_generated"`

    Organization invite link was generated.

  - `"org_invite_link_regenerated"`

    Organization invite link was regenerated (previous link invalidated).

  - `"org_invite_viewed"`

    An organization invite was viewed.

  - `"org_invites_listed"`

    Organization invites were listed.

  - `"org_ip_restriction_created"`

    Organization IP restriction was created.

  - `"org_ip_restriction_deleted"`

    Organization IP restriction was deleted.

  - `"org_ip_restriction_updated"`

    Organization IP restriction was updated.

  - `"org_join_proposal_decided"`

    Approve or reject decision on a parent-org join proposal.

  - `"org_join_request_approved"`

    Admin approved a join request.

  - `"org_join_request_created"`

    User requested to join an organization.

  - `"org_join_request_dismissed"`

    Admin dismissed a join request.

  - `"org_join_request_instant_approved"`

    Join request was instantly approved.

  - `"org_join_requests_bulk_dismissed"`

    Admin bulk-dismissed join requests.

  - `"org_magic_link_second_factor_toggled"`

    Organization magic link second factor was toggled.

  - `"org_member_invites_disabled"`

    Admin disabled member invites for the organization.

  - `"org_member_invites_enabled"`

    Admin enabled member invites for the organization.

  - `"org_members_exported"`

    Organization members list was exported as CSV.

  - `"org_model_default_updated"`

    An organization or role default model setting was changed by an administrator.

  - `"org_parent_join_proposal_created"`

    Organization parent join proposal was created.

  - `"org_parent_search_performed"`

    Organization parent search was performed.

  - `"org_sso_add_initiated"`

    Organization SSO setup was initiated.

  - `"org_sso_connection_activated"`

    Organization SSO connection was activated.

  - `"org_sso_connection_deactivated"`

    Organization SSO connection was deactivated.

  - `"org_sso_connection_deleted"`

    Organization SSO connection was deleted.

  - `"org_sso_group_role_mappings_updated"`

    Organization SSO group role mappings were updated.

  - `"org_sso_provisioning_mode_changed"`

    Organization SSO provisioning mode was changed.

  - `"org_sso_scim_welcome_email_toggled"`

    Organization SCIM-provisioned welcome email was toggled.

  - `"org_sso_seat_tier_assignment_toggled"`

    Organization SSO seat tier assignment was toggled.

  - `"org_sso_seat_tier_mappings_updated"`

    Organization SSO seat tier mappings were updated.

  - `"org_sso_toggled"`

    Organization SSO was toggled on or off.

  - `"org_sync_deleting_synchronized_files_started"`

    Organization started deleting synchronized files.

  - `"org_sync_synchronized_files_deleted"`

    Organization synchronized files were deleted.

  - `"org_taint_added"`

    A taint was added to an organization.

  - `"org_taint_removed"`

    A taint was removed from an organization.

  - `"org_user_deleted"`

    User was removed from organization.

  - `"org_user_invite_accepted"`

    Organization user invite was accepted.

  - `"org_user_invite_deleted"`

    Organization user invite was deleted.

  - `"org_user_invite_re_sent"`

    Organization user invite was re-sent.

  - `"org_user_invite_rejected"`

    Organization user invite was rejected.

  - `"org_user_invite_sent"`

    Organization user invite was sent.

  - `"org_user_left"`

    User removed themselves from organization.

  - `"org_user_trusted_devices_revoked"`

    An organization admin revoked a member's trusted devices and signed the member out of all active sessions.

  - `"org_user_viewed"`

    An organization user was viewed.

  - `"org_users_listed"`

    Organization users were listed.

  - `"org_work_across_apps_disabled"`

    The organization's "Let Claude work across apps" setting was turned off.

  - `"org_work_across_apps_enabled"`

    The organization's "Let Claude work across apps" setting was turned on.

  - `"organization_address_updated"`

    The organization's billing or shipping address was updated.

  - `"organization_icon_deleted"`

    Organization's custom icon deleted.

  - `"organization_icon_updated"`

    Organization's custom icon uploaded or replaced.

  - `"owned_projects_access_restored"`

    Access to owned projects was restored.

  - `"payment_method_updated"`

    The organization's default payment method was updated.

  - `"pending_share_created"`

    A pending share of a project or skill was created for an email address that is not yet an organization member.

  - `"pending_share_revoked"`

    A pending share of a project or skill was revoked before the invitee joined the organization.

  - `"phone_code_sent"`

    User requested a phone verification code.

  - `"phone_code_verified"`

    User successfully verified their phone code.

  - `"platform_agent_archived"`

    An agent was archived on the API platform.

  - `"platform_agent_created"`

    An agent was created on the API platform.

  - `"platform_agent_deleted"`

    An agent was deleted from the API platform.

  - `"platform_agent_deployment_archived"`

    An agent deployment was archived on the API platform.

  - `"platform_agent_deployment_created"`

    An agent deployment was created on the API platform.

  - `"platform_agent_deployment_deleted"`

    An agent deployment was deleted from the API platform.

  - `"platform_agent_deployment_paused"`

    An agent deployment was paused on the API platform.

  - `"platform_agent_deployment_run_triggered"`

    An agent deployment was run on demand on the API platform.

  - `"platform_agent_deployment_unpaused"`

    An agent deployment was resumed on the API platform.

  - `"platform_agent_deployment_updated"`

    An agent deployment was updated on the API platform.

  - `"platform_agent_session_archived"`

    An agent session was archived on the API platform.

  - `"platform_agent_session_created"`

    An agent session was created on the API platform.

  - `"platform_agent_session_deleted"`

    An agent session was deleted from the API platform.

  - `"platform_agent_session_resource_added"`

    A resource was attached to an agent session.

  - `"platform_agent_session_resource_deleted"`

    A resource attached to an agent session was removed.

  - `"platform_agent_session_resource_updated"`

    A resource attached to an agent session was updated.

  - `"platform_agent_session_thread_archived"`

    A thread within an agent session was archived.

  - `"platform_agent_session_updated"`

    An agent session was updated on the API platform.

  - `"platform_agent_updated"`

    An agent was updated on the API platform.

  - `"platform_api_key_created"`

    An API key was created.

  - `"platform_api_key_updated"`

    An API key was updated.

  - `"platform_app_attest_authentication"`

    An attested mobile device attempted to exchange an Apple App Attest assertion for Anthropic API credentials.

  - `"platform_billing_upgraded_to_prepaid"`

    The organization's API billing was upgraded to the prepaid plan.

  - `"platform_clearance_workspace_program_request_cleared"`

    A workspace's clearance program assignment was removed.

  - `"platform_clearance_workspace_program_request_set"`

    A workspace's clearance program assignment was created or updated.

  - `"platform_cost_report_viewed"`

    The cost report was viewed.

  - `"platform_dream_archived"`

    A Dream (asynchronous memory-consolidation job) was archived.

  - `"platform_dream_cancelled"`

    A Dream (asynchronous memory-consolidation job) was cancelled before it completed.

  - `"platform_dream_created"`

    A Dream (asynchronous memory-consolidation job) was created.

  - `"platform_federated_authentication"`

    A federated workload identity attempted to exchange an OIDC token for Anthropic API credentials.

  - `"platform_federation_issuer_archived"`

    An OIDC federation issuer was archived.

  - `"platform_federation_issuer_updated"`

    An OIDC federation issuer was updated.

  - `"platform_federation_rule_archived"`

    An OIDC federation rule was archived.

  - `"platform_federation_rule_updated"`

    An OIDC federation rule was updated.

  - `"platform_federation_rule_workspace_added"`

    A federation rule was enabled for a workspace.

  - `"platform_federation_rule_workspace_removed"`

    A federation rule was disabled for a workspace.

  - `"platform_file_content_downloaded"`

    Activity logged when file content is downloaded via GET /v1/files/{file_id}/content.

  - `"platform_file_deleted"`

    Activity logged when a file is deleted via DELETE /v1/files/{file_id}.

  - `"platform_file_uploaded"`

    Activity logged when a file is uploaded via POST /v1/files.

  - `"platform_memory_created"`

    An agent memory document was created.

  - `"platform_memory_deleted"`

    An agent memory document was deleted.

  - `"platform_memory_store_archived"`

    An agent memory store was archived. Archived stores reject new memory writes and cannot be attached to new sessions; deletion and redaction remain permitted for privacy scrubbing.

  - `"platform_memory_store_created"`

    An agent memory store was created.

  - `"platform_memory_store_deleted"`

    An agent memory store was deleted. Memory content removal may complete asynchronously for very large stores.

  - `"platform_memory_store_updated"`

    An agent memory store's name, description, or metadata was updated.

  - `"platform_memory_updated"`

    An agent memory document's content or path was updated.

  - `"platform_memory_version_redacted"`

    A historical version of an agent memory document was redacted. Redaction scrubs the stored content of a specific version while preserving the version's existence in the history.

  - `"platform_oauth_app_created"`

    An OAuth app was created.

  - `"platform_oauth_app_revoked"`

    An OAuth app was revoked.

  - `"platform_oauth_app_updated"`

    An OAuth app was updated.

  - `"platform_plugin_directory_submission_created"`

    A plugin directory submission was created on the API platform. A plugin directory submission is a request to list a plugin in the public plugin directory.

  - `"platform_plugin_directory_submission_deleted"`

    A plugin directory submission was deleted on the API platform.

  - `"platform_plugin_directory_submission_updated"`

    A plugin directory submission was updated on the API platform.

  - `"platform_service_account_archived"`

    A service account was archived.

  - `"platform_service_account_updated"`

    A service account was updated.

  - `"platform_service_account_workspace_member_added"`

    A service account was added as a member of a workspace.

  - `"platform_service_account_workspace_member_removed"`

    A service account was removed from a workspace.

  - `"platform_service_account_workspace_member_updated"`

    A service account's workspace membership role was updated.

  - `"platform_signing_key_created"`

    Activity logged when a new request-signing key is registered for the org.

  - `"platform_signing_key_deleted"`

    Activity logged when a signing key is permanently deleted.

  - `"platform_signing_key_rotated"`

    Activity logged when an in-memory signing key is rotated.

  - `"platform_skill_version_created"`

    Activity logged when a skill version is created via POST /v1/skills/{skill_id}/versions.

  - `"platform_skill_version_deleted"`

    Activity logged when a skill version is deleted via DELETE /v1/skills/{skill_id}/versions/{version}.

  - `"platform_spend_limit_alert_emails_updated"`

    Spend limit alert email addresses and role targets were updated for an org.

  - `"platform_spend_limit_created"`

    An org-level fixed-dollar spend limit was created.

  - `"platform_spend_limit_deleted"`

    An org-level spend limit was removed.

  - `"platform_spend_limit_updated"`

    An org-level spend limit snooze/ignore state was changed.

  - `"platform_usage_report_claude_code_viewed"`

    The Claude Code usage report was viewed.

  - `"platform_usage_report_messages_viewed"`

    The messages usage report was viewed.

  - `"platform_workspace_archived"`

    A workspace was archived.

  - `"platform_workspace_created"`

    A workspace was created.

  - `"platform_workspace_inference_data_retention_disabled"`

    The zero data retention override was disabled for a workspace.

  - `"platform_workspace_inference_data_retention_enabled"`

    The zero data retention override was enabled for a workspace.

  - `"platform_workspace_member_added"`

    A member was added to a workspace.

  - `"platform_workspace_member_removed"`

    A member was removed from a workspace.

  - `"platform_workspace_member_updated"`

    A workspace member was updated.

  - `"platform_workspace_member_viewed"`

    A workspace member was viewed.

  - `"platform_workspace_members_listed"`

    Workspace members were listed.

  - `"platform_workspace_rate_limit_deleted"`

    A workspace rate limit was deleted.

  - `"platform_workspace_rate_limit_updated"`

    A workspace rate limit was created or updated.

  - `"platform_workspace_updated"`

    A workspace was updated.

  - `"plugin_installation_preference_updated"`

    An org admin changed the installation preference for a plugin.

  - `"prepaid_auto_recharge_disabled"`

    Auto-recharge was disabled for API prepaid org.

  - `"prepaid_auto_recharge_updated"`

    Auto-recharge settings were updated for API prepaid org.

  - `"prepaid_extra_usage_auto_reload_disabled"`

    Prepaid usage credit auto-reload was disabled.

  - `"prepaid_extra_usage_auto_reload_enabled"`

    Prepaid usage credit auto-reload was enabled.

  - `"prepaid_extra_usage_auto_reload_settings_updated"`

    Prepaid usage credit auto-reload settings were updated.

  - `"primary_owner_transferred"`

    Primary owner role was transferred to another org member.

  - `"rbac_role_assigned"`

    Admin assigned an RBAC custom role to a principal.

  - `"rbac_role_created"`

    Admin created an RBAC custom role.

  - `"rbac_role_deleted"`

    Admin deleted an RBAC custom role.

  - `"rbac_role_permission_added"`

    Admin added a permission to an RBAC custom role.

    Emitted once per requested permission, including permissions the role
    already had, so a retried request still produces a complete audit record.

  - `"rbac_role_permission_removed"`

    Admin removed a permission from an RBAC custom role.

    Emitted once per requested permission, including permissions the role
    already lacked, so a retried request still produces a complete audit
    record.

  - `"rbac_role_unassigned"`

    Admin unassigned an RBAC custom role from a principal.

  - `"rbac_role_updated"`

    Admin updated an RBAC custom role.

  - `"role_assignment_granted"`

    Role assignment was granted.

  - `"role_assignment_revoked"`

    Role assignment was revoked.

  - `"scim_user_created"`

    A SCIM user was provisioned.

  - `"scim_user_deleted"`

    A SCIM user was deleted.

  - `"scim_user_updated"`

    A SCIM user was updated.

  - `"scoped_api_key_deleted"`

    A scoped API key was deleted.

  - `"scoped_api_key_updated"`

    A scoped API key was renamed or its activation state changed.

  - `"seat_tier_changes_cancelled"`

    Scheduled seat tier downgrades were cancelled.

  - `"seat_tiers_purchased"`

    Seat tiers were purchased or upgraded on a subscription.

  - `"service_created"`

    Activity logged when an org service is explicitly created.

  - `"service_deleted"`

    Activity logged when an org service is deleted.

  - `"service_key_created"`

    Activity logged when a new org service key is created.

  - `"service_key_revoked"`

    Activity logged when an org service key is revoked.

  - `"session_revoked"`

    User revoked a specific session.

  - `"session_share_accessed"`

    Session share was accessed.

  - `"session_share_created"`

    Session share was created.

  - `"session_share_revoked"`

    Session share was revoked.

  - `"slack_workspace_claim_revoked"`

    A Slack workspace or Enterprise Grid organization was disconnected
    from the organization for Claude in Slack.

  - `"slack_workspace_claimed"`

    A Slack workspace or Enterprise Grid organization was connected to
    the organization for Claude in Slack.

  - `"social_login_succeeded"`

    A user successfully signed in with a social identity provider (Google, Apple, or Microsoft).

  - `"sso_login_failed"`

    An SSO sign-in attempt failed.

  - `"sso_login_initiated"`

    A user started an SSO sign-in flow.

  - `"sso_login_succeeded"`

    A user successfully signed in with SSO.

  - `"sso_second_factor_magic_link"`

    SSO second factor magic link was used.

  - `"step_up_authentication_failed"`

    An additional identity check failed.

  - `"step_up_authentication_succeeded"`

    The user completed an additional identity check to confirm a sensitive action.

  - `"step_up_credential_enrolled"`

    A user enrolled a passkey for confirming sensitive actions on their account.

  - `"subscription_cancellation_scheduled"`

    Subscription cancellation was scheduled at end of billing period.

  - `"subscription_quantity_updated"`

    Contracted subscription seat quantity was updated.

  - `"subscription_renewed"`

    A cancelled subscription was renewed.

  - `"subscription_resumed"`

    A scheduled subscription cancellation was reversed.

  - `"subscription_started"`

    A new subscription was created (Team or Enterprise).

  - `"subscription_upgraded"`

    Subscription plan was upgraded (e.g. Team to Enterprise).

  - `"trusted_device_credential_rotated"`

    The identity-verification credential of a trusted device was rotated to a new key.

  - `"trusted_device_enrolled"`

    A device was enrolled as a trusted device for the user's account. Trusted devices can be used to confirm the user's identity for sensitive actions.

  - `"trusted_device_revoked"`

    A trusted device was removed from the user's account.

  - `"tunnel_archived"`

    An MCP tunnel was archived.

  - `"tunnel_certificate_added"`

    An inner-TLS CA certificate was added to a tunnel.

  - `"tunnel_certificate_revoked"`

    An inner-TLS CA certificate was revoked from a tunnel.

  - `"tunnel_created"`

    An MCP tunnel was created.

  - `"tunnel_token_minted"`

    An OAuth bearer token for the tunnel management API was minted.

  - `"tunnel_token_revealed"`

    The Cloudflare connector secret for a tunnel was revealed to the caller.

  - `"tunnel_token_revoked"`

    An OAuth bearer token for the tunnel management API was revoked.

  - `"tunnel_token_rotated"`

    The Cloudflare connector secret for a tunnel was rotated.

    `tunnel_token_id` is the id of the *newly-issued* token. The previous
    token is invalidated by the rotation and its id is not recorded here.

  - `"user_consent_recorded"`

    User granted a consent for a specific entity (e.g. consumer health consent for an MCP server).

  - `"user_consent_revoked"`

    User revoked a previously granted consent for a specific entity.

  - `"user_logged_out"`

    A user signed out of one or all sessions.

  - `"verification_evidence_submitted"`

    Verification evidence was submitted for an organization's verification.

  - `"verification_program_application_created"`

    An organization applied to a verification program.

  - `"workspace_member_spend_limit_created"`

    A per-member or workspace-default Claude Code spend limit was created.

  - `"workspace_member_spend_limit_deleted"`

    A per-member or workspace-default Claude Code spend limit was deleted.

  - `"workspace_member_spend_limit_updated"`

    A per-member Claude Code spend limit amount was updated.

  - `"workspace_spend_limit_alert_emails_updated"`

    Spend limit alert email recipients were updated for a workspace.

  - `"workspace_spend_limit_created"`

    A workspace-level API spend limit was created.

  - `"workspace_spend_limit_deleted"`

    A workspace-level API spend limit was deleted.

- `actor_ids: optional array of string`

  Filter activities by actor IDs (currently only `user_...` IDs are supported). Enumerate IDs via `GET /v1/compliance/organizations/{org_uuid}/users`.

- `after_id: optional string`

  Pagination cursor for retrieving the next page of results. To paginate, pass the `last_id` value from the most recent response. Clients should treat this value as an opaque string and not attempt to parse or interpret its contents, as the format may change without notice.

- `before_id: optional string`

  Pagination cursor for retrieving the previous page of results. To paginate, pass the `first_id` value from the most recent response. Clients should treat this value as an opaque string and not attempt to parse or interpret its contents, as the format may change without notice.

- `created_at: optional object`

  - `gt: optional string`

    Filter activities created after this time (RFC 3339 format)

    format: date-time

  - `gte: optional string`

    Filter activities created at or after this time (RFC 3339 format)

    format: date-time

  - `lt: optional string`

    Filter activities created before this time (RFC 3339 format)

    format: date-time

  - `lte: optional string`

    Filter activities created at or before this time (RFC 3339 format)

    format: date-time

- `exclude_activity_types: optional array of "abuse_decision_received" or "account_deleted" or "admin_api_key_created" or 480 more`

  Exclude activities of these types. Cannot be combined with `activity_types[]`.

  - `"abuse_decision_received"`

    An external anti-abuse service reported a consequential decision about a sign-in or sign-up attempt.

  - `"account_deleted"`

    User-initiated self-service account deletion.

  - `"admin_api_key_created"`

    An admin API key was created.

  - `"admin_api_key_deleted"`

    An admin API key was deleted.

  - `"admin_api_key_updated"`

    An admin API key was updated (renamed or activated/deactivated).

  - `"admin_connector_request_resolved"`

    Admin approved or dismissed pending member requests to enable an MCP connector.

  - `"admin_request_created"`

    Admin request created by an org member (seat upgrade, limit increase, join org, end-user invite).

  - `"age_verified"`

    User age was verified.

  - `"anonymous_mobile_login_attempted"`

    Anonymous mobile login was attempted.

  - `"api_key_created"`

    Activity logged when a new API key is created.

  - `"audit_log_export_accessed"`

    Audit log export file was accessed/downloaded via signed URL.

  - `"audit_log_export_started"`

    Audit log export was initiated.

  - `"billing_emails_updated"`

    The organization's billing email recipients were updated.

  - `"ccr_agent_created"`

    A Claude Code agent was created.

  - `"ccr_agent_deleted"`

    A Claude Code agent was deleted.

  - `"ccr_agent_proxy_credential_created"`

    A Claude Code agent proxy credential was created. Credentials hold the secrets the agent proxy injects into requests Claude Code sessions send to approved external services; each credential belongs to an agent proxy profile. Audit events carry only credential names and settings, never the secret material itself.

  - `"ccr_agent_proxy_credential_deleted"`

    A Claude Code agent proxy credential was deleted. Its secret material was removed and can no longer be sent to any host.

  - `"ccr_agent_proxy_credential_rotated"`

    A Claude Code agent proxy credential's secret material was replaced. The replacement keeps the same name, profile, and allowed hosts under a new credential identifier, and everything that referenced the old credential now uses the replacement.

  - `"ccr_agent_proxy_credential_updated"`

    A Claude Code agent proxy credential's settings were updated. Only the display name and the allowed host patterns can be updated; the secret material can only be replaced through a rotation.

  - `"ccr_agent_proxy_destination_deleted"`

    An agent proxy destination was deleted.

  - `"ccr_agent_proxy_network_events_listed"`

    A Claude Code network activity export was accessed for the given hour.

  - `"ccr_agent_proxy_profile_bound"`

    A Claude Code agent proxy profile was bound to a scope, applying its policy to Claude Code sessions in that scope.

  - `"ccr_agent_proxy_profile_created"`

    A Claude Code agent proxy profile was created. Agent proxy profiles are named, reusable bundles of access policy that administrators bind to parts of the organization.

  - `"ccr_agent_proxy_profile_deleted"`

    A Claude Code agent proxy profile was deleted, removing its policy from everything it was bound to.

  - `"ccr_agent_proxy_profile_unbound"`

    A Claude Code agent proxy profile was unbound from a scope, removing its policy from Claude Code sessions in that scope.

  - `"ccr_agent_proxy_profile_updated"`

    A Claude Code agent proxy profile's configuration was updated.

  - `"ccr_agent_proxy_provisioning_credential_rejected"`

    An organization owner rejected a credential that a teammate submitted via an agent proxy provisioning link: the credential and its disabled rule were deleted and the link was revoked. The actor is the owner; the submitter is recorded for attribution.

  - `"ccr_agent_proxy_provisioning_link_enabled"`

    An organization owner enabled a credential that a teammate submitted via an agent proxy provisioning link: the disabled rule created at submission was switched to enforce, so the credential now takes traffic. The actor is the owner; the submitter is the actor on the prior ccr_agent_proxy_provisioning_link_submitted event.

  - `"ccr_agent_proxy_provisioning_link_generated"`

    An organization owner generated a one-time agent proxy credential provisioning link so a teammate can submit a credential into the target agent proxy profile without holding the owner role.

  - `"ccr_agent_proxy_provisioning_link_revoked"`

    An organization owner revoked an unfilled agent proxy provisioning link.

  - `"ccr_agent_proxy_provisioning_link_submitted"`

    A teammate submitted a credential via an agent proxy provisioning link. The credential and a disabled rule are created; the credential takes traffic only after an organization owner enables the submitted credential. This event records the link-mediated lifecycle; the credential itself additionally emits ccr_agent_proxy_credential_created.

  - `"ccr_agent_proxy_rule_deleted"`

    An agent proxy rule was deleted.

  - `"ccr_agent_slack_access_scope_created"`

    A Claude Code agent was granted access to read or write in an additional Slack channel beyond the one it is assigned to.

  - `"ccr_agent_slack_access_scope_deleted"`

    A Claude Code agent's access to an additional Slack channel was revoked.

  - `"ccr_agent_slack_binding_created"`

    A Claude Code agent was assigned to a Slack channel or workspace as its dedicated agent.

  - `"ccr_agent_slack_binding_deleted"`

    A Claude Code agent's assignment to a Slack channel or workspace was removed.

  - `"ccr_agent_updated"`

    A Claude Code agent's configuration was updated. Also emitted with updated_fields ["is_virtual"] alone when an auto-provisioned agent is promoted to a configured one, whether by an update request targeting it or by binding an agent proxy profile to it.

  - `"ccr_role_channel_assignment_deleted"`

    CcrRoleChannelAssignmentDeleted is emitted when an org owner/admin removes an RBAC role's channel assignment row (the role reverts to granting zero channels).

  - `"ccr_role_channel_assignment_updated"`

    CcrRoleChannelAssignmentUpdated is emitted when an org owner/admin sets or replaces the list of Slack channels an RBAC role's holders may configure via the delegated Claude-in-Slack channel-manage surface.

  - `"ccr_session_created"`

    A Claude Code session was created. A session is one coding interaction with Claude.

  - `"ccr_session_deleted"`

    A Claude Code session was deleted.

  - `"ccr_session_updated"`

    A Claude Code session's settings were updated.

  - `"claude_artifact_access_failed"`

    An attempt to access an artifact failed.

  - `"claude_artifact_commented"`

    Comment activity on a published artifact: a comment was added, a thread's resolved state was changed, or a thread was deleted. The actor is the user who performed the action; the comment text itself is stored with the artifact and is not part of this record.

  - `"claude_artifact_comments_viewed"`

    An artifact's comments were viewed.

  - `"claude_artifact_created"`

    An artifact was created.

  - `"claude_artifact_duplicated"`

    A user duplicated an artifact they could view into a new artifact that they own. The actor is the user who created the copy; the source artifact is not modified.

  - `"claude_artifact_published"`

    A new version of an artifact was published — for an artifact created in a chat this is the action that made it publicly viewable; for an artifact created outside a chat it is recorded on every save, including saves of private artifacts, and changes to who can access the artifact are recorded separately as claude_artifact_sharing_updated.

  - `"claude_artifact_sharing_updated"`

    An artifact's sharing settings were updated.

  - `"claude_artifact_viewed"`

    An artifact was viewed.

  - `"claude_chat_access_failed"`

    A user was denied access to a Claude.ai chat conversation.

  - `"claude_chat_created"`

    User created a chat.

  - `"claude_chat_deleted"`

    A user deleted a Claude.ai chat conversation.

  - `"claude_chat_deletion_failed"`

    A request to delete a Claude.ai chat conversation failed.

  - `"claude_chat_settings_updated"`

    User updated the settings for a conversation.

  - `"claude_chat_snapshot_created"`

    User created/shared a chat snapshot.

  - `"claude_chat_snapshot_deleted"`

    User deleted/unshared a chat snapshot.

  - `"claude_chat_snapshot_viewed"`

    User viewed a chat snapshot (authenticated or public/unauthenticated).

  - `"claude_chat_sync_source_created"`

    A sync source was connected for syncing external content into Claude chats.

  - `"claude_chat_sync_source_deleted"`

    A sync source was disconnected from Claude chats.

  - `"claude_chat_sync_source_updated"`

    A Claude chat sync source's configuration was updated.

  - `"claude_chat_updated"`

    User updated the chat metadata (e.g name, model).

  - `"claude_chat_viewed"`

    A user viewed a Claude.ai chat conversation.

  - `"claude_code_credential_revoked"`

    A Claude Code credential (runner pool key, runner token, or session token) was revoked. The credential itself is never recorded.

  - `"claude_code_review_config_updated"`

    Claude Code Review configuration was enabled/disabled for an org.

  - `"claude_code_review_repository_added"`

    A repository was added to org-level Claude Code Review configuration.

  - `"claude_code_review_repository_removed"`

    A repository was removed from org-level Claude Code Review configuration.

  - `"claude_code_review_repository_updated"`

    A Claude Code Review repository configuration was updated.

  - `"claude_code_runner_deleted"`

    A self-hosted runner was forcibly removed from its pool. Sessions assigned to the runner were returned to the pool queue, unless a session had already been requeued repeatedly, in which case it was marked stuck instead of being requeued again.

  - `"claude_code_runner_pool_created"`

    A self-hosted runner pool for Claude Code was created.

  - `"claude_code_runner_pool_deleted"`

    A self-hosted runner pool was deleted.

  - `"claude_code_runner_pool_secret_minted"`

    A registration key for a self-hosted runner pool was minted. Runners present this key to join the pool. The key itself is never recorded.

  - `"claude_code_runner_pool_session_queue_updated"`

    An admin changed a session's position in its self-hosted runner pool's queue: requeued it onto a different runner, dismissed it from the queue, or re-admitted it for another runner provisioning attempt.

  - `"claude_code_runner_pool_updated"`

    A self-hosted runner pool's settings were updated.

  - `"claude_code_security_center_config_updated"`

    Claude Code Security Center scanning was enabled/disabled for an org.

  - `"claude_code_security_scan_cancelled"`

    In-flight Claude Code Security scans were cancelled for a project.

  - `"claude_code_security_scan_created"`

    A Claude Code Security scan was started.

  - `"claude_code_security_scan_project_member_updated"`

    A person's access to a Claude Code Security scan project was granted, changed, or revoked.

  - `"claude_code_security_scan_project_updated"`

    A Claude Code Security scan project was archived, unarchived, created, or migrated to a new product experience.

  - `"claude_code_security_scan_project_visibility_updated"`

    A Claude Code Security scan project was shared with the organization or made private.

  - `"claude_code_security_scan_run_updated"`

    A single Claude Code Security scan run was archived, unarchived, or resumed after a billing pause.

  - `"claude_code_security_scan_schedule_deleted"`

    A recurring scan schedule was deleted for a Claude Code Security project.

  - `"claude_code_security_scan_schedule_updated"`

    A recurring scan schedule was set or replaced for a Claude Code Security project.

  - `"claude_code_security_vulnerability_fix_session_created"`

    A Claude Code remediation session was created for a Claude Code Security vulnerability finding.

  - `"claude_code_security_vulnerability_updated"`

    A Claude Code Security vulnerability finding was dismissed, restored, marked fixed, or reopened.

  - `"claude_code_security_webhook_created"`

    A Claude Code Security outbound webhook was created.

  - `"claude_code_security_webhook_deleted"`

    A Claude Code Security outbound webhook was deleted.

  - `"claude_code_security_webhook_secret_updated"`

    The HMAC signing secret for a Claude Code Security webhook was rotated.

  - `"claude_code_security_webhook_updated"`

    A Claude Code Security outbound webhook was updated.

  - `"claude_code_team_memory_acl_updated"`

    An RBAC group was added to or removed from the Claude Code team-memory ACL.

  - `"claude_code_team_memory_updated"`

    Claude Code team memory shared with the organization was updated.

  - `"claude_code_team_onboarding_guide_updated"`

    A Claude Code team onboarding guide was created, updated, or deleted.

  - `"claude_code_user_marketplaces_updated"`

    A user's Claude Code plugin marketplace selections were updated on Anthropic servers.

  - `"claude_code_user_memory_updated"`

    A user's synced private Claude Code memory was updated or deleted on Anthropic servers.

  - `"claude_code_user_plugins_updated"`

    A user's Claude Code plugin selections — which plugins are installed and enabled — were updated on Anthropic servers.

  - `"claude_code_user_settings_updated"`

    A user's synced Claude Code settings were updated or deleted on Anthropic servers.

  - `"claude_command_created"`

    Command was created.

  - `"claude_command_deleted"`

    Command was deleted.

  - `"claude_command_replaced"`

    Command was replaced.

  - `"claude_enterprise_upgrade_credit_updated"`

    An organization admin cancelled, or turned back on, the monthly usage credit the organization receives for upgrading from the Team plan to the Enterprise plan, together with the recurring monthly charge that accompanies it.

  - `"claude_file_access_failed"`

    A user was denied access to a file in Claude.ai.

  - `"claude_file_deleted"`

    A file was deleted.

  - `"claude_file_exported"`

    A file was exported from Claude to an external storage destination.

  - `"claude_file_uploaded"`

    A file was uploaded.

  - `"claude_file_viewed"`

    A user viewed a file in Claude.ai.

  - `"claude_gdrive_integration_created"`

    A Google Drive integration was enabled for the organization.

  - `"claude_gdrive_integration_deleted"`

    A Google Drive integration was disabled for the organization.

  - `"claude_gdrive_integration_updated"`

    A Google Drive integration's configuration was updated.

  - `"claude_github_integration_created"`

    A GitHub integration was enabled for the organization.

  - `"claude_github_integration_deleted"`

    A GitHub integration was disabled for the organization.

  - `"claude_github_integration_updated"`

    A GitHub integration's configuration was updated.

  - `"claude_organization_settings_updated"`

    Organization settings were updated.

  - `"claude_plugin_created"`

    Plugin was created.

  - `"claude_plugin_deleted"`

    Plugin was deleted.

  - `"claude_plugin_disabled"`

    User disabled a plugin for their account.

  - `"claude_plugin_enabled"`

    User enabled a plugin for their account.

  - `"claude_plugin_replaced"`

    Plugin was replaced.

  - `"claude_plugin_updated"`

    Plugin was updated.

  - `"claude_project_archived"`

    A Claude project was archived.

  - `"claude_project_created"`

    A Claude project was created.

  - `"claude_project_deleted"`

    A Claude project was deleted.

  - `"claude_project_document_access_failed"`

    An attempt to access a document in a Claude project failed.

  - `"claude_project_document_bulk_deletion_audit_truncated"`

    A bulk request to delete documents from a Claude project failed with more documents requested than were individually recorded in the audit log.

  - `"claude_project_document_deleted"`

    A document was deleted from a Claude project.

  - `"claude_project_document_deletion_failed"`

    A request to delete a document from a Claude project failed.

  - `"claude_project_document_updated"`

    The content of a document in a Claude project was replaced in place.

  - `"claude_project_document_uploaded"`

    A document was uploaded to a Claude project.

  - `"claude_project_document_viewed"`

    A document in a Claude project was viewed.

  - `"claude_project_file_access_failed"`

    An attempt to access a file in a Claude project failed.

  - `"claude_project_file_bulk_deletion_audit_truncated"`

    A bulk request to delete files from a Claude project failed with more files requested than were individually recorded in the audit log.

  - `"claude_project_file_deleted"`

    A file was deleted from a Claude project.

  - `"claude_project_file_deletion_failed"`

    A request to delete a file from a Claude project failed.

  - `"claude_project_file_uploaded"`

    A file was uploaded to a Claude project.

  - `"claude_project_reported"`

    A Claude project was reported.

  - `"claude_project_sharing_updated"`

    A Claude project's sharing settings were updated.

  - `"claude_project_sync_source_created"`

    A sync source was connected to a Claude project's knowledge base.

  - `"claude_project_sync_source_deleted"`

    A sync source was disconnected from a Claude project's knowledge base.

  - `"claude_project_sync_source_updated"`

    A Claude project sync source's configuration was updated.

  - `"claude_project_viewed"`

    A Claude project was viewed.

  - `"claude_published_artifact_deleted"`

    A published artifact was deleted or unpublished — by its creator, by an organization admin, or by Anthropic (for example, when it was removed for a policy violation).

  - `"claude_pubsec_identity_configured"`

    SAML IdP configuration updated for a public sector organization.

  - `"claude_skill_created"`

    Skill was created.

  - `"claude_skill_deleted"`

    Skill was deleted.

  - `"claude_skill_disabled"`

    User disabled a skill for their account.

  - `"claude_skill_enabled"`

    User enabled a skill for their account.

  - `"claude_skill_replaced"`

    Skill was replaced.

  - `"claude_user_role_updated"`

    A user's role within the organization was changed, or the user was added to or removed from the organization.

  - `"claude_user_seat_tier_updated"`

    An organization member's seat tier was changed. A null `previous_seat_tier` means the member previously had no seat assigned; a null `current_seat_tier` means the seat was removed.

  - `"claude_user_settings_updated"`

    User updated their personal settings.

  - `"cli_plugin_exec_policy_updated"`

    Admin set or cleared the per-op permission ceiling for a plugin CLI.

  - `"compliance_api_accessed"`

    Logging event auto-generated for each compliance API request.

  - `"cowork_session_updated"`

    A Cowork session was updated.

  - `"design_project_artifact_published"`

    A Claude Design project's content was published as a claude.ai artifact, making a snapshot of one of its files viewable outside the project's sharing settings.

  - `"design_project_created"`

    A Claude Design project was created.

  - `"design_project_deleted"`

    A Claude Design project was deleted.

  - `"design_project_member_added"`

    A member was granted access to a Claude Design project.

  - `"design_project_member_removed"`

    A member's access to a Claude Design project was revoked.

  - `"design_project_member_role_updated"`

    A Claude Design project member's role was changed.

  - `"design_project_published"`

    A Claude Design template or design system was published, making it discoverable by everyone in its organization.

  - `"design_project_sharing_updated"`

    A Claude Design project's link-sharing settings were changed — who the project's link works for, and what people opening it through the link may do. Access granted to individual members is reported separately (see design_project_member_added).

  - `"design_project_unpublished"`

    A Claude Design template or design system was unpublished, removing it from its organization's shared gallery.

  - `"design_project_updated"`

    A Claude Design project's metadata was updated.

  - `"design_project_version_restored"`

    A Claude Design project's working tree was rolled back to a previously saved version, replacing its current files with that version's files.

  - `"design_project_viewed"`

    A Claude Design project's content was read. The surface field records which kind of read — a project open, a full-content read, a single-file read, a saved-version read, or an export request. The actor is the reader.

    This activity type is retired: project content reads are no longer
    recorded. Events of this type may still appear in feeds for reads that
    occurred while it was active.

  - `"desktop_extension_allowlisted"`

    A desktop extension was added to an org's allowlist.

  - `"desktop_extension_blocklisted"`

    A desktop extension was added to the global blocklist.

  - `"desktop_extension_deleted"`

    A desktop extension was deleted, either globally by an admin or org-scoped by an org owner.

  - `"desktop_extension_removed_from_allowlist"`

    A desktop extension was removed from an org's allowlist.

  - `"desktop_extension_unblocked"`

    A desktop extension was removed from the global blocklist.

  - `"desktop_extension_uploaded"`

    A desktop extension was uploaded, either globally by an admin or org-scoped by an org owner.

  - `"desktop_extension_version_uploaded"`

    A new version of an existing org-owned desktop extension was uploaded.

  - `"domain_claim_initiated"`

    Domain capture claim initiated over personal accounts on verified domains.

  - `"end_user_invite_requested"`

    Non-admin member submitted an invite request for a new org member.

  - `"extra_usage_billing_enabled"`

    Usage credit billing was enabled for an organization.

  - `"extra_usage_credit_granted"`

    A promotional usage credit grant was claimed.

  - `"extra_usage_spend_limit_created"`

    Usage credit spend limit was created.

  - `"extra_usage_spend_limit_deleted"`

    Usage credit spend limit was deleted.

  - `"extra_usage_spend_limit_increase_request_approved"`

    A usage credit spend limit increase request was approved.

  - `"extra_usage_spend_limit_increase_request_denied"`

    A usage credit spend limit increase request was denied.

  - `"extra_usage_spend_limit_updated"`

    Usage credit spend limit was updated.

  - `"ghe_configuration_created"`

    Admin created a GHE configuration.

  - `"ghe_configuration_deleted"`

    Admin deleted a GHE configuration.

  - `"ghe_configuration_updated"`

    Admin updated a GHE configuration. Previous/new field pairs are recorded only for settings that changed in the update; secret credentials are never recorded, only whether they were replaced.

  - `"ghe_user_connected"`

    User connected to a GHE instance.

  - `"ghe_user_disconnected"`

    User disconnected from a GHE instance.

  - `"ghe_webhook_signature_invalid"`

    Webhook signature validation failed.

  - `"github_token_import"`

    A user attempted to import a personal GitHub access token for use with Claude Code. The `result` field indicates the outcome of the import (imported, rejected, or failed).

  - `"group_created"`

    A group was created (RBAC admin or SCIM provisioning).

  - `"group_deleted"`

    A group was deleted (RBAC admin or SCIM provisioning).

  - `"group_list_viewed"`

    Admin viewed the list of RBAC groups.

  - `"group_member_added"`

    One or more members were added to a group.

  - `"group_member_addition_failed"`

    A request to add members to a group failed. Some of the requested members may have been added before the failure.

  - `"group_member_list_viewed"`

    Admin viewed the members of an RBAC group.

  - `"group_member_removal_failed"`

    A request to remove members from a group failed. Some of the requested members may have been removed before the failure.

  - `"group_member_removed"`

    One or more members were removed from a group.

  - `"group_project_shares_revoked"`

    An RBAC group's project shares in one organization were revoked in bulk.

  - `"group_skill_shares_revoked"`

    An RBAC group's skill shares in one organization were revoked in bulk.

  - `"group_updated"`

    A group was updated (RBAC admin or SCIM provisioning).

  - `"group_viewed"`

    A group was viewed.

  - `"group_visibility_updated"`

    An RBAC group's visibility policy was updated.

  - `"inference_hooks_circuit_breaker_tripped"`

    The organization's Inference hooks circuit breaker tripped automatically: calls to the organization's Inference hooks endpoint crossed a failure threshold, and inspection was suspended to protect live traffic. While tripped, requests are handled according to the organization's failure handling setting — allowed through uninspected (fail open) or rejected (fail closed) — and no per-request Inference hooks activities are recorded. The tripped state persists until an administrator re-enables Inference hooks inspection (or explicitly resets the circuit breaker).

  - `"inference_hooks_config_deleted"`

    Inference hooks configuration was removed for the
    organization.

  - `"inference_hooks_config_updated"`

    Inference hooks configuration was created or updated for the
    organization.

  - `"inference_hooks_request_denied"`

    Inference hooks inspection denied a request. The request was blocked and no model response was produced.

  - `"inference_hooks_request_failed_open"`

    A request proceeded without Inference hooks inspection because a verdict could not be obtained and the organization's Inference hooks configuration is set to fail open.

  - `"inference_hooks_signing_secret_generated"`

    A request signing secret was generated for the organization's
    Inference hooks configuration.

  - `"integration_user_connected"`

    User connected to an integration.

  - `"integration_user_disconnected"`

    User disconnected from an integration.

  - `"invoice_collection_method_updated"`

    Invoice collection method was changed.

  - `"lti_launch_initiated"`

    LTI launch was initiated.

  - `"lti_launch_success"`

    LTI launch completed successfully.

  - `"lti_platform_created"`

    Anthropic staff created an LTI platform integration on behalf of an org.

  - `"lti_platform_updated"`

    Anthropic staff updated an LTI platform integration on behalf of an org.

  - `"magic_link_login_failed"`

    A magic link sign-in attempt failed.

  - `"magic_link_login_initiated"`

    A user requested a magic link sign-in email.

  - `"magic_link_login_succeeded"`

    A user successfully signed in with a magic link email.

  - `"managed_organization_setup_completed"`

    Managed (AWS Marketplace) organization setup was completed.

  - `"marketplace_created"`

    Admin created an organization marketplace.

  - `"marketplace_deleted"`

    Admin deleted an organization marketplace.

  - `"marketplace_updated"`

    Admin updated an organization marketplace.

  - `"marketplace_webhook_deleted"`

    Admin removed the GitHub push webhook for a marketplace.

  - `"marketplace_webhook_provisioned"`

    Admin provisioned a GitHub push webhook for a marketplace.

  - `"mcp_directory_server_published"`

    The organization published its approved MCP directory listing.

  - `"mcp_server_created"`

    An MCP server was added to the organization.

  - `"mcp_server_deleted"`

    An MCP server was removed from the organization.

  - `"mcp_server_managed_auth_token_exchanged"`

    A user attempted to obtain an access token for an MCP server via enterprise managed authorization. This event reports the outcomes of attempted token exchanges. Repeated failures with the same cause may be reported once until the cause changes, and requests denied by organization policy before a token exchange is attempted are not reported, with the exception of the "connector_scope_not_granted" failures described under error_type.

  - `"mcp_server_managed_auth_updated"`

    An MCP server's enterprise managed authorization settings were set, changed, or cleared, including when they were supplied while the server was being added or edited. Fields without a "previous_" prefix describe the settings after the change and are null when the server has no managed authorization settings afterwards; "previous_" fields describe the settings before the change and are null when the server had none before (always the case for a newly added server).

  - `"mcp_server_updated"`

    An MCP server's configuration was updated.

  - `"mcp_tool_policy_updated"`

    The permission restriction for an MCP tool was set or cleared.

  - `"org_analytics_api_capability_updated"`

    Organization analytics_api capability was enabled or disabled.

  - `"org_bulk_delete_initiated"`

    Organization bulk deletion was initiated.

  - `"org_capability_grant_added"`

    A capability grant was added to a workspace or role.

  - `"org_capability_grant_removed"`

    A capability grant was removed from a workspace or role.

  - `"org_claude_code_data_sharing_disabled"`

    Organization Claude Code data sharing was disabled.

  - `"org_claude_code_data_sharing_enabled"`

    Organization Claude Code data sharing was enabled.

  - `"org_claude_code_desktop_disabled"`

    Organization Claude Code Desktop was disabled.

  - `"org_claude_code_desktop_enabled"`

    Organization Claude Code Desktop was enabled.

  - `"org_claude_code_zero_data_retention_disabled"`

    A primary owner disabled zero data retention for Claude Code, so Claude
    Code content is retained according to the organization's data retention
    settings.

  - `"org_compliance_api_settings_updated"`

    Organization compliance API settings were updated.

  - `"org_connector_domain_guard_updated"`

    Enterprise admin changed whether connectors are restricted to verified domains.

  - `"org_cowork_act_without_asking_mode_disabled"`

    The "Act without asking" mode in Cowork was disabled for the organization, so members can no longer let Claude act without asking for approval.

  - `"org_cowork_act_without_asking_mode_enabled"`

    The "Act without asking" mode in Cowork was enabled for the organization, allowing members to let Claude act without asking for approval.

  - `"org_cowork_agent_disabled"`

    Organization Cowork Agent was disabled.

  - `"org_cowork_agent_enabled"`

    Organization Cowork Agent was enabled.

  - `"org_cowork_auto_mode_disabled"`

    The "Auto" permission mode in Cowork was disabled for the organization, so members can no longer let Claude approve its own actions after a safety check.

  - `"org_cowork_auto_mode_enabled"`

    The "Auto" permission mode in Cowork was enabled for the organization, allowing members to let Claude approve its own actions after a safety check.

  - `"org_cowork_disabled"`

    Organization cowork was disabled.

  - `"org_cowork_enabled"`

    Organization cowork was enabled.

  - `"org_cowork_mcp_always_allow_disabled"`

    The "Always allow" option for connector tools in Cowork was disabled for the organization, so each use of a connector tool that can make changes requires approval. Read-only connector tools are not affected by this setting.

  - `"org_cowork_mcp_always_allow_enabled"`

    The "Always allow" option for connector tools in Cowork was enabled for the organization, letting members approve a connector tool that can make changes once and allow its later uses automatically. Read-only connector tools are not affected by this setting.

  - `"org_cowork_otlp_settings_updated"`

    The organization's Cowork OpenTelemetry monitoring export settings were updated.

  - `"org_cowork_remote_disabled"`

    Running Cowork in the cloud was disabled for the organization, so members can no longer run Cowork sessions in Anthropic-hosted remote environments.

  - `"org_cowork_remote_enabled"`

    Running Cowork in the cloud was enabled for the organization, allowing members to run Cowork sessions in Anthropic-hosted remote environments.

  - `"org_creation_blocked"`

    Organization creation was blocked.

  - `"org_data_export_accessed"`

    Organization data export file was accessed/downloaded via signed URL.

  - `"org_data_export_completed"`

    Organization data export was completed.

  - `"org_data_export_started"`

    Organization data export was started.

  - `"org_data_residency_updated"`

    The organization's inference data residency settings were updated.

  - `"org_deleted_via_bulk"`

    Organization was deleted via bulk operation.

  - `"org_deletion_requested"`

    Organization deletion was requested.

  - `"org_directory_resync_completed"`

    Organization directory resync completed successfully.

  - `"org_directory_resync_failed"`

    Organization directory resync failed.

  - `"org_directory_resync_started"`

    Organization directory resync was started asynchronously.

  - `"org_directory_sync_activated"`

    Organization directory sync was activated.

  - `"org_directory_sync_add_initiated"`

    Organization directory sync setup was initiated.

  - `"org_directory_sync_deleted"`

    Organization directory sync was deleted.

  - `"org_discoverability_disabled"`

    Admin disabled organization discoverability.

  - `"org_discoverability_enabled"`

    Admin enabled organization discoverability.

  - `"org_discoverability_settings_updated"`

    Admin updated organization discoverability settings.

  - `"org_domain_add_initiated"`

    Organization domain verification was initiated.

  - `"org_domain_removed"`

    Organization domain was removed.

  - `"org_domain_verified"`

    Organization domain was verified.

  - `"org_external_key_created"`

    A CMEK external key config was created.

  - `"org_external_key_deleted"`

    A CMEK external key config was deleted.

  - `"org_external_key_updated"`

    A CMEK external key config was updated.

  - `"org_external_key_validated"`

    A CMEK external key config was validated against the customer's KMS.

  - `"org_hipaa_self_serve_enabled"`

    A primary owner click-accepted the BAA and enabled HIPAA protections
    for the organization via the self-serve flow.

  - `"org_invite_link_disabled"`

    Organization invite link was disabled.

  - `"org_invite_link_generated"`

    Organization invite link was generated.

  - `"org_invite_link_regenerated"`

    Organization invite link was regenerated (previous link invalidated).

  - `"org_invite_viewed"`

    An organization invite was viewed.

  - `"org_invites_listed"`

    Organization invites were listed.

  - `"org_ip_restriction_created"`

    Organization IP restriction was created.

  - `"org_ip_restriction_deleted"`

    Organization IP restriction was deleted.

  - `"org_ip_restriction_updated"`

    Organization IP restriction was updated.

  - `"org_join_proposal_decided"`

    Approve or reject decision on a parent-org join proposal.

  - `"org_join_request_approved"`

    Admin approved a join request.

  - `"org_join_request_created"`

    User requested to join an organization.

  - `"org_join_request_dismissed"`

    Admin dismissed a join request.

  - `"org_join_request_instant_approved"`

    Join request was instantly approved.

  - `"org_join_requests_bulk_dismissed"`

    Admin bulk-dismissed join requests.

  - `"org_magic_link_second_factor_toggled"`

    Organization magic link second factor was toggled.

  - `"org_member_invites_disabled"`

    Admin disabled member invites for the organization.

  - `"org_member_invites_enabled"`

    Admin enabled member invites for the organization.

  - `"org_members_exported"`

    Organization members list was exported as CSV.

  - `"org_model_default_updated"`

    An organization or role default model setting was changed by an administrator.

  - `"org_parent_join_proposal_created"`

    Organization parent join proposal was created.

  - `"org_parent_search_performed"`

    Organization parent search was performed.

  - `"org_sso_add_initiated"`

    Organization SSO setup was initiated.

  - `"org_sso_connection_activated"`

    Organization SSO connection was activated.

  - `"org_sso_connection_deactivated"`

    Organization SSO connection was deactivated.

  - `"org_sso_connection_deleted"`

    Organization SSO connection was deleted.

  - `"org_sso_group_role_mappings_updated"`

    Organization SSO group role mappings were updated.

  - `"org_sso_provisioning_mode_changed"`

    Organization SSO provisioning mode was changed.

  - `"org_sso_scim_welcome_email_toggled"`

    Organization SCIM-provisioned welcome email was toggled.

  - `"org_sso_seat_tier_assignment_toggled"`

    Organization SSO seat tier assignment was toggled.

  - `"org_sso_seat_tier_mappings_updated"`

    Organization SSO seat tier mappings were updated.

  - `"org_sso_toggled"`

    Organization SSO was toggled on or off.

  - `"org_sync_deleting_synchronized_files_started"`

    Organization started deleting synchronized files.

  - `"org_sync_synchronized_files_deleted"`

    Organization synchronized files were deleted.

  - `"org_taint_added"`

    A taint was added to an organization.

  - `"org_taint_removed"`

    A taint was removed from an organization.

  - `"org_user_deleted"`

    User was removed from organization.

  - `"org_user_invite_accepted"`

    Organization user invite was accepted.

  - `"org_user_invite_deleted"`

    Organization user invite was deleted.

  - `"org_user_invite_re_sent"`

    Organization user invite was re-sent.

  - `"org_user_invite_rejected"`

    Organization user invite was rejected.

  - `"org_user_invite_sent"`

    Organization user invite was sent.

  - `"org_user_left"`

    User removed themselves from organization.

  - `"org_user_trusted_devices_revoked"`

    An organization admin revoked a member's trusted devices and signed the member out of all active sessions.

  - `"org_user_viewed"`

    An organization user was viewed.

  - `"org_users_listed"`

    Organization users were listed.

  - `"org_work_across_apps_disabled"`

    The organization's "Let Claude work across apps" setting was turned off.

  - `"org_work_across_apps_enabled"`

    The organization's "Let Claude work across apps" setting was turned on.

  - `"organization_address_updated"`

    The organization's billing or shipping address was updated.

  - `"organization_icon_deleted"`

    Organization's custom icon deleted.

  - `"organization_icon_updated"`

    Organization's custom icon uploaded or replaced.

  - `"owned_projects_access_restored"`

    Access to owned projects was restored.

  - `"payment_method_updated"`

    The organization's default payment method was updated.

  - `"pending_share_created"`

    A pending share of a project or skill was created for an email address that is not yet an organization member.

  - `"pending_share_revoked"`

    A pending share of a project or skill was revoked before the invitee joined the organization.

  - `"phone_code_sent"`

    User requested a phone verification code.

  - `"phone_code_verified"`

    User successfully verified their phone code.

  - `"platform_agent_archived"`

    An agent was archived on the API platform.

  - `"platform_agent_created"`

    An agent was created on the API platform.

  - `"platform_agent_deleted"`

    An agent was deleted from the API platform.

  - `"platform_agent_deployment_archived"`

    An agent deployment was archived on the API platform.

  - `"platform_agent_deployment_created"`

    An agent deployment was created on the API platform.

  - `"platform_agent_deployment_deleted"`

    An agent deployment was deleted from the API platform.

  - `"platform_agent_deployment_paused"`

    An agent deployment was paused on the API platform.

  - `"platform_agent_deployment_run_triggered"`

    An agent deployment was run on demand on the API platform.

  - `"platform_agent_deployment_unpaused"`

    An agent deployment was resumed on the API platform.

  - `"platform_agent_deployment_updated"`

    An agent deployment was updated on the API platform.

  - `"platform_agent_session_archived"`

    An agent session was archived on the API platform.

  - `"platform_agent_session_created"`

    An agent session was created on the API platform.

  - `"platform_agent_session_deleted"`

    An agent session was deleted from the API platform.

  - `"platform_agent_session_resource_added"`

    A resource was attached to an agent session.

  - `"platform_agent_session_resource_deleted"`

    A resource attached to an agent session was removed.

  - `"platform_agent_session_resource_updated"`

    A resource attached to an agent session was updated.

  - `"platform_agent_session_thread_archived"`

    A thread within an agent session was archived.

  - `"platform_agent_session_updated"`

    An agent session was updated on the API platform.

  - `"platform_agent_updated"`

    An agent was updated on the API platform.

  - `"platform_api_key_created"`

    An API key was created.

  - `"platform_api_key_updated"`

    An API key was updated.

  - `"platform_app_attest_authentication"`

    An attested mobile device attempted to exchange an Apple App Attest assertion for Anthropic API credentials.

  - `"platform_billing_upgraded_to_prepaid"`

    The organization's API billing was upgraded to the prepaid plan.

  - `"platform_clearance_workspace_program_request_cleared"`

    A workspace's clearance program assignment was removed.

  - `"platform_clearance_workspace_program_request_set"`

    A workspace's clearance program assignment was created or updated.

  - `"platform_cost_report_viewed"`

    The cost report was viewed.

  - `"platform_dream_archived"`

    A Dream (asynchronous memory-consolidation job) was archived.

  - `"platform_dream_cancelled"`

    A Dream (asynchronous memory-consolidation job) was cancelled before it completed.

  - `"platform_dream_created"`

    A Dream (asynchronous memory-consolidation job) was created.

  - `"platform_federated_authentication"`

    A federated workload identity attempted to exchange an OIDC token for Anthropic API credentials.

  - `"platform_federation_issuer_archived"`

    An OIDC federation issuer was archived.

  - `"platform_federation_issuer_updated"`

    An OIDC federation issuer was updated.

  - `"platform_federation_rule_archived"`

    An OIDC federation rule was archived.

  - `"platform_federation_rule_updated"`

    An OIDC federation rule was updated.

  - `"platform_federation_rule_workspace_added"`

    A federation rule was enabled for a workspace.

  - `"platform_federation_rule_workspace_removed"`

    A federation rule was disabled for a workspace.

  - `"platform_file_content_downloaded"`

    Activity logged when file content is downloaded via GET /v1/files/{file_id}/content.

  - `"platform_file_deleted"`

    Activity logged when a file is deleted via DELETE /v1/files/{file_id}.

  - `"platform_file_uploaded"`

    Activity logged when a file is uploaded via POST /v1/files.

  - `"platform_memory_created"`

    An agent memory document was created.

  - `"platform_memory_deleted"`

    An agent memory document was deleted.

  - `"platform_memory_store_archived"`

    An agent memory store was archived. Archived stores reject new memory writes and cannot be attached to new sessions; deletion and redaction remain permitted for privacy scrubbing.

  - `"platform_memory_store_created"`

    An agent memory store was created.

  - `"platform_memory_store_deleted"`

    An agent memory store was deleted. Memory content removal may complete asynchronously for very large stores.

  - `"platform_memory_store_updated"`

    An agent memory store's name, description, or metadata was updated.

  - `"platform_memory_updated"`

    An agent memory document's content or path was updated.

  - `"platform_memory_version_redacted"`

    A historical version of an agent memory document was redacted. Redaction scrubs the stored content of a specific version while preserving the version's existence in the history.

  - `"platform_oauth_app_created"`

    An OAuth app was created.

  - `"platform_oauth_app_revoked"`

    An OAuth app was revoked.

  - `"platform_oauth_app_updated"`

    An OAuth app was updated.

  - `"platform_plugin_directory_submission_created"`

    A plugin directory submission was created on the API platform. A plugin directory submission is a request to list a plugin in the public plugin directory.

  - `"platform_plugin_directory_submission_deleted"`

    A plugin directory submission was deleted on the API platform.

  - `"platform_plugin_directory_submission_updated"`

    A plugin directory submission was updated on the API platform.

  - `"platform_service_account_archived"`

    A service account was archived.

  - `"platform_service_account_updated"`

    A service account was updated.

  - `"platform_service_account_workspace_member_added"`

    A service account was added as a member of a workspace.

  - `"platform_service_account_workspace_member_removed"`

    A service account was removed from a workspace.

  - `"platform_service_account_workspace_member_updated"`

    A service account's workspace membership role was updated.

  - `"platform_signing_key_created"`

    Activity logged when a new request-signing key is registered for the org.

  - `"platform_signing_key_deleted"`

    Activity logged when a signing key is permanently deleted.

  - `"platform_signing_key_rotated"`

    Activity logged when an in-memory signing key is rotated.

  - `"platform_skill_version_created"`

    Activity logged when a skill version is created via POST /v1/skills/{skill_id}/versions.

  - `"platform_skill_version_deleted"`

    Activity logged when a skill version is deleted via DELETE /v1/skills/{skill_id}/versions/{version}.

  - `"platform_spend_limit_alert_emails_updated"`

    Spend limit alert email addresses and role targets were updated for an org.

  - `"platform_spend_limit_created"`

    An org-level fixed-dollar spend limit was created.

  - `"platform_spend_limit_deleted"`

    An org-level spend limit was removed.

  - `"platform_spend_limit_updated"`

    An org-level spend limit snooze/ignore state was changed.

  - `"platform_usage_report_claude_code_viewed"`

    The Claude Code usage report was viewed.

  - `"platform_usage_report_messages_viewed"`

    The messages usage report was viewed.

  - `"platform_workspace_archived"`

    A workspace was archived.

  - `"platform_workspace_created"`

    A workspace was created.

  - `"platform_workspace_inference_data_retention_disabled"`

    The zero data retention override was disabled for a workspace.

  - `"platform_workspace_inference_data_retention_enabled"`

    The zero data retention override was enabled for a workspace.

  - `"platform_workspace_member_added"`

    A member was added to a workspace.

  - `"platform_workspace_member_removed"`

    A member was removed from a workspace.

  - `"platform_workspace_member_updated"`

    A workspace member was updated.

  - `"platform_workspace_member_viewed"`

    A workspace member was viewed.

  - `"platform_workspace_members_listed"`

    Workspace members were listed.

  - `"platform_workspace_rate_limit_deleted"`

    A workspace rate limit was deleted.

  - `"platform_workspace_rate_limit_updated"`

    A workspace rate limit was created or updated.

  - `"platform_workspace_updated"`

    A workspace was updated.

  - `"plugin_installation_preference_updated"`

    An org admin changed the installation preference for a plugin.

  - `"prepaid_auto_recharge_disabled"`

    Auto-recharge was disabled for API prepaid org.

  - `"prepaid_auto_recharge_updated"`

    Auto-recharge settings were updated for API prepaid org.

  - `"prepaid_extra_usage_auto_reload_disabled"`

    Prepaid usage credit auto-reload was disabled.

  - `"prepaid_extra_usage_auto_reload_enabled"`

    Prepaid usage credit auto-reload was enabled.

  - `"prepaid_extra_usage_auto_reload_settings_updated"`

    Prepaid usage credit auto-reload settings were updated.

  - `"primary_owner_transferred"`

    Primary owner role was transferred to another org member.

  - `"rbac_role_assigned"`

    Admin assigned an RBAC custom role to a principal.

  - `"rbac_role_created"`

    Admin created an RBAC custom role.

  - `"rbac_role_deleted"`

    Admin deleted an RBAC custom role.

  - `"rbac_role_permission_added"`

    Admin added a permission to an RBAC custom role.

    Emitted once per requested permission, including permissions the role
    already had, so a retried request still produces a complete audit record.

  - `"rbac_role_permission_removed"`

    Admin removed a permission from an RBAC custom role.

    Emitted once per requested permission, including permissions the role
    already lacked, so a retried request still produces a complete audit
    record.

  - `"rbac_role_unassigned"`

    Admin unassigned an RBAC custom role from a principal.

  - `"rbac_role_updated"`

    Admin updated an RBAC custom role.

  - `"role_assignment_granted"`

    Role assignment was granted.

  - `"role_assignment_revoked"`

    Role assignment was revoked.

  - `"scim_user_created"`

    A SCIM user was provisioned.

  - `"scim_user_deleted"`

    A SCIM user was deleted.

  - `"scim_user_updated"`

    A SCIM user was updated.

  - `"scoped_api_key_deleted"`

    A scoped API key was deleted.

  - `"scoped_api_key_updated"`

    A scoped API key was renamed or its activation state changed.

  - `"seat_tier_changes_cancelled"`

    Scheduled seat tier downgrades were cancelled.

  - `"seat_tiers_purchased"`

    Seat tiers were purchased or upgraded on a subscription.

  - `"service_created"`

    Activity logged when an org service is explicitly created.

  - `"service_deleted"`

    Activity logged when an org service is deleted.

  - `"service_key_created"`

    Activity logged when a new org service key is created.

  - `"service_key_revoked"`

    Activity logged when an org service key is revoked.

  - `"session_revoked"`

    User revoked a specific session.

  - `"session_share_accessed"`

    Session share was accessed.

  - `"session_share_created"`

    Session share was created.

  - `"session_share_revoked"`

    Session share was revoked.

  - `"slack_workspace_claim_revoked"`

    A Slack workspace or Enterprise Grid organization was disconnected
    from the organization for Claude in Slack.

  - `"slack_workspace_claimed"`

    A Slack workspace or Enterprise Grid organization was connected to
    the organization for Claude in Slack.

  - `"social_login_succeeded"`

    A user successfully signed in with a social identity provider (Google, Apple, or Microsoft).

  - `"sso_login_failed"`

    An SSO sign-in attempt failed.

  - `"sso_login_initiated"`

    A user started an SSO sign-in flow.

  - `"sso_login_succeeded"`

    A user successfully signed in with SSO.

  - `"sso_second_factor_magic_link"`

    SSO second factor magic link was used.

  - `"step_up_authentication_failed"`

    An additional identity check failed.

  - `"step_up_authentication_succeeded"`

    The user completed an additional identity check to confirm a sensitive action.

  - `"step_up_credential_enrolled"`

    A user enrolled a passkey for confirming sensitive actions on their account.

  - `"subscription_cancellation_scheduled"`

    Subscription cancellation was scheduled at end of billing period.

  - `"subscription_quantity_updated"`

    Contracted subscription seat quantity was updated.

  - `"subscription_renewed"`

    A cancelled subscription was renewed.

  - `"subscription_resumed"`

    A scheduled subscription cancellation was reversed.

  - `"subscription_started"`

    A new subscription was created (Team or Enterprise).

  - `"subscription_upgraded"`

    Subscription plan was upgraded (e.g. Team to Enterprise).

  - `"trusted_device_credential_rotated"`

    The identity-verification credential of a trusted device was rotated to a new key.

  - `"trusted_device_enrolled"`

    A device was enrolled as a trusted device for the user's account. Trusted devices can be used to confirm the user's identity for sensitive actions.

  - `"trusted_device_revoked"`

    A trusted device was removed from the user's account.

  - `"tunnel_archived"`

    An MCP tunnel was archived.

  - `"tunnel_certificate_added"`

    An inner-TLS CA certificate was added to a tunnel.

  - `"tunnel_certificate_revoked"`

    An inner-TLS CA certificate was revoked from a tunnel.

  - `"tunnel_created"`

    An MCP tunnel was created.

  - `"tunnel_token_minted"`

    An OAuth bearer token for the tunnel management API was minted.

  - `"tunnel_token_revealed"`

    The Cloudflare connector secret for a tunnel was revealed to the caller.

  - `"tunnel_token_revoked"`

    An OAuth bearer token for the tunnel management API was revoked.

  - `"tunnel_token_rotated"`

    The Cloudflare connector secret for a tunnel was rotated.

    `tunnel_token_id` is the id of the *newly-issued* token. The previous
    token is invalidated by the rotation and its id is not recorded here.

  - `"user_consent_recorded"`

    User granted a consent for a specific entity (e.g. consumer health consent for an MCP server).

  - `"user_consent_revoked"`

    User revoked a previously granted consent for a specific entity.

  - `"user_logged_out"`

    A user signed out of one or all sessions.

  - `"verification_evidence_submitted"`

    Verification evidence was submitted for an organization's verification.

  - `"verification_program_application_created"`

    An organization applied to a verification program.

  - `"workspace_member_spend_limit_created"`

    A per-member or workspace-default Claude Code spend limit was created.

  - `"workspace_member_spend_limit_deleted"`

    A per-member or workspace-default Claude Code spend limit was deleted.

  - `"workspace_member_spend_limit_updated"`

    A per-member Claude Code spend limit amount was updated.

  - `"workspace_spend_limit_alert_emails_updated"`

    Spend limit alert email recipients were updated for a workspace.

  - `"workspace_spend_limit_created"`

    A workspace-level API spend limit was created.

  - `"workspace_spend_limit_deleted"`

    A workspace-level API spend limit was deleted.

- `limit: optional number`

  Maximum results (default: 100, max: 5000)

  default: 100, maximum: 5000, minimum: 1

- `order: optional "asc" or "desc"`

  Sort direction by `created_at`. `desc` (default) returns newest-first; `asc` returns oldest-first for incremental sync. Activities become queryable after a short asynchronous ingestion delay. When using `asc` with `after_id` for incremental sync, late-arriving rows with timestamps behind the cursor will be skipped; consumers that need at-least-once delivery should periodically re-poll an overlap window via `created_at.gte` and deduplicate by `id`. `after_id` and `before_id` are relative to this order.

  default: desc

  - `"asc"`

  - `"desc"`

- `organization_ids: optional array of string`

  Filter activities by organization IDs (accepts `org_...` or organization UUID). Enumerate IDs via `GET /v1/compliance/organizations`.

- `user_ids: optional array of string`

  Alias for `actor_ids[]`, for consistency with other compliance routes. If both are provided, the lists are merged.

## Headers

- `"x-api-key": optional string`

<!-- snapshot truncated at '## Returns' by scripts/snapshot_spec.py:
     the omitted section is the per-activity-type response schema
     (~3 MB), which the SDK does not model. See activity-types.txt
     for the diffable list of type names. -->
