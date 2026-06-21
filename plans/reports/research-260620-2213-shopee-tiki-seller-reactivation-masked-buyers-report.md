# Shopee VN / Tiki VN: Seller Reactivation Levers for Masked Buyers
**Date:** 2026-06-20 | **Purpose:** Validate strategic levers for Hug Campaign — wake dormant masked buyers → trigger reorder → Hug QR captures in parcel → de-masks contact.

---

## 1. Platform Tool Matrix

### Shopee Vietnam

| Lever | Can target past buyers? | Requires follow/opt-in first? | Cost | Policy risk | Estimated effectiveness |
|---|---|---|---|---|---|
| **Chat Broadcast** | YES — buyers who transacted in past 720 days are eligible recipients | NO (buyers auto-eligible without following) | Free | Medium — promotional spam prohibited; ads/promotions via chat are a violation; only order-related content is clean | Medium-high if message is framed as order follow-up or restock alert; purely promo content = risk |
| **Follow Prize Voucher** | NO — only NEW followers who have NEVER followed before and never claimed a prize | Yes — buyer must click Follow during claim period | Voucher cost only (seller-set) | Low | Low for dormant past buyers (they already may have followed or not be eligible) |
| **Shop Voucher (public)** | NO — broadcast to all, not targeted | No | Voucher cost | Low | Low targeting precision; good for broad reactivation |
| **Smart Voucher (Shopee-funded)** | Algorithmically determined by Shopee — no seller control over who | No | Zero (Shopee-paid) | None | Unknown for dormant-specific targeting; requires GMV Max (Custom ROAS) ad campaign |
| **Shopee Ads — Discovery** | Algorithmic: shows to buyers of similar products in last 30 days; not seller-controlled | No | Paid per click/impression | Low | Passive; may catch recently lapsed buyers; not granular to 180+ day dormant |
| **Shopee Ads — GMV Max** | Algorithmic: Shopee targets "right buyer at right time" — past buyers likely weighted | No | Paid; ROI-driven | Low | Moderate — best bet for algorithm to rediscover dormant buyers at low ROAS risk |
| **Shopee Live** | Passive — push notification sent to FOLLOWERS who enabled alerts; past non-follower buyers not notified | YES — buyer must be a follower | Free to host; optional ad spend to boost reach | Low | Low for non-follower past buyers; high for active followers |
| **Shopee Feed posts** | Passive — visible in feed to followers; no active push to non-followers | YES — must follow shop | Free | Low | Low for dormant non-followers |
| **Physical parcel insert (card/QR)** | YES — every parcel is an insert opportunity | No | Print cost only (~500–2,000 VND/card) | HIGH if directing to Zalo/off-platform transaction; MEDIUM if directing to follow Shopee shop; complex grey area (see Section 4) | HIGH for in-parcel capture — but applicable only to ACTIVE orders, not dormant buyers |

### Tiki Vietnam

| Lever | Can target past buyers? | Requires follow/opt-in first? | Cost | Policy risk | Estimated effectiveness |
|---|---|---|---|---|---|
| **Seller Chat** | YES — sellers can message buyers after order via Seller Center chat | NO — order creates a chat thread | Free | Medium — promotional spam likely prohibited; Tiki has similar anti-spam posture | Low-medium; reactive only (buyer must have recent order) |
| **Follower Discount** | YES — targets shop followers specifically | YES — buyer must follow shop | Discount cost | Low | Medium for followers; misses dormant non-followers |
| **Shop Vouchers / Coupons** | NO — public/general availability | No | Voucher cost | Low | Low targeting precision |
| **Flash Sale / Category Deal** | NO — open to all buyers on platform | No | Typically requires margin sacrifice | Low | Reach is broad; no dormant-specific targeting |
| **Tiki Ads** | Algorithmic (Shopee-style discovery); no confirmed past-buyer segment targeting per available docs | No | Paid | Low | Moderate passive reach |
| **TikiLIVE** | Passive — followers notified; non-followers not | YES — must follow | Free to host | Low | Low for dormant non-followers |
| **Tiki Feed** | Content visible in feed to followers | YES — must follow | Free | Low | Low for non-followers |
| **Physical parcel insert** | YES — same logic as Shopee | No | Print cost | Unknown — Tiki ToS less publicly documented; assumed similar prohibition on off-platform transaction solicitation | HIGH for active orders only |

