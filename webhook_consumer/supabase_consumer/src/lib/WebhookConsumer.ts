import { SupabaseClient } from '@supabase/supabase-js';
import { QueueMessage } from '../types';
import { WebhookStorage, InsertWebhookResult } from './WebhookStorage.js';

export class WebhookConsumer {
    private running = false;
    private pollInterval = 5000; // 5 second
    private batchSize = 20;
    private webhookStorage: WebhookStorage;
    private supabaseClient: SupabaseClient;

    constructor(webhookStorage: WebhookStorage, supabaseClient: SupabaseClient) {
        this.webhookStorage = webhookStorage;
        this.supabaseClient = supabaseClient;
    }

    async processWebhook(message: QueueMessage) {
        // console.log(message);  
        try {
            const webhookRecord = this.webhookStorage.createWebhookRecord(message);
            const result: InsertWebhookResult = await this.webhookStorage.insertWebhook(webhookRecord);

            // Delete from queue after successful processing
            await this.supabaseClient.rpc('delete_message', {
                queue_name: 'webhook_queue',
                msg_id: message.msg_id
            });

            if (!result.isDuplicate) {
                console.log(`Successful processe message: ${message.msg_id}`);
            }
            else if (result.isDuplicate) { 
                console.error(`Duplicated message: ${message.msg_id}`);
            }
            
        }
        catch (err: any) {

            // Return message to queue if processing failed
            await this.supabaseClient.rpc('release_message', {
                queue_name: 'webhook_queue',
                msg_id: message.msg_id
            });

            console.error(`Error processing message ${message.msg_id}:`, err);
        }
    }

    async start() {
        await this.webhookStorage.initialize();

        this.running = true;
        console.log('Starting consume webhook...');

        while (this.running) {
            try {
                // Read messages from queue
                const { data, error } = await this.supabaseClient.rpc('read_queue', {
                    queue_name: 'webhook_queue',
                    max_count: this.batchSize
                });

                if (error) throw error;

                if (data && data.length > 0) {
                    console.log(`Processing ${data.length} messages`);

                    // Process each message
                    for (const msg of data as QueueMessage[]) {
                        await this.processWebhook(msg)
                    }
                }

                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, this.pollInterval));
            }
            catch (err: any) {
                console.error('Consumer error:', err);

                // Wait longer on error
                await new Promise(resolve => setTimeout(resolve, this.pollInterval * 5));
            }
        }
    }

    stop() {
        this.running = false;
        console.log('Stopping webhook consumer...');
    }
}