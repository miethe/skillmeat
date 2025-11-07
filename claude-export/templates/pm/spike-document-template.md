# SPIKE Document Template

<!--
Template Variables (configure in config/template-config.json):
- {{PROJECT_NAME}} - Project/organization name
- {{PROJECT_ARCHITECTURE}} - System architecture description
- {{LAYER_ARCHITECTURE}} - Detailed layer breakdown
- {{PROJECT_STANDARDS}} - Core standards and patterns
- {{CODE_QUALITY_STANDARDS}} - Quality requirements
- {{ADR_PATH}} - Architecture Decision Records location
- {{OBSERVABILITY_REQUIRED}} - Whether observability is required
-->

Use this template for technical research and feasibility analysis.

---

# SPIKE: [Feature/Decision Name]

**SPIKE ID**: `SPIKE-{YYYY-MM-DD}-{SHORT-NAME}`
**Date**: [YYYY-MM-DD]
**Author(s)**: [Agent coordination summary or team member names]
**Related Request**: [Link to original feature request or problem statement]
**Complexity**: [Small/Medium/Large/XL]
**Estimated Research Time**: [Hours/Days]

## Executive Summary

[2-3 sentences summarizing what was investigated, key findings, and recommended direction]

## Research Scope & Objectives

**Primary Questions:**
1. [Key question 1]
2. [Key question 2]
3. [Key question 3]

**Out of Scope:**
- [What was explicitly not investigated]

## Technical Analysis

### {{PROJECT_NAME}} Architecture Layer Impact

**UI Layer Changes:**
- [ ] New UI components required
- [ ] Existing component modifications
- [ ] State management updates
- [ ] Accessibility considerations

**API Layer Changes:**
- [ ] New endpoints required
- [ ] Existing endpoint modifications
- [ ] Request/response schema changes
- [ ] Error handling updates

**Service Layer Changes:**
- [ ] New business logic required
- [ ] Existing service modifications
- [ ] DTO schema changes
- [ ] Integration patterns

**Repository Layer Changes:**
- [ ] New data access patterns
- [ ] Query optimization requirements
- [ ] Security policy updates
- [ ] Pagination considerations

**Database Layer Changes:**
- [ ] Schema modifications required
- [ ] New tables/indexes needed
- [ ] Migration complexity assessment
- [ ] Performance impact analysis

**Infrastructure Changes:**
- [ ] Deployment updates needed
- [ ] Configuration changes required
- [ ] Monitoring/observability updates
- [ ] Security considerations

### Architecture Compliance Review

**{{PROJECT_NAME}} Pattern Adherence:**
- [ ] Follows {{PROJECT_ARCHITECTURE}}
- [ ] Uses standard error envelope for errors
- [ ] Implements pagination for lists
- [ ] Maintains authentication integration
- [ ] Uses standard UI components
- [ ] {{OBSERVABILITY_REQUIRED}} - Includes observability instrumentation

**Compliance Notes:**
[Any deviations from {{PROJECT_STANDARDS}} and justification]

### Alternative Approaches Considered

#### Approach A: [Name/Description]
- **Pros**: [Benefits of this approach]
- **Cons**: [Drawbacks and limitations]
- **Complexity**: [High/Medium/Low]
- **Risk**: [High/Medium/Low]
- **Decision**: [Selected/Rejected - with reason]

#### Approach B: [Name/Description]
- **Pros**: [Benefits of this approach]
- **Cons**: [Drawbacks and limitations]
- **Complexity**: [High/Medium/Low]
- **Risk**: [High/Medium/Low]
- **Decision**: [Selected/Rejected - with reason]

#### Recommended Approach: [Selected Approach]
**Rationale**: [Detailed explanation of why this approach was chosen]

## Implementation Design

### Phase 1: Foundation Layer (Database & Repository)
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] Schema design and migration scripts
- [ ] RLS policy implementation
- [ ] Repository interface definition
- [ ] Base CRUD operations
- [ ] Query optimization and indexing

**Key Decisions**:
- [Decision 1 with rationale]
- [Decision 2 with rationale]

### Phase 2: Service Layer (Business Logic)
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] DTO schema definitions
- [ ] Business logic implementation
- [ ] Service interface contracts
- [ ] Error handling patterns
- [ ] {{OBSERVABILITY_REQUIRED}} - Observability instrumentation

**Key Decisions**:
- [Decision 1 with rationale]
- [Decision 2 with rationale]

### Phase 3: API Layer (Routes & Validation)
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] Router endpoint implementation
- [ ] Request/response validation
- [ ] Error envelope compliance
- [ ] API documentation
- [ ] Authentication/authorization

**Key Decisions**:
- [Decision 1 with rationale]
- [Decision 2 with rationale]

### Phase 4: UI Layer (Components & Integration)
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] UI component creation/updates
- [ ] State management hooks
- [ ] API integration
- [ ] Accessibility implementation
- [ ] Mobile responsiveness

**Key Decisions**:
- [Decision 1 with rationale]
- [Decision 2 with rationale]