---

## 2. Recommended Channel-2 Playbook: Wake Dormant Masked Buyers

**Strategic constraint:** Cannot contact directly. Must create conditions where dormant buyer self-initiates a return visit, converts, and then Hug captures via parcel QR.

### Phase A — Follower Base Growth (Weeks 1–4, ongoing)
*Goal: Convert dormant past buyers who haven't followed the shop into followers — the only way to reach them via free push tools.*

1. **Run Follow Prize campaign on Shopee** (`Seller Center > Marketing > Follow Prize`). Set voucher value 10–15% off or free shipping (health/supplement repeat items: ~15K–30K VND discount is sufficient). Limitation: only captures *new* followers who have never followed before — so dormant past buyers who already followed won't qualify, but those who never followed will.
2. **Run GMV Max (Custom ROAS) Ads** targeting broad category (supplements / health / beauty). Enable Smart Voucher. This lets Shopee's algorithm re-serve ads to lapsed buyers using algorithmic lookalike + past-interaction signals. Set ROAS target at 3–4x (not too tight — allows algorithm room to chase dormant segments). Budget: 500K–1M VND/day minimum for algorithm to learn.
3. **Shopee Live sessions bi-weekly.** Schedule 60-minute sessions with "exclusive live voucher" (5–10%). Pre-set Shopee Live Alerts (up to 60 days advance). Live notifications only push to followers — so Phases A.1 and A.2 must grow follower base first. Even 1–2 dormant followers converting = Hug capture opportunity.

### Phase B — Chat Broadcast to Past Buyers (Week 2 onwards)
*Shopee's most direct lever for sellers to reach past buyers without requiring follow.*

