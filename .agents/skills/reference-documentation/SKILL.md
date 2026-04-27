# reference_documentation

## Name
`reference_documentation`

## Description
Efficient schema, dataset, and API specification reference. When users ask about features, changes, or integrations involving data structures, endpoints, or compliance requirements, consult this skill to find the exact document without scanning all PDFs. Saves context and API tokens by mapping queries directly to source material.

## When to Use This Skill

Trigger this skill when the user's question involves:
- **Schema questions**: "What fields are in this data structure?"
- **Data structure changes**: "How do I modify the response format?"
- **Dataset specifications**: "What's the exact format of [data]?"
- **API endpoints**: "What parameters does [endpoint] accept?"
- **Feed formats**: "How is [message] structured?"
- **Compliance requirements**: "What are the compliance specs?"
- **Integration details**: "How do I parse [data type]?"
- **Service definitions**: "What does this service return?"

**Do NOT trigger if**: User is asking general questions, troubleshooting code logic, or needs conceptual explanation without schema detail.

---

## Document Index & Mapping

### 📄 Document 1: Development Guide
**File**: `./docs/transportnsw_documentations/How to Use Open Data to Develop an Application _ Transport Open Data.pdf`  
**Location**: `./docs/transportnsw_documentations/How to Use Open Data to Develop an Application _ Transport Open Data.pdf`  
**Size**: ~1MB | **Pages**: ~25  

**When to Reference**:
- Getting started with the ecosystem
- Understanding API authentication basics
- Learning what services are available
- Initial setup and prerequisites

**Key Sections** (for quick navigation):
- Introduction to TfNSW APIs
- Getting Started Guide
- Available Services Overview
- Authentication Basics
- Data Format Overview
- Best Practices

**Not useful for**: Detailed schema, exact field definitions, protocol specifications

---

### 📄 Document 2: Real-Time Train Technical Document
**File**: `./docs/transportnsw_documentations/Real Time Train Technical Document v3_6_open data_0.pdf`  
**Location**: `./docs/transportnsw_documentations/Real Time Train Technical Document v3_6_open data_0.pdf`  
**Size**: ~4.6MB | **Pages**: ~120  

**When to Reference** (⭐ Most important for schema questions):
- Real-time vehicle position data structure
- Train operational state definitions
- Feed message formats and updates
- Message encoding and parsing requirements
- Vehicle status codes and meanings
- Real-time data performance specifications
- Feed refresh rates and latency requirements

**Key Sections** (where schema lives):
- Real-Time Data Overview
- Message Format Specifications
- Vehicle State Definitions
- Feed Update Protocols
- Data Structure & Encoding
- Operational Status Codes
- Implementation Examples

**Query Examples That Route Here**:
- "What fields does a vehicle position message contain?"
- "What are the possible vehicle states?"
- "How often is the feed updated?"
- "What's the exact structure of a real-time update?"
- "How do I parse the vehicle location data?"

---

### 📄 Document 3: Trip Planner API Manual
**File**: `./docs/transportnsw_documentations/Trip Planner API manual-opendataproduction v3.2.pdf`  
**Location**: `./docs/transportnsw_documentations/Trip Planner API manual-opendataproduction v3.2.pdf`  
**Size**: ~5.2MB | **Pages**: ~100  

**When to Reference** (⭐ For API endpoints and request/response schemas):
- Trip search API endpoints and parameters
- Request payload structure
- Response data structure and fields
- HTTP status codes and error responses
- Rate limiting and quota specifications
- Request/response examples
- Data types and field validations
- Optional vs required parameters

**Key Sections** (where API schemas live):
- API Endpoints Reference
- Request Parameter Specifications
- Response Structure Documentation
- Error Codes & Meanings
- Data Type Definitions
- Field Validation Rules
- Request/Response Examples
- Rate Limits & Quotas

