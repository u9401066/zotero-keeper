# Product Context

## Overview

**Zotero Keeper** is a MCP (Model Context Protocol) server that enables AI Agents to manage local Zotero bibliographic databases. The primary use case is allowing multiple users with Copilot Agent (or Claude Desktop) to search for references and store them in their local Zotero installation.

## Problem Statement

Researchers and knowledge workers need to:
1. Find relevant bibliographic references during research
2. Store them in their personal Zotero library
3. Do this seamlessly through AI assistants

Current solutions require manual copy-paste or complex workflows.

## Solution

Zotero Keeper provides MCP tools that allow AI Agents to:
- **Search**: Find existing references in local Zotero
- **Read**: Retrieve detailed metadata
- **Write**: Add new references directly to Zotero

## Core Features

- MCP Protocol integration for AI Agent communication
- Read operations via Zotero Local API
- Write operations via Zotero Connector API
- Multi-user support (each user connects to their own Zotero)
- Duplicate detection before adding new references
- Validation of reference metadata

## Target Users

1. **Researchers**: Managing academic references
2. **Knowledge Workers**: Organizing web articles and reports
3. **Students**: Building bibliographies for papers

## Technical Stack

- Python 3.11+
- FastMCP SDK
- httpx (HTTP client)
- Pydantic (data validation)
- Zotero 7.0+ (desktop client)

## Unique Value Proposition

Unlike existing Zotero MCP projects (54yyyu, kujenga) that are READ-ONLY, Zotero Keeper supports both READ and WRITE operations, making it the only MCP server that can actually add references to Zotero.

## Success Metrics

- References successfully added to Zotero
- Search response time < 500ms
- Zero data loss in write operations
- User satisfaction with AI workflow
