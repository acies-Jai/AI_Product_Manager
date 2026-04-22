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
- DB: PostgreSQL + Redis
- Search: Elasticsearch
- ML infra: Internal feature store + Vertex AI

## Active Problems
1. **Checkout latency P95 = 4.2s** — root cause: synchronous inventory check call to OMS on every page load; needs async caching layer
2. **Payment failure rate 2.1%** — UPI timeout after 30s; Juspay suggests reducing to 20s with retry logic
3. **Android crash rate 1.4%** on API level ≤29 (Android 10) during payment webview — affects ~18% of user base
4. **Search 0-result rate 21%** — Elasticsearch index not handling transliteration or common Hindi/Tamil synonyms

## Feasibility Notes
- **1-click reorder**: 1–2 sprints. Cart service already supports saved carts.
- **Automated refund for small orders**: 2–3 sprints. Rule engine + payment gateway refund API already wired.
- **Proactive ETA alerts**: 2 sprints. Kafka event for ETA change exists; just needs notification dispatch.
- **Checkout flow redesign (reduce steps)**: 4–5 sprints. Requires FE + BE + design alignment.
- **Regional language search**: 3–4 sprints. Elasticsearch synonym config + transliteration plugin.
- **Real-time order tracking (packing status)**: 3 sprints. Dark store tablet app already pushes events to Kafka.
- **Personalised home screen**: 5–6 sprints. Personalisation pod has model ready; FE integration pending.

## Capacity Constraints
- Platform Pod fully committed to Kafka migration until end of Q1 (~5 weeks)
- 2 senior engineers from Checkout Pod on PCI-DSS compliance audit until mid-Q2
- Personalisation Pod has 3 open reqs — operating at 6/9 capacity
