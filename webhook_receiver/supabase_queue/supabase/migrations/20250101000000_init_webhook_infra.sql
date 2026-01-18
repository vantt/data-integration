-- Enable PGMQ extension
create extension if not exists pgmq;

-- Create the webhook queue
select pgmq.create_queue('webhook_queue');

-- Create function to insert into queue
create or replace function queue_webhook(webhook_data jsonb)
returns void as $$
begin
  perform pgmq.send(
    queue_name => 'webhook_queue',
    msg => webhook_data
  );
end;
$$ language plpgsql security definer;

-- Grant access to queue_webhook
grant execute on function queue_webhook to service_role;

-- Function to read from queue
create or replace function read_queue(queue_name text, max_count int)
returns table (msg_id bigint, msg jsonb, enqueued_at timestamp) as $$
begin
  return query select r.msg_id, r.msg, r.enqueued_at 
  from pgmq.read(
    queue_name => queue_name,
    vt         => 60,
    qty        => max_count
  ) r;
end;
$$ language plpgsql security definer;

-- Function to delete message
create or replace function delete_message(queue_name text, msg_id bigint)
returns void as $$
begin
  perform pgmq.delete(
    queue_name => queue_name,
    msg_id => msg_id
  );
end;
$$ language plpgsql security definer;

-- Function to release message
create or replace function release_message(queue_name text, msg_id bigint)
returns void as $$
begin
  perform pgmq.release(
    queue_name => queue_name,
    msg_id => msg_id
  );
end;
$$ language plpgsql security definer;

-- Grant access to the helper functions
grant execute on function read_queue to service_role;
grant execute on function delete_message to service_role;
grant execute on function release_message to service_role;
