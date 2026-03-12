Based on the design specification `ownership-resolution-and-membership-semantics.md` and the 3-tier enterprise governance architecture previously discussed, here is a structured review of the proposed Ownership Resolution layer.

### 1. Overall Design Notes

The specification correctly identifies a critical architectural risk: **overloading the `AuthContext` with state**. In enterprise environments, a user’s authentication (who they are, what tenant they belong to) should remain separate from their active authorization scope (which team they are acting on behalf of at this exact second).

By proposing a dedicated **Ownership Resolution** layer between authentication and the repository/data layer, the design successfully prevents the core auth middleware from becoming bloated and deeply coupled to product-specific team routing. This layered approach ensures that the database repositories only have to answer "does this user's current resolved context have permission to view/edit this `owner_id`?"

**Primary Gap in Overall Design:** The design does not explicitly address **query performance and N+1 risks** regarding visibility filtering. In a 3-tier architecture, a single user could be part of 1 Enterprise, 5 Teams, and 1 User scope. When querying `GET /artifacts`, the Ownership Resolver must be able to compile the user's entire accessible graph of `owner_id`s and inject them into the SQLAlchemy repository as a single `WHERE owner_id IN (...)` clause to prevent massive database overhead.

---

### 2. Review of Open Design Questions

### Q1. What exact `owner_id` value should represent enterprise ownership?

**Recommendation:** Use the `tenant_id`.

In a multi-tenant SaaS architecture, the "Enterprise" boundary is fundamentally defined by the tenant. By setting `owner_id = tenant_id` when `owner_type = 'enterprise'`, you achieve several immediate benefits:

* **Zero-Lookup Resolution:** The `tenant_id` is already present on the lightweight `AuthContext` (derived from the auth token). The backend does not need to query an `enterprises` or `organizations` table to figure out what the top-level `owner_id` should be.
* **Query Simplicity:** When the `OwnershipResolver` builds its visibility graph, the enterprise scope is simply resolved as `WHERE (owner_type = 'enterprise' AND owner_id = :tenant_id)`.

### Q2. Should enterprise-owned resources default to a particular visibility?

**Recommendation:** They should default to `Private` upon creation, moving to an `Enterprise` (or `Tenant`) visibility upon publication.

* **Why Private first?** Enterprise governance artifacts (like a standardized `CLAUDE.md` security policy) often require drafting and review by `system_admin`s before they are forcefully rolled out to thousands of developers. `Private` ensures the draft is only visible to the authoring admin.
* **Why not default to Team?** Applying `Team` visibility to an `Enterprise`-owned artifact is a domain mismatch and should be rejected by the validation layer.

### Q3. Does the product need a distinct `enterprise` visibility mode later, or is owner_type + current visibility enough?

**Recommendation:** Yes, the product **must** introduce a distinct `Enterprise` (or `Tenant`) visibility mode in the database schema.

Currently, the system uses `Private`, `Team`, and `Public`. Relying on the combination of `owner_type: enterprise` + `visibility: Public` to mean "available to everyone in the organization" is a dangerous anti-pattern.

* **The "Public" Trap:** If SkillMeat eventually introduces a true community marketplace (allowing users to share templates across different companies on the internet), `Public` must strictly mean "Internet Public."
* **The Solution:** Expand the visibility enum to `ENUM('Private', 'Team', 'Enterprise', 'Public')`.
* `Private`: Accessible only to the author.
* `Team`: Accessible to the resolved `team_id`.
* `Enterprise`: Accessible to anyone matching the `tenant_id`.
* `Public`: Accessible across the platform, regardless of `tenant_id`.

By creating an explicit `Enterprise` visibility mode, your `OwnershipResolver` logic becomes highly explicit and immune to accidental data leaks between tenants.

**Q4. Which APIs should accept implicit team inference versus requiring explicit owner selection?**

* **Analysis:** Implicit inference is highly dangerous in a 3-tier model. If a developer uses a CLI command or API to deploy an artifact, and the system "guesses" their team based on their last active session, they could easily leak a private `User` artifact into a shared `Team` collection, or overwrite an `Enterprise` policy if they have admin rights.
* **Recommendation:** * **Explicit Selection (Mandatory):** Any API that performs a mutation (`POST`, `PUT`, `PATCH`, `DELETE`) *must* require an explicit `owner_type` and `owner_id` in the payload or path. No guessing allowed.
* **Implicit Inference (Allowed):** Read-only aggregation APIs (e.g., `GET /artifacts`, `GET /search`) can implicitly infer context by resolving *all* the scopes the user has access to, returning a merged view of Enterprise + Team + User artifacts.


**Q5. Should resolved ownership context be cached per request only, or also per short-lived session?**

* **Analysis:** Caching ownership context at the session level creates a security vulnerability known as "stale authorization." If an Enterprise admin demotes a user from `team_admin` to `viewer`, a session-level cache might allow them to continue modifying artifacts until their session expires. Conversely, resolving the database graph fresh on every single request can choke the database.
* **Recommendation:** Cache the *membership graph* using a fast, centralized store (e.g., Redis) rather than tying it to the HTTP session. The application should resolve the graph at the dependency-injection layer *per request* by checking the Redis cache. This provides sub-millisecond lookups while allowing you to instantly invalidate the specific user's Redis key the moment their team membership is changed in the admin panel.

---

### 3. Review of Immediate Recommendations

The spec suggests not blocking the current **SkillBOM** foundation work, but mandates setting up `enterprise` enums, the resolver abstraction, and API semantics before Phase 4/7 proceeds.

**Is this the right approach?**
**Yes. This is a sound, agile technical strategy.** SkillBOM's core value is cryptographic tracking and attestation history. It can function effectively in the short term using the existing `User` and `Team` owner types. Blocking SkillBOM to rewrite the entire auth middleware would needlessly stall product momentum.

**Gap Coverage for the Prerequisites (Before Phase 4/7):**

1. **`enterprise` enum support:** Do this immediately in the database schemas (`owner_type: ENUM('user', 'team', 'enterprise')`) and Pydantic DTOs. Even if the logic isn't wired up yet, getting the schema migrated prevents a painful database refactor later when the SkillBOM tables are full of data.
2. **Clear API semantics for owner selection:** Establish a standard HTTP header pattern for the web UI/CLI to announce their context to the backend. For example, `X-SkillMeat-Scope-Type` and `X-SkillMeat-Scope-ID`. The new Ownership Resolver can read these headers, validate them against the AuthContext, and pass the resolved scope down to the repositories.
3. **Membership-aware visibility filtering:** When building the `OwnershipContextService`, ensure it returns a structured dataclass (e.g., `ResolvedScope(active_owner_id: UUID, readable_owner_ids: List[UUID], role: RoleEnum)`). This allows the repository layer to apply a clean SQL filter rather than doing Python-level loops over returned data.