#!/usr/bin/env python3
"""
Elasticsearch User Setup Script

This script creates the medvault_app user with appropriate roles for the 
prescription search functionality. Must be run after Elasticsearch is started
and the elastic superuser password is set.

Usage:
    python setup_es_user.py --host http://localhost:9200 --elastic-user elastic --elastic-pass <password>

The script will:
1. Connect to Elasticsearch using the elastic superuser
2. Create a custom role 'medvault_app_role' with limited permissions
3. Create the 'medvault_app' user with the custom role
4. Test the connection with the new user
"""
import argparse
import sys
import requests
import json
from urllib.parse import urljoin
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def create_custom_role(es_host: str, elastic_user: str, elastic_pass: str) -> bool:
    """Create a custom role with limited permissions for the medvault_app user."""
    role_url = urljoin(es_host, "/_security/role/medvault_app_role")
    
    role_body = {
        "cluster": ["monitor"],
        "indices": [
            {
                "names": ["prescriptions", "prescriptions_*"],
                "privileges": ["create", "read", "write", "delete", "create_index", "view_index_metadata"],
                "field_security": {"grant": ["*"]},
                "query": {"match_all": {}}
            }
        ],
        "applications": [],
        "run_as": [],
        "metadata": {
            "description": "Custom role for MedVault application with limited permissions"
        }
    }
    
    try:
        response = requests.put(
            role_url,
            auth=(elastic_user, elastic_pass),
            headers={"Content-Type": "application/json"},
            json=role_body,
            verify=False
        )
        
        if response.status_code in [200, 201]:
            print("✓ Custom role 'medvault_app_role' created successfully")
            return True
        else:
            print(f"✗ Failed to create role: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error creating role: {e}")
        return False


def create_medvault_user(es_host: str, elastic_user: str, elastic_pass: str, app_pass: str) -> bool:
    """Create the medvault_app user with the custom role."""
    user_url = urljoin(es_host, "/_security/user/medvault_app")
    
    user_body = {
        "password": app_pass,
        "roles": ["medvault_app_role"],
        "full_name": "MedVault Application User",
        "email": "app@medvault.local",
        "metadata": {
            "description": "Application user for MedVault prescription search service"
        }
    }
    
    try:
        response = requests.post(
            user_url,
            auth=(elastic_user, elastic_pass),
            headers={"Content-Type": "application/json"},
            json=user_body,
            verify=False
        )
        
        if response.status_code in [200, 201]:
            print("✓ User 'medvault_app' created successfully")
            return True
        else:
            print(f"✗ Failed to create user: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return False


def test_medvault_user(es_host: str, app_pass: str) -> bool:
    """Test the connection with the new medvault_app user."""
    try:
        # Test cluster health
        health_url = urljoin(es_host, "/_cluster/health")
        response = requests.get(
            health_url,
            auth=("medvault_app", app_pass),
            verify=False
        )
        
        if response.status_code == 200:
            print("✓ medvault_app user can access cluster health")
        else:
            print(f"✗ medvault_app user cannot access cluster health: {response.status_code}")
            return False
        
        # Test index creation
        test_index_url = urljoin(es_host, "/test_medvault_connection")
        response = requests.put(
            test_index_url,
            auth=("medvault_app", app_pass),
            headers={"Content-Type": "application/json"},
            json={"settings": {"number_of_shards": 1}},
            verify=False
        )
        
        if response.status_code in [200, 201]:
            print("✓ medvault_app user can create indices")
            # Clean up test index
            requests.delete(test_index_url, auth=("medvault_app", app_pass), verify=False)
        else:
            print(f"✗ medvault_app user cannot create indices: {response.status_code}")
            return False
        
        # Test prescriptions index operations
        prescriptions_url = urljoin(es_host, "/prescriptions")
        response = requests.get(
            prescriptions_url,
            auth=("medvault_app", app_pass),
            verify=False
        )
        
        # 404 is fine (index doesn't exist yet), 200 means it exists
        if response.status_code in [200, 404]:
            print("✓ medvault_app user can access prescriptions index")
        else:
            print(f"✗ medvault_app user cannot access prescriptions index: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing user: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup Elasticsearch user for MedVault")
    parser.add_argument("--host", default="http://localhost:9200", help="Elasticsearch host URL")
    parser.add_argument("--elastic-user", default="elastic", help="Elasticsearch superuser name")
    parser.add_argument("--elastic-pass", required=True, help="Elasticsearch superuser password")
    parser.add_argument("--app-pass", default="StrongPassword123!", help="Password for medvault_app user")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MedVault Elasticsearch User Setup")
    print("=" * 60)
    print(f"\nElasticsearch Host: {args.host}")
    print(f"Elastic User: {args.elastic_user}")
    print(f"App User Password: {'*' * len(args.app_pass)}")
    print()
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Step 1: Create custom role
    print("Step 1: Creating custom role 'medvault_app_role'...")
    if not create_custom_role(args.host, args.elastic_user, args.elastic_pass):
        print("\n✗ Role creation failed. Aborting.")
        sys.exit(1)
    
    # Step 2: Create medvault_app user
    print("\nStep 2: Creating user 'medvault_app'...")
    if not create_medvault_user(args.host, args.elastic_user, args.elastic_pass, args.app_pass):
        print("\n✗ User creation failed. Aborting.")
        sys.exit(1)
    
    # Step 3: Test the new user
    print("\nStep 3: Testing medvault_app user permissions...")
    if not test_medvault_user(args.host, args.app_pass):
        print("\n✗ User permission test failed.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    print("\nYou can now use these credentials in your .env file:")
    print(f"  ES_PASS={args.app_pass}")
    print("\nTest the connection with:")
    print(f"  python tests/test_es_connection.py")
    print()


if __name__ == "__main__":
    main()