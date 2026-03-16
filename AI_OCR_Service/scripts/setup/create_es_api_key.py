#!/usr/bin/env python3
"""
Create Elasticsearch API Key with Proper Privileges

This script creates an API key with sufficient permissions for the MedVault application.
Must be run using the elastic superuser credentials.

Usage:
    python scripts/create_es_api_key.py --elastic-pass <password>

The script will:
1. Connect to Elasticsearch using the elastic superuser
2. Create an API key with appropriate privileges
3. Output the API key to add to .env file
"""
import argparse
import sys
import requests
import json
import base64
from typing import Optional
from urllib.parse import urljoin

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_api_key(es_host: str, elastic_user: str, elastic_pass: str, api_key_name: str = "medvault_api_key") -> Optional[dict]:
    """
    Create an API key with restricted privileges for the MedVault FastAPI backend.
    
    The API key will have privileges to:
    - Read and write documents in prescriptions* indices
    - Create new indices matching prescriptions*
    - View index metadata
    - Monitor cluster health
    """
    api_key_url = urljoin(es_host, "/_security/api_key")
    
    # Create API key with appropriate role descriptors
    # Note: Omit 'expiration' field entirely for no expiration (null not accepted)
    api_key_body = {
        "name": api_key_name,
        "role_descriptors": {
            "fastapi_role": {
                "cluster": ["monitor"],
                "indices": [
                    {
                        "names": ["prescriptions*"],
                        "privileges": ["read", "write", "create_index", "view_index_metadata"],
                        "allow_restricted_indices": False
                    }
                ],
                "applications": [],
                "run_as": [],
                "metadata": {
                    "owner": "search-module",
                    "environment": "production",
                    "service": "fastapi-backend",
                    "created_by": "kibana-ui"
                }
            }
        }
    }
    
    try:
        response = requests.post(
            api_key_url,
            auth=(elastic_user, elastic_pass),
            headers={"Content-Type": "application/json"},
            json=api_key_body,
            verify=False,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"✗ Failed to create API key: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error creating API key: {e}")
        return None


def list_existing_api_keys(es_host: str, elastic_user: str, elastic_pass: str) -> list:
    """List existing API keys."""
    api_key_url = urljoin(es_host, "/_security/api_key")
    
    try:
        response = requests.get(
            api_key_url,
            auth=(elastic_user, elastic_pass),
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("api_keys", [])
        return []
            
    except Exception as e:
        print(f"  Note: Could not list existing API keys: {e}")
        return []


def invalidate_api_key(es_host: str, elastic_user: str, elastic_pass: str, api_key_name: str) -> bool:
    """Invalidate an existing API key by name."""
    api_key_url = urljoin(es_host, "/_security/api_key")
    
    try:
        response = requests.delete(
            api_key_url,
            auth=(elastic_user, elastic_pass),
            headers={"Content-Type": "application/json"},
            json={"name": api_key_name},
            verify=False,
            timeout=30
        )
        
        return response.status_code in [200, 204]
            
    except Exception as e:
        print(f"  Note: Could not invalidate existing API key: {e}")
        return False


def test_api_key(es_host: str, api_key: str) -> bool:
    """Test the API key by connecting to Elasticsearch."""
    try:
        # Test basic connection
        info_url = urljoin(es_host, "/")
        response = requests.get(
            info_url,
            headers={"Authorization": f"ApiKey {api_key}"},
            verify=False,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ✗ API key test failed: {response.status_code}")
            return False
        
        info = response.json()
        print(f"  ✓ Connected to cluster: {info.get('cluster_name', 'unknown')}")
        print(f"  ✓ Elasticsearch version: {info.get('version', {}).get('number', 'unknown')}")
        
        # Test index access
        test_url = urljoin(es_host, "/prescriptions/_search")
        response = requests.get(
            test_url,
            headers={"Authorization": f"ApiKey {api_key}"},
            params={"size": 0},
            verify=False,
            timeout=10
        )
        
        if response.status_code in [200, 404]:
            print("  ✓ API key can access prescriptions index")
            return True
        else:
            print(f"  ✗ API key cannot access prescriptions index: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error testing API key: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Create Elasticsearch API Key for MedVault")
    parser.add_argument("--host", default="http://localhost:9200", help="Elasticsearch host URL")
    parser.add_argument("--elastic-user", default="elastic", help="Elasticsearch superuser name")
    parser.add_argument("--elastic-pass", required=True, help="Elasticsearch superuser password")
    parser.add_argument("--name", default="medvault_api_key", help="Name for the API key")
    parser.add_argument("--invalidate-existing", action="store_true", help="Invalidate existing API keys with same name")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Elasticsearch API Key Creator")
    print("=" * 60)
    print(f"\nElasticsearch Host: {args.host}")
    print(f"Elastic User: {args.elastic_user}")
    print(f"API Key Name: {args.name}")
    print()
    
    # Step 1: Optionally invalidate existing keys
    if args.invalidate_existing:
        print("Step 1: Checking for existing API keys...")
        existing_keys = list_existing_api_keys(args.host, args.elastic_user, args.elastic_pass)
        matching_keys = [k for k in existing_keys if k.get("name") == args.name]
        
        if matching_keys:
            print(f"  Found {len(matching_keys)} existing key(s) named '{args.name}'")
            if invalidate_api_key(args.host, args.elastic_user, args.elastic_pass, args.name):
                print(f"  ✓ Invalidated existing API key(s)")
            else:
                print(f"  ! Could not invalidate existing key(s)")
        else:
            print(f"  No existing keys named '{args.name}' found")
        print()
    
    # Step 2: Create new API key
    print(f"Step {'2' if args.invalidate_existing else '1'}: Creating API key...")
    result = create_api_key(args.host, args.elastic_user, args.elastic_pass, args.name)
    
    if not result:
        print("\n✗ Failed to create API key")
        sys.exit(1)
    
    api_key = result.get("api_key", "")
    api_key_id = result.get("id", "")
    encoded_key = result.get("encoded", "")
    
    if not api_key:
        # If api_key not returned, use encoded
        if encoded_key:
            api_key = encoded_key
        else:
            # Manual encoding
            to_encode = f"{api_key_id}:{result.get('api_key', '')}"
            api_key = base64.b64encode(to_encode.encode()).decode()
    
    print(f"  ✓ API key created successfully!")
    print(f"  ID: {api_key_id}")
    print()
    
    # Step 3: Test the API key
    print(f"Step {'3' if args.invalidate_existing else '2'}: Testing API key...")
    if not test_api_key(args.host, api_key):
        print("\n⚠ API key was created but test failed")
        print("  The key may have limited permissions")
    print()
    
    # Output configuration
    print("=" * 60)
    print("API Key Created Successfully!")
    print("=" * 60)
    print("\nAdd this to your .env file:")
    print("-" * 40)
    print(f'ES_API_KEY="{api_key}"')
    print("-" * 40)
    print("\nOr use the encoded key (if provided):")
    if encoded_key:
        print(f"  Encoded: {encoded_key}")
    print("\nThe API key has restricted privileges (read, write, create_index, view_index_metadata) for prescriptions* indices.")


if __name__ == "__main__":
    main()