1. In `Seller Center > Chat > Chat Broadcast > Buyer List`: filter buyers with transactions in past 720 days. This pool includes your masked dormant customers (Shopee shows them as buyers even if you don't have their contact info).
2. Craft message as **restock/product update** (not pure promo — reduces spam risk). Example: "Sản phẩm [X] vừa có lô mới — dành riêng voucher [Y]% cho khách đã mua" (New batch available — exclusive voucher for previous buyers).
3. Attach 1 voucher + 1 product link per broadcast (within Shopee's content limits).
4. **Frequency:** Max 1 message/buyer/day; 2x per week per buyer across all sellers. Do not exceed. Segment by purchase recency to prioritize 180–365 day dormant first.
5. **Weekly cap:** Recipients capped at 2× your follower count. If follower base = 500, you can broadcast to max 1,000 recipients/week. Growing followers (Phase A) directly unlocks more broadcast reach.

### Phase C — Reorder Triggers (Parallel)
*Platform-level vouchers to sweeten return.*

1. Create a **shop voucher** with: minimum order 150K VND, 20K off, validity 14 days. Keep visible on shop page. When Phase B broadcast drives a visit, this voucher reduces friction.
2. On Tiki: use **Follower Discount** for any followers. Use Flash Sale participation for broad exposure.

### Phase D — Parcel Capture (Every active order)
*For customers who DO reorder (the first convert after Phase A–C), capture them via Hug.*

1. Every parcel includes the Hug QR sticker as primary capture mechanism.
2. For the "follow Zalo for member perks" insert: see Section 4 (compliance) before including.

### Expected funnel:
```
~433 masked dormant buyers
  ↓ Shopee Chat Broadcast reaches up to 720-day history (many included)
  ↓ 3–8% chat-to-click rate (typical for Shopee broadcast; est. 13–35 clicks)
  ↓ 1–3% conversion to order (est. 4–13 reorders/campaign)
  ↓ Each reorder → Hug QR in parcel → de-mask
  ↓ De-masked buyers enter owned channel (Zalo OA / phone)
```
Payoff is **compounding**: each de-masked buyer no longer needs marketplace tools → can be reactivated directly in perpetuity.

---

## 3. Compliance: Moving Buyers to Direct Contact Legitimately

### What the law and platforms say

**Shopee's off-platform transaction policy (active 2024–2026):**
- Prohibited: directing buyers to pay via bank transfer/Zalo Pay/external app
- Prohibited: sharing phone numbers, Zalo IDs, Facebook URLs *in chat or product listings* to solicit purchases
- Prohibited: mentioning other platforms or social apps in chat content
- Explicitly allowed: Shopee-internal tools (Chat, Vouchers, Shopee Live, Feed)

**Physical parcel inserts — grey area:**
- Shopee ToS addresses *digital chat and listing content*; the official policies reviewed do NOT explicitly extend to physical materials placed inside boxes
- Practice among Vietnamese sellers: "thư cảm ơn" (thank-you cards) with hotline numbers are widely used without apparent enforcement — but these stop short of directing buyers to complete purchases elsewhere
- The policy's *intent* clearly covers off-platform transaction solicitation; physical inserts that drive *purchases* via Zalo would likely violate spirit if not letter
- Inserts that say "follow our Zalo OA for warranty tracking / health tips / member rewards" (not "buy here") occupy a materially different position — they do not solicit a transaction, they offer a service/community follow

**Safe approach for Hug's Zalo OA + warranty insert:**

> "Đăng ký thành viên FineJapan để nhận: (1) hướng dẫn sử dụng chi tiết, (2) nhắc nhở tái đặt hàng sức khỏe, (3) ưu đãi thành viên. Quét mã QR → Zalo OA FineJapan."
> ("Register as FineJapan member for: health usage guide, replenishment reminders, member perks. Scan QR → FineJapan Zalo OA.")

**Why this is defensible:**
- No transaction is solicited in the insert
- It's a *service* extension (warranty / health guidance), not a purchase redirect
- The actual purchase capture happens when buyer scans Hug QR in the same parcel — that is a CRM identity capture, not an off-platform sale
- Precedent: Zalo OA QR codes in physical retail receipts and packages are standard practice across Vietnam retail (PangoCDP case: ~1,000–2,000 VND/follower cost, mainstream for F&B/retail chains)

**Tiki:** ToS less publicly documented; assume similar spirit. Same insert strategy applies. Risk level uncertain.

---

## 4. Hard Limits (What We CANNOT Do)

| Action | Why prohibited / impossible |
|---|---|
| Send Zalo/SMS/email directly to masked buyer | Marketplace hides all PII; we don't have the contact |
| Share our Zalo number in Shopee chat to solicit purchase | Explicit policy violation → account freeze / permanent ban (ecommax.vn, 2024) |
| Run a Facebook/Google retargeting ad against Shopee buyer list | Shopee does not provide buyer PII to sellers; no exportable audience list |
| Build a custom audience of dormant buyers for Shopee Ads | Shopee Ads has NO seller-controllable audience upload for past buyers; all targeting is algorithmic |
| Send Chat Broadcast to more buyers than 2× follower count/week | Hard platform cap; cannot be bypassed |
| Send Chat Broadcast to buyers who purchased >720 days ago | Hard eligibility window; truly lapsed >2yr buyers are out of reach |
| Target dormant buyers specifically by "last purchase date" in Shopee Ads | No such audience filter exists for sellers |
| Use Follow Prize to win back existing followers | Follow Prize only works for *first-time* followers who have never followed and never claimed a prize |
| Tiki: direct chat broadcast to all past buyers unsolicited | No evidence Tiki exposes a chat broadcast to past-buyers tool comparable to Shopee's; only reactive post-order chat documented |

---

## 5. Cost Summary

| Lever | Cost type | Estimated cost |
|---|---|---|
| Chat Broadcast | Free (platform tool) | 0 |
| Follow Prize Voucher | Voucher subsidy | 10–30K VND/voucher claimed |
| Shop Voucher | Discount cost | Seller-set (e.g., 20K VND) |
| Smart Voucher | Zero — 100% Shopee-funded | 0 to seller |
| Shopee Ads (GMV Max) | CPC/CPM; ROAS-target managed | 500K–2M VND/day recommended minimum |
| Shopee Live hosting | Free | 0 (optional ad boost: 200–500K VND/session) |
| Parcel insert card (print) | Print + design | 500–2,000 VND/card |
| Zalo OA follower acquisition via QR | Incremental cost per follower (est. industry: 1,000–2,000 VND/follower) | Per Pango CDP benchmark |

---

## 6. Confidence & Source Freshness

| Claim | Confidence | Source | Freshness |
|---|---|---|---|
| Chat Broadcast targets buyers up to 720 days | High | Shopee official edu PDFs (MY/SG); cross-referenced across 3 guides | 2020–2024 docs; UI may have updated |
| Max recipients = 2× followers/week | High | Shopee SG Seller Education Hub; multiple cross-references | 2024 |
| Promotional content in chat = spam violation | High | BigSeller, Duoke analyses; Shopee policy cross-referenced | 2024–2025 |
| Off-platform redirect in chat → ban | High | ecommax.vn Vietnamese-language analysis; Haravan; verified terminology | 2024–2026 |
| Smart Voucher = 100% Shopee-funded, zero seller cost | High | dreamagency.vn; Shopee Ads SG official FAQ | 2025 |
| Smart Voucher requires GMV Max campaign | High | Same sources as above | 2025 |
| Follow Prize: new followers only, never claimed before | High | Shopee SG Seller Education Hub article 650 | 2024 |
| Parcel insert grey area (not explicitly prohibited in ToS) | Medium | ToS text analysis; practitioner norms; no explicit enforcement case found | 2024; policies could change |
| Tiki lacks chat broadcast to past buyers (no evidence found) | Medium | Hocvien.tiki.vn; Tiki Seller Center docs; Diversitech guide — all silent on this | 2024–2025; Tiki docs are sparse publicly |
| Zalo OA insert cost 1,000–2,000 VND/follower | Medium | PangoCDP case study (120+ deployments) | 2024 |

---

## Sources

- [Shopee Chat Violations & Penalties — BigSeller](https://www.bigseller.com/blog/articleDetails/3359/shopee-seller-chat-violation-penalties.htm)
- [Master Shopee Chat Rules — Duoke](https://www.duoke.com/en/blog/article/264-Shopee-Chat-Violations)
- [WEB Chat Broadcast User Guide — Shopee official PDF](https://deo.shopeemobile.com/shopee/seller/seller_cms/b4b2b09c27337409c62458b5614f4fd4/Web%20Chat%20Broadcast%20User%20Guide.pdf)
- [Chat Broadcast — Shopee SG Seller Education Hub](https://seller.shopee.sg/edu/article/7088/about-chat-broadcast)
- [What is Chat Broadcast? — Shopee SG](https://seller.shopee.sg/edu/article/921/What-is-Chat-Broadcast)
- [Custom Broadcast Target Audience — Shopee MY](https://seller.shopee.com.my/edu/article/10644/determine-chat-broadcast-target-audience)
- [Follow Prize Voucher — Shopee SG Education Hub](https://seller.shopee.sg/edu/article/650)
- [Smart Voucher — Shopee Ads SG](https://ads.shopee.sg/learn/faq/519/1976)
- [Voucher Thông Minh Shopee — DreamAgency VN](https://dreamagency.vn/voucher-thong-minh-shopee/)
- [Shopee Loyalty Program Strategy 2025 — HeightMedia VN](https://heightmedia.vn/bai-viet/cach-xay-dng-chng-trinh-khach-hang-than-thit-shopee-2025-dj-tang-doanh-thu/)
- ["Bay Màu" Gian Hàng Vì Vi Phạm Giao Dịch Ngoài Shopee — EcomMax VN](https://ecommax.vn/vi-pham-giao-dich-ngoai-shopee/)
- [Shopee Policy Vietnam 2026 — GHN.VN](https://ghn.vn/blogs/tip-ban-hang/cap-nhat-chinh-sach-ban-hang-tren-shopee-moi-nhat-hien-nay)
- [Zalo OA Follower Growth from Existing Customers — PangoCDP](https://pangocdp.com/vi/blog/tang-truong-zalo-oa-follower-tu-tap-khach-hang-hien-huu-cho-chuoi-retail-va-fb/)
- [Tiki Discount List — Học viện Tiki](https://hocvien.tiki.vn/faq/discount-list/)
- [Tiki Seller Center Intro — Học viện Tiki](https://hocvien.tiki.vn/faq/introduction-to-seller-center/)
- [Shopee Ads Vietnam overview — Feedforce VN](https://www.feedforce.vn/articles/ec-shopee-ads-optimize-revenue)
- [Shopee Mega Sale Seller Strategy 2025 — Duoke](https://www.duoke.com/en/blog/article/65-Shopee-Mega-Sale-Seller-Strategy-Guide-Your-Ultimate-2025-Guide)

---

## Unresolved Questions

1. **Chat Broadcast eligibility on Shopee Vietnam specifically:** The 720-day window and 2× follower cap are documented for SG/MY — need confirmation these same limits apply to the VN seller portal (`banhang.shopee.vn`). UI may differ; verify by logging into VN Seller Center > Chat Broadcast.

2. **Shopee Chat Broadcast promotional content rule:** Exact line between "order-related content" (allowed) and "promotional broadcast" (spam) is blurry in practice. A message saying "your product is back in stock + voucher" may or may not trigger spam detection. Recommend testing with a small batch (50 buyers) before full blast to monitor account health score.

3. **Tiki chat broadcast to past buyers:** No public documentation found confirming Tiki has a dedicated "past buyer broadcast" tool. Needs direct verification via Tiki seller support or Học viện Tiki login-gated content.

4. **Parcel insert enforcement:** No documented enforcement case found for "follow Zalo" QR in physical parcel (as distinct from chat solicitation). Practical risk appears low based on widespread industry practice, but no formal Shopee ruling confirms this. Consider asking Shopee Vietnam seller support explicitly for written clarification.

5. **Smart Voucher VN availability:** Smart Voucher is confirmed for Shopee SG and PH; need to verify it is live on Shopee Vietnam's GMV Max campaign type (ads.shopee.vn).

6. **Dormant buyer >720 days:** ~76% of our 433 masked buyers are dormant >180 days; some subset may exceed 720 days. Those buyers are completely unreachable via any Shopee seller tool. Exact count of >720-day dormant buyers should be pulled from the data to quantify the hard-floor loss.

---

**Status:** DONE
**Summary:** Shopee Chat Broadcast (past buyers up to 720 days, no follow required) is the single most actionable lever for reaching dormant masked buyers in-platform; combined with GMV Max Ads + Smart Voucher for algorithmic rediscovery. Parcel insert with "join Zalo OA for member perks" (not transaction solicitation) is defensible as the de-mask mechanism. Tiki tools are materially weaker — no confirmed past-buyer broadcast exists.
**Evidence:** 16 sources; Shopee official education PDFs, Vietnamese practitioner blogs (EcomMax, DreamAgency, HeightMedia, PangoCDP), Shopee Ads official FAQ, Học viện Tiki
**Concerns:** (1) SG/MY chat broadcast rules may not map 1:1 to VN portal — verify. (2) Smart Voucher VN availability unconfirmed. (3) Tiki past-buyer outreach is largely a blank — treat Tiki as low-priority channel for this campaign.
