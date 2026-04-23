# Tech / Engineering Team — Context

## Team
VP Engineering (Karthik Anand) + 4 engineering managers + 48 engineers across 6 pods.
3-week sprints. Effective new-feature velocity: ~3 pods at a time (others on infra/debt).

## Pod Structure
- **App Pod** (iOS + Android + Web, 8 engineers): React Native + Next.js
- **Checkout & Payments Pod** (7 engineers): Go microservices, Razorpay + Juspay integration
- **Search & Discovery Pod** (6 engineers): Elasticsearch, ML ranking
- **Order Management Pod** (8 engineers): Core OMS, dark store sync
- **Platform Pod** (10 engineers): Infra, Kafka, observability
- **Personalisation Pod** (9 engineers): Recommendation engine, A/B infra

## Current Stack
- Backend: Go (primary), Python (ML services)
- Mobile: React Native
- Data streaming: Kafka
- DB: PostgreSQL + Redis + MySQL
- Search: Elasticsearch
- ML infra: Internal feature store + Vertex AI
## Active Problems
1. **Checkout latency P95 = 4.2s** — root cause: synchronous inventory check call to OMS on every page load; needs async caching layer
2. **Payment failure rate 2.1%** — UPI timeout after 30s; Juspay suggests reducing to 20s with retry logic
3. **Android crash rate 1.4%** on API level ≤29 (Android 10) during payment webview — affects ~18% of user base
4. **Search 0-result rate 21%** — Elasticsearch index not handling transliteration or common Hindi/Tamil synonyms

## Feasibility Notes
per previous notes. Additional note: 2 new engineers are joining next sprint.

## Capacity Constraints
- Platform Pod fully committed to Kafka migration until end of Q1 (~5 weeks, clears mid-May 2026)
- 2 senior engineers from Checkout Pod on PCI-DSS compliance audit until mid-July 2026 (Sprint 5)
- Personalisation Pod has 3 open reqs — operating at 6/9 capacity until Jun 2026; full capacity from Jul 2026

## Sprint Calendar (FY27)
3-week sprints:
- Sprint 1:  7 Apr – 25 Apr 2026  *(in progress)*
- Sprint 2: 28 Apr – 16 May 2026
- Sprint 3: 19 May –  6 Jun 2026
- Sprint 4:  9 Jun – 27 Jun 2026
- Sprint 5: 30 Jun – 18 Jul 2026
- Sprint 6: 21 Jul –  8 Aug 2026
- Sprint 7: 11 Aug – 29 Aug 2026
- Sprint 8:  1 Sep – 19 Sep 2026
- Sprint 9: 22 Sep –  9 Oct 2026
- Sprint 10: 12 Oct – 30 Oct 2026

## Pod Availability Windows
- App Pod: Available Sprint 1 onward (no blocking constraints)
- Checkout & Payments Pod: Reduced capacity until mid-Jul (Sprint 5); full team from Sprint 6 (21 Jul)
- Search & Discovery Pod: Available Sprint 1 onward
- Order Management Pod: Available Sprint 2 onward (Sprint 1: closing OMS config audit)
- Platform Pod: Kafka migration completes Sprint 2 (mid-May); available Sprint 3 onward
- Personalisation Pod: 6/9 capacity until Sprint 4 (Jun); full 9-engineer capacity from Sprint 5 (Jul)

## Estimated Delivery Windows
Based on pod availability, sprint count, and team sizing:
- **1-click reorder** — App Pod + Order Management Pod, 1 sprint → Apr–May 2026
- **Proactive ETA alerts** — App Pod + Order Management Pod, 1 sprint → May–Jun 2026
- **Search transliteration / regional language** — Search & Discovery Pod, 2 sprints → Apr–Jun 2026
- **Push notification copy refresh** — App Pod, 1 sprint → Apr–May 2026
- **Real-time packing status** — Order Management Pod + App Pod, 2 sprints → May–Jul 2026
- **Automated refunds for small orders** — Checkout Pod (post-PCI), 1 sprint → Jul–Aug 2026
- **Checkout flow redesign** — Checkout Pod + App Pod, 3 sprints, unblocked post-PCI → Jul–Sep 2026
- **Personalised home screen** — Personalisation Pod at full capacity, 3 sprints → Aug–Oct 2026
- **Real-time inventory display** — Platform Pod post-Kafka + Order Management Pod, 2 sprints → Jun–Aug 2026
