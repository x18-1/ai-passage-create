# Context-Augmented 5-Agent Creation Flow Design

## Goal

Upgrade the existing fixed 5-Agent article creation pipeline into a context-augmented Agent workflow for Agent-development job positioning.

Phase 1 adds three context sources to the current flow:

- User memory: long-term writing preferences, platform preferences, topic interests, constraints, and visual preferences.
- Writing Skills: reusable prompt templates that apply to specific Agent stages.
- RAG knowledge: private documents, historical articles, and hotspot records retrieved by an internalized RAG Kernel derived from `plugin/MODULAR-RAG-MCP-SERVER`.

The existing article creation flow remains intact:

```text
Title Agent -> Outline Agent -> Content Agent -> Image Analysis Agent -> Image Generation/Merge
```

Phase 1 does not add a supervisor Agent, Tool layer, or MCP client integration. Those are later phases after the current workflow has strong context and RAG support.

## Non-Goals

- No supervisor/planner Agent in Phase 1.
- No Agent Tool abstraction in Phase 1.
- No MCP stdio client/server integration in the main request path.
- No Graph RAG.
- No automatic long-term memory summarization.
- No full migration of the RAG dashboard or evaluation UI.
- No marketplace for shared Skills.

## Architecture

The project will treat `MODULAR-RAG-MCP-SERVER` as the source for an internal RAG Kernel, not as a long-term cross-directory plugin dependency.

Core RAG modules will be copied and adapted into:

```text
backend/app/rag/
  core/
  ingestion/
  retrieval/
  vector_store/
  libs/
  observability/
```

The main application will own business concepts:

- Users and authorization.
- Article tasks.
- Knowledge document metadata.
- Memory records.
- Writing Skills.
- Which context is injected into each Agent stage.

The RAG Kernel will own retrieval mechanics:

- Document loading.
- Chunking.
- Embedding.
- Chroma persistence.
- BM25 indexing.
- Hybrid Search.
- RRF fusion.
- Optional reranking.
- Citations and trace records.

The first migration should include only the RAG modules needed for ingestion and query. MCP server code, dashboard pages, and evaluation modules remain out of scope.

## New Backend Services

### `MemoryService`

Manages user long-term memories.

Responsibilities:

- Create, update, delete, list, and toggle memories.
- Filter active memories by type and user.
- Return stage-specific memory snippets for prompt injection.

### `WritingSkillService`

Manages system and user-defined writing Skills.

Responsibilities:

- Create, update, delete, list, and toggle Skills.
- Seed system Skills.
- Filter Skills by user, active state, and applicable stage.
- Return prompt templates for Agent context injection.

### `RagKnowledgeService`

Business wrapper around the internal RAG Kernel.

Responsibilities:

- Ingest uploaded PDF / Markdown / TXT files.
- Ingest completed articles into the writing-sample collection.
- Ingest selected hotspot records into the hotspot collection.
- Query one or more user-scoped collections.
- Maintain `knowledge_document` metadata and status.
- Convert RAG results into concise prompt-ready context.

### `AgentContextBuilder`

Builds the stage-specific context block injected into each Agent prompt.

Inputs:

- `taskId`
- `userId`
- `topic`
- `style`
- `stage`
- `enableMemory`
- `enableRag`
- `enabledSkillIds`
- `ragCollections`

Output:

```text
AgentContext
- memoryContext
- skillContext
- ragContext
- hotspotContext
- articleExampleContext
- instructionBlock
```

`instructionBlock` is the final text appended to the base Agent prompt.

## Data Model

### `user_memory`

```text
id bigint primary key
userId bigint not null
memoryType varchar(32) not null
title varchar(200) not null
content text not null
weight int default 50
source varchar(32) default 'manual'
isActive tinyint default 1
createTime datetime
updateTime datetime
isDelete tinyint default 0
```

Supported `memoryType` values:

- `style`
- `platform`
- `topic`
- `constraint`
- `visual`

### `writing_skill`

```text
id bigint primary key
userId bigint null
name varchar(100) not null
description varchar(500) null
promptTemplate text not null
applicableStages json not null
isSystem tinyint default 0
isActive tinyint default 1
createTime datetime
updateTime datetime
isDelete tinyint default 0
```

Supported stage values:

