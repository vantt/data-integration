// Process single webhook
/*
async function processWebhook(message: any): Promise<boolean> {
    const webhook = message.message
    const client = await localPool.connect()
    
    try {
      await client.query('BEGIN')
  
      // Store in local database
      await client.query(
        `INSERT INTO webhook_logs (
          id, entity_type, entity_id, action, action_group,
          source_system, source_timestamp, payload, payload_hash, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        [
          webhook.id,
          webhook.entity_type,
          webhook.entity_id,
          webhook.action,
          webhook.action_group,
          webhook.source_system,
          webhook.source_timestamp,
          webhook.payload,
          webhook.payload_hash,
          webhook.created_at,
        ]
      )
  
      // Mark message as completed
      const { data, error: completeError } = await supabase
        .rpc('complete_message', {
          p_message_id: message.id,
          p_consumer_name: config.puller.consumerId
        })
  
      if (completeError) throw completeError
  
      await client.query('COMMIT')
      return true
    } catch (error) {
      await client.query('ROLLBACK')
      console.error(`Error processing webhook ${webhook.id}:`, error)
  
      // Release message back to queue with delay
      await supabase.rpc('release_message', {
        p_message_id: message.id,
        p_consumer_name: config.puller.consumerId,
        p_delay: '5 minutes'
      })
  
      return false
    } finally {
      client.release()
    }
  }
    */