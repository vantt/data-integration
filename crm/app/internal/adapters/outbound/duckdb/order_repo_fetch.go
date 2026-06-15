package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"math"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── scan helpers ─────────────────────────────────────────────────────────────

func ns(v sql.NullString) string { return v.String }

// ni rounds a nullable float64 to int64 (monetary DECIMAL → VND integer).
func ni(v sql.NullFloat64) int64 {
	if !v.Valid {
		return 0
	}
	return int64(math.Round(v.Float64))
}

// nf lifts a nullable float64 to *float64 (percentage fields).
func nf(v sql.NullFloat64) *float64 {
	if !v.Valid {
		return nil
	}
	cp := v.Float64
	return &cp
}

func nb(v sql.NullBool) bool  { return v.Valid && v.Bool }
func nii(v sql.NullInt64) int { return int(v.Int64) }

// fmtUTC formats a nullable TIMESTAMPTZ as UTC ISO-8601 ("2006-01-02T15:04:05Z").
func fmtUTC(t sql.NullTime) string {
	if !t.Valid {
		return ""
	}
	return t.Time.UTC().Format("2006-01-02T15:04:05Z")
}

// fmtDate formats a nullable DATE or TIMESTAMPTZ as "YYYY-MM-DD".
func fmtDate(t sql.NullTime) string {
	if !t.Valid {
		return ""
	}
	return t.Time.UTC().Format("2006-01-02")
}

// ─── fetchHeader ──────────────────────────────────────────────────────────────

const headerSQL = `
SELECT
    fo.order_id, fo.order_code, fo.customer_key,
    fo.status, fo.payment_status, fo.fulfillment_status,
    fo.ordered_at                                         AS created_at,
    fo.first_shipped_at, fo.updated_at,
    CAST(fo.time_to_complete_hours  AS DOUBLE)            AS time_to_complete_hours,
    fo.shipping_address,
    CAST(fo.max_discount_rate       AS DOUBLE)            AS max_discount_rate,
    fo.primary_discount_type,
    CAST(fo.gross_revenue    AS DOUBLE)                   AS gross_revenue,
    CAST(fo.discount_amount  AS DOUBLE)                   AS discount_amount,
    CAST(fo.net_revenue      AS DOUBLE)                   AS net_revenue,
    CAST(fo.vat_amount       AS DOUBLE)                   AS vat_amount,
    CAST(fo.total_collected  AS DOUBLE)                   AS total_collected,
    CAST(foe.cogs_amount              AS DOUBLE)          AS cogs_amount,
    CAST(foe.gross_profit             AS DOUBLE)          AS gross_profit,
    CAST(foe.gross_margin_pct         AS DOUBLE)          AS gross_margin_pct,
    CAST(foe.channel_net_profit       AS DOUBLE)          AS channel_net_profit,
    CAST(foe.channel_net_margin_pct   AS DOUBLE)          AS channel_net_margin_pct,
    CAST(foe.shopee_platform_fees     AS DOUBLE)          AS shopee_platform_fees,
    CAST(foe.shopee_infra_fee         AS DOUBLE)          AS shopee_infra_fee,
    CAST(foe.shopee_voucher_xtra_fee  AS DOUBLE)          AS shopee_voucher_xtra_fee,
    CAST(foe.shopee_taxes             AS DOUBLE)          AS shopee_taxes,
    CAST(foe.shopee_net_settlement    AS DOUBLE)          AS shopee_net_settlement,
    CAST(foe.cod_amount               AS DOUBLE)          AS cod_amount,
    foe.carrier_id,
    CAST(foe.return_amount            AS DOUBLE)          AS return_amount,
    foe.return_count,
    foe.has_cogs, foe.has_platform_fees, foe.has_returns,
    CAST(foe.promo_goods_cost         AS DOUBLE)          AS promo_goods_cost,
    CAST(foe.allocated_overhead       AS DOUBLE)          AS allocated_overhead,
    foe.is_overhead_estimated,
    CAST(foe.fully_loaded_net_profit  AS DOUBLE)          AS fully_loaded_net_profit,
    CAST(foe.fully_loaded_margin_pct  AS DOUBLE)          AS fully_loaded_margin_pct,
    foe.cogs_source,
    CAST(us.total_us_revenue_excl_vat AS DOUBLE)          AS total_us_revenue_excl_vat,
    CAST(us.total_us_revenue_incl_vat AS DOUBLE)          AS total_us_revenue_incl_vat,
    us.line_item_count                                    AS us_line_item_count,
    us.has_unpriced_sku, us.unpriced_sku_count,
    (us.order_id IS NOT NULL)                             AS is_us,
    ch.channel_name, ch.channel_code, ch.channel_category, ch.channel_format,
    ch.platform, ch.channel_brand, ch.market,
    pr.promotion_code,
    seller.full_name   AS seller_name, seller.email AS seller_email,
    creator.full_name  AS creator_name,
    tm.team_name, bl.branch_location_name AS branch_name,
    geo.province, geo.district, geo.ward, geo.country,
    cust.customer_id   AS cust_customer_id,
    cust.full_name     AS cust_full_name,
    cust.customer_type AS cust_customer_type,
    cust.value_group   AS cust_value_group,
    CAST(cust.lifetime_value AS DOUBLE)                   AS cust_lifetime_value
FROM fact_orders fo
LEFT JOIN fact_order_economics foe    ON fo.order_id = foe.order_id
LEFT JOIN fact_us_shipment_economics us ON fo.order_id = us.order_id
LEFT JOIN dim_channels ch             ON fo.channel_key = ch.channel_key
LEFT JOIN dim_promotions pr           ON fo.promotion_key = pr.promotion_key
LEFT JOIN dim_staff seller            ON fo.seller_staff_key = seller.staff_key
LEFT JOIN dim_staff creator           ON fo.creator_staff_key = creator.staff_key
LEFT JOIN dim_teams tm                ON fo.team_key = tm.team_key
LEFT JOIN dim_branch_location bl      ON fo.branch_location_key = bl.branch_location_key
LEFT JOIN dim_geography geo           ON fo.shipping_geography_key = geo.geography_key
LEFT JOIN dim_customers cust          ON fo.customer_key = cust.customer_key
WHERE UPPER(fo.order_code) = UPPER(?)
LIMIT 1`

