// Package domain — warehouse cache insight entities (Phase 04).
// Read-only view of data computed in the warehouse; CRM never recomputes these.
package domain

// CustomerInsight holds the pre-computed RFM + behavioural signals cached from
// the warehouse (wh_customer_insight in cache.db).
// All monetary values are VND integers. Margins use realized_margin_pct (H010-corrected).
type CustomerInsight struct {
	CustomerKey                string
	CustomerID                 int64
	ValueGroup                 string  // VIP|GOLD|SILVER|BRONZE
	CustomerStatus             string  // active|at_risk|churned
	NextPurchaseSignal         string  // OVERDUE|DUE_SOON|ON_TRACK
	PredictedNextPurchaseDate  string  // YYYY-MM-DD or empty
	AvgDaysBetweenOrders       float64
	AvgOrderSpend              float64
	DiscountSensitivity        string  // HIGH|MEDIUM|LOW
	CancelRate                 float64
	LastPurchasedSKU           string
	TopAffinityProduct         string
	SecondAffinityProduct      string
	ChannelPreference          string
	LifetimeContributionMargin float64
	IsMarginNegative           bool
	RefreshedAt                string
}

// ActionQueueItem is one recommended action from the warehouse action queue.
type ActionQueueItem struct {
	ActionID        string
	CustomerKey     string
	CustomerName    string  // display_name from wh_customer_base; empty when not found
	PartyID         *string // CRM party_id resolved via crm_party_identity; nil when not yet synced
	ActionType      string  // CALL_NOW|REORDER_NUDGE|WIN_BACK|UPSELL|CROSS_SELL|COLLECT_FEEDBACK
	RationaleVI     string  // Vietnamese rationale text
	ValueAtStakeVND int64
	Priority        int
	GeneratedDate   string // YYYY-MM-DD
	RefreshedAt     string
}

// RecentOrder is a slim order header row from wh_order_hdr.
type RecentOrder struct {
	OrderID    string
	OrderCode  string
	CustomerID int64
	DateKey    int    // ICT YYYYMMDD (pass-through from warehouse)
	NetRevenue int64  // VND INTEGER (VAT-inclusive)
	Status     string
	Channel    string
	ItemCount  int
}

// CacheInsight is the composed read model returned by GetCustomerInsight.
// nil pointer fields mean the cache is empty or the customer was not found.
type CacheInsight struct {
	Insight      *CustomerInsight  // nil when no insight row exists
	Actions      []ActionQueueItem // empty slice when none
	RecentOrders []RecentOrder     // empty slice when none (last N orders)
	RefreshedAt  string            // from Insight.RefreshedAt or empty
}

// PartySeed is a row from wh_party_seed used by the seed consumer to create
// crm_party records without the Python sync touching crm.db.
//
// DisplayName/Phone/Email are enriched from wh_customer_base (joined by the
// integer customer_id) so the seed consumer can populate the golden record.
// They are empty when no matching wh_customer_base row exists.
type PartySeed struct {
	CustomerID           int64
	CustomerKey          string
	SeenAt               string
	DisplayName          string
	Phone                string
	Email                string
	SourceContactQuality string // masked|real — warehouse-computed, immutable
	ContactQuality       string // masked|unverified|verified — initial value from warehouse
}
