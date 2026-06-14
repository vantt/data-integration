// Package sqlite — CacheRepo: read-only adapter over cache.db (ATTACHed as "cache").
//
// Design constraints:
//   - All queries use the "cache." schema prefix (Go ATTACHes cache.db read-only).
//   - "no such table" errors are caught and treated as empty results so the app
//     works before the first Python sync run.
//   - Python is the SOLE writer of cache.db; this adapter never writes to it.
//   - Money = INTEGER (VND); margin uses realized_margin_pct (H010-corrected).
//   - date_key is ICT YYYYMMDD — passed through as-is, never recomputed.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// CacheRepo satisfies ports.CacheRepository.
type CacheRepo struct {
	db *DB
}

// NewCacheRepo constructs a CacheRepo.
func NewCacheRepo(db *DB) ports.CacheRepository {
	return &CacheRepo{db: db}
}

// isMissingTable returns true when SQLite reports "no such table" — meaning
// cache.db exists but the Python sync has not yet populated the wh_* tables.
func isMissingTable(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "no such table")
}

// GetCustomerInsight returns the composed insight for a Sapo customer_id.
// Returns (nil, nil) when no data exists or tables are absent (graceful empty).
func (r *CacheRepo) GetCustomerInsight(ctx context.Context, customerID int64) (*domain.CacheInsight, error) {
	insight, err := r.fetchInsight(ctx, customerID)
	if err != nil {
		return nil, err
	}

	actions, err := r.fetchActions(ctx, func() string {
		if insight != nil {
			return insight.CustomerKey
		}
		return ""
	}())
	if err != nil {
		return nil, err
	}

	orders, err := r.fetchRecentOrders(ctx, customerID)
	if err != nil {
		return nil, err
	}

	// Return nil when the cache is genuinely empty for this customer.
	if insight == nil && len(actions) == 0 && len(orders) == 0 {
		return nil, nil
	}

	result := &domain.CacheInsight{
		Insight:      insight,
		Actions:      actions,
		RecentOrders: orders,
	}
	if insight != nil {
		result.RefreshedAt = insight.RefreshedAt
	}
	return result, nil
}

func (r *CacheRepo) fetchInsight(ctx context.Context, customerID int64) (*domain.CustomerInsight, error) {
	const q = `
		SELECT
			customer_key, customer_id,
			value_group, customer_status,
			next_purchase_signal, predicted_next_purchase_date,
			avg_days_between_orders, avg_order_spend,
			discount_sensitivity, cancel_rate,
			last_purchased_sku, top_affinity_product, second_affinity_product,
			channel_preference, lifetime_contribution_margin, is_margin_negative,
			refreshed_at
		FROM cache.wh_customer_insight
		WHERE customer_id = ?
		LIMIT 1`

	row := r.db.SQLDB().QueryRowContext(ctx, q, customerID)
	var i domain.CustomerInsight
	var (
		valueGroup, custStatus, nps, predDate sql.NullString
		discSens, lastSKU, topAff, secAff     sql.NullString
		chanPref                              sql.NullString
		avgDays, avgSpend, ltcm, cancelRate   sql.NullFloat64
		isMarginNeg                           sql.NullInt64
	)

	err := row.Scan(
		&i.CustomerKey, &i.CustomerID,
		&valueGroup, &custStatus,
		&nps, &predDate,
		&avgDays, &avgSpend,
		&discSens, &cancelRate,
		&lastSKU, &topAff, &secAff,
		&chanPref, &ltcm, &isMarginNeg,
		&i.RefreshedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		if isMissingTable(err) {
			return nil, nil // cache not yet populated
		}
		return nil, fmt.Errorf("cache repo: fetch insight: %w", err)
	}

	i.ValueGroup = valueGroup.String
	i.CustomerStatus = custStatus.String
	i.NextPurchaseSignal = nps.String
	i.PredictedNextPurchaseDate = predDate.String
	i.AvgDaysBetweenOrders = avgDays.Float64
	i.AvgOrderSpend = avgSpend.Float64
	i.DiscountSensitivity = discSens.String
	i.CancelRate = cancelRate.Float64
	i.LastPurchasedSKU = lastSKU.String
	i.TopAffinityProduct = topAff.String
	i.SecondAffinityProduct = secAff.String
	i.ChannelPreference = chanPref.String
	i.LifetimeContributionMargin = ltcm.Float64
	i.IsMarginNegative = isMarginNeg.Int64 != 0
	return &i, nil
}

func (r *CacheRepo) fetchActions(ctx context.Context, customerKey string) ([]domain.ActionQueueItem, error) {
	if customerKey == "" {
		return []domain.ActionQueueItem{}, nil
	}

	const q = `
		SELECT action_id, customer_key, action_type, rationale_vi,
		       value_at_stake_vnd, priority, generated_date, refreshed_at
		FROM cache.wh_action_queue
		WHERE customer_key = ?
		ORDER BY priority ASC
		LIMIT 10`

	rows, err := r.db.SQLDB().QueryContext(ctx, q, customerKey)
	if err != nil {
		if isMissingTable(err) {
			return []domain.ActionQueueItem{}, nil
		}
		return nil, fmt.Errorf("cache repo: fetch actions: %w", err)
	}
	defer rows.Close()

	var out []domain.ActionQueueItem
	for rows.Next() {
		var a domain.ActionQueueItem
		var rationale, genDate, refreshed sql.NullString
		var valueAtStake sql.NullInt64
		var priority sql.NullInt64

		if err := rows.Scan(
			&a.ActionID, &a.CustomerKey, &a.ActionType,
			&rationale, &valueAtStake, &priority, &genDate, &refreshed,
		); err != nil {
			return nil, fmt.Errorf("cache repo: scan action: %w", err)
		}
		a.RationaleVI = rationale.String
		a.ValueAtStakeVND = valueAtStake.Int64
		a.Priority = int(priority.Int64)
		a.GeneratedDate = genDate.String
		a.RefreshedAt = refreshed.String
		out = append(out, a)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("cache repo: action rows: %w", err)
	}
	if out == nil {
		out = []domain.ActionQueueItem{}
	}
	return out, nil
}