func (r *OrderRepo) fetchHeader(ctx context.Context, orderCode string) (
	hdr *domain.OrderHeader,
	fin *domain.OrderFinancial,
	ch *domain.ChannelInfo,
	staff *domain.StaffInfo,
	ship *domain.ShippingInfo,
	cust *domain.CustomerRef,
	orderID, canonicalCode string,
	err error,
) {
	row := r.db.QueryRowContext(ctx, headerSQL, orderCode)

	var (
		sOrderID, sOrderCode, sCustomerKey sql.NullString
		sStatus, sPayStatus, sFulStatus    sql.NullString
		tCreated, tShipped, tUpdated       sql.NullTime
		fTTC                               sql.NullFloat64
		sShipAddr                          sql.NullString
		fMaxDisc                           sql.NullFloat64
		sPrimDisc                          sql.NullString
		// revenue waterfall (fact_orders)
		fGross, fDisc, fNet, fVat, fColl sql.NullFloat64
		// P&L economics (fact_order_economics — LEFT JOIN)
		fCogs, fGP, fGMP                    sql.NullFloat64
		fCNP, fCNMP                         sql.NullFloat64
		fSPF, fSIF, fSVXF, fST, fSNS       sql.NullFloat64
		fCOD                                sql.NullFloat64
		sCarrier                            sql.NullString
		fRetAmt                             sql.NullFloat64
		iRetCnt                             sql.NullInt64
		bHasCogs, bHasPF, bHasRet          sql.NullBool
		fPromo, fOH                         sql.NullFloat64
		bOHEst                              sql.NullBool
		fFLNP, fFLMP                        sql.NullFloat64
		sCogsSource                         sql.NullString
		// US CrossBorder (fact_us_shipment_economics — LEFT JOIN)
		fUSExcl, fUSIncl sql.NullFloat64
		iUSLI            sql.NullInt64
		bHasUnpriced     sql.NullBool
		iUnpricedCnt     sql.NullInt64
		bIsUS            sql.NullBool
		// channel dims
		sChanName, sChanCode, sChanCat, sChanFmt sql.NullString
		sPlatform, sChanBrand, sMarket           sql.NullString
		sPromoCode                               sql.NullString
		// staff dims
		sSellerName, sSellerEmail, sCreatorName sql.NullString
		sTeamName, sBranchName                  sql.NullString
		// geo dims
		sProvince, sDistrict, sWard, sCountry sql.NullString
		// customer dim
		iCustID                             sql.NullInt64 // INTEGER in dim_customers
		sCustName, sCustType, sCustVG       sql.NullString
		fCustLTV                            sql.NullFloat64
	)

	scanErr := row.Scan(
		&sOrderID, &sOrderCode, &sCustomerKey,
		&sStatus, &sPayStatus, &sFulStatus,
		&tCreated, &tShipped, &tUpdated,
		&fTTC, &sShipAddr,
		&fMaxDisc, &sPrimDisc,
		&fGross, &fDisc, &fNet, &fVat, &fColl,
		&fCogs, &fGP, &fGMP,
		&fCNP, &fCNMP,
		&fSPF, &fSIF, &fSVXF, &fST, &fSNS,
		&fCOD, &sCarrier, &fRetAmt, &iRetCnt,
		&bHasCogs, &bHasPF, &bHasRet,
		&fPromo, &fOH, &bOHEst,
		&fFLNP, &fFLMP, &sCogsSource,
		&fUSExcl, &fUSIncl, &iUSLI,
		&bHasUnpriced, &iUnpricedCnt,
		&bIsUS,
		&sChanName, &sChanCode, &sChanCat, &sChanFmt,
		&sPlatform, &sChanBrand, &sMarket,
		&sPromoCode,
		&sSellerName, &sSellerEmail, &sCreatorName,
		&sTeamName, &sBranchName,
		&sProvince, &sDistrict, &sWard, &sCountry,
		&iCustID, &sCustName, &sCustType, &sCustVG, &fCustLTV,
	)
	if errors.Is(scanErr, sql.ErrNoRows) {
		return nil, nil, nil, nil, nil, nil, "", "", nil
	}
	if scanErr != nil {
		return nil, nil, nil, nil, nil, nil, "", "",
			fmt.Errorf("duckdb order repo: scan header: %w", scanErr)
	}

	orderID = ns(sOrderID)
	canonicalCode = ns(sOrderCode)
	if canonicalCode == "" {
		canonicalCode = orderCode
	}

	var ttcHours *float64
	if fTTC.Valid {
		cp := fTTC.Float64
		ttcHours = &cp
	}

	hdr = &domain.OrderHeader{
		OrderCode:           canonicalCode,
		OrderID:             orderID,
		Status:              ns(sStatus),
		PaymentStatus:       ns(sPayStatus),
		FulfillmentStatus:   ns(sFulStatus),
		CreatedAt:           fmtUTC(tCreated),
		FirstShippedAt:      fmtUTC(tShipped),
		UpdatedAt:           fmtUTC(tUpdated),
		TimeToCompleteHours: ttcHours,
	}

	fin = &domain.OrderFinancial{
		GrossRevenue:         ni(fGross),
		DiscountAmount:       ni(fDisc),
		NetRevenue:           ni(fNet),
		VatAmount:            ni(fVat),
		TotalCollected:       ni(fColl),
		CogsAmount:           ni(fCogs),
		GrossProfit:          ni(fGP),
		GrossMarginPct:       nf(fGMP),
		ChannelNetProfit:     ni(fCNP),
		ChannelNetMarginPct:  nf(fCNMP),
		ShopeePlatformFees:   ni(fSPF),
		ShopeeInfraFee:       ni(fSIF),
		ShopeeVoucherXtraFee: ni(fSVXF),
		ShopeeTaxes:          ni(fST),
		ShopeeNetSettlement:  ni(fSNS),
		CODAmount:            ni(fCOD),
		CarrierID:            ns(sCarrier),
		ReturnAmount:         ni(fRetAmt),
		ReturnCount:          nii(iRetCnt),
		HasCogs:              nb(bHasCogs),
		HasPlatformFees:      nb(bHasPF),
		HasReturns:           nb(bHasRet),
		PromoGoodsCost:       ni(fPromo),
		CogsSource:           ns(sCogsSource),
		AllocatedOverhead:    ni(fOH),
		IsOverheadEstimated:  nb(bOHEst),
		FullyLoadedNetProfit: ni(fFLNP),
		FullyLoadedMarginPct: nf(fFLMP),
		IsUS:                 nb(bIsUS),
		USRevenueExclVAT:     ni(fUSExcl),
		USRevenueInclVAT:     ni(fUSIncl),
		USLineItemCount:      nii(iUSLI),
		HasUnpricedSKU:       nb(bHasUnpriced),
		UnpricedSKUCount:     nii(iUnpricedCnt),
	}

	ch = &domain.ChannelInfo{
		ChannelName:         ns(sChanName),
		ChannelCode:         ns(sChanCode),
		ChannelCategory:     ns(sChanCat),
		ChannelFormat:       ns(sChanFmt),
		Platform:            ns(sPlatform),
		ChannelBrand:        ns(sChanBrand),
		Market:              ns(sMarket),
		PromotionCode:       ns(sPromoCode),
		MaxDiscountRate:     nf(fMaxDisc),
		PrimaryDiscountType: ns(sPrimDisc),
	}

	staff = &domain.StaffInfo{
		SellerName:  ns(sSellerName),
		SellerEmail: ns(sSellerEmail),
		CreatorName: ns(sCreatorName),
		TeamName:    ns(sTeamName),
		BranchName:  ns(sBranchName),
	}

	ship = &domain.ShippingInfo{
		Province: ns(sProvince),
		District: ns(sDistrict),
		Ward:     ns(sWard),
		Country:  ns(sCountry),
		Address:  ns(sShipAddr),
	}

	if iCustID.Valid && iCustID.Int64 != 0 {
		cust = &domain.CustomerRef{
			CustomerID:    fmt.Sprintf("%d", iCustID.Int64),
			FullName:      ns(sCustName),
			CustomerType:  ns(sCustType),
			ValueGroup:    ns(sCustVG),
			LifetimeValue: ni(fCustLTV),
		}
	}

	return hdr, fin, ch, staff, ship, cust, orderID, canonicalCode, nil
}

