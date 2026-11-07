# Strata Cloud Manager (SCM) API — endpoint catalogue

Reference of **every endpoint published in the SCM OpenAPI specs**, and whether the
`PaloAltoNetworks/scm` Terraform provider can manage it. Use it to decide *how* (or *if*)
something can be automated in this project.

| | |
|---|---|
| Source | OpenAPI specs in [PaloAltoNetworks/pan.dev](https://github.com/PaloAltoNetworks/pan.dev/tree/master/openapi-specs/scm) @ `99309c720132` (2026-11-06) |
| Terraform provider | `PaloAltoNetworks/scm` v1.0.13 — 137 resources |
| Size | 1190 operations, 378 endpoints, 36 API groups |
| Terraform coverage | 129 endpoints map to 129 Terraform resources |
| Machine-readable | [`scm_api_endpoints.json`](scm_api_endpoints.json) — one entry per operation, with summary |

> This file is a snapshot. Endpoints added after the source date are not listed. Anything
> **not** listed here is not available through the public SCM API as of that date.

## How to read this

- **Hosts** — config APIs live on `https://api.strata.paloaltonetworks.com` (the older alias
  `api.sase.paloaltonetworks.com` also works). OAuth2 tokens come from
  `https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token` with scope `tsg_id:<TSG>`.
- **Products** — `NGFW` = firewalls managed by SCM, `PA` = Prisma Access, `CNGFW` = Cloud NGFW,
  `Platform` = tenant / IAM / subscription APIs; `Posture`, `TLS`, `Add-on` = separately licensed products.
- **Operations** — `list` / `create` act on the endpoint path; `get by id` / `update` / `delete` on
  `<path>/{id}`; `action` = a one-off operation (`:push`, `:move`, `:load` …).
  Config objects are always scoped with `?folder=`, `?snippet=` or `?device=`.
- **Terraform** — `scm_<name>` means manage it with Terraform (the default here). `—` means
  **API only**: it needs a script (or the SCM UI) and is not tracked in Terraform state.
- Writes to config endpoints change the **candidate** config only. Nothing reaches devices until
  a push (`/config/operations/v1/config-versions/candidate:push`), which per `CLAUDE.md` only the
  repo owner performs.

## Summary by API group

| API group | Base path | Products | Endpoints | Terraform-managed |
|---|---|---|---:|---:|
| [Application Tags](#application-tags) | `/config/objects/v1` | CNGFW, NGFW, PA | 2 | 0 |
| [Config Operations](#config-operations) | `/config/operations/v1` | CNGFW, NGFW, PA | 7 | 0 |
| [Configuration Setup](#configuration-setup) | `/config/setup/v1` | CNGFW, NGFW, PA | 21 | 4 |
| [Device Onboarding](#device-onboarding) | `/config/setup/device-onboarding/v1` | CNGFW, NGFW, PA | 5 | 0 |
| [Device Settings](#device-settings) | `/config/device/v1` | NGFW | 30 | 13 |
| [GlobalProtect](#globalprotect) | `/config/mobile-agent/v1` | PA | 14 | 5 |
| [Identity Services](#identity-services) | `/config/identity/v1` | CNGFW, NGFW, PA | 21 | 15 |
| [Logical Routers](#logical-routers) | `/config/network/v1` | NGFW, PA | 1 | 1 |
| [Network Deployment](#network-deployment) | `/config/deployment/v1` | PA | 13 | 8 |
| [Network Services](#network-services) | `/config/network/v1` | NGFW, PA | 55 | 46 |
| [Objects](#objects) | `/config/objects/v1` | CNGFW, NGFW, PA | 21 | 17 |
| [Security Services](#security-services) | `/config/security/v1` | CNGFW, NGFW, PA | 27 | 20 |
| [VR Routing Profiles](#vr-routing-profiles) | `/config/network/v1` | NGFW, PA | 6 | 0 |
| [Virtual Routers](#virtual-routers) | `/config/network/v1` | NGFW, PA | 1 | 0 |
| [Access Policies](#access-policies) | `/iam/v1` | Platform | 1 | 0 |
| [Authentication Service API](#authentication-service-api) | `/auth/v1` | Platform | 2 | 0 |
| [Custom Roles](#custom-roles) | `/iam/v1` | Platform | 1 | 0 |
| [Instances](#instances) | `/subscription/v1` | Platform | 1 | 0 |
| [Licenses](#licenses) | `/subscription/v1` | Platform | 1 | 0 |
| [Permission Sets](#permission-sets) | `/iam/v1` | Platform | 1 | 0 |
| [Permissions](#permissions) | `/iam/v1` | Platform | 1 | 0 |
| [Roles](#roles) | `/iam/v1` | Platform | 1 | 0 |
| [Service Accounts](#service-accounts) | `/iam/v1` | Platform | 2 | 0 |
| [Tenant Service Group](#tenant-service-group) | `/tenancy/v1` | Platform | 3 | 0 |
| [User Accounts](#user-accounts) | `/iam/v1` | Platform | 1 | 0 |
| [Advanced DNS Security Resolver Configuration](#advanced-dns-security-resolver-configuration) | `/adns-resolver/v1` | Add-on, CNGFW, NGFW, PA | 15 | 0 |
| [CIE - Cloud Dynamic User Group CRUD Operations APIs Mounted on Strata Cloud Manager](#cie---cloud-dynamic-user-group-crud-operations-apis-mounted-on-strata-cloud-manager) | `/directory-sync/v1` | Add-on | 4 | 0 |
| [CIE Directory Sync Service APIs Mounted on Strata Cloud Manager](#cie-directory-sync-service-apis-mounted-on-strata-cloud-manager) | `/cie/directory-sync/v1` | Add-on | 4 | 0 |
| [Compliance Center API](#compliance-center-api) | `/posture/compliance-frameworks/v1` | Posture | 11 | 0 |
| [Config Cleanup API](#config-cleanup-api) | `/posture/config-cleanup/v1` | Posture | 1 | 0 |
| [Operations and Troubleshooting](#operations-and-troubleshooting) | `/operations/v1` | NGFW | 10 | 0 |
| [Policy Optimizer API](#policy-optimizer-api) | `/posture/policy-optimizer/v1` | Posture | 1 | 0 |
| [Posture Check Upload Initiation API](#posture-check-upload-initiation-api) | `/posture/checks/v1` | Posture | 9 | 0 |
| [Secure Agentless Access (SAA) Configuration](#secure-agentless-access-saa-configuration) | `/secure-agentless-access/v1` | Add-on | 8 | 0 |
| [TLS Protect Cloud API for Strata Cloud Manager](#tls-protect-cloud-api-for-strata-cloud-manager) | `/ngts` | TLS | 74 | 0 |
| [Unified Incident Framework APIs](#unified-incident-framework-apis) | `/incidents/v1` | Add-on | 2 | 0 |

## What we can and cannot do

### ✅ Manageable with Terraform

Every endpoint with a `scm_*` resource in the tables below: objects, security / NAT / decryption
policy, security profiles, network (interfaces, zones, routing, IKE / IPsec), identity, device
settings, folders / snippets / labels / variables, and Prisma Access deployment (remote networks,
service connections, bandwidth). This is the default way to make changes in this project.

### ⚠️ API only — needs a script (ask before writing one)

Notable endpoints that can be called but **cannot** be managed with Terraform:

- `/config/operations/v1/config-versions/candidate:push` — push candidate config to devices / Prisma Access — **owner only, never automated by Claude**
- `/config/operations/v1/config-versions/candidate` — revert (delete) the candidate config
- `/config/operations/v1/config-versions:load` — load a previous config version
- `/config/operations/v1/jobs` — track push / commit jobs
- `/config/setup/v1/devices` — device inventory (read / update device attributes)
- `/config/identity/v1/certificates` — certificates (also `:import` / `:export`)
- `/config/setup/v1/snippet-snapshots` — snippet snapshots (publish, diff, compare, load)
- `/config/device/v1/software-upgrade-rules` — PAN-OS software upgrade rules and schedules
- `/config/device/v1/ha-configurations` — high-availability configuration
- `/config/network/v1/virtual-routers` — legacy virtual routers (Terraform has `scm_logical_router`)
- `/config/network/v1/gre-tunnels` — GRE tunnels
- `/config/mobile-agent/v1/agent-profiles` — GlobalProtect app profiles (also tunnel profiles, infrastructure settings)
- `/config/setup/device-onboarding/v1/onboarding-rules` — zero-touch device onboarding rules
- `/operations/v1/jobs/route-table` — live troubleshooting jobs (route / FIB tables, interfaces …)

The platform APIs (IAM roles and service accounts, tenant service groups, subscriptions and
licences), posture management, Advanced DNS Security, TLS Protect, CIE and Secure Agentless
Access are also **API only**.

### ❌ Not possible or out of bounds

- Anything not listed in this file: the public API does not expose it.
- Add-on APIs (TLS Protect, Advanced DNS Security, CIE, SAA, posture) only work if the tenant
  has that licence. Check the Subscription APIs first.
- Every call is limited by the **role of the service account**. A missing permission returns
  `403`, whatever this catalogue says.
- The Terraform ZTNA Connector resources (`scm_ztna_*`) use a separate ZTNA API (`ztna_host`,
  `x_panw_region`) that is not part of these specs.

## Endpoints by API group

### Application Tags

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/objects/v1/application-tags` | list, create, update, delete, get by id | — |
| `/config/objects/v1/application-tags/bulk` | create | — |

### Config Operations

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/operations/v1/config-versions` | list, get by id | — |
| `/config/operations/v1/config-versions/candidate` | delete | — |
| `/config/operations/v1/config-versions/candidate:push` | action (POST) | — |
| `/config/operations/v1/config-versions/running` | list | — |
| `/config/operations/v1/config-versions:load` | action (POST) | — |
| `/config/operations/v1/config-versions:push` | action (POST) | — |
| `/config/operations/v1/jobs` | list, get by id | — |

### Configuration Setup

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/setup/v1/devices` | list, get by id, update | — |
| `/config/setup/v1/folders` | list, create, get by id, update, delete | `scm_folder` |
| `/config/setup/v1/labels` | list, create, get by id, update, delete | `scm_label` |
| `/config/setup/v1/shared-snippets` | list, update | — |
| `/config/setup/v1/shared-snippets:load` | action (POST) | — |
| `/config/setup/v1/snippet-audit-logs` | create, get by id | — |
| `/config/setup/v1/snippet-categories` | list, get by id, delete | — |
| `/config/setup/v1/snippet-snapshots` | create | — |
| `/config/setup/v1/snippet-snapshots:compare` | action (POST) | — |
| `/config/setup/v1/snippet-snapshots:convert` | action (POST) | — |
| `/config/setup/v1/snippet-snapshots:diff` | action (POST) | — |
| `/config/setup/v1/snippet-snapshots:load` | action (POST) | — |
| `/config/setup/v1/snippet-snapshots:publish` | action (POST) | — |
| `/config/setup/v1/snippet-snapshots:updates` | action (POST) | — |
| `/config/setup/v1/snippets` | list, create, get by id, update, delete | `scm_snippet` |
| `/config/setup/v1/subscribed-tenants` | create, update, delete, get by id | — |
| `/config/setup/v1/trust-validations` | create | — |
| `/config/setup/v1/trusted-tenant-overview` | list | — |
| `/config/setup/v1/trusted-tenants` | list | — |
| `/config/setup/v1/trusts` | create, delete | — |
| `/config/setup/v1/variables` | list, create, get by id, update, delete | `scm_variable` |

### Device Onboarding

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/setup/device-onboarding/v1/onboarding-rules` | list, create, get by id, update, delete | — |
| `/config/setup/device-onboarding/v1/onboarding-rules/{id}:move` | action (POST) | — |
| `/config/setup/device-onboarding/v1/properties` | list, create, get by id, update, delete | — |
| `/config/setup/device-onboarding/v1/site-groups` | list, create, get by id, update, delete | — |
| `/config/setup/device-onboarding/v1/sites` | list, create, get by id, update, delete | — |

### Device Settings

Host: `api.strata.paloaltonetworks.com` · Products: NGFW

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/device/v1/authentication-settings` | list, create, get by id, update, delete | `scm_authentication_setting` |
| `/config/device/v1/autoscale` | list, create, update, delete | — |
| `/config/device/v1/content-cloud-settings` | list, create, get by id, update, delete | — |
| `/config/device/v1/content-id-settings` | list, create, get by id, update, delete | `scm_content_id_setting` |
| `/config/device/v1/device-context-segment-association` | list, create, delete, get by id, update | — |
| `/config/device/v1/device-redistribution-collector` | list, create, get by id, update, delete | `scm_device_redistribution_collector` |
| `/config/device/v1/general-settings` | list, create, get by id, update, delete | `scm_general_setting` |
| `/config/device/v1/ha-configurations` | list, create, update, delete | — |
| `/config/device/v1/ha-configurations-gateways` | list | — |
| `/config/device/v1/ha-configurations-ip-addresses` | list | — |
| `/config/device/v1/ha-configurations-netmasks` | list | — |
| `/config/device/v1/ha-configurations-ports` | list | — |
| `/config/device/v1/ha-devices` | list | — |
| `/config/device/v1/management-interface` | list, create, get by id, update, delete | `scm_management_interface` |
| `/config/device/v1/models` | list | — |
| `/config/device/v1/motd-banner-settings` | list, create, get by id, update, delete | `scm_motd_banner_setting` |
| `/config/device/v1/named-snapshots` | list, delete | — |
| `/config/device/v1/named-snapshots:load` | action (POST) | — |
| `/config/device/v1/service-route` | list, create, get by id, update, delete | `scm_service_route` |
| `/config/device/v1/service-settings` | list, create, get by id, update, delete | `scm_service_setting` |
| `/config/device/v1/session-settings` | list, create, get by id, update, delete | `scm_session_setting` |
| `/config/device/v1/session-timeouts` | list, create, get by id, update, delete | `scm_session_timeout` |
| `/config/device/v1/software-upgrade-match-criteria` | create | — |
| `/config/device/v1/software-upgrade-rules` | list, create, get by id, update, delete | — |
| `/config/device/v1/software-upgrade-schedules` | list, create, get by id, update, delete | — |
| `/config/device/v1/software-upgrade-status` | list | — |
| `/config/device/v1/software-versions` | list | — |
| `/config/device/v1/tcp-settings` | list, create, get by id, update, delete | `scm_tcp_setting` |
| `/config/device/v1/update-schedule` | list, create, get by id, update, delete | `scm_update_schedule` |
| `/config/device/v1/vpn-settings` | list, create, get by id, update, delete | `scm_vpn_setting` |

### GlobalProtect

Host: `api.strata.paloaltonetworks.com` · Products: PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/mobile-agent/v1/agent-profiles` | list, create, update, delete | — |
| `/config/mobile-agent/v1/agent-versions` | list | — |
| `/config/mobile-agent/v1/authentication-settings` | list, create, update, delete | — |
| `/config/mobile-agent/v1/authentication-settings/{name}:move` | action (POST) | — |
| `/config/mobile-agent/v1/enable` | list, create | — |
| `/config/mobile-agent/v1/forwarding-profile-destinations` | list, create, get by id, update, delete | `scm_forwarding_profile_destination` |
| `/config/mobile-agent/v1/forwarding-profile-regional-and-custom-proxies` | list, create, get by id, update, delete | `scm_forwarding_profile_regional_and_custom_proxy` |
| `/config/mobile-agent/v1/forwarding-profile-source-applications` | list, create, get by id, update, delete | `scm_forwarding_profile_source_application` |
| `/config/mobile-agent/v1/forwarding-profile-user-locations` | list, create, get by id, update, delete | `scm_forwarding_profile_user_location` |
| `/config/mobile-agent/v1/forwarding-profiles` | list, create, get by id, update, delete | `scm_forwarding_profile` |
| `/config/mobile-agent/v1/global-settings` | list, update | — |
| `/config/mobile-agent/v1/infrastructure-settings` | list, create, update, delete | — |
| `/config/mobile-agent/v1/locations` | list, update | — |
| `/config/mobile-agent/v1/tunnel-profiles` | list, create, update, delete | — |

### Identity Services

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/identity/v1/authentication-portals` | list, create, get by id, update, delete | `scm_authentication_portal` |
| `/config/identity/v1/authentication-profiles` | list, create, get by id, update, delete | `scm_authentication_profile` |
| `/config/identity/v1/authentication-rules` | list, create, get by id, update, delete | `scm_authentication_rule` |
| `/config/identity/v1/authentication-rules/{id}:move` | action (POST) | — |
| `/config/identity/v1/authentication-sequences` | list, create, get by id, update, delete | `scm_authentication_sequence` |
| `/config/identity/v1/certificate-profiles` | list, create, get by id, update, delete | `scm_certificate_profile` |
| `/config/identity/v1/certificates` | list, create, get by id, delete | — |
| `/config/identity/v1/certificates/{id}:export` | action (POST) | — |
| `/config/identity/v1/certificates:import` | action (POST) | — |
| `/config/identity/v1/kerberos-server-profiles` | list, create, get by id, update, delete | `scm_kerberos_server_profile` |
| `/config/identity/v1/ldap-server-profiles` | list, create, get by id, update, delete | `scm_ldap_server_profile` |
| `/config/identity/v1/local-user-groups` | list, create, get by id, update, delete | `scm_local_user_group` |
| `/config/identity/v1/local-users` | list, create, get by id, update, delete | `scm_local_user` |
| `/config/identity/v1/mfa-servers` | list, create, get by id, update, delete | `scm_mfa_server` |
| `/config/identity/v1/ocsp-responders` | list, create, get by id, update, delete | — |
| `/config/identity/v1/radius-server-profiles` | list, create, get by id, update, delete | `scm_radius_server_profile` |
| `/config/identity/v1/saml-server-profiles` | list, create, get by id, update, delete | `scm_saml_server_profile` |
| `/config/identity/v1/scep-profiles` | list, create, get by id, update, delete | `scm_scep_profile` |
| `/config/identity/v1/tacacs-server-profiles` | list, create, get by id, update, delete | `scm_tacacs_server_profile` |
| `/config/identity/v1/tls-service-profiles` | list, create, get by id, update, delete | `scm_tls_service_profile` |
| `/config/identity/v1/trusted-certificate-authorities` | list | — |

### Logical Routers

Host: `api.strata.paloaltonetworks.com` · Products: NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/network/v1/logical-routers` | list, create, get by id, update, delete | `scm_logical_router` |

### Network Deployment

Host: `api.strata.paloaltonetworks.com` · Products: PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/deployment/v1/bandwidth-allocations` | list, create, update, delete | `scm_bandwidth_allocation` |
| `/config/deployment/v1/bgp-routing` | list, update | `scm_bgp_routing` |
| `/config/deployment/v1/enable` | create | — |
| `/config/deployment/v1/internal-dns-servers` | list, create, get by id, update, delete | `scm_internal_dns_server` |
| `/config/deployment/v1/locations` | list | — |
| `/config/deployment/v1/remote-networks` | list, create, get by id, update, delete | `scm_remote_network` |
| `/config/deployment/v1/remote-networks:query` | action (POST) | — |
| `/config/deployment/v1/service-connection-groups` | list, create, get by id, update, delete | `scm_service_connection_group` |
| `/config/deployment/v1/service-connections` | list, create, get by id, update, delete | `scm_service_connection` |
| `/config/deployment/v1/shared-infrastructure-settings` | list, update | — |
| `/config/deployment/v1/sites` | list, create, get by id, update, delete | `scm_site` |
| `/config/deployment/v1/sites:query` | action (POST) | — |
| `/config/deployment/v1/traffic-steering-rules` | list, create, get by id, update, delete | `scm_traffic_steering_rule` |

### Network Services

Host: `api.strata.paloaltonetworks.com` · Products: NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/network/v1/aggregate-interfaces` | list, create, get by id, update, delete | `scm_aggregate_interface` |
| `/config/network/v1/auto-vpn-clusters` | list, create, get by id, update, delete | `scm_auto_vpn_cluster` |
| `/config/network/v1/auto-vpn-monitor` | list | — |
| `/config/network/v1/auto-vpn-push` | create | — |
| `/config/network/v1/auto-vpn-settings` | list, update | `scm_auto_vpn_setting` |
| `/config/network/v1/bgp-address-family-profiles` | list, create, get by id, update, delete | `scm_bgp_address_family_profile` |
| `/config/network/v1/bgp-auth-profiles` | list, create, get by id, update, delete | `scm_bgp_auth_profile` |
| `/config/network/v1/bgp-filtering-profiles` | list, create, get by id, update, delete | `scm_bgp_filtering_profile` |
| `/config/network/v1/bgp-redistribution-profiles` | list, create, get by id, update, delete | `scm_bgp_redistribution_profile` |
| `/config/network/v1/bgp-route-map-redistributions` | list, create, get by id, update, delete | `scm_bgp_route_map_redistribution` |
| `/config/network/v1/bgp-route-maps` | list, create, get by id, update, delete | `scm_bgp_route_map` |
| `/config/network/v1/config-match-list` | list, create, get by id, update, delete | `scm_config_match_list` |
| `/config/network/v1/dhcp-interfaces` | list, create, get by id, update, delete | `scm_dhcp_interface` |
| `/config/network/v1/dns-proxies` | list, create, get by id, update, delete | `scm_dns_proxy` |
| `/config/network/v1/ethernet-interfaces` | list, create, get by id, update, delete | `scm_ethernet_interface` |
| `/config/network/v1/globalprotect-match-list` | list, create, get by id, update, delete | `scm_globalprotect_match_list` |
| `/config/network/v1/gp-tunnel-settings` | list, create, update, delete | — |
| `/config/network/v1/gre-tunnels` | list, create, get by id, update, delete | — |
| `/config/network/v1/hipmatch-match-list` | list, create, get by id, update, delete | `scm_hipmatch_match_list` |
| `/config/network/v1/ike-crypto-profiles` | list, create, get by id, update, delete | `scm_ike_crypto_profile` |
| `/config/network/v1/ike-gateways` | list, create, get by id, update, delete | `scm_ike_gateway` |
| `/config/network/v1/ike-gateways:generate-ppk` | action (POST) | — |
| `/config/network/v1/interface-management-profiles` | list, create, get by id, update, delete | `scm_interface_management_profile` |
| `/config/network/v1/ipsec-crypto-profiles` | list, create, get by id, update, delete | `scm_ipsec_crypto_profile` |
| `/config/network/v1/ipsec-tunnels` | list, create, get by id, update, delete | `scm_ipsec_tunnel` |
| `/config/network/v1/iptag-match-list` | list, create, get by id, update, delete | `scm_iptag_match_list` |
| `/config/network/v1/layer2-subinterfaces` | list, create, get by id, update, delete | `scm_layer2_subinterface` |
| `/config/network/v1/layer3-subinterfaces` | list, create, get by id, update, delete | `scm_layer3_subinterface` |
| `/config/network/v1/link-tags` | list, create, get by id, update, delete | `scm_link_tag` |
| `/config/network/v1/lldp-profiles` | list, create, get by id, update, delete | `scm_lldp_profile` |
| `/config/network/v1/loopback-interfaces` | list, create, get by id, update, delete | `scm_loopback_interface` |
| `/config/network/v1/nat-rules` | list, create, get by id, update, delete | `scm_nat_rule` |
| `/config/network/v1/network_packet_broker_profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/network_packet_broker_rules` | list, create, get by id, update, delete | — |
| `/config/network/v1/ospf-auth-profiles` | list, create, get by id, update, delete | `scm_ospf_auth_profile` |
| `/config/network/v1/pbf-rules` | list, create, get by id, update, delete | `scm_pbf_rule` |
| `/config/network/v1/qos-policy-rules` | list, create, get by id, update, delete | `scm_qos_policy_rule` |
| `/config/network/v1/qos-policy-rules/{id}:move` | action (POST) | — |
| `/config/network/v1/qos-profiles` | list, create, get by id, update, delete | `scm_qos_profile` |
| `/config/network/v1/remote-networks-license-info` | list | — |
| `/config/network/v1/route-access-lists` | list, create, get by id, update, delete | `scm_route_access_list` |
| `/config/network/v1/route-community-lists` | list, create, get by id, update, delete | `scm_route_community_list` |
| `/config/network/v1/route-path-access-lists` | list, create, get by id, update, delete | `scm_route_path_access_list` |
| `/config/network/v1/route-prefix-lists` | list, create, get by id, update, delete | `scm_route_prefix_list` |
| `/config/network/v1/sdwan-error-correction-profiles` | list, create, get by id, update, delete | `scm_sdwan_error_correction_profile` |
| `/config/network/v1/sdwan-path-quality-profiles` | list, create, get by id, update, delete | `scm_sdwan_path_quality_profile` |
| `/config/network/v1/sdwan-rules` | list, create, get by id, update, delete | `scm_sdwan_rule` |
| `/config/network/v1/sdwan-saas-quality-profiles` | list, create, get by id, update, delete | `scm_sdwan_saas_quality_profile` |
| `/config/network/v1/sdwan-traffic-distribution-profiles` | list, create, get by id, update, delete | `scm_sdwan_traffic_distribution_profile` |
| `/config/network/v1/system-match-list` | list, create, get by id, update, delete | `scm_system_match_list` |
| `/config/network/v1/tunnel-interfaces` | list, create, get by id, update, delete | `scm_tunnel_interface` |
| `/config/network/v1/userid-match-list` | list, create, get by id, update, delete | `scm_userid_match_list` |
| `/config/network/v1/vlan-interfaces` | list, create, get by id, update, delete | `scm_vlan_interface` |
| `/config/network/v1/zone-protection-profiles` | list, create, get by id, update, delete | `scm_zone_protection_profile` |
| `/config/network/v1/zones` | list, create, get by id, update, delete | `scm_zone` |

### Objects

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/objects/v1/address-groups` | list, create, get by id, update, delete | `scm_address_group` |
| `/config/objects/v1/addresses` | list, create, get by id, update, delete | `scm_address` |
| `/config/objects/v1/advanced-device-objects` | list, create, update, delete, get by id | — |
| `/config/objects/v1/application-filters` | list, create, get by id, update, delete | `scm_application_filter` |
| `/config/objects/v1/application-groups` | list, create, get by id, update, delete | `scm_application_group` |
| `/config/objects/v1/applications` | list, create, get by id, update, delete | `scm_application` |
| `/config/objects/v1/auto-tag-actions` | list, create, update, delete | — |
| `/config/objects/v1/device-context-segments` | list, create, delete, get by id, update | — |
| `/config/objects/v1/dynamic-user-groups` | list, create, get by id, update, delete | `scm_dynamic_user_group` |
| `/config/objects/v1/external-dynamic-lists` | list, create, get by id, update, delete | `scm_external_dynamic_list` |
| `/config/objects/v1/hip-objects` | list, create, get by id, update, delete | `scm_hip_object` |
| `/config/objects/v1/hip-profiles` | list, create, get by id, update, delete | `scm_hip_profile` |
| `/config/objects/v1/http-server-profiles` | list, create, get by id, update, delete | `scm_http_server_profile` |
| `/config/objects/v1/log-forwarding-profiles` | list, create, get by id, update, delete | `scm_log_forwarding_profile` |
| `/config/objects/v1/quarantined-devices` | list, create, delete | — |
| `/config/objects/v1/regions` | list, create, get by id, update, delete | `scm_region` |
| `/config/objects/v1/schedules` | list, create, get by id, update, delete | `scm_schedule` |
| `/config/objects/v1/service-groups` | list, create, get by id, update, delete | `scm_service_group` |
| `/config/objects/v1/services` | list, create, get by id, update, delete | `scm_service` |
| `/config/objects/v1/syslog-server-profiles` | list, create, get by id, update, delete | `scm_syslog_server_profile` |
| `/config/objects/v1/tags` | list, create, get by id, update, delete | `scm_tag` |

### Security Services

Host: `api.strata.paloaltonetworks.com` · Products: CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/security/v1/anti-spyware-profiles` | list, create, get by id, update, delete | `scm_anti_spyware_profile` |
| `/config/security/v1/anti-spyware-signatures` | list, create, get by id, update, delete | `scm_anti_spyware_signature` |
| `/config/security/v1/app-override-rules` | list, create, get by id, update, delete | `scm_app_override_rule` |
| `/config/security/v1/app-override-rules/{id}:move` | action (POST) | — |
| `/config/security/v1/data-filtering-profiles` | list, create, get by id, update, delete | `scm_data_filtering_profile` |
| `/config/security/v1/data-objects` | list, create, get by id, update, delete | `scm_data_object` |
| `/config/security/v1/decryption-exclusions` | list, create, get by id, update, delete | `scm_decryption_exclusion` |
| `/config/security/v1/decryption-profiles` | list, create, get by id, update, delete | `scm_decryption_profile` |
| `/config/security/v1/decryption-rules` | list, create, get by id, update, delete | `scm_decryption_rule` |
| `/config/security/v1/decryption-rules/{id}:move` | action (POST) | — |
| `/config/security/v1/dns-security-profiles` | list, create, get by id, update, delete | `scm_dns_security_profile` |
| `/config/security/v1/dos-protection-profiles` | list, create, get by id, update, delete | `scm_dos_protection_profile` |
| `/config/security/v1/dos-protection-rules` | list, create, get by id, update, delete | `scm_dos_protection_rule` |
| `/config/security/v1/file-blocking-profiles` | list, create, get by id, update, delete | `scm_file_blocking_profile` |
| `/config/security/v1/http-header-profiles` | list, create, get by id, update, delete | `scm_http_header_profile` |
| `/config/security/v1/profile-groups` | list, create, get by id, update, delete | `scm_profile_group` |
| `/config/security/v1/saas-tenant-restrictions` | list, update | — |
| `/config/security/v1/security-rules` | list, create, get by id, update, delete | `scm_security_rule` |
| `/config/security/v1/security-rules/{id}:move` | action (POST) | — |
| `/config/security/v1/ssl-decryption-settings` | list, create, update, delete | — |
| `/config/security/v1/url-access-profiles` | list, create, get by id, update, delete | `scm_url_access_profile` |
| `/config/security/v1/url-admin-override` | list, create, delete | — |
| `/config/security/v1/url-categories` | list, create, get by id, update, delete | `scm_url_category` |
| `/config/security/v1/url-filtering-categories` | list | — |
| `/config/security/v1/vulnerability-protection-profiles` | list, create, get by id, update, delete | `scm_vulnerability_protection_profile` |
| `/config/security/v1/vulnerability-protection-signatures` | list, create, get by id, update, delete | `scm_vulnerability_protection_signature` |
| `/config/security/v1/wildfire-anti-virus-profiles` | list, create, get by id, update, delete | `scm_wildfire_anti_virus_profile` |

### VR Routing Profiles

Host: `api.strata.paloaltonetworks.com` · Products: NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/network/v1/bgp-vr-auth-profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/ospf-vr-auth-profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/ospfv3-vr-auth-profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/vr-bfd-profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/vr-redistribution-profiles` | list, create, get by id, update, delete | — |
| `/config/network/v1/vr-redistribution-profiles-ipv6` | list, create, get by id, update, delete | — |

### Virtual Routers

Host: `api.strata.paloaltonetworks.com` · Products: NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/config/network/v1/virtual-routers` | list, create, get by id, update, delete | — |

### Access Policies

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/access_policies` | list, create, get by id, delete | — |

### Authentication Service API

Host: `auth.apps.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/auth/v1/oauth2/access_token` | create | — |
| `/auth/v1/oauth2/userinfo` | list, create | — |

### Custom Roles

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/custom_roles` | list, create, get by id, update, delete | — |

### Instances

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/subscription/v1/instances` | list, create | — |

### Licenses

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/subscription/v1/licenses` | list | — |

### Permission Sets

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/permission_sets` | list, get by id | — |

### Permissions

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/permissions` | list, get by id | — |

### Roles

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/roles` | list, get by id | — |

### Service Accounts

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/service_accounts` | list, create, get by id, update, delete | — |
| `/iam/v1/service_accounts/{id}/operations/reset` | create | — |

### Tenant Service Group

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/tenancy/v1/tenant_service_groups` | list, create, get by id, update, delete | — |
| `/tenancy/v1/tenant_service_groups/{tsg_id}/operations/list_ancestors` | create | — |
| `/tenancy/v1/tenant_service_groups/{tsg_id}/operations/list_children` | create | — |

### User Accounts

Host: `api.sase.paloaltonetworks.com` · Products: Platform

| Endpoint | Operations | Terraform |
|---|---|---|
| `/iam/v1/sso_users` | list, create | — |

### Advanced DNS Security Resolver Configuration

Host: `api.strata.paloaltonetworks.com` · Products: Add-on, CNGFW, NGFW, PA

| Endpoint | Operations | Terraform |
|---|---|---|
| `/adns-resolver/v1/ca-certs` | list, get by id, delete | — |
| `/adns-resolver/v1/ca-certs/{ca-cert-id}/download` | list | — |
| `/adns-resolver/v1/ca-certs:upload` | action (POST) | — |
| `/adns-resolver/v1/connection-sources` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/connection-sources/subnets` | list, get by id | — |
| `/adns-resolver/v1/connection-sources/{connection-source-id}/subnets` | list, create, get by id, delete | — |
| `/adns-resolver/v1/connection-sources/{connection-source-id}/subnets/{subnet-id}:verify-update` | action (POST) | — |
| `/adns-resolver/v1/custom-fqdns` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/edls` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/internal-domains` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/misconfigured-domains` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/profiles` | list, create, get by id, update, delete | — |
| `/adns-resolver/v1/profiles/categories` | list | — |
| `/adns-resolver/v1/resolver-info` | list | — |
| `/adns-resolver/v1/security-policy/rules` | list, create, get by id, update, delete | — |

### CIE - Cloud Dynamic User Group CRUD Operations APIs Mounted on Strata Cloud Manager

Host: `api.strata.paloaltonetworks.com` · Products: Add-on

| Endpoint | Operations | Terraform |
|---|---|---|
| `/directory-sync/v1/cloud-dug-definition` | create | — |
| `/directory-sync/v1/cloud-dug-definition/category` | list | — |
| `/directory-sync/v1/cloud-dug-definition/group` | list, update, delete | — |
| `/directory-sync/v1/user-attr-values` | list | — |

### CIE Directory Sync Service APIs Mounted on Strata Cloud Manager

Host: `api.sase.paloaltonetworks.com` · Products: Add-on

| Endpoint | Operations | Terraform |
|---|---|---|
| `/cie/directory-sync/v1/cache-groups` | create | — |
| `/cie/directory-sync/v1/cache-users` | create | — |
| `/cie/directory-sync/v1/connection/update-secret` | create | — |
| `/cie/directory-sync/v1/domains` | list | — |

### Compliance Center API

Host: `api.strata.paloaltonetworks.com` · Products: Posture

| Endpoint | Operations | Terraform |
|---|---|---|
| `/posture/compliance-frameworks/v1/benchmark-monitoring` | create | — |
| `/posture/compliance-frameworks/v1/benchmark-monitoring/download` | create | — |
| `/posture/compliance-frameworks/v1/compliance-controls` | get by id | — |
| `/posture/compliance-frameworks/v1/configurations-assessed` | get by id | — |
| `/posture/compliance-frameworks/v1/definitions` | list, create, get by id, update, delete | — |
| `/posture/compliance-frameworks/v1/definitions/{id}:benchmark` | action (POST) | — |
| `/posture/compliance-frameworks/v1/definitions/{id}:clone` | action (POST) | — |
| `/posture/compliance-frameworks/v1/definitions/{id}:un-benchmark` | action (POST) | — |
| `/posture/compliance-frameworks/v1/overall-compliance` | get by id | — |
| `/posture/compliance-frameworks/v1/overall-compliance-timeline` | get by id | — |
| `/posture/compliance-frameworks/v1/summaries` | list | — |

### Config Cleanup API

Host: `api.strata.paloaltonetworks.com` · Products: Posture

| Endpoint | Operations | Terraform |
|---|---|---|
| `/posture/config-cleanup/v1/zerohit-rules` | list | — |

### Operations and Troubleshooting

Host: `api.strata.paloaltonetworks.com` · Products: NGFW

| Endpoint | Operations | Terraform |
|---|---|---|
| `/operations/v1/device/jobs` | get by id | — |
| `/operations/v1/jobs/bgp-policy-export` | create | — |
| `/operations/v1/jobs/device-interfaces` | create | — |
| `/operations/v1/jobs/device-rules` | create | — |
| `/operations/v1/jobs/dns-proxy` | create | — |
| `/operations/v1/jobs/fib-table` | create | — |
| `/operations/v1/jobs/logging-service-forwarding-status` | create | — |
| `/operations/v1/jobs/route-table` | create | — |
| `/operations/v1/local-config/download` | list | — |
| `/operations/v1/local-config/versions` | list | — |

### Policy Optimizer API

Host: `api.strata.paloaltonetworks.com` · Products: Posture

| Endpoint | Operations | Terraform |
|---|---|---|
| `/posture/policy-optimizer/v1/security-rules` | list, get by id | — |

### Posture Check Upload Initiation API

Host: `api.strata.paloaltonetworks.com` · Products: Posture

| Endpoint | Operations | Terraform |
|---|---|---|
| `/posture/checks/v1/all-checks` | list, create, get by id, update, delete | — |
| `/posture/checks/v1/all-checks/batch-delete` | create | — |
| `/posture/checks/v1/all-checks/batch-upsert` | create | — |
| `/posture/checks/v1/all-checks/{id}:clone` | action (POST) | — |
| `/posture/checks/v1/report` | list, get by id | — |
| `/posture/checks/v1/report/object-types` | list | — |
| `/posture/checks/v1/report/objects` | get by id | — |
| `/posture/checks/v1/reports/config-file-upload` | create | — |
| `/posture/checks/v1/reports/{id}/bpa-result` | list | — |

### Secure Agentless Access (SAA) Configuration

Host: `api.strata.paloaltonetworks.com` · Products: Add-on

| Endpoint | Operations | Terraform |
|---|---|---|
| `/secure-agentless-access/v1/active-sessions` | list | — |
| `/secure-agentless-access/v1/active-sessions:disconnect` | action (POST) | — |
| `/secure-agentless-access/v1/active-sessions:disconnect-all` | action (POST) | — |
| `/secure-agentless-access/v1/application-groups` | list, create, get by id, update, delete | — |
| `/secure-agentless-access/v1/application-policies` | list, create, get by id, update, delete | — |
| `/secure-agentless-access/v1/application-profiles` | list, create, get by id, update, delete | — |
| `/secure-agentless-access/v1/applications` | list, create, get by id, update, delete | — |
| `/secure-agentless-access/v1/applications:delete` | action (POST) | — |

### TLS Protect Cloud API for Strata Cloud Manager

Host: `api.strata.paloaltonetworks.com` · Products: TLS

| Endpoint | Operations | Terraform |
|---|---|---|
| `/ngts/outagedetection/v1/certificateinstances` | list, get by id | — |
| `/ngts/outagedetection/v1/certificateinstances/validation` | create | — |
| `/ngts/outagedetection/v1/certificateinstancesearch` | create | — |
| `/ngts/outagedetection/v1/certificaterequests` | list, create, get by id | — |
| `/ngts/outagedetection/v1/certificaterequests/validation` | create | — |
| `/ngts/outagedetection/v1/certificaterequests/{id}/resubmission` | create | — |
| `/ngts/outagedetection/v1/certificaterequestssearch` | create | — |
| `/ngts/outagedetection/v1/certificates` | list, create, get by id | — |
| `/ngts/outagedetection/v1/certificates/deletion` | create | — |
| `/ngts/outagedetection/v1/certificates/recovery` | create | — |
| `/ngts/outagedetection/v1/certificates/retirement` | create | — |
| `/ngts/outagedetection/v1/certificates/validation` | create | — |
| `/ngts/outagedetection/v1/certificates/{id}/contents` | list | — |
| `/ngts/outagedetection/v1/certificatesearch` | create | — |
| `/ngts/outagedetection/v1/inventorymonitoringconfig` | get by id, update | — |
| `/ngts/outagedetection/v1/inventorymonitoringconfig/{type}/scheduler` | update | — |
| `/ngts/v1/activitylogsearch` | create | — |
| `/ngts/v1/activitylogsearch/export` | create | — |
| `/ngts/v1/activitytypes` | list | — |
| `/ngts/v1/autorenewal/status` | list | — |
| `/ngts/v1/autorenewal/tenantconfiguration` | list, update | — |
| `/ngts/v1/autorenewal/trigger` | create | — |
| `/ngts/v1/certificateissuingtemplates` | list, create, get by id, update, delete | — |
| `/ngts/v1/certificateissuingtemplates/domainssynchronization` | create | — |
| `/ngts/v1/certificaterequests/approval/bulk` | post by id | — |
| `/ngts/v1/certificaterequests/approvalrequests` | get by id | — |
| `/ngts/v1/certificaterequests/approvalrules` | list, create, get by id, update, delete | — |
| `/ngts/v1/certificaterequests/{id}/approval` | post by id | — |
| `/ngts/v1/certificates/imports` | create, get by id | — |
| `/ngts/v1/certificates/revocations/approvalrules` | list, create, get by id, update, delete | — |
| `/ngts/v1/credentialmanagerconfigurations` | list, create, update, get by id, delete | — |
| `/ngts/v1/credentialmanagerconfigurations/test` | create | — |
| `/ngts/v1/credentialmanagerconfigurations/{id}/test` | create | — |
| `/ngts/v1/credentials` | list, create, update, delete, get by id | — |
| `/ngts/v1/credentials/test` | create | — |
| `/ngts/v1/distributedissuers/configurations` | list, create, get by id, patch, delete | — |
| `/ngts/v1/distributedissuers/intermediatecertificates` | list | — |
| `/ngts/v1/distributedissuers/policies` | list, create, get by id, patch, delete | — |
| `/ngts/v1/distributedissuers/subcaproviders` | list, create, get by id, patch, delete | — |
| `/ngts/v1/edgeencryptionkeys` | list, get by id | — |
| `/ngts/v1/edgeinstances` | list, get by id, update | — |
| `/ngts/v1/edgeinstances/{id}/update` | create | — |
| `/ngts/v1/edgeworkers` | list, create, delete | — |
| `/ngts/v1/edgeworkers/{id}/pair` | create | — |
| `/ngts/v1/expirationnotifications/tenantconfiguration` | list, update | — |
| `/ngts/v1/integrationservices` | list, create, get by id, patch, delete | — |
| `/ngts/v1/machineidentities` | list, create, get by id, patch, delete | — |
| `/ngts/v1/machineidentities/{id}/workflows` | create | — |
| `/ngts/v1/machineidentitysearch` | create | — |
| `/ngts/v1/machines` | list, create, get by id, patch, delete | — |
| `/ngts/v1/machines/workflows` | create | — |
| `/ngts/v1/machines/{id}/batchprovisionings/abort` | create | — |
| `/ngts/v1/machines/{id}/discovery` | list | — |
| `/ngts/v1/machines/{id}/discovery/abort` | create | — |
| `/ngts/v1/machines/{id}/workflows` | create | — |
| `/ngts/v1/machinesearch` | create | — |
| `/ngts/v1/machinetypes` | list | — |
| `/ngts/v1/pairingcodes/satellite` | create | — |
| `/ngts/v1/plugins` | list, create, get by id, patch, delete | — |
| `/ngts/v1/plugins/disablements` | list | — |
| `/ngts/v1/plugins/{id}/disablements` | create, delete | — |
| `/ngts/v1/recoverycodes/satellite` | create | — |
| `/ngts/v1/serviceaccounts` | list, create, get by id, patch, delete | — |
| `/ngts/v1/serviceaccounts/scopes` | list | — |
| `/ngts/v1/serviceaccounts/{id}/credentials` | update | — |
| `/ngts/v1/serviceaccounts/{id}/ocitoken` | update | — |
| `/ngts/v1/tags` | list, create, get by id, delete | — |
| `/ngts/v1/tags/creation` | create | — |
| `/ngts/v1/tags/deletion` | create | — |
| `/ngts/v1/tags/values` | list | — |
| `/ngts/v1/tags/{name}/values` | list, create, delete | — |
| `/ngts/v1/tagsassignment` | patch | — |
| `/ngts/v1/tagsassignment/aggregates` | create | — |
| `/ngts/v1/updatesconfig` | list, patch | — |

### Unified Incident Framework APIs

Host: `api.strata.paloaltonetworks.com` · Products: Add-on

| Endpoint | Operations | Terraform |
|---|---|---|
| `/incidents/v1/details` | get by id | — |
| `/incidents/v1/search` | create | — |