- `title`
- `outline`
- `content`
- `image`

System Skills are shared and cannot be deleted by regular users.

### `knowledge_document`

```text
id bigint primary key
userId bigint not null
title varchar(255) not null
sourceType varchar(32) not null
sourceId varchar(64) null
collectionName varchar(128) not null
filePath varchar(1024) null
status varchar(32) not null
chunkCount int default 0
errorMessage text null
createTime datetime
updateTime datetime
isDelete tinyint default 0
```

Supported `sourceType` values:

- `upload`
- `article`
- `hotspot`
- `system`

Supported `status` values:

- `pending`
- `processing`
- `ready`
- `failed`

### `agent_context_snapshot`

```text
id bigint primary key
taskId varchar(64) not null
userId bigint not null
stage varchar(32) not null
memoryContext mediumtext null
skillContext mediumtext null
ragContext mediumtext null
hotspotContext mediumtext null
articleExampleContext mediumtext null
tokenEstimate int default 0
createTime datetime
```

This table records the exact context injected into each Agent stage for debugging and interview/demo visibility.

### Article Table Additions

Add fields to persist the article task's context settings:

```text
enableMemory tinyint default 1
enableRag tinyint default 1
enabledSkillIds json null
ragCollections json null
```

These values must be stored with the article so async phase execution can rebuild context without relying on frontend state.

## Collection Strategy

Phase 1 uses simple fixed collections:

```text
user_{userId}_knowledge
user_{userId}_articles
user_{userId}_hotspots
global_writing_guides
```

Mapping:

- User uploads -> `user_{userId}_knowledge`
- Completed articles -> `user_{userId}_articles`
- Selected hotspot records -> `user_{userId}_hotspots`
- System writing guides -> `global_writing_guides`

No domain-specific collection splitting in Phase 1.

## Prompt Injection Strategy

Context must be stage-specific. Do not inject every context source into every Agent.

### Title Stage

Inject:

- User title/style/platform memories.
- Title-stage Skills.
- Relevant hotspot context.
- Historical article title examples.

### Outline Stage

Inject:

- Structure/style memories.
- Outline-stage Skills.
- Knowledge context.
- Hotspot background.

### Content Stage

Inject:

- Style, platform, topic, and constraint memories.
- Content-stage Skills.
- Knowledge RAG snippets.
- Hotspot RAG snippets.
- Historical article examples.
- Citation/source hints.

### Image Stage

Inject:

- Visual memories.
- Image-stage Skills.
- Platform visual constraints.
- Short article summary if needed.

### Image Generation Stage

Agent5 mainly executes image generation from Agent4's image requirements. Phase 1 does not inject extra LLM context into Agent5 unless an LLM prompt is introduced there later.

## API Design

### Knowledge

```http
POST /api/knowledge/upload
GET /api/knowledge/documents
DELETE /api/knowledge/documents/{id}
POST /api/knowledge/documents/{id}/reingest
POST /api/knowledge/articles/{taskId}/ingest
POST /api/knowledge/hotspots/ingest
POST /api/knowledge/query
```

`/api/knowledge/query` is a manual debug endpoint for testing RAG results from the UI.

### Memories

```http
GET /api/memories
POST /api/memories
PATCH /api/memories/{id}
PATCH /api/memories/{id}/toggle
DELETE /api/memories/{id}
```

### Writing Skills

```http
GET /api/writing-skills
POST /api/writing-skills
PATCH /api/writing-skills/{id}
PATCH /api/writing-skills/{id}/toggle
DELETE /api/writing-skills/{id}
```

### Article Create Request Additions

```text
enableMemory: bool
enableRag: bool
enabledSkillIds: list[int]
ragCollections: list[str]
```

Defaults:

- `enableMemory = true`
- `enableRag = true`
- `enabledSkillIds = []`
- `ragCollections = []`, which means use the default user collections.

## Frontend Design

Add a new page:

```text
/knowledge
Navigation label: 知识库
Page title: 知识与风格
```

Tabs:

- 资料库
- 记忆
- 写作 Skills
- RAG 测试

### 资料库 Tab

Features:

- Upload PDF / Markdown / TXT.
- List documents.
- Show source type, collection, status, chunk count, create time.
- Delete document.
- Reingest failed/stale document.

### 记忆 Tab

Features:

- Create, edit, delete, toggle memories.
- Filter by memory type.
- Display memory weight and active state.

### 写作 Skills Tab

Features:

- Create, edit, delete, toggle user Skills.
- Display system Skills.
- Select applicable stages.
- System Skills cannot be deleted by regular users.

### RAG 测试 Tab

Features:

- Enter query.
- Select collection.
- Set topK.
- Display retrieved snippets, sources/citations, and scores.

## Existing Page Changes

### Article Create Page

Add an "上下文增强" advanced section:

- Enable long-term memory.
- Enable RAG knowledge.
- Select writing Skills.
- Select knowledge scopes: uploaded documents, historical articles, hotspot records.

### Article List / Detail

For completed articles, add:

```text
加入写作样例库
```

This ingests the completed article into `user_{userId}_articles`.

### Hotspot Monitor Page

Add:

```text
加入知识库
批量加入知识库
```

Selected records are ingested into `user_{userId}_hotspots`.

### Agent Logs / Article Detail

Add a way to inspect `agent_context_snapshot` by stage.

This can be lightweight in Phase 1: a modal or expandable panel showing the injected memory, Skills, and RAG snippets.

## Error Handling

Context enhancement must not block article generation.

Rules:

- Memory load failure: log warning and continue.
- Skill load failure: log warning and continue.
- RAG query failure: log warning, store snapshot with failure text, continue.
- RAG ingestion failure: mark `knowledge_document.status = failed`, store `errorMessage`.
- Article generation failures remain handled by the existing Agent pipeline error handling.

## Testing Plan

Backend tests:

- `MemoryService` CRUD, toggle, user isolation.
- `WritingSkillService` CRUD, toggle, system Skill restrictions.
- `RagKnowledgeService` ingestion metadata updates with mocked RAG Kernel.
- `RagKnowledgeService` query formatting with mocked results.
- `AgentContextBuilder` stage-specific context selection.
- `ArticleAgentService` prompt injection path.
- Article create request persistence for context flags.
- Hotspot ingestion request creates knowledge documents.
- Article ingestion request rejects unauthorized task access.

Frontend tests:

- Knowledge page state transitions for upload/list/delete.
- Memory form create/edit/toggle behavior.
- Skill form stage selection.
- Article create page serializes context settings.

RAG Kernel tests:

- Keep a focused subset from `MODULAR-RAG-MCP-SERVER` for imported modules.
- Do not migrate dashboard/evaluation E2E tests in Phase 1.

## Acceptance Criteria

Phase 1 is complete when:

1. A user can upload PDF / Markdown / TXT into the knowledge base.
2. Uploaded documents are ingested and show `ready` status with chunk count.
3. A user can create and enable memories.
4. A user can create and enable writing Skills.
5. A user can ingest completed articles as writing samples.
6. A user can ingest selected hotspot records as hotspot knowledge.
7. Article creation can enable/disable memory and RAG and select Skills.
8. Title, outline, content, and image-analysis prompts receive stage-specific context.
9. Context snapshots are persisted and viewable for a generated article.
10. RAG failure does not prevent article generation.
11. A generated article can visibly use uploaded or hotspot knowledge when relevant.

## Resume Positioning

After Phase 1, the project can be described as:

```text
Designed and implemented a Memory + Writing Skill + RAG context augmentation layer for a 5-Agent content creation pipeline. Adapted a self-built Modular RAG Kernel into the main FastAPI backend, supporting PDF/Markdown/TXT ingestion, Hybrid Search, RRF fusion, optional reranking, citations, and user-scoped collections. Injected long-term user preferences, reusable writing Skills, historical articles, hotspot records, and private knowledge into title, outline, content, and image-analysis Agents to improve personalization, consistency, and factual density.
```

## Later Phases

Phase 2:

- Extract Agent Tool layer.
- Wrap memory, Skill, RAG, hotspot, article generation, and publishing capabilities as internal tools.

Phase 3:

- Add supervisor Agent for user-goal planning and tool orchestration.
- Support plan preview, user confirmation, retries, and resumable runs.

Phase 4:

- Reintroduce MCP as a public interface.
- Expose selected tools such as RAG query, article creation, and hotspot search to external Agent clients.
