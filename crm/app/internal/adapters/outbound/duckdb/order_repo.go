// Package duckdb — read-only DuckDB adapter for on-demand order detail queries.
// Reads from olap.duckdb (the warehouse serving layer) via CGO-backed go-duckdb.
// The serving layer must be bootstrapped (bootstrap_serving_views.py) before this
// adapter can find any data; a missing file causes NewOrderRepo to return an error
// which main.go logs as a warning and substitutes a no-op reader.
//
// Constraints:
//   - access_mode=read_only — never acquires a write lock.
//   - TimeZone='Asia/Ho_Chi_Minh' is set per connection so STRFTIME renders ICT.
//   - TIMESTAMPTZ is scanned as time.Time (UTC); templates call formatICTHelper.
//   - Monetary DECIMAL columns are scanned as float64 and rounded to int64.
//   - Optional child collections (shipments, costs, etc.) degrade to [] on error.
package duckdb

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"fmt"

	duck "github.com/marcboeker/go-duckdb"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// OrderRepo reads order aggregates from olap.duckdb (serving layer).
type OrderRepo struct {
	db *sql.DB
}

// NewOrderRepo opens olap.duckdb read-only and sets the ICT session timezone.
// Returns an error when the file cannot be opened (e.g. missing, locked by writer).
func NewOrderRepo(olapPath string) (*OrderRepo, error) {
	dsn := olapPath + "?access_mode=read_only"
	connector, err := duck.NewConnector(dsn, func(execer driver.ExecerContext) error {
		_, err := execer.ExecContext(context.Background(), "SET TimeZone='Asia/Ho_Chi_Minh'", nil)
		return err
	})
	if err != nil {
		return nil, fmt.Errorf("duckdb order repo: open %q: %w", olapPath, err)
	}
	db := sql.OpenDB(connector)
	db.SetMaxOpenConns(4)
	return &OrderRepo{db: db}, nil
}

// Close releases the underlying connection pool.
func (r *OrderRepo) Close() error { return r.db.Close() }

// GetByCode fetches the full order aggregate for orderCode (case-insensitive).
// Returns (nil, nil) when the order is not found.
// Optional child collections degrade gracefully to empty slices on query error.
func (r *OrderRepo) GetByCode(ctx context.Context, orderCode string) (*domain.OrderDetail, error) {
	if orderCode == "" {
		return nil, nil
	}

	hdr, fin, ch, staff, ship, cust, orderID, canonicalCode, err := r.fetchHeader(ctx, orderCode)
	if err != nil {
		return nil, err
	}
	if hdr == nil {
		return nil, nil
	}

	lineItems, _ := r.fetchLineItems(ctx, orderID)
	costs, _ := r.fetchCosts(ctx, orderID)
	payments, _ := r.fetchPayments(ctx, orderID)
	returns, _ := r.fetchReturns(ctx, canonicalCode)
	shipments, _ := r.fetchShipments(ctx, canonicalCode)
	cogsItems, _ := r.fetchCogsItems(ctx, canonicalCode)

	return &domain.OrderDetail{
		Header:     *hdr,
		Financial:  *fin,
		LineItems:  lineItems,
		CostLedger: costs,
		CogsItems:  cogsItems,
		Payments:   payments,
		Returns:    returns,
		Shipments:  shipments,
		Channel:    *ch,
		Staff:      *staff,
		Shipping:   *ship,
		Customer:   cust,
	}, nil
}