**Query Examples That Route Here**:
- "What parameters does the trip search endpoint accept?"
- "What's in the trip search response?"
- "What are the valid values for [parameter]?"
- "How do I structure a trip request?"
- "What error codes can this API return?"
- "Are these fields required or optional?"
- "What's the rate limit for this endpoint?"

---

### 📄 Document 4: GTFS-R Implementation Specification
**File**: `./docs/transportnsw_documentations/TfNSW GTFS  GTFS R Implementation Specification v2 June 2025.pdf`  
**Location**: `./docs/transportnsw_documentations/TfNSW GTFS  GTFS R Implementation Specification v2 June 2025.pdf`  
**Size**: ~8.6MB | **Pages**: ~150+  

**When to Reference** (⭐ For format standards and compliance):
- GTFS-R protocol buffer definitions
- Static schedule data structure (GTFS)
- Real-time feed message structure (GTFS-R)
- Service calendar and schedule format
- Stop definitions and sequences
- Alert and advisory message formats
- Feed validity and compliance requirements
- Protocol buffer field specifications

**Key Sections** (where data standards live):
- GTFS & GTFS-R Overview
- Schedule Data Format (GTFS)
- Real-Time Message Format (GTFS-R)
- Service Calendar Definitions
- Stop & Route Definitions
- Alert Protocol Specifications
- Feed Message Structure
- Compliance & Validation Rules
- Protocol Buffer Definitions

**Query Examples That Route Here**:
- "What's the GTFS-R format for [message type]?"
- "How do I structure a service calendar?"
- "What fields are required in a GTFS stop definition?"
- "What's the protocol buffer definition for [entity]?"
- "How are alerts encoded in GTFS-R?"
- "What compliance requirements apply?"
- "How is schedule data organized in GTFS?"

---

## Quick Reference: Query Routing Map

| User Query Type | Route To | Why |
|---|---|---|
| "What fields in vehicle data?" | Real-Time Train Doc | Contains exact message structures |
| "How to structure API request?" | Trip Planner API Manual | Has request schemas |
| "What's the API response?" | Trip Planner API Manual | Response format documented |
| "GTFS-R format for [X]?" | GTFS-R Specification | Protocol specifications |
| "What are valid vehicle states?" | Real-Time Train Doc | Status codes defined |
| "Schedule data structure?" | GTFS-R Specification | GTFS standard specs |
| "API parameters & validation?" | Trip Planner API Manual | Parameter specs |
| "How to parse real-time feed?" | Real-Time Train Doc | Feed encoding explained |
| "Alert message structure?" | GTFS-R Specification | Alert definitions |
| "Rate limits?" | Trip Planner API Manual | Quota specs |

---

## Content Mapping: What's Actually In Each Document

### Real-Time Train Technical Document
**Contains exact schemas for**:
```
Vehicle Position Message
├─ Timestamp
├─ Vehicle ID
├─ Latitude/Longitude
├─ Bearing
├─ Speed
├─ Status Code
├─ Journey Info
└─ Additional Fields

Vehicle Status Enum
├─ Stopped
├─ In Motion
├─ Cancelled
├─ Diverted
└─ [Complete list]

Feed Update Message
├─ Timestamp
├─ Vehicle Updates (array)
├─ Service Alerts
└─ Metadata
```

**DO NOT look here for**: API endpoint parameters, GTFS standards

---

### Trip Planner API Manual
**Contains exact schemas for**:
```
Trip Search Request
├─ origin (required)
├─ destination (required)
├─ departTime (optional)
├─ preferredModes (optional)
├─ accessibilityOptions (optional)
├─ maxTransfers (optional)
└─ [Complete parameter list]

Trip Search Response
├─ trips (array)
│  ├─ legs (array)
│  │  ├─ startTime
│  │  ├─ endTime
│  │  ├─ mode
│  │  ├─ route
│  │  └─ stops
│  ├─ duration
│  └─ accessibility
├─ metadata
└─ errors

HTTP Status Codes
├─ 200: Success
├─ 400: Bad Request (with field errors)
├─ 401: Unauthorized
├─ 429: Rate Limited
└─ 500: Server Error
```

