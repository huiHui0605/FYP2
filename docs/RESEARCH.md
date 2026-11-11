# Research notes and SDG alignment

Research inspected on **11 November 2026 (Malaysia time)**. This is a small public-project landscape review, not a systematic literature review or a claim of worldwide originality. Topic ordering, stars and GitHub descriptions do not establish academic quality or market demand.

## Sources actually inspected

The following GitHub topic pages and repository descriptions were retrieved successfully over HTTPS during implementation:

| Source | What was visible | Design lesson / difference |
|---|---|---|
| [Final-year-project topic](https://github.com/topics/final-year-project) | Project listings included resume analysis, health chatbots, gesture control, plant disease classification and attendance recognition | Familiar FYP directions exist; choose a system with a tangible end-to-end community workflow instead of another generic classifier |
| [Food-waste topic](https://github.com/topics/food-waste) | Listings included pantry management and surplus-food projects | SDG-focused software can combine ordinary transactions with clearly defined sustainability outcomes |
| [Repair-cafe topic](https://github.com/topics/repair-cafe) | Repair-oriented tools and community projects | Explore repair/reuse as the project domain; the topic label alone is not proof every listed project is a deployed repair cafe |
| [felixwanders/rustine](https://github.com/felixwanders/rustine) | Repository description: tool to help fix a bike | Domain-specific repair guidance is useful; LoopLocal instead coordinates people, requests, tools and event capacity |
| [KanadeK/fixyield](https://github.com/KanadeK/fixyield) | Description: auditable donor-part allocations across competing repair jobs | Repair decisions benefit from understandable records; LoopLocal records status history and explains volunteer scores |
| [KanadeK/parttrail](https://github.com/KanadeK/parttrail) | Description: local-first teardown journal and reverse-order reassembly checklist | Keeping repair knowledge with an item is useful; LoopLocal provides a selective public repair passport |
| [AngelHuang5335/pantrykind](https://github.com/AngelHuang5335/pantrykind) | Description: private self-hosted kitchen companion, tracking food and reducing waste, using Python/Django | Self-hosted sustainability software can avoid expensive external APIs |
| [deepakpadhi986/AI-Resume-Analyzer](https://github.com/deepakpadhi986/AI-Resume-Analyzer) | Description: resume parsing, keyword matching and recommendations | Recommendations need not be opaque; LoopLocal explicitly describes its rules and does not claim ML |

Only topic listings and repository descriptions were reviewed. These observations do **not** constitute running, auditing or exhaustively comparing those codebases. No reference implementation source was copied, and none of these projects is a dependency. The comparative statements describe LoopLocal's scope, not verified absence of features in those projects.

## SDG mapping

Authoritative reference: [UN Sustainable Development Goals](https://sdgs.un.org/goals) and [Goal 12](https://sdgs.un.org/goals/goal12).

The supplied UN URL was requested during implementation, but this cloud environment's restricted network returned an HTTP CONNECT 403. Its live text was therefore **not retrieved**. The mapping below uses the established wording/intent of Goal 12; the links are provided for direct verification. No claim is made that the UN endorses this application.

| Target | Relevance | Implemented evidence | Limit |
|---|---|---|---|
| 12.5 — substantially reduce waste generation through prevention, reduction, recycling and reuse by 2030 | Repair and shared tools can help keep existing goods in service | Completed repair count, estimated item weight, repair history, tool borrowing | A completed repair is not proof of displaced purchases or permanent waste prevention |
| 12.8 — information and awareness for sustainable development and lifestyles in harmony with nature | Practical repair learning and transparent information | Repair clinics, safety guidance, visible impact methodology | Learning outcomes have not been evaluated |

## Original contribution proposed

An integrated neighbourhood workflow combining **explainable skill/location/workload matching**, **transaction-safe tool sharing**, **capacity-limited repair learning**, and **privacy-conscious item passports**. This combination is the project hypothesis and engineering contribution. Do not present it as a patent-level novelty finding.

## Impact methodology

- Count only `tickets.status='repaired'`; one ticket is counted once. Existing records cannot transition back into a completed state repeatedly.
- Waste figure = sum of owner-estimated item weights in kg. It is more accurately “weight kept in use” than measured landfill diversion.
- Illustrative CO₂e = sum of repaired weight × category factor. Factors: Electronics 18, Appliances 12, Bicycles 6, Furniture 3, Textiles 8, Other 4 kg CO₂e/kg.
- **These factors were invented for a transparent demonstration scenario, not derived from a scientific lifecycle dataset.** They are not suitable for carbon accounting or credit claims.
- Real evaluation should record item material, baseline replacement likelihood, repair inputs, transport, useful-life extension and rebound effects; then use locally appropriate verified lifecycle datasets.
- Seeded records and screenshots represent a demonstration community, not field results.

## Follow-up academic research

For the final dissertation, conduct a documented search of peer-reviewed work on repair cafes, product passports, collaborative consumption, circular economy platforms and explainable recommendation. Record search terms, inclusion criteria, dates and limitations. Interview actual community stakeholders before claiming validated user requirements. The requirements in this repository are engineering assumptions for a runnable project, not invented interview findings.
