# Product: Zepto — Customer App & Checkout Experience

## Company
Zepto — India's leading quick commerce platform. Delivers groceries and essentials in 10 minutes via a network of dark stores. Series E funded, 8000+ employees across tech, ops, and business.

## Charter
Customer App & Checkout Experience — owns the end-to-end customer journey from browse to post-delivery, including search, cart, checkout, payment, order tracking, and refund flows.

## Current Scale
- 3M+ daily orders across 100+ Indian cities
- 700+ dark stores operational
- App MAU: 22M (iOS + Android + web)
- Avg order value: ₹520

## North Star Metrics
- Order Completion Rate (OCR): currently 84%, target 90%
- Checkout-to-Payment P95 latency: currently 4.2s, target <2s
- Refund Resolution Time: currently 48h, target <6h

## Key Product Gaps (known)
- Checkout flow has 3 unnecessary steps — high drop-off at payment page (~18%)
- Search relevance is poor for regional language queries (Hindi, Tamil, Telugu)
- Order tracking screen does not show real-time dark store packing status
- No proactive communication to customers when ETA changes post-order
- Refund flow is manual — CS agents process each ticket individually

## Planning Horizon (FY27)

**Q1 FY27 (Apr–Jun 2026):** Quick wins and search fixes
- Ship 1-click reorder (App Pod + OMS, 1 sprint)
- Ship proactive ETA alerts (App Pod + OMS, 1 sprint)
- Fix search 0-result rate via transliteration and regional synonyms (Search Pod, 2 sprints)
- Push notification copy refresh (App Pod, 1 sprint)
- Target: OCR +1%, search 0-result rate below 12%

**Q2 FY27 (Jul–Sep 2026):** Core conversion improvements
- Checkout flow redesign — Checkout + App Pod, 3 sprints (unblocked after PCI-DSS audit completes mid-Jul)
- Automated refunds for small orders — Checkout Pod, 1 sprint
- Real-time packing status — Order Management + App Pod, 2 sprints
- Q2 leadership review: demonstrate OCR +3%, checkout latency <2s, support ticket reduction

**Q3 FY27 (Oct–Dec 2026):** Personalisation and long-tail growth
- Personalised home screen — Personalisation Pod at full capacity, 3 sprints
- Real-time inventory display — Platform Pod (post-Kafka migration) + OMS Pod, 2 sprints
- Target: support ticket volume −25%, contribution margin improvement towards 6% threshold

## Competitive Context
- Blinkit: Strong on app UX, weak on tier-2 cities
- Swiggy Instamart: Strong on brand trust, slow tech iteration
- BB Now: Good on fresh produce, poor on app performance
