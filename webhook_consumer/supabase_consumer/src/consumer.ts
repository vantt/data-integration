// src/consumer.ts
import { createClient } from '@supabase/supabase-js';
import { WebhookStorage } from './lib/WebhookStorage.js';
import { WebhookConsumer } from './lib/WebhookConsumer.js';
import dotenv from 'dotenv';

/**
 * 
 * orders/create orders/update orders/cancelled orders/finalized orders/fulfilled orders/paid orders/received
 * orders/create_return orders/receive_return orders/create_refund
 * customers/create customers/update customers/delete
 * 
 */

// Initialize environment variables
dotenv.config();


// Main function
async function main() {
    try {
        //await setupLocalDb();
        const webhookStorage = new WebhookStorage({
            host: process.env.POSTGRESQL_HOST || 'localhost',
            port: 5432,
            database: 'data_lake',
            user: 'postgres',
            password: '123456'
        });

        const supabaseClient = createClient(
            process.env.SUPABASE_URL ?? '',
            process.env.SUPABASE_SERVICE_ROLE_KEY ?? ''
        );

        const consumer = new WebhookConsumer(webhookStorage, supabaseClient);

        // Handle shutdown gracefully
        process.on('SIGINT', () => {
            console.log('Received SIGINT. Shutting down...');
            consumer.stop();
        });

        process.on('SIGTERM', () => {
            console.log('Received SIGTERM. Shutting down...');
            consumer.stop();
        });

        await consumer.start();
    } catch (err) {
        console.error('Fatal error:', err);
        process.exit(1);
    }
}

// Start the consumer
main().catch(console.error);