**DO NOT look here for**: Real-time vehicle data, GTFS standards

---

### GTFS-R Specification
**Contains exact schemas for**:
```
Static GTFS Data
├─ stops.txt
├─ routes.txt
├─ trips.txt
├─ stop_times.txt
├─ calendar.txt
└─ [Full format specification]

GTFS-Realtime Message Structure
├─ FeedMessage
│  ├─ header (FeedHeader)
│  └─ entity (repeated FeedEntity)
│     ├─ id
│     ├─ vehicle (VehiclePosition)
│     ├─ alert (Alert)
│     └─ tripUpdate (TripUpdate)

VehiclePosition (Protocol Buffer)
├─ trip_id
├─ vehicle (VehicleDescriptor)
├─ position (Position)
├─ current_stop_sequence
├─ current_status
└─ timestamp

Alert Message Structure
├─ active_period
├─ informed_entity
├─ cause
├─ effect
├─ url
└─ description

Service Calendar Format
├─ service_id
├─ monday through sunday (0/1)
├─ start_date
└─ end_date
```

**DO NOT look here for**: API request/response, real-time vehicle field specifics

---

## How to Use This Skill Effectively

### Step 1: Identify Query Type
When user asks about schema/dataset:
- Is it about **real-time vehicle data**? → Real-Time Train Doc
- Is it about **API endpoints/requests/responses**? → Trip Planner API Manual
- Is it about **GTFS standards/compliance**? → GTFS-R Specification
- Is it about **getting started**? → Development Guide

### Step 2: Reference Correct Document
Point user to exact section of correct PDF.

**Example workflow**:
```
User: "What fields does a vehicle position message have?"
→ Route to: Real-Time Train Technical Document
→ Section: "Message Format Specifications"
→ Deliver: Exact field list with types and descriptions
```

### Step 3: Save Tokens by Being Direct
Don't scan all 4 documents. Use this index to go directly to the right one.

---

## Document Selection Logic

**Decision Tree for Routing**:

```
Is the question about...?

REAL-TIME VEHICLE DATA?
├─ YES: Vehicle position, status, updates
├─ DOCUMENT: Real-Time Train Technical Doc
└─ SECTIONS: Message Format, Status Codes, Feed Structure

API ENDPOINTS / REQUESTS / RESPONSES?
├─ YES: Trip search, parameters, response fields
├─ DOCUMENT: Trip Planner API Manual
└─ SECTIONS: Endpoints, Request Schema, Response Schema

GTFS STANDARDS / PROTOCOLS / SCHEDULE DATA?
├─ YES: Feed format, schedule, protocols, compliance
├─ DOCUMENT: GTFS-R Specification
└─ SECTIONS: Data Format, Protocol Buffer, Service Calendar

GENERAL OVERVIEW / GETTING STARTED?
├─ YES: What services exist, how to begin
├─ DOCUMENT: Development Guide
└─ SECTIONS: Overview, Getting Started

NONE OF THE ABOVE?
└─ This is NOT a schema question - consult general documentation
```

---

## Field Reference: Where Each Schema Lives

**Real-Time Vehicle Position**
- Document: Real-Time Train Technical Doc
- Section: "Data Structure & Encoding" or "Message Format"
- Contains: All fields, types, valid values, descriptions

**Trip Search API Request**
- Document: Trip Planner API Manual
- Section: "Request Parameter Specifications"
- Contains: All parameters, required/optional, types, validation

**Trip Search API Response**
- Document: Trip Planner API Manual
- Section: "Response Structure Documentation"
- Contains: All response fields, nested structure, data types

**GTFS Schedule Data**
- Document: GTFS-R Specification
- Section: "Schedule Data Format (GTFS)"
- Contains: All GTFS files, fields, format specifications

**GTFS-Realtime Messages**
- Document: GTFS-R Specification
- Section: "Real-Time Message Format (GTFS-R)"
- Contains: Protocol buffer definitions, message structures

**Vehicle Status Codes**
- Document: Real-Time Train Technical Doc
- Section: "Operational Status Codes"
- Contains: All possible status values and meanings

**API Error Codes**
- Document: Trip Planner API Manual
- Section: "Error Codes & Meanings"
- Contains: HTTP status codes, error response format

**Rate Limits & Quotas**
- Document: Trip Planner API Manual
- Section: "Rate Limits & Quotas"
- Contains: Request limits, quota specifications

---

## Implementation Notes for AI Agents

When using this skill:

1. **Never say "scanning all documents"** - Be direct: "According to [Document Name], [Schema Detail]"

2. **Always cite the section** - "In the Real-Time Train Technical Document, under Message Format Specifications..."

3. **Copy exact schema** - Don't paraphrase field definitions; quote the exact specification

4. **Include types & constraints** - When describing fields, include data type, format, valid values, required/optional

5. **Link to document** - "See page X of [Document Name]" if multiple references needed

6. **Token-efficient** - Use this index to avoid fetching irrelevant documents

---

## Common Schema Questions & Routing

| Question | Route | Document Section |
|---|---|---|
| "What's in a vehicle position?" | Real-Time Train Doc | Message Format Specifications |
| "Required parameters for trip search?" | Trip Planner API | Request Parameter Specs |
| "Vehicle status options?" | Real-Time Train Doc | Operational Status Codes |
| "Response format for trip search?" | Trip Planner API | Response Structure Docs |
| "GTFS stop definition?" | GTFS-R Spec | Schedule Data Format (GTFS) |
| "GTFS-R alert structure?" | GTFS-R Spec | Alert Protocol Specifications |
| "API error responses?" | Trip Planner API | Error Codes & Meanings |
| "Feed update frequency?" | Real-Time Train Doc | Feed Update Protocols |
| "Rate limit rules?" | Trip Planner API | Rate Limits & Quotas |
| "Schedule calendar format?" | GTFS-R Spec | Service Calendar Definitions |

---

## Context Preservation

This skill's purpose is to **eliminate document scanning** and **preserve context tokens**.

Instead of:
```
Agent: Let me search all 4 documents for vehicle position fields...
[scans Real-Time Doc, Trip Planner, GTFS, Guide]
Found it in Real-Time Doc section X...
```

Do this:
```
Agent: User asked about vehicle position fields.
Reference: Real-Time Train Technical Document, "Message Format Specifications"
Response: [Direct answer with exact schema]
```

**Tokens saved per query**: ~500-2000 tokens (depending on document size)

---

## File Paths for Direct Access

```
./docs/transportnsw_documentations/How to Use Open Data to Develop an Application _ Transport Open Data.pdf
./docs/transportnsw_documentations/Real Time Train Technical Document v3_6_open data_0.pdf
./docs/transportnsw_documentations/Trip Planner API manual-opendataproduction v3.2.pdf
./docs/transportnsw_documentations/TfNSW GTFS  GTFS R Implementation Specification v2 June 2025.pdf
```

---

## Versioning & Maintenance

- **Version**: 1.0
- **Created**: April 2026
- **Status**: Production
- **Last Updated**: April 2026
- **Documents Covered**: 4 TfNSW Transport API docs
- **Scope**: Schema, dataset, API specification reference

When documents update, revise this skill's sections accordingly.

---

## Summary

This skill provides a **direct index** to schema and dataset information across 4 documents. Use it to:
- ✅ Find exact data structures without scanning all PDFs
- ✅ Answer schema questions with precise citations
- ✅ Save API tokens by avoiding irrelevant fetches
- ✅ Preserve context for follow-up questions
- ✅ Provide authoritative specification answers

**Never scan all documents when one will do.**