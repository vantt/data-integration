import requests
import os
import time

class CloudflareWorkerClient:
    def __init__(self, worker_url: str):
        self.worker_url = worker_url.rstrip('/')

    def poll_messages(self, source_system: str = None, limit: int = 100) -> list:
        """
        Polls for new messages from the worker.
        """
        params = {'limit': limit}
        if source_system:
            params['source_system'] = source_system
        
        url = f"{self.worker_url}/poll"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('messages', [])
        except requests.exceptions.RequestException as e:
            print(f"Error polling messages: {e}")
            if e.response:
                print(f"Response: {e.response.text}")
            return []

    def batch_ack(self, message_ids: list):
        """
        Acknowledges a batch of messages, deleting them from the source.
        """
        if not message_ids:
            return

        url = f"{self.worker_url}/ack-batch"
        try:
            response = requests.post(url, json={'ids': message_ids})
            response.raise_for_status()
            print(f"Successfully acknowledged {len(message_ids)} messages.")
        except requests.exceptions.RequestException as e:
            print(f"Error acknowledging messages: {e}")
            if e.response:
                print(f"Response: {e.response.text}")

    def release(self, message_id: str):
        """
        Releases a message back to the queue (NACK).
        """
        url = f"{self.worker_url}/release"
        try:
            response = requests.post(url, json={'id': message_id})
            response.raise_for_status()
            print(f"Released message {message_id}")
        except requests.exceptions.RequestException as e:
             print(f"Error releasing message {message_id}: {e}")

