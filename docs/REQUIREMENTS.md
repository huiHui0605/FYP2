# Software requirements specification

## Goal, stakeholders and assumptions

Enable residents at a Malaysian community hub to keep items in use by coordinating volunteer repair, tool borrowing and practical learning. Stakeholders: residents, self-declared repair volunteers, hub administrators and public passport readers. The initial deployment serves one organisation with neighbourhood labels, not a multi-tenant marketplace. There are no payments, transport bookings or external identity providers.

All user requirements here are **proposed assumptions**; no stakeholder interviews or acceptance studies are claimed.

## Functional requirements and acceptance criteria

| ID | Requirement | Acceptance criterion / verification |
|---|---|---|
| FR01 | Account registration and login | Resident/fixer registration works; duplicate email and admin self-registration are rejected; password is hashed |
| FR02 | Role and object authorization | Residents cannot read another resident's repair; unassigned volunteers can only see open requests; staff can moderate |
| FR03 | Repair submission | Category, neighbourhood, description, finite positive weight and safety answer are validated; hazardous items rejected |
| FR04 | Explainable suggestions | Up to three active volunteers sorted by the documented score with skill, locality and workload explanations |
| FR05 | Exclusive repair claims | Matching self-declared skill required, no self-claim, three-active-repair limit; concurrent claims produce exactly one assignment |
| FR06 | Repair workflow | Only legal state transitions; owners can cancel but cannot mark completed; completion requires substantive notes |
| FR07 | Repair discussion | Only owner, assigned volunteer and administrators may post; messages are escaped and time-stamped |
| FR08 | Item passport | Only repaired tickets resolve to a public passport; personal identity, neighbourhood and free-text notes omitted; browser print supported |
| FR09 | Tool reservation | Capacity checked for each inclusive day, up to seven inclusive calendar days, within 90 days; overlaps and duplicate reservations blocked |
| FR10 | Tool custody | Only administrators check out/return; only reserved dates permit checkout; an actual unreturned copy cannot be handed out twice |
| FR11 | Clinics | Admin creates future events with capacity; members join/leave; duplicates, over-capacity and cancelled/past events rejected |
| FR12 | Notifications | Assignment, messages, repair status, loan changes and clinic registration/cancellation generate private in-app notices |
| FR13 | Impact | Only completed repairs contribute weight and scenario emissions; methodology and demo limitations visible |
| FR14 | Admin export | CSV includes completed-repair IDs, categories, weights and scenario estimates; personal identities omitted |
| FR15 | Administration | Add/retire tools, enable/disable non-admin accounts, review repairs and recent audit records |
| FR16 | Account maintenance | Members edit name/location/skills and change password with current password verification; inactive sessions lose access |
| FR17 | Discovery | Repair title/category search and status filtering; tool title/category search |
| FR18 | Persistent state | Restarting services preserves database content; initialization and demo seeding are repeatable |

## Nonfunctional requirements

| ID | Requirement | Mechanism / scope |
|---|---|---|
| NFR01 | Security by default | scrypt password hashes, parameterized SQL, Jinja escaping, CSRF tokens on POST, HttpOnly/SameSite cookies, CSP and frame blocking |
| NFR02 | Transactional consistency | SQLite foreign keys, constraints, WAL and `BEGIN IMMEDIATE` on writes; tests race claims, stock and clinic places |
| NFR03 | Basic abuse resistance | 15 failed login attempts per direct client IP per 15 minutes; input length and request-size limits; reverse-proxy hardening still required |
| NFR04 | Privacy | Private repair conversations; public passport projection excludes sensitive fields; CSV has no personal identifiers |
| NFR05 | Usability | Responsive layout, labels, focus outlines, skip link, empty/error states; desktop/mobile smoke tests; no formal WCAG certification claimed |
| NFR06 | Deployability | Python 3.12+, no external services or keys; pinned dependencies, setup/start scripts, health endpoint, CI workflow |
| NFR07 | Transparency | Explainable matching and explicitly hypothetical environmental estimates |
| NFR08 | Maintainability | App factory, schema, template/static separation, isolated fixtures, requirements traceability and operational documentation |

## Role access matrix

| Action | Resident | Volunteer | Administrator | Anonymous |
|---|---|---|---|---|
| Register/login | Yes | Yes | CLI creation | Yes |
| Submit own repair | Yes | Yes | Yes | No |
| See repair | Own | Own, assigned, open community | All | No |
| Claim | No | Skill match, not own, capacity | No | No |
| Update repair | Cancel own | Assigned work / cancel own | Moderate | No |
| Private discussion | Own | Own/assigned | All | No |
| Reserve tools/join clinic | Yes | Yes | Yes | No |
| Check out/return tools | No | No | Yes | No |
| Publish/cancel clinic | No | No | Yes | No |
| Read public repaired passport | Yes | Yes | Yes | Yes |
| Export/administer | No | No | Yes | No |

## Use case: complete a repair

Precondition: resident has submitted a non-hazardous item. Volunteer has a matching skill and fewer than three active jobs. Main flow: discover → view item and safety answer → claim → private clarification → mark in progress → perform actual repair outside the system → document checks → mark repaired → share passport. Alternative outcomes: owner cancels; assigned operator records unrepairable; unsafe item is referred to a professional. System status does not certify real-world safety.

## Use case: borrow a tool

Resident searches catalogue and selects collection/return dates. Server checks each day, duplicate reservations and overdue custody under a write lock. Successful reservation becomes `reserved`. Hub staff checks the borrower's booking and physically available copy, then records `collected`. After inspection on return, staff records `returned`. Reservations may be cancelled before collection; collected loans cannot be cancelled to hide unreturned inventory.

## Out of scope / future work

Professional verification, payments, deposits, warranties, route maps, image uploads, email/SMS, email verification and password-reset delivery, self-service account deletion, multi-hub tenancy, chat streaming, calibrated LCA, automatic external certification, offline sync and formal research validation. These are not represented as working features.
