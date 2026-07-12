---
title: "Introduction"
source_url: "https://neo4j.com/docs/upgrade-migration-guide/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:10.956Z"
---
[](https://neo4j.com/docs)

# Introduction

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_about_this_guide)About this guide

Keeping your Neo4j deployment always up-to-date ensures that you are provided with the latest improvements in performance, security, and bug fixes.

*Who should read this?*

This upgrade and migration guide is written for experienced system administrators and operations engineers who want to upgrade or migrate self-managed Neo4j deployments.

If you are using Neo4j Aura, you do not need to upgrade or migrate, as the service is always up-to-date. However, if you want to move from Aura 4.4 to the latest version, from self-managed Neo4j to Aura, or from Aura Free to another plan, you can refer to the following tutorials:

-   [Migrate a version 4 instance to the latest version](https://neo4j.com/docs/aura/tutorials/upgrade/)

-   [Migrate from self-managed Neo4j to Aura](https://neo4j.com/docs/aura/tutorials/migration/)

-   [Migrating your AuraDB Free instance to another AuraDB tier](https://neo4j.com/docs/aura/tutorials/migration-free/)


This page introduces some important Neo4j concepts before referring to the version-specific pages.

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_preparation)Preparation

Preparation is key to any successful upgrade or migration. Before making changes to a production DBMS, it is highly recommended to use a test environment to check:

-   The upgrade/migration process.

-   Compatibility with other systems.


## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_version_numbers)Version numbers

From January 2025 Neo4j Server adopted calendar versioning (CalVer). Earlier versions, such as Neo4j 4 and 5 used semantic versioning (SemVer). Neo4j’s fully managed cloud service [Neo4j Aura](https://neo4j.com/cloud/aura/) uses only the latest version.

### [](https://neo4j.com/docs/upgrade-migration-guide/current/#_neo4j_server_versioning)Neo4j server versioning

Introduced in 2025.01

The Calendar versioning (CalVer) format, `YYYY.MM.PATCH`, is based on the year and month of the release, for example, 2025.01, 2025.02, and so on. The patch number is incremented for each release within the same month.

A CalVer may optionally have a fourth component, `LTS`. This marks the release as a Long-Term Support (LTS) release. There is a new LTS version of Neo4j roughly every 18 to 24 months. LTS releases have a three-year support window during which they receive critical patches and security updates but not new features or improvements.

In the release immediately after an LTS, some deprecated features may be removed, software requirements and the default configuration may change. So care must be taken when upgrading between versions that span an LTS release. LTS release are treated as checkpoints and during upgrades Neo4j server must be upgraded to each LTS version/checkpoint between the current and the desired version.

### [](https://neo4j.com/docs/upgrade-migration-guide/current/#_neo4j_4_and_5_versioning)Neo4j 4 and 5 versioning

Neo4j versions 4 and 5 use semantic versioning (SemVer). Neo4j version numbers are in the pattern `MAJOR.MINOR.PATCH`.

-   `MAJOR` versions introduce significant architectural improvements and features. They are not compatible with previous `MAJOR` versions. Systems that interact with the database may require updating.

-   `MINOR` versions introduce improvements and new features. They are backward compatible with other `MINOR` versions of the `MAJOR` version.

-   `PATCH` versions fix critical bugs and security issues. They are backward compatible and replace previous releases of the same `MAJOR.MINOR` version.


Neo4j 4.4 and 5.26 are designated as LTS releases. LTS releases have a three-year support window during which they receive critical patches and security updates but not new features or improvements. Neo4j 4.4 long-term support ended on November 30, 2025. Neo4j 5 will be supported until November 2028.

### [](https://neo4j.com/docs/upgrade-migration-guide/current/#_cypher_versions)Cypher versions

Introduced in 2025.06

As of Neo4j 2025.06, the Cypher® language is decoupled from the Neo4j server and follows its own versioning. You can choose between Cypher 5 and Cypher 25.

You can specify the version of Cypher by configuring a default Cypher version for the whole DBMS, per database, or by setting it on a per-query basis.

<table><tbody><tr><td class="icon"><i class="fa icon-important" title="Important"></i></td><td class="content"><div class="paragraph"><p>Setting the default language to <code>CYPHER 5</code> ensures that all queries run on that database will use the version of <code>Cypher 5</code> as it existed at the time of the Neo4j 2025.06 release (unless you prepend your queries with <code>CYPHER 25</code>, which overrides this default). Any changes introduced after the 2025.06 release will not affect the semantics of the query.</p></div><div class="paragraph"><p>Setting the default language to <code>CYPHER 25</code> ensures that all queries run on that database will use the version of <code>Cypher 25</code> that the database is currently running (unless you prepend your queries with <code>CYPHER 5</code>, which overrides this default). For example, a Neo4j 2025.08 database with default language <code>Cypher 25</code> will use <code>Cypher 25</code> as it exists in Neo4j 2025.08, including any changes introduced in Neo4j 2025.06, 2025.07, and 2025.08.</p></div></td></tr></tbody></table>

For more information, see the [Operations Manual → Configure the Cypher default version](https://neo4j.com/docs/operations-manual/current/configuration/cypher-version-configuration) and [Cypher Manual → Select Cypher version](https://neo4j.com/docs/cypher-manual/current/queries/select-version/).

The following table outlines which Cypher version is assigned to databases in different upgrade or installation scenarios, when not explicitly set on the DBMS level (using `db.query.default_language`):

Table 1. Default Cypher version per scenario
| Scenario | Existing databases | New databases |
| --- | --- | --- |
|
New installation

 |

N/A

 |

Defaults to Cypher 5

 |
|

Upgrades

 |

Cypher 5

 |

Defaults to Cypher 5

 |
|

Upgrades

 |

Cypher 25

 |

Defaults to Cypher 5

 |

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_downtime)Downtime

When configured as a cluster, Neo4j can be upgraded without downtime, with the exception of Neo4j 4.4 to Neo4j 5.26. Online upgrades from Neo4j 5.26 LTS to any Neo4j 2025-2026 version are supported.

Standalone Neo4j always requires downtime to upgrade.

Servers are upgraded by updating their binaries and restarting. When you move from Neo4j 4.4 to Neo4j 5.26, you must migrate the databases from the old server to the new server.

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_store_format)Store format

Store format updates are optional unless you are moving to a version that removes support for your old store format. For more information on the available store formats per Neo4j version, see the [Operations Manual → Store formats](https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/).

There are no changes to store formats between Neo4j 4.4 and any Neo4j 2025-2026 version. However, `block` format, introduced is Neo4j 5.16, is the default store format for new databases in Enterprise Edition starting with Neo4j 5.22, and is the default format for all databases in 5.26 and later. `High_limit` and `standard` have been deprecated in 5.23 and are scheduled to be removed after 2026 LTS.

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_downgrades)Downgrades

Neo4j does not support downgrades. If the upgrade or migration is not successful, you have to do a full rollback, including restoring a pre-upgrade or a pre-migration backup.

## [](https://neo4j.com/docs/upgrade-migration-guide/current/#_continue_reading)Continue reading

If you are on a Neo4j 2025-2026 version or want to upgrade your databases from Neo4j 5, you can proceed to the [Neo4j 2025-2026](https://neo4j.com/docs/upgrade-migration-guide/current/version-2025-2026/) section.

If you are on Neo4j 5 or want to migrate your databases from 4.4, you can proceed to the [Neo4j 5](https://neo4j.com/docs/upgrade-migration-guide/current/version-5/) section.

If you are upgrading to a version of Neo4j 4, read the [Neo4j 4](https://neo4j.com/docs/upgrade-migration-guide/current/version-4/) section.

© 2026 [Creative Commons 4.0](https://neo4j.com/docs/license/)
