# Plan: Social Commerce Conversation Data

> Created: 2026-06-09
> Status: ❌ Not started
> Origin: `analytics_improvement_opportunities.md` § Social Commerce Conversation Data

## Objective

Move from social revenue reporting to chat-to-order funnel optimization — inbound volume, response time, agent conversion.

## What this unlocks

- Inbound conversation volume (Facebook, Zalo)
- First response time (FRT)
- Average handling time (AHT)
- Agent conversion rate (conversations → orders)
- Missed opportunity detection (high-intent chats without order)
- Staffing and coaching recommendations

## Data needed

- Conversation ID, channel (Facebook / Zalo), customer ID or matched phone
- Assigned agent, first customer message timestamp, first agent reply timestamp
- Conversation status (open / resolved / abandoned)
- Linked order ID (when order was created from conversation)
- Message volume per conversation

## Current state

- No conversation data source connected
- FRT and AHT data are missing
- Social revenue and orders by channel/staff are available in existing dashboards (Social Commerce Operations playbook)
- Current coverage: output side (orders, revenue per agent) — missing input side (conversations, response behavior)

## Implementation steps

- [ ] Identify conversation data source (Pancake, Subiz, Facebook API, Zalo OA API)
- [ ] Define minimum schema: conversation_id, channel, agent_id, customer_id, first_msg_at, first_reply_at, status, linked_order_id
- [ ] Build ingestion (API pull or export) — full message content NOT required for first version
- [ ] Create `fact_conversations` mart
- [ ] Create `int_agent_funnel_daily` with FRT, AHT, conversion_rate, revenue_per_conversation
- [ ] Add Chat Funnel tab to Social Commerce Operations dashboard
- [ ] Add Agent Performance table with fairness controls (assignments, FRT, conversion, AOV)
- [ ] Add Missed Opportunity queue (high-intent without order, slow first response)

## Note

Full message content not required for first useful version — metadata only (timestamps, status, linked order) is sufficient for funnel and FRT metrics.
