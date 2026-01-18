// Action groups for each entity
type OrderActionGroup = 'crud' | 'status' | 'financial' | 'workflow' | 'lifecycle';
type CustomerActionGroup = 'crud' | 'status' | 'security' | 'financial' | 'lifecycle';
type ShipmentActionGroup = 'crud' | 'status' | 'workflow' | 'lifecycle';
type PaymentActionGroup = 'crud' | 'status' | 'financial' | 'security';
type ProductActionGroup = 'crud' | 'status' | 'inventory' | 'pricing' | 'catalog';
type TimestampWithTimezone = string; // ISO 8601 format, e.g. "2024-11-17T14:20:00Z"

// Entity-specific action types
type OrderAction =
  // CRUD operations
  | 'order.created' | 'order.updated' | 'order.deleted'
  // Status changes
  | 'order.pending' | 'order.confirmed' | 'order.processing' | 'order.ready_to_ship'
  | 'order.completed' | 'order.on_hold' | 'order.cancelled'
  // Financial events
  | 'order.paid' | 'order.payment_failed' | 'order.refunded' | 'order.partially_refunded'
  | 'order.payment_disputed'
  // Workflow events
  | 'order.split' | 'order.merged' | 'order.assigned' | 'order.flagged_fraud'
  | 'order.unflagged_fraud'
  // Lifecycle events
  | 'order.expired' | 'order.archived' | 'order.restored';

type CustomerAction =
  // CRUD operations
  | 'customer.created' | 'customer.updated' | 'customer.deleted'
  // Status changes
  | 'customer.activated' | 'customer.suspended' | 'customer.blocked'
  // Security events
  | 'customer.password_changed' | 'customer.mfa_enabled' | 'customer.mfa_disabled'
  | 'customer.login_failed' | 'customer.locked_out'
  // Financial events
  | 'customer.credit_added' | 'customer.credit_used' | 'customer.tier_changed'
  | 'customer.payment_method_added' | 'customer.payment_method_removed'
  // Lifecycle events
  | 'customer.converted' | 'customer.churned' | 'customer.reactivated' | 'customer.merged';

type ShipmentAction =
  // CRUD operations
  | 'shipment.created' | 'shipment.updated' | 'shipment.deleted'
  // Status changes
  | 'shipment.pending' | 'shipment.label_created' | 'shipment.picked_up'
  | 'shipment.in_transit' | 'shipment.out_for_delivery' | 'shipment.delivered'
  | 'shipment.failed_delivery' | 'shipment.exception'
  // Workflow events
  | 'shipment.carrier_assigned' | 'shipment.route_optimized' | 'shipment.rescheduled'
  | 'shipment.split' | 'shipment.merged'
  // Lifecycle events
  | 'shipment.lost' | 'shipment.damaged' | 'shipment.cancelled'
  | 'shipment.returned_to_sender';

type PaymentAction =
  // CRUD operations
  | 'payment.created' | 'payment.updated' | 'payment.deleted'
  // Status changes
  | 'payment.pending' | 'payment.authorized' | 'payment.captured' | 'payment.failed'
  | 'payment.declined' | 'payment.refunded' | 'payment.partially_refunded'
  | 'payment.voided'
  // Financial events
  | 'payment.settlement_completed' | 'payment.fee_assessed'
  | 'payment.currency_converted' | 'payment.tax_calculated'
  // Security events
  | 'payment.fraud_detected' | 'payment.verification_required'
  | 'payment.verified' | 'payment.risk_assessed';

type ProductAction =
  // CRUD operations
  | 'product.created' | 'product.updated' | 'product.deleted'
  // Status changes
  | 'product.draft' | 'product.published' | 'product.unpublished'
  | 'product.archived' | 'product.discontinued'
  // Inventory events
  | 'product.stock_updated' | 'product.low_stock' | 'product.out_of_stock'
  | 'product.back_in_stock' | 'product.reserved' | 'product.released'
  // Pricing events
  | 'product.price_updated' | 'product.sale_started' | 'product.sale_ended'
  | 'product.bulk_price_updated' | 'product.tax_changed'
  // Catalog events
  | 'product.categorized' | 'product.uncategorized' | 'product.featured'
  | 'product.unfeatured' | 'product.variant_added' | 'product.variant_removed';

