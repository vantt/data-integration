// Package domain — order detail aggregate read from olap.duckdb (serving layer).
// CRM reads these from fact_orders + fact_order_economics + dimension tables via
// the DuckDB adapter; Python never writes here (read-only from CRM's perspective).
package domain

// OrderDetail is the full single-order aggregate.
type OrderDetail struct {
	Header     OrderHeader
	Financial  OrderFinancial
	LineItems  []LineItem
	CostLedger []CostRow
	CogsItems  []CogsItem
	Payments   []Payment
	Returns    []ReturnEvent
	Shipments  []Shipment
	Channel    ChannelInfo
	Staff      StaffInfo
	Shipping   ShippingInfo
	Customer   *CustomerRef // nil when order has no linked customer
}

// OrderHeader holds per-order identity and lifecycle timestamps.
// CreatedAt / FirstShippedAt / UpdatedAt are UTC ISO-8601 strings
// (the templates' formatICTHelper converts them to ICT display).
type OrderHeader struct {
	OrderCode           string
	OrderID             string
	Status              string
	PaymentStatus       string
	FulfillmentStatus   string
	CreatedAt           string
	FirstShippedAt      string
	UpdatedAt           string
	TimeToCompleteHours *float64 // nil when order is not yet complete
}

// OrderFinancial holds the revenue waterfall + P&L economics for one order.
// All *VND* amounts are int64 (rounded from warehouse DECIMAL).
// Pct fields are *float64 so nil indicates "not applicable" (e.g. zero revenue).
type OrderFinancial struct {
	// Revenue waterfall (fact_orders)
	GrossRevenue  int64
	DiscountAmount int64
	NetRevenue    int64
	VatAmount     int64
	TotalCollected int64
	// P&L economics (fact_order_economics — LEFT JOIN, all may be zero)
	CogsAmount           int64
	GrossProfit          int64
	GrossMarginPct       *float64
	ChannelNetProfit     int64
	ChannelNetMarginPct  *float64
	ShopeePlatformFees   int64
	ShopeeInfraFee       int64
	ShopeeVoucherXtraFee int64
	ShopeeTaxes          int64
	ShopeeNetSettlement  int64
	CODAmount            int64
	CarrierID            string
	ReturnAmount         int64
	ReturnCount          int
	HasCogs              bool
	HasPlatformFees      bool
	HasReturns           bool
	// Phase-06 fully-loaded fields
	PromoGoodsCost       int64
	CogsSource           string // sapo_mac|misa|both|none
	AllocatedOverhead    int64
	IsOverheadEstimated  bool
	FullyLoadedNetProfit int64
	FullyLoadedMarginPct *float64
	// US CrossBorder (fact_us_shipment_economics — LEFT JOIN)
	IsUS            bool
	USRevenueExclVAT int64
	USRevenueInclVAT int64
	USLineItemCount  int
	HasUnpricedSKU   bool
	UnpricedSKUCount int
}

// LineItem is one fact_sales row (joined to dim_products).
type LineItem struct {
	OrderLineID               string
	SKU                       string
	ProductName               string
	VariantName               string
	BrandName                 string
	Category                  string
	Unit                      string
	Quantity                  int
	Revenue                   int64
	DiscountAmount            int64
	DistributedDiscountAmount int64
	WeightGrams               *int64 // nil when absent
}

// Shipment is one fact_fulfillments row.
type Shipment struct {
	FulfillmentID   string
	FulfillmentCode string
	TrackingCode    string
	CarrierID       string
	ShippingService string
	Status          string
	CODAmount       int64
	CreatedAt       string // UTC ISO
	ShippedAt       string // UTC ISO, empty if not shipped
}

// CostRow is one fact_order_costs row (cost ledger).
type CostRow struct {
	CostType     string
	CostCategory string
	Amount       int64
	DiscountRate *float64
	DiscountType string
	SourceSystem string
	SourceRecord string
	FeeSource    string
}

// CogsItem is one int_order_cogs_reconciled row (per-SKU COGS breakdown).
type CogsItem struct {
	SKU              string
	VariantID        string
	CogsGoodsSapo    int64
	CogsGoodsMisa    int64
	CogsGoodsPrimary int64
	CogsSource       string
	QtySapo          float64
	IsPromo          bool
	IsGiftNoInvoice  bool
}

// Payment is one fact_payments row (joined to dim_payment_methods).
type Payment struct {
	PaymentMethodName string
	PaymentMethodType string
	Amount            int64
	Status            string
	PaymentTimestamp  string // UTC ISO, empty when absent
	PaidOn            string // YYYY-MM-DD, empty when absent
}

// ReturnEvent is one fact_order_returns row.
type ReturnEvent struct {
	ReturnDate     string // YYYY-MM-DD
	RefundAmount   int64
	ReturnQuantity int
	ReturnStatus   string
	RefundStatus   string
	ReturnReason   string
}

// ChannelInfo holds dimension data from dim_channels + dim_promotions.
type ChannelInfo struct {
	ChannelName         string
	ChannelCode         string
	ChannelCategory     string
	ChannelFormat       string
	Platform            string
	ChannelBrand        string
	Market              string
	PromotionCode       string
	MaxDiscountRate     *float64
	PrimaryDiscountType string
}

// StaffInfo holds dimension data from dim_staff + dim_teams + dim_branch_location.
type StaffInfo struct {
	SellerName  string
	SellerEmail string
	CreatorName string
	TeamName    string
	BranchName  string
}

// ShippingInfo holds dimension data from dim_geography + fact_orders.shipping_address.
type ShippingInfo struct {
	Province string
	District string
	Ward     string
	Country  string
	Address  string
}

// CustomerRef is the linked customer from dim_customers (nil when no customer_key).
type CustomerRef struct {
	CustomerID              string // Sapo customer_id (VARCHAR in serving layer)
	FullName                string
	CustomerType            string
	ValueGroup              string
	LifetimeValue           int64
	CustomerActionType      string // from mart_customer_action_queue, empty when absent
	CustomerActionRationale string
}
