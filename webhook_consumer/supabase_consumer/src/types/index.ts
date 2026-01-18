import { WebhookPayload } from './webhook';

interface QueueMessage {
    msg_id: BigInt;
    msg: WebhookPayload;
    enqueued_at: string;
}

type QueueMessages = QueueMessage[];

export type {
  QueueMessage, 
  QueueMessages,
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
  } from './webhook';
  
  export {
    isOrderAction,
    isCustomerAction,
    isShipmentAction,
    isPaymentAction,
    isProductAction
  } from './webhook';