### Phase 5: Testing & Quality Assurance
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] Unit tests (per {{CODE_QUALITY_STANDARDS}})
- [ ] Integration tests for APIs
- [ ] Component tests with user interactions
- [ ] E2E tests for critical paths
- [ ] Performance/load testing
- [ ] Accessibility testing

### Phase 6: Documentation & Deployment
**Timeline**: [Estimated duration]
**Dependencies**: [Prerequisites]

- [ ] API documentation updates
- [ ] Component documentation
- [ ] User guides and help documentation (per {{DOC_POLICY}})
- [ ] Feature flag implementation
- [ ] {{OBSERVABILITY_REQUIRED}} - Monitoring and alerting setup
- [ ] Rollout plan execution

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Owner |
|------|--------|------------|-------------------|-------|
| [Risk description] | High/Med/Low | High/Med/Low | [Specific mitigation approach] | [Team/Person] |
| [Risk description] | High/Med/Low | High/Med/Low | [Specific mitigation approach] | [Team/Person] |
| [Risk description] | High/Med/Low | High/Med/Low | [Specific mitigation approach] | [Team/Person] |

## Performance Implications

**Expected Performance Impact:**
- [ ] Database query performance: [Positive/Negative/Neutral]
- [ ] API response times: [Positive/Negative/Neutral]
- [ ] Frontend rendering: [Positive/Negative/Neutral]
- [ ] Overall system load: [Positive/Negative/Neutral]

**Benchmarks and Targets:**
- [Specific performance targets and how they'll be measured]

**Optimization Strategies:**
- [Approaches for maintaining/improving performance]

## Security Implications

**Security Assessment:**
- [ ] Authentication patterns maintained
- [ ] Authorization properly implemented
- [ ] Data access controls enforced
- [ ] PII handling compliant
- [ ] Input validation comprehensive
- [ ] Output sanitization proper

**Security Decisions:**
- [Key security decisions and rationale]

## Success Criteria

**Functional Success Criteria:**
- [ ] [Specific functional outcome 1]
- [ ] [Specific functional outcome 2]
- [ ] [Specific functional outcome 3]

**Non-Functional Success Criteria:**
- [ ] Performance targets met
- [ ] Security standards maintained
- [ ] Accessibility compliance achieved
- [ ] Architecture patterns followed
- [ ] Code quality standards met

**Business Success Criteria:**
- [ ] [Business metric target 1]
- [ ] [Business metric target 2]
- [ ] [User satisfaction target]

## Effort Estimation

**Development Time Breakdown:**
- Database Layer: [X days/hours]
- Repository Layer: [X days/hours]
- Service Layer: [X days/hours]
- API Layer: [X days/hours]
- UI Layer: [X days/hours]
- Testing: [X days/hours]
- Documentation: [X days/hours]
- **Total Estimated Effort**: [X days/hours]

**Confidence Level**: [High/Medium/Low]

**Factors Affecting Estimate:**
- [Factor 1 and impact]
- [Factor 2 and impact]

## Dependencies & Prerequisites

**Internal Dependencies:**
- [MP system/component dependencies]

**External Dependencies:**
- [Third-party service/library dependencies]

**Team Dependencies:**
- [Skills, availability, coordination needs]

**Infrastructure Dependencies:**
- [Platform, deployment, configuration needs]

## Recommendations

### Immediate Actions Required
1. [Specific actionable recommendation with owner and timeline]
2. [Specific actionable recommendation with owner and timeline]
3. [Specific actionable recommendation with owner and timeline]

### Architecture Decision Records Needed
- **ADR Topic**: [Decision topic]
  - **Rationale**: [Why this needs an ADR]
  - **Timeline**: [When to create]
  - **Location**: {{ADR_PATH}}

### Follow-up Research Questions
- **Question**: [Research question]
  - **Approach**: [Suggested research approach]
  - **Priority**: [High/Medium/Low]

### Go/No-Go Recommendation
**Recommendation**: [Proceed/Do Not Proceed/Proceed with Modifications]

**Rationale**: [Detailed explanation supporting the recommendation]

**Conditions for Proceeding** (if applicable):
- [Condition 1]
- [Condition 2]

## Appendices

### A. Expert Consultation Summary
[Summary of insights from domain expert coordination, including which experts were consulted and key insights gained]

### B. Code Examples/Prototypes
```typescript
// Example code snippets or proof-of-concept implementations
```

### C. Reference Materials
- [Documentation links]
- [Research articles]
- [Prior art references]
- [Competitive analysis links]

### D. Decision Log
| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| [Date] | [Decision made] | [Why it was made] | [How it affects implementation] |

---

**SPIKE Template Version**: 1.0
**Last Updated**: [Date]
**Next Review**: [Date - when this SPIKE should be reviewed/updated]

**Sign-off:**
- Technical Lead: _________________ Date: _________
- Product Owner: _________________ Date: _________
- Architecture Review: _________________ Date: _________ (if required)
