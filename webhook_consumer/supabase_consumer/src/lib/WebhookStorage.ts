import crypto from 'crypto';
import { WebhookPayload, WebhookRecord } from '../types/webhook';
import { QueueMessage } from '../types';
import pkg from 'pg';

const DOING_SCHEMA_INITIALIZE = false;

const createTableSQL = `
    CREATE TABLE IF NOT EXISTS webhook_logs (

        -- Standard ID fields
        _id TEXT primary key,
        
        -- Entity Classification
        entity_type TEXT NOT NULL CHECK (entity_type IN ('order', 'customer', 'shipment', 'product', 'payment')),
        entity_id TEXT NOT NULL,                

        -- Action Classification
        action_group TEXT NOT NULL CHECK (action_group IN ('crud', 'status', 'lifecycle', 'system', 'financial', 'security', 'ownership', 'workflow')),
        action TEXT not null,

        -- Source Context
        source_system TEXT not null CHECK (source_system IN ('sapo', 'smaxai', 'shopee', 'fb', 'gads', 'tiktok')),
        source_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

        -- Webhook Data
        payload_hash TEXT NOT NULL,
        payload JSONB NOT NULL,
        
        -- Processing Metadata
        status TEXT NOT NULL CHECK (status IN ('received', 'validated', 'processing', 'completed', 'failed')),                
        processing_priority TEXT NOT NULL DEFAULT 'medium' CHECK (processing_priority IN ('high', 'medium', 'low')),
        retry_count INTEGER NOT NULL DEFAULT 0,
        next_retry_at TIMESTAMP WITH TIME ZONE,
        processing_history JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for common query patterns
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_entity ON webhook_logs (entity_type, entity_id);
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_action ON webhook_logs (action_group, action);
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_status ON webhook_logs (status, processing_priority);
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_payload_hash ON webhook_logs USING hash (payload_hash);    
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_timestamps ON webhook_logs (source_timestamp, created_at);
    CREATE INDEX IF NOT EXISTS idx_webhook_logs_payload_hash_created_at (payload_hash, created_at);
    

    -- Timestamp trigger for updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    CREATE OR REPLACE TRIGGER update_webhook_logs_updated_at
        BEFORE UPDATE ON webhook_logs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
`
const { Pool } = pkg;

export interface InsertWebhookResult extends WebhookRecord {
    isDuplicate?: boolean;
}

// WebhookStorage class for managing webhook data
export class WebhookStorage {
    private pool;
    private initialized: boolean = (!DOING_SCHEMA_INITIALIZE);

    constructor(connectionConfig: {
        host: string;
        port: number;
        database: string;
        user: string;
        password: string;
    }) {
        this.pool = new Pool({
            ...connectionConfig,
            max: 20, // Maximum number of clients in pool
            idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
            connectionTimeoutMillis: 2000, // Return an error after 2 seconds if connection not established
        });
    }

    /**
     * Initialize the database schema
     */
    async initialize(): Promise<void> {
        if (this.initialized) return;

        console.log('Starting initializae DB Schema...');
        const client = await this.pool.connect();

        try {
            await client.query(createTableSQL);
            this.initialized = true;
        } finally {
            client.release();
        }
    }

    /**
     * Generate a hash of the webhook payload for idempotency checking
     */
    private generatePayloadHash(payload: Record<string, unknown>): string {
        const sortedPayload = JSON.stringify(payload, Object.keys(payload).sort());
        return crypto.createHash('sha256').update(sortedPayload).digest('hex');
    }

    createWebhookRecord(queueMessage: QueueMessage): WebhookRecord {
        const webhook = queueMessage.msg;

        // Generate payload hash for idempotency checking
        const payloadHash = this.generatePayloadHash(webhook.payload);

        // Determine processing priority based on action group
        const processingPriority = this.determineProcessingPriority(webhook);

        // Current timestamp for record creation
        const now = new Date();

        return {
            // Include all fields from the original payload

            ...webhook,

            _id: queueMessage.msg_id.toString(),
            entity_id: webhook.payload.id as string,


            // Add system-generated fields      
            action_group: 'crud',
            source_timestamp: queueMessage.enqueued_at,
            status: 'received',
            processing_priority: processingPriority,
            retry_count: 0,
            processing_history: [
                {
                    timestamp: now.toISOString(),
                    status: 'received',
                    notes: 'Initial webhook reception'
                }
            ],
            payload_hash: payloadHash,
        };
    }

