import argparse
import json
import logging
import os
import requests
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetabaseProvisioner:
    def __init__(self, url, username, password):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.headers = {'Content-Type': 'application/json'}
        self.token = None

    def authenticate(self):
        """Authenticate with Metabase and get a session token."""
        endpoint = f"{self.url}/api/session"
        payload = {
            "username": self.username,
            "password": self.password
        }
        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            self.token = response.json().get("id")
            self.headers["X-Metabase-Session"] = self.token
            logger.info("Successfully authenticated with Metabase.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            sys.exit(1)

    def get_database_id(self, db_name):
        """Find database ID by name."""
        endpoint = f"{self.url}/api/database"
        try:
            response = self.session.get(endpoint, headers=self.headers)
            response.raise_for_status()
            databases = response.json()
            for db in databases:
                if db['name'] == db_name:
                    return db['id']
            logger.error(f"Database '{db_name}' not found.")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch databases: {e}")
            return None

    def create_card(self, card_def, db_id):
        """Create a new question (card)."""
        endpoint = f"{self.url}/api/card"
        
        # Inject database ID into the query
        if 'dataset_query' in card_def and 'database' in card_def['dataset_query']:
             # If strictly null in JSON, we use the resolved db_id
             if card_def['dataset_query']['database'] is None:
                 card_def['dataset_query']['database'] = db_id
        
        payload = {
            "name": card_def.get("name"),
            "display": card_def.get("display", "table"),
            "dataset_query": card_def.get("dataset_query"),
            "visualization_settings": card_def.get("visualization_settings", {}),
            "collection_id": card_def.get("collection_id", None) # Default to root if None
        }

        try:
            response = self.session.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            card = response.json()
            logger.info(f"Created card: {card['name']} (ID: {card['id']})")
            return card['id']
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create card '{card_def.get('name')}': {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def create_dashboard(self, dash_def):
        """Create a new dashboard."""
        endpoint = f"{self.url}/api/dashboard"
        payload = {
            "name": dash_def.get("name"),
            "description": dash_def.get("description", ""),
            "collection_id": dash_def.get("collection_id", None)
        }
        
        try:
            response = self.session.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            dashboard = response.json()
            logger.info(f"Created dashboard: {dashboard['name']} (ID: {dashboard['id']})")
            return dashboard['id']
        except requests.exceptions.RequestException as e:
             logger.error(f"Failed to create dashboard '{dash_def.get('name')}': {e}")
             return None

    def add_card_to_dashboard(self, dashboard_id, card_id, position):
        """Add a card to a dashboard at a specific position."""
        endpoint = f"{self.url}/api/dashboard/{dashboard_id}/cards"
        payload = {
            "cardId": card_id,
            "size_x": position.get("size_x", 4),
            "size_y": position.get("size_y", 4),
            "col": position.get("col", 0),
            "row": position.get("row", 0)
        }
        
        try:
            response = self.session.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Added card {card_id} to dashboard {dashboard_id}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add card {card_id} to dashboard {dashboard_id}: {e}")

    def provision(self, config_path, db_name_override=None):
        logger.info(f"Reading configuration from {config_path}")
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.authenticate()

        # Resolve Database ID
        # In a real scenario, we might want to specify which DB to run queries against
        # For now, let's assume valid DB name is passed or defined
        db_id = None
        if db_name_override:
            db_id = self.get_database_id(db_name_override)
            if not db_id:
                logger.error("Could not resolve database ID. Aborting.")
                return

        # 1. Create Dashboard Shell
        dash_config = config.get("dashboard")
        dashboard_id = self.create_dashboard(dash_config)
        if not dashboard_id:
            logger.error("Failed to create dashboard. Aborting.")
            return

        # 2. Create Cards and add to Dashboard
        cards_config = config.get("cards", [])
        for card_def in cards_config:
            # Create the card first
            card_id = self.create_card(card_def, db_id)
            if card_id:
                # Add to dashboard
                position = card_def.get("position", {})
                self.add_card_to_dashboard(dashboard_id, card_id, position)

        logger.info(f"Dashboard '{dash_config['name']}' provisioned successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision Metabase Config")
    parser.add_argument("--config", required=True, help="Path to dashboard JSON config")
    parser.add_argument("--url", default=os.environ.get("METABASE_URL"), help="Metabase URL")
    parser.add_argument("--user", default=os.environ.get("METABASE_USER"), help="Metabase Username")
    parser.add_argument("--password", default=os.environ.get("METABASE_PASSWORD"), help="Metabase Password")
    parser.add_argument("--db-name", help="Name of the database in Metabase to execute queries against")

    args = parser.parse_args()

    if not all([args.url, args.user, args.password]):
        logger.error("Metabase URL, User, and Password are required (via args or env vars).")
        sys.exit(1)

    provisioner = MetabaseProvisioner(args.url, args.user, args.password)
    provisioner.provision(args.config, args.db_name)