// Combined action type
type WebhookAction = OrderAction | CustomerAction | ShipmentAction | PaymentAction | ProductAction;

// Combined action group type
type ActionGroup = OrderActionGroup | CustomerActionGroup | ShipmentActionGroup | PaymentActionGroup | ProductActionGroup;

// Processing status types
type WebhookStatus = 'received' | 'validated' | 'processing' | 'completed' | 'failed';
type ProcessingPriority = 'high' | 'medium' | 'low';
type ValidationStatus = 'valid' | 'invalid';
type Environment = 'production' | 'staging' | 'development';

// Entity types
type EntityType = 'order' | 'customer' | 'shipment' | 'payment' | 'product';
type SourceSystem = 'sapo' | 'shopee' | 'fb' | 'tiktok' | 'lazada' | 'gads';

// Related entity type
interface RelatedEntity {
  entity_type: EntityType;
  entity_id: string;
  relationship: string;
}

// Parent entity type
interface ParentEntity {
  entity_type: EntityType;
  entity_id: string;
}

// Processing history entry type
interface ProcessingHistoryEntry {
  timestamp: TimestampWithTimezone;
  status: string;
  error?: string;
  notes?: string;
}

// Client information type
interface ClientInfo {
  ip: string;
  user_agent: string;
  geo_location?: string;
}

// Types and Interfaces
interface WebhookPayload {
  entity_type: EntityType;
  action: string;
  source_system: SourceSystem;
  payload: Record<string, unknown>;
}

// Main WebhookDocument interface
interface WebhookRecord extends WebhookPayload {
  // Standard CouchDB fields
  _id: string;
  //   _rev?: string;
  //   type: 'webhook_log';

  // Entity Classification
  entity_type: EntityType;
  entity_id: string;

  // Action Classification
  action: string; //WebhookAction;
  action_group: string; //ActionGroup;

  // Source Context
  source_system: SourceSystem;
  source_timestamp: TimestampWithTimezone;
  //source_version?: string;

  // Webhook Data
  payload: Record<string, unknown>;
  //   raw_request: {
  //     headers: Record<string, string>;
  //     body: unknown;
  //   };

  // Processing Metadata
  status: WebhookStatus;
  processing_priority: ProcessingPriority;
  retry_count: number;
  next_retry_at?: TimestampWithTimezone;
  processing_history?: ProcessingHistoryEntry[];

  // Validation & Schema
  //   schema_version: string;
  //   validation_status: ValidationStatus;
  payload_hash: string;

  // Business Context
  //   tenant_id: string;
  //   environment: Environment;
  //   business_unit?: string;

  // Related Entities
  //   related_entities?: RelatedEntity[];
  //   parent_entity?: ParentEntity;

  // Reception Metadata
  created_at?: TimestampWithTimezone;
  updated_at?: TimestampWithTimezone;
  // received_by: string;
  //   client_info: ClientInfo;
}

// Type guard functions
function isOrderAction(action: WebhookAction): action is OrderAction {
  return action.startsWith('order.');
}

function isCustomerAction(action: WebhookAction): action is CustomerAction {
  return action.startsWith('customer.');
}

function isShipmentAction(action: WebhookAction): action is ShipmentAction {
  return action.startsWith('shipment.');
}

function isPaymentAction(action: WebhookAction): action is PaymentAction {
  return action.startsWith('payment.');
}

function isProductAction(action: WebhookAction): action is ProductAction {
  return action.startsWith('product.');
}

export type {
  WebhookPayload,
  WebhookRecord,
  WebhookAction,
  OrderAction,
  CustomerAction,
  ShipmentAction,
  PaymentAction,
  ProductAction,
  ActionGroup,
  OrderActionGroup,
  CustomerActionGroup,
  ShipmentActionGroup,
  PaymentActionGroup,
  ProductActionGroup,
  WebhookStatus,
  ProcessingPriority,
  ValidationStatus,
  Environment,
  EntityType,
  RelatedEntity,
  ParentEntity,
  ProcessingHistoryEntry,
  ClientInfo
};

export {
  isOrderAction,
  isCustomerAction,
  isShipmentAction,
  isPaymentAction,
  isProductAction
};