// ─── fetchLineItems ───────────────────────────────────────────────────────────

func (r *OrderRepo) fetchLineItems(ctx context.Context, orderID string) ([]domain.LineItem, error) {
	const q = `
		SELECT fs.order_line_id, dp.sku, dp.product_name, dp.variant_name,
		       dp.brand_name, dp.category, dp.unit,
		       fs.quantity,
		       CAST(fs.net_revenue                AS DOUBLE) AS revenue,
		       CAST(fs.discount_amount             AS DOUBLE) AS discount_amount,
		       CAST(fs.distributed_discount_amount AS DOUBLE) AS distributed_discount_amount,
		       CAST(fs.weight_grams               AS DOUBLE) AS weight_grams
		FROM fact_sales fs
		LEFT JOIN dim_products dp ON fs.product_key = dp.product_key
		WHERE fs.order_id = ?
		ORDER BY fs.order_line_id`

	rows, err := r.db.QueryContext(ctx, q, orderID)
	if err != nil {
		return []domain.LineItem{}, nil // degrade gracefully
	}
	defer rows.Close()

	var out []domain.LineItem
	for rows.Next() {
		var (
			sID, sSKU, sProd, sVar sql.NullString
			sBrand, sCat, sUnit    sql.NullString
			iQty                   sql.NullInt64
			fRev, fDisc, fDDist   sql.NullFloat64
			fWt                    sql.NullFloat64
		)
		if err := rows.Scan(&sID, &sSKU, &sProd, &sVar, &sBrand, &sCat, &sUnit,
			&iQty, &fRev, &fDisc, &fDDist, &fWt); err != nil {
			continue
		}
		item := domain.LineItem{
			OrderLineID:               ns(sID),
			SKU:                       ns(sSKU),
			ProductName:               ns(sProd),
			VariantName:               ns(sVar),
			BrandName:                 ns(sBrand),
			Category:                  ns(sCat),
			Unit:                      ns(sUnit),
			Quantity:                  int(iQty.Int64),
			Revenue:                   ni(fRev),
			DiscountAmount:            ni(fDisc),
			DistributedDiscountAmount: ni(fDDist),
		}
		if fWt.Valid {
			v := ni(fWt)
			item.WeightGrams = &v
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

// ─── fetchCosts ───────────────────────────────────────────────────────────────

func (r *OrderRepo) fetchCosts(ctx context.Context, orderID string) ([]domain.CostRow, error) {
	const q = `
		SELECT cost_type, cost_category,
		       CAST(amount AS DOUBLE) AS amount,
		       CAST(discount_rate AS DOUBLE) AS discount_rate,
		       discount_type, source_system, source_record, fee_source
		FROM fact_order_costs
		WHERE order_id = ?
		ORDER BY cost_category, cost_type`

	rows, err := r.db.QueryContext(ctx, q, orderID)
	if err != nil {
		return []domain.CostRow{}, nil
	}
	defer rows.Close()

	var out []domain.CostRow
	for rows.Next() {
		var (
			sType, sCat, sDiscType sql.NullString
			sSrc, sRec, sFeeSrc    sql.NullString
			fAmt, fDiscRate        sql.NullFloat64
		)
		if err := rows.Scan(&sType, &sCat, &fAmt, &fDiscRate, &sDiscType,
			&sSrc, &sRec, &sFeeSrc); err != nil {
			continue
		}
		out = append(out, domain.CostRow{
			CostType:     ns(sType),
			CostCategory: ns(sCat),
			Amount:       ni(fAmt),
			DiscountRate: nf(fDiscRate),
			DiscountType: ns(sDiscType),
			SourceSystem: ns(sSrc),
			SourceRecord: ns(sRec),
			FeeSource:    ns(sFeeSrc),
		})
	}
	return out, rows.Err()
}

// ─── fetchPayments ────────────────────────────────────────────────────────────

func (r *OrderRepo) fetchPayments(ctx context.Context, orderID string) ([]domain.Payment, error) {
	const q = `
		SELECT pm.payment_method_name, pm.payment_method_type,
		       CAST(fp.amount AS DOUBLE) AS amount,
		       fp.status, fp.payment_timestamp, fp.paid_on
		FROM fact_payments fp
		LEFT JOIN dim_payment_methods pm ON fp.payment_method_key = pm.payment_method_key
		WHERE fp.order_id = ?
		ORDER BY fp.payment_timestamp`

	rows, err := r.db.QueryContext(ctx, q, orderID)
	if err != nil {
		return []domain.Payment{}, nil
	}
	defer rows.Close()

	var out []domain.Payment
	for rows.Next() {
		var (
			sName, sType, sStatus sql.NullString
			fAmt                  sql.NullFloat64
			tStamp, tPaid         sql.NullTime
		)
		if err := rows.Scan(&sName, &sType, &fAmt, &sStatus, &tStamp, &tPaid); err != nil {
			continue
		}
		out = append(out, domain.Payment{
			PaymentMethodName: ns(sName),
			PaymentMethodType: ns(sType),
			Amount:            ni(fAmt),
			Status:            ns(sStatus),
			PaymentTimestamp:  fmtUTC(tStamp),
			PaidOn:            fmtDate(tPaid),
		})
	}
	return out, rows.Err()
}

// ─── fetchReturns ─────────────────────────────────────────────────────────────

func (r *OrderRepo) fetchReturns(ctx context.Context, orderCode string) ([]domain.ReturnEvent, error) {
	const q = `
		SELECT return_date,
		       CAST(refund_amount AS DOUBLE) AS refund_amount,
		       return_quantity, return_status, refund_status, return_reason
		FROM fact_order_returns
		WHERE UPPER(order_code) = UPPER(?)
		ORDER BY return_date`

	rows, err := r.db.QueryContext(ctx, q, orderCode)
	if err != nil {
		return []domain.ReturnEvent{}, nil
	}
	defer rows.Close()

	var out []domain.ReturnEvent
	for rows.Next() {
		var (
			tDate                          sql.NullTime
			fRefund                        sql.NullFloat64
			iQty                           sql.NullInt64
			sRetStat, sRefStat, sReason    sql.NullString
		)
		if err := rows.Scan(&tDate, &fRefund, &iQty, &sRetStat, &sRefStat, &sReason); err != nil {
			continue
		}
		out = append(out, domain.ReturnEvent{
			ReturnDate:     fmtDate(tDate),
			RefundAmount:   ni(fRefund),
			ReturnQuantity: int(iQty.Int64),
			ReturnStatus:   ns(sRetStat),
			RefundStatus:   ns(sRefStat),
			ReturnReason:   ns(sReason),
		})
	}
	return out, rows.Err()
}

// ─── fetchShipments ───────────────────────────────────────────────────────────

func (r *OrderRepo) fetchShipments(ctx context.Context, orderCode string) ([]domain.Shipment, error) {
	const q = `
		SELECT fulfillment_id, fulfillment_code, tracking_code, carrier_id,
		       shipping_service, status,
		       CAST(cod_amount AS DOUBLE) AS cod_amount,
		       created_at, shipped_at
		FROM fact_fulfillments
		WHERE UPPER(order_code) = UPPER(?)
		ORDER BY shipped_at NULLS LAST, created_at`

	rows, err := r.db.QueryContext(ctx, q, orderCode)
	if err != nil {
		return []domain.Shipment{}, nil
	}
	defer rows.Close()

	var out []domain.Shipment
	for rows.Next() {
		var (
			sID, sCode, sTrack   sql.NullString
			sCarrier, sSvc, sSt  sql.NullString
			fCOD                 sql.NullFloat64
			tCreated, tShipped   sql.NullTime
		)
		if err := rows.Scan(&sID, &sCode, &sTrack, &sCarrier, &sSvc, &sSt,
			&fCOD, &tCreated, &tShipped); err != nil {
			continue
		}
		out = append(out, domain.Shipment{
			FulfillmentID:   ns(sID),
			FulfillmentCode: ns(sCode),
			TrackingCode:    ns(sTrack),
			CarrierID:       ns(sCarrier),
			ShippingService: ns(sSvc),
			Status:          ns(sSt),
			CODAmount:       ni(fCOD),
			CreatedAt:       fmtUTC(tCreated),
			ShippedAt:       fmtUTC(tShipped),
		})
	}
	return out, rows.Err()
}

// ─── fetchCogsItems ───────────────────────────────────────────────────────────

func (r *OrderRepo) fetchCogsItems(ctx context.Context, orderCode string) ([]domain.CogsItem, error) {
	const q = `
		SELECT r.sku, r.variant_id,
		       CAST(r.cogs_goods_sapo    AS DOUBLE) AS cogs_goods_sapo,
		       CAST(r.cogs_goods_misa    AS DOUBLE) AS cogs_goods_misa,
		       CAST(r.cogs_goods_primary AS DOUBLE) AS cogs_goods_primary,
		       r.cogs_source,
		       CAST(r.qty_sapo           AS DOUBLE) AS qty_sapo,
		       (p.order_code IS NOT NULL) AS is_promo, p.is_gift_no_invoice
		FROM int_order_cogs_reconciled r
		LEFT JOIN int_order_promo_goods_cost p
		    ON r.order_code = p.order_code AND r.sku = p.sku
		WHERE r.order_code = ?
		ORDER BY COALESCE(p.order_code IS NOT NULL, FALSE), r.sku`

	rows, err := r.db.QueryContext(ctx, q, orderCode)
	if err != nil {
		return []domain.CogsItem{}, nil
	}
	defer rows.Close()

	var out []domain.CogsItem
	for rows.Next() {
		var (
			sSKU, sVariantID, sCogsSource sql.NullString
			fSapo, fMisa, fPrimary, fQty  sql.NullFloat64
			bIsPromo, bIsGift             sql.NullBool
		)
		if err := rows.Scan(&sSKU, &sVariantID, &fSapo, &fMisa, &fPrimary,
			&sCogsSource, &fQty, &bIsPromo, &bIsGift); err != nil {
			continue
		}
		out = append(out, domain.CogsItem{
			SKU:              ns(sSKU),
			VariantID:        ns(sVariantID),
			CogsGoodsSapo:    ni(fSapo),
			CogsGoodsMisa:    ni(fMisa),
			CogsGoodsPrimary: ni(fPrimary),
			CogsSource:       ns(sCogsSource),
			QtySapo:          fQty.Float64,
			IsPromo:          nb(bIsPromo),
			IsGiftNoInvoice:  nb(bIsGift),
		})
	}
	return out, rows.Err()
}