func (r *CacheRepo) fetchRecentOrders(ctx context.Context, customerID int64) ([]domain.RecentOrder, error) {
	const q = `
		SELECT order_id, order_code, customer_id, date_key,
		       net_revenue, status, channel, item_count
		FROM cache.wh_order_hdr
		WHERE customer_id = ?
		ORDER BY date_key DESC
		LIMIT 20`

	rows, err := r.db.SQLDB().QueryContext(ctx, q, customerID)
	if err != nil {
		if isMissingTable(err) {
			return []domain.RecentOrder{}, nil
		}
		return nil, fmt.Errorf("cache repo: fetch orders: %w", err)
	}
	defer rows.Close()

	var out []domain.RecentOrder
	for rows.Next() {
		var o domain.RecentOrder
		var orderCode, status, channel sql.NullString
		var netRev, dateKey sql.NullInt64
		var itemCount sql.NullInt64

		if err := rows.Scan(
			&o.OrderID, &orderCode, &o.CustomerID, &dateKey,
			&netRev, &status, &channel, &itemCount,
		); err != nil {
			return nil, fmt.Errorf("cache repo: scan order: %w", err)
		}
		o.OrderCode = orderCode.String
		o.DateKey = int(dateKey.Int64)
		o.NetRevenue = netRev.Int64
		o.Status = status.String
		o.Channel = channel.String
		o.ItemCount = int(itemCount.Int64)
		out = append(out, o)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("cache repo: order rows: %w", err)
	}
	if out == nil {
		out = []domain.RecentOrder{}
	}
	return out, nil
}

// ListAllActionQueue returns every row from cache.wh_action_queue.
// Returns empty slice when table is absent (graceful-empty).
func (r *CacheRepo) ListAllActionQueue(ctx context.Context) ([]domain.ActionQueueItem, error) {
	const q = `
		SELECT action_id, customer_key, action_type, rationale_vi,
		       value_at_stake_vnd, priority, generated_date, refreshed_at
		FROM cache.wh_action_queue
		ORDER BY priority ASC`

	rows, err := r.db.SQLDB().QueryContext(ctx, q)
	if err != nil {
		if isMissingTable(err) {
			return []domain.ActionQueueItem{}, nil
		}
		return nil, fmt.Errorf("cache repo: list all actions: %w", err)
	}
	defer rows.Close()

	var out []domain.ActionQueueItem
	for rows.Next() {
		var a domain.ActionQueueItem
		var rationale, genDate, refreshed sql.NullString
		var valueAtStake, priority sql.NullInt64

		if err := rows.Scan(
			&a.ActionID, &a.CustomerKey, &a.ActionType,
			&rationale, &valueAtStake, &priority, &genDate, &refreshed,
		); err != nil {
			return nil, fmt.Errorf("cache repo: scan all actions: %w", err)
		}
		a.RationaleVI = rationale.String
		a.ValueAtStakeVND = valueAtStake.Int64
		a.Priority = int(priority.Int64)
		a.GeneratedDate = genDate.String
		a.RefreshedAt = refreshed.String
		out = append(out, a)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("cache repo: all actions rows: %w", err)
	}
	if out == nil {
		out = []domain.ActionQueueItem{}
	}
	return out, nil
}

// ListPartySeed returns all rows from cache.wh_party_seed, enriched with the
// real display_name/phone/email from cache.wh_customer_base.
//
// The LEFT JOIN is on the INTEGER customer_id (both columns are INTEGER in
// cache.db) — this avoids the TEXT↔INTEGER cast pitfall that would arise if the
// match were done against crm_party_identity.identity_value (TEXT). When no
// wh_customer_base row matches, the enrichment fields come back NULL → empty
// strings, so the seed still produces a party (just without a name).
//
// Returns empty slice when wh_party_seed is absent (cache not yet populated).
// The query degrades gracefully if wh_customer_base is also absent: "no such
// table" is treated as empty, never an error.
func (r *CacheRepo) ListPartySeed(ctx context.Context) ([]domain.PartySeed, error) {
	const q = `
		SELECT ps.customer_id, ps.customer_key, ps.seen_at,
		       bc.display_name, bc.phone, bc.email
		FROM cache.wh_party_seed ps
		LEFT JOIN cache.wh_customer_base bc ON bc.customer_id = ps.customer_id`

	rows, err := r.db.SQLDB().QueryContext(ctx, q)
	if err != nil {
		if isMissingTable(err) {
			return []domain.PartySeed{}, nil
		}
		return nil, fmt.Errorf("cache repo: list party seed: %w", err)
	}
	defer rows.Close()

	var out []domain.PartySeed
	for rows.Next() {
		var s domain.PartySeed
		var displayName, phone, email sql.NullString
		if err := rows.Scan(
			&s.CustomerID, &s.CustomerKey, &s.SeenAt,
			&displayName, &phone, &email,
		); err != nil {
			return nil, fmt.Errorf("cache repo: scan party seed: %w", err)
		}
		s.DisplayName = displayName.String
		s.Phone = phone.String
		s.Email = email.String
		out = append(out, s)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("cache repo: party seed rows: %w", err)
	}
	if out == nil {
		out = []domain.PartySeed{}
	}
	return out, nil
}