    /**
     * Store a new webhook in the database
     */
    async insertWebhook(webhook: WebhookRecord): Promise<InsertWebhookResult> {
        const client = await this.pool.connect();
        try {
            // Start transaction
            await client.query('BEGIN');

            // Acquire advisory lock to prevent concurrent inserts
            await client.query('SELECT pg_advisory_xact_lock(hashtext($1))', [webhook.payload_hash]);

            // Check for duplicates in webhook_logs within the last 24 hours
            const duplicateCheck = await client.query(
                'SELECT 1 FROM webhook_logs WHERE payload_hash = $1 AND created_at > NOW() - INTERVAL \'24 hours\' LIMIT 1',
                [webhook.payload_hash]
            );

            if (duplicateCheck.rows.length > 0) {
                // Duplicate found: insert into webhook_logs_duplicated
                const duplicateInsert = await client.query(
                    `INSERT INTO webhook_logs_duplicated (
                        webhook_id, entity_type, entity_id, action, action_group,
                        source_system, source_timestamp, 
                        payload_hash, payload,
                        processing_priority, processing_history, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING *`,
                    [
                        webhook._id,
                        webhook.entity_type,
                        webhook.entity_id,
                        webhook.action,
                        webhook.action_group,
                        webhook.source_system,
                        webhook.source_timestamp,
                        webhook.payload_hash,
                        JSON.stringify(webhook.payload),
                        webhook.processing_priority,
                        JSON.stringify(webhook.processing_history || [{
                            timestamp: new Date().toISOString(),
                            status: 'received',
                            notes: 'Duplicate webhook detected'
                        }]),
                        webhook.status
                    ]
                );

                // Commit the transaction
                await client.query('COMMIT');

                // Return the original webhook with a duplicate flag
                return { ...webhook, isDuplicate: true };
            } else {
                // No duplicate: insert into webhook_logs
                const insertResult = await client.query(
                    `INSERT INTO webhook_logs (
                        _id, entity_type, entity_id, action, action_group,
                        source_system, source_timestamp, 
                        payload_hash, payload,
                        processing_priority, processing_history, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING *`,
                    [
                        webhook._id,
                        webhook.entity_type,
                        webhook.entity_id,
                        webhook.action,
                        webhook.action_group,
                        webhook.source_system,
                        webhook.source_timestamp,
                        webhook.payload_hash,
                        JSON.stringify(webhook.payload),
                        webhook.processing_priority,
                        JSON.stringify([{
                            timestamp: new Date().toISOString(),
                            status: 'received',
                            notes: 'Initial webhook reception'
                        }]),
                        webhook.status
                    ]
                );

                // Commit the transaction
                await client.query('COMMIT');

                // Return the inserted record
                return insertResult.rows[0] as WebhookRecord;
            }
        } catch (error: any) {
            // Roll back on error
            await client.query('ROLLBACK');
            throw error;
        } finally {
            // Release the client back to the pool
            client.release();
        }
    }

    /**
     * Determine processing priority based on webhook characteristics
     */
    private determineProcessingPriority(webhook: WebhookPayload): 'high' | 'medium' | 'low' {
        return 'medium';

        // if (webhook.action_group === 'financial' || webhook.action_group === 'security') {
        //     return 'high';
        // }
        // if (webhook.action_group === 'status' || webhook.action_group === 'workflow') {
        //     return 'medium';
        // }
        // return 'low';
    }

    /**
     * Update webhook processing status
     */
    async updateWebhookStatus(id: string, status: WebhookRecord['status'], error?: string): Promise<void> {
        const client = await this.pool.connect();
        try {
            await client.query('BEGIN');

            const webhook = await client.query(
                'SELECT processing_history, retry_count FROM webhook_logs WHERE _id = $1',
                [id]
            );

            if (webhook.rows.length === 0) {
                throw new Error('Webhook not found');
            }

            const processingHistory = [
                ...webhook.rows[0].processing_history,
                {
                    timestamp: new Date(),
                    status,
                    ...(error && { error })
                }
            ];

            const nextRetryAt = status === 'failed'
                ? new Date(Date.now() + Math.pow(2, webhook.rows[0].retry_count) * 1000 * 60) // Exponential backoff
                : null;

            await client.query(
                `UPDATE webhook_logs 
           SET status = $1, 
               processing_history = $2,
               retry_count = CASE WHEN $1 = 'failed' THEN retry_count + 1 ELSE retry_count END,
               next_retry_at = $3
           WHERE id = $4`,
                [status, JSON.stringify(processingHistory), nextRetryAt, id]
            );

            await client.query('COMMIT');
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    }

    /**
     * Find webhooks ready for processing
     */
    async findWebhooksForProcessing(limit: number = 10): Promise<WebhookRecord[]> {
        const result = await this.pool.query(
            `SELECT * FROM webhook_logs 
         WHERE (status = 'received' OR (status = 'failed' AND next_retry_at <= NOW()))
         ORDER BY 
           CASE processing_priority 
             WHEN 'high' THEN 1 
             WHEN 'medium' THEN 2 
             WHEN 'low' THEN 3 
           END,
           created_at ASC
         LIMIT $1`,
            [limit]
        );
        return result.rows as WebhookRecord[];
    }

    /**
     * Query webhooks by entity
     */
    async queryWebhooksByEntity(entityType: WebhookPayload['entity_type'], entityId: string, options: { startDate?: Date; endDate?: Date; status?: WebhookRecord['status']; limit?: number; } = {}): Promise<WebhookRecord[]> {
        const params: any[] = [entityType, entityId];
        let query = 'SELECT * FROM webhook_logs WHERE entity_type = $1 AND entity_id = $2';

        if (options.startDate) {
            params.push(options.startDate);
            query += ` AND source_timestamp >= $${params.length}`;
        }

        if (options.endDate) {
            params.push(options.endDate);
            query += ` AND source_timestamp <= $${params.length}`;
        }

        if (options.status) {
            params.push(options.status);
            query += ` AND status = $${params.length}`;
        }

        query += ' ORDER BY source_timestamp DESC';

        if (options.limit) {
            params.push(options.limit);
            query += ` LIMIT $${params.length}`;
        }

        const result = await this.pool.query(query, params);
        return result.rows as WebhookRecord[];
    }

    /**
     * Clean up old webhook records
     */
    // async cleanupOldWebhooks(daysToRetain: number): Promise<number> {
    //     const result = await this.pool.query(
    //         `DELETE FROM webhook_logs 
    //      WHERE created_at < NOW() - INTERVAL '1 day' * $1 
    //      AND status IN ('completed', 'failed')
    //      RETURNING id`,
    //         [daysToRetain]
    //     );
    //     return result.rowCount;
    // }

    /**
     * Close the database connection pool
     */
    async close(): Promise<void> {
        await this.pool.end();
    }
}