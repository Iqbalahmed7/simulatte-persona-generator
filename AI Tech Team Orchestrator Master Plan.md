{\rtf1\ansi\ansicpg1252\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fnil\fcharset0 .SFNS-Semibold;\f1\fnil\fcharset0 .SFNS-Regular;\f2\fswiss\fcharset0 Helvetica;
\f3\froman\fcharset0 TimesNewRomanPSMT;}
{\colortbl;\red255\green255\blue255;\red14\green14\blue14;}
{\*\expandedcolortbl;;\cssrgb\c6700\c6700\c6700;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs44 \cf2 AI Tech Team Orchestrator \'97 Master Plan
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 1. Purpose of this document
\f1\b0\fs28 \
\
This document is the single source of truth for the product.\
\
Every future coding task must be evaluated against this document before implementation begins.\
No agent should treat chat memory as authoritative when it conflicts with this document.\
If a new idea appears in chat but is not reflected here, it is a proposal, not approved scope.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 2. Product goal
\f1\b0\fs28 \
\
Build a lightweight AI Tech Team Orchestrator for a single operator.\
\
The operator interacts only at the vision level with:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	CPO\
	\'95	CTO\
\
The CPO and CTO collaborate to produce:\
	\'95	PRD\
	\'95	architecture\
	\'95	implementation approach\
	\'95	resource and token usage considerations\
\
Then the work is handed to:\
	\'95	Tech Lead\
\
The Tech Lead:\
	\'95	converts the approved plan into sprints and tasks\
	\'95	decides how many software engineers are needed for the project\
	\'95	assigns work to flexible engineer slots: SE-1, SE-2, SE-3, \'85 SE-N\
\
Each engineer slot is logical, not fixed.\
Each slot can be backed by any available coding tool or model.\
\
This system is meant to help a single founder or operator run an AI-assisted software team.\
It is not an enterprise workflow platform.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 3. Non-goals
\f1\b0\fs28 \
\
The following are explicitly out of scope for the MVP unless added later by formal change control:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	multi-tenancy\
	\'95	RBAC\
	\'95	JWT auth\
	\'95	user/org management\
	\'95	audit log platformization\
	\'95	enterprise observability stacks\
	\'95	Grafana / Prometheus as core MVP requirements\
	\'95	advanced billing systems\
	\'95	complicated deployment architecture\
	\'95	hard production scaling concerns\
	\'95	generalized workflow engine beyond this use case\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 4. Product principles
\f1\b0\fs28 \
\pard\tqr\tx260\tx420\li420\fi-420\sl324\slmult1\sb240\partightenfactor0

\f3 \cf2 	1.	Keep it small.\
	2.	Keep it single-operator.\
	3.	Keep it flexible.\
	4.	Keep it demoable quickly.\
	5.	Prefer mocked execution where real integrations are unnecessary.\
	6.	Separate logical team structure from backing tools.\
	7.	Optimize for delivery quality with minimal token usage.\
	8.	Human approval gates remain explicit.\
	9.	This document overrides conversational drift.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 5. Core user journey
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Stage 1 \'97 Vision input
\f1\b0\fs28 \
\
The operator creates a project by entering:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	project name\
	\'95	optional description\
	\'95	vision / business goal\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Stage 2 \'97 Planning
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	CPO generates PRD\
	\'95	CTO generates architecture\
	\'95	operator reviews outputs\
	\'95	operator approves or requests revision\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Stage 3 \'97 Delivery planning
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	Tech Lead generates sprint plan\
	\'95	Tech Lead creates tasks\
	\'95	Tech Lead recommends number of engineer slots\
	\'95	Tech Lead maps engineer slots to available tools\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Stage 4 \'97 Execution
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	tasks are executed through engineer slots\
	\'95	outputs are stored as artifacts\
	\'95	review and QA are visible\
	\'95	costs are tracked simply\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Stage 5 \'97 Summary
\f1\b0\fs28 \
\
The operator can inspect:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	project state\
	\'95	PRD\
	\'95	architecture\
	\'95	sprint plan\
	\'95	tasks and outputs\
	\'95	engineer slot assignments\
	\'95	simple cost summary\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 6. Core abstractions
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 6.1 Roles
\f1\b0\fs28 \
\
Logical roles in the system:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	CPO\
	\'95	CTO\
	\'95	TECH_LEAD\
	\'95	SOFTWARE_ENGINEER\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 6.2 Engineer slots
\f1\b0\fs28 \
\
Engineer slots are logical delivery seats.\
Examples:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	SE-1\
	\'95	SE-2\
	\'95	SE-3\
\
Each slot is assigned dynamically per workflow run.\
The slot is the stable planning abstraction.\
The backing tool is replaceable.\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 6.3 Agent configs
\f1\b0\fs28 \
\
An AgentConfig represents an available backing tool or model.\
Examples:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	cpo-default\
	\'95	cto-default\
	\'95	tech-lead-default\
	\'95	cursor\
	\'95	codex\
	\'95	sonnet\
	\'95	opencode\
	\'95	goose\
\
For engineers, tasks are assigned to slots, and slots resolve to AgentConfig.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 7. Minimal data model
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Project
\f1\b0\fs28 \
\
Root object for a product effort.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	name\
	\'95	description\
	\'95	vision\
	\'95	status\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 WorkflowRun
\f1\b0\fs28 \
\
A planning/execution attempt within a project.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	project_id\
	\'95	version\
	\'95	state\
	\'95	label\
	\'95	notes\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Artifact
\f1\b0\fs28 \
\
Persisted output of planning or execution.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	project_id\
	\'95	workflow_run_id\
	\'95	artifact_type\
	\'95	title\
	\'95	content\
	\'95	content_type\
	\'95	version\
	\'95	created_by_agent\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Task
\f1\b0\fs28 \
\
Unit of planned or executed work.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	project_id\
	\'95	workflow_run_id\
	\'95	title\
	\'95	description\
	\'95	status\
	\'95	sprint_number\
	\'95	sequence_order\
	\'95	assigned_engineer_slot_id\
	\'95	input_artifact_id\
	\'95	output_artifact_id\
	\'95	review_status\
	\'95	qa_status\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Approval
\f1\b0\fs28 \
\
Human gate on planning progression.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	project_id\
	\'95	workflow_run_id\
	\'95	artifact_id\
	\'95	status\
	\'95	requested_by\
	\'95	approved_by\
	\'95	notes\
	\'95	resolved_at\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 EngineerSlot
\f1\b0\fs28 \
\
Logical engineer seat for a workflow run.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	workflow_run_id\
	\'95	slot_key\
	\'95	assigned_agent_slug\
	\'95	responsibility_hint\
	\'95	sequence_order\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 AgentConfig
\f1\b0\fs28 \
\
Available backing model/tool.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	slug\
	\'95	display_name\
	\'95	role\
	\'95	provider\
	\'95	model\
	\'95	state\
	\'95	cost_weight\
	\'95	capability_tags\
	\'95	is_available_for_assignment\
	\'95	created_at\
	\'95	updated_at\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 CostEvent
\f1\b0\fs28 \
\
Simple token/cost ledger.\
\
Fields:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	id\
	\'95	project_id\
	\'95	workflow_run_id\
	\'95	task_id\
	\'95	agent_slug\
	\'95	provider\
	\'95	model\
	\'95	prompt_tokens\
	\'95	completion_tokens\
	\'95	total_tokens\
	\'95	cost_usd\
	\'95	extra\
	\'95	created_at\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 8. Workflow states
\f1\b0\fs28 \
\
Recommended states:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	draft\
	\'95	prd_ready\
	\'95	architecture_ready\
	\'95	awaiting_approval\
	\'95	planning_ready\
	\'95	execution_in_progress\
	\'95	review_in_progress\
	\'95	completed\
	\'95	failed\
\
These should remain simple and only change when truly needed.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 9. Artifact types
\f1\b0\fs28 \
\
Recommended artifact types:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	prd\
	\'95	architecture\
	\'95	sprint_plan\
	\'95	task_list\
	\'95	implementation_output\
	\'95	review_notes\
	\'95	qa_notes\
	\'95	demo_preview\
	\'95	general\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 10. MVP architecture
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 10.1 Backend
\f1\b0\fs28 \
\
Use FastAPI + SQLite + SQLAlchemy + Pydantic.\
\
The backend provides:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	project creation\
	\'95	planning endpoints\
	\'95	approval endpoints\
	\'95	sprint/task generation\
	\'95	engineer slot assignment\
	\'95	mock execution\
	\'95	review visibility\
	\'95	cost summary\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 10.2 Provider layer
\f1\b0\fs28 \
\
Use mocked providers first.\
\
Mock provider responsibilities:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	generate PRD for CPO\
	\'95	generate architecture for CTO\
	\'95	generate sprint plan for Tech Lead\
	\'95	generate task outputs for software engineers\
\
The provider layer should be swappable later, but do not overbuild it now.\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 10.3 UI
\f1\b0\fs28 \
\
Use the fastest possible UI that demonstrates the workflow.\
Preferred options:\
\pard\tqr\tx260\tx420\li420\fi-420\sl324\slmult1\sb240\partightenfactor0

\f3 \cf2 	1.	Streamlit\
	2.	simple FastAPI-served HTML\
\
The UI must allow the operator to:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	create project\
	\'95	view PRD\
	\'95	view architecture\
	\'95	approve/reject\
	\'95	view sprint plan and tasks\
	\'95	view engineer slots and assignments\
	\'95	trigger execution\
	\'95	inspect outputs and costs\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 11. Minimal endpoint surface
\f1\b0\fs28 \
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Projects
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	create project\
	\'95	list projects\
	\'95	get project\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Planning
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	generate PRD\
	\'95	generate architecture\
	\'95	submit for approval\
	\'95	approve\
	\'95	reject\
	\'95	get planning artifacts\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Sprinting
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	generate sprint plan\
	\'95	list tasks\
	\'95	list engineer slots\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Execution
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	execute next task\
	\'95	execute all tasks\
	\'95	get task details\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Agents
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	list agent configs\
	\'95	activate/bench/disable agent\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Summary
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	get project summary\
	\'95	get workflow run summary\
	\'95	get cost summary\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 12. Cost philosophy
\f1\b0\fs28 \
\
This MVP only needs simple cost awareness.\
\
Minimum requirements:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	every planning/execution call writes a CostEvent\
	\'95	cost can be seen at project level and run level\
	\'95	routing should prefer cheaper acceptable tools where reasonable\
	\'95	operator should be able to bench expensive tools manually\
\
Do not build enterprise billing logic.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 13. Quality philosophy
\f1\b0\fs28 \
\
Quality is controlled through:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	explicit approval gates\
	\'95	Tech Lead planning before execution\
	\'95	visible task outputs\
	\'95	lightweight review and QA states\
	\'95	ability to re-plan\
\
Do not build a massive QA framework in MVP.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 14. Progress measurement against business plan
\f1\b0\fs28 \
\
Every implementation task must be rated against the original business goal, not just against code completion.\
\
Use this rating rubric for every phase and major task:\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 14.1 Alignment score
\f1\b0\fs28 \
\
Score 1 to 5:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	5 = directly advances core product goal\
	\'95	4 = strongly supportive\
	\'95	3 = useful but not essential\
	\'95	2 = nice-to-have / deferable\
	\'95	1 = drift / not aligned\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 14.2 Delivery score
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	not started\
	\'95	in progress\
	\'95	demoable\
	\'95	validated\
	\'95	complete\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 14.3 Cost efficiency note
\f1\b0\fs28 \
\
For each feature/task, note whether it:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	reduces token usage\
	\'95	increases token usage slightly but is justified\
	\'95	significantly increases complexity/cost and should be deferred\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 14.4 Required implementation note format
\f1\b0\fs28 \
\
For any future coding batch, use:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	Business goal touched\
	\'95	Scope being implemented\
	\'95	Alignment score\
	\'95	Why now\
	\'95	What is explicitly not being built\
	\'95	Demoable outcome\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 15. Rules for future coding agents
\f1\b0\fs28 \
\
Any future coding agent must follow these rules:\
\pard\tqr\tx440\tx600\li600\fi-600\sl324\slmult1\sb240\partightenfactor0

\f3 \cf2 	1.	Treat this document as the canonical plan.\
	2.	Before coding, identify which section of this plan the work supports.\
	3.	State the alignment score before implementation.\
	4.	If a task is alignment score 1 or 2, do not implement without explicit approval.\
	5.	If a task expands the platform beyond the MVP, stop and flag it as scope drift.\
	6.	Every new phase must include:\
\pard\tqr\tx500\tx660\li660\fi-660\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	what business problem it solves\
	\'95	what user-visible behavior it unlocks\
	\'95	why it is necessary now\
	\'95	what remains intentionally deferred\
\pard\tqr\tx440\tx600\li600\fi-600\sl324\slmult1\sb240\partightenfactor0
\cf2 	7.	Do not invent enterprise features unless explicitly approved.\
	8.	Prefer the thinnest working version first.\
	9.	When uncertain, choose demoability over elegance.\
	10.	Update this plan when scope is formally changed.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 16. Definition of MVP success
\f1\b0\fs28 \
\
The MVP is successful if the operator can:\
\pard\tqr\tx440\tx600\li600\fi-600\sl324\slmult1\sb240\partightenfactor0

\f3 \cf2 	1.	enter a vision\
	2.	get a PRD\
	3.	get an architecture\
	4.	approve or reject\
	5.	get sprint/tasks\
	6.	see dynamic engineer slots assigned to tools\
	7.	run mocked task execution\
	8.	inspect outputs\
	9.	see simple token/cost summary\
	10.	re-plan and continue\
\
If those ten things work cleanly, the MVP is achieved.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 17. What is left after MVP
\f1\b0\fs28 \
\
Possible later phases, only after MVP is validated:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	real provider integrations\
	\'95	better routing heuristics\
	\'95	richer UI\
	\'95	persistent memory improvements\
	\'95	collaborative use\
	\'95	audit logs\
	\'95	auth/RBAC\
	\'95	telemetry\
	\'95	stronger deployment and production hardening\
\
These are optional future layers, not MVP requirements.\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 18. Current implementation status
\f1\b0\fs28 \
\
Status: reset requested\
\
Interpretation:\
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	prior architectural expansion should not be treated as binding\
	\'95	this document defines the new baseline\
	\'95	future work should start from this reduced scope\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f2\fs24 \cf0 \
\uc0\u11835 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f1\fs28 \cf2 \
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs34 \cf2 19. Change control
\f1\b0\fs28 \
\
Any scope change must be recorded here before coding proceeds.\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Proposed change format
\f1\b0\fs28 \
\pard\tqr\tx100\tx260\li260\fi-260\sl324\slmult1\sb240\partightenfactor0
\cf2 	\'95	Change title\
	\'95	Why it is needed\
	\'95	Business goal impact\
	\'95	Alignment score\
	\'95	Cost/complexity impact\
	\'95	Approved or rejected\
\
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\sl324\slmult1\pardirnatural\partightenfactor0

\f0\b\fs30 \cf2 Rule
\f1\b0\fs28 \
\
If it is not added here, it is not approved scope.}