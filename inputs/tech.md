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
- Platform Pod fully committed to Kafka migration until end of Q1 (~5 weeks)
- 2 senior engineers from Checkout Pod on PCI-DSS compliance audit until mid-Q2
- Personalisation Pod has 3 open reqs — operating at 6/9 